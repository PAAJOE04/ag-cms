"""AI assistant service using OpenAI API."""
import json
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models.member import Member
from app.models.attendance import Attendance, AttendanceType
from app.models.finance import Transaction
from app.models.department import Department, DepartmentMember
from app.models.event import Event


class AIService:
    """Church AI assistant powered by OpenAI."""

    def __init__(self):
        self.api_key = current_app.config.get('OPENAI_API_KEY', '')
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    def _gather_context(self):
        """Gather church data context for AI queries."""
        today = datetime.utcnow().date()
        year_start = today.replace(month=1, day=1)

        total_members = Member.query.filter_by(
            membership_status='active', is_visitor=False
        ).count()
        new_members = Member.query.filter(
            Member.membership_date >= year_start,
            Member.is_visitor == False  # noqa: E712
        ).count()

        month_start = today.replace(day=1)
        income = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.type == 'income',
            Transaction.transaction_date >= month_start
        ).scalar() or 0

        expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.type == 'expense',
            Transaction.transaction_date >= month_start
        ).scalar() or 0

        upcoming_events = Event.query.filter(
            Event.start_date >= datetime.utcnow(),
            Event.status == 'upcoming'
        ).count()

        birthdays = Member.query.filter(
            func.extract('month', Member.date_of_birth) == today.month,
            Member.membership_status == 'active'
        ).count()

        return {
            'total_members': total_members,
            'new_members_this_year': new_members,
            'monthly_income': float(income),
            'monthly_expenses': float(expenses),
            'upcoming_events': upcoming_events,
            'birthdays_this_month': birthdays,
            'report_date': today.isoformat(),
        }

    def query(self, question):
        """Process a natural language query."""
        context = self._gather_context()

        # Try local handlers first for common queries
        local_response = self._local_query_handler(question.lower(), context)
        if local_response:
            return local_response

        if not self.client:
            return self._fallback_response(question, context)

        try:
            response = self.client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are an AI assistant for a church management system. '
                            'Answer questions based on the provided church data context. '
                            'Be helpful, concise, and pastoral in tone. '
                            f'Context: {json.dumps(context)}'
                        ),
                    },
                    {'role': 'user', 'content': question},
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            current_app.logger.error(f'AI query error: {e}')
            return self._fallback_response(question, context)

    def _local_query_handler(self, question, context):
        """Handle common queries without API call."""
        if 'new member' in question and 'year' in question:
            return (
                f"This year, {context['new_members_this_year']} new members "
                f"have joined the church. Total active members: {context['total_members']}."
            )

        if 'birthday' in question and 'month' in question:
            members = Member.query.filter(
                func.extract('month', Member.date_of_birth) == datetime.utcnow().month,
                Member.membership_status == 'active'
            ).all()
            if not members:
                return 'No birthdays this month.'
            names = ', '.join(f'{m.full_name} ({m.date_of_birth.strftime("%b %d")})'
                              for m in members[:10] if m.date_of_birth)
            extra = f' and {len(members) - 10} more' if len(members) > 10 else ''
            return f'Birthdays this month: {names}{extra}.'

        if 'financial' in question or 'finance' in question:
            net = context['monthly_income'] - context['monthly_expenses']
            return (
                f"This month's financial summary:\n"
                f"- Income: GH₵{context['monthly_income']:,.2f}\n"
                f"- Expenses: GH₵{context['monthly_expenses']:,.2f}\n"
                f"- Net: GH₵{net:,.2f}"
            )

        if 'missed' in question and ('consecutive' in question or 'absent' in question):
            return self._find_absent_members(4)

        if 'department' in question and 'grow' in question:
            return self._fastest_growing_department()

        if 'attendance' in question and 'predict' in question:
            return self._predict_attendance()

        if 'announcement' in question:
            return self._generate_announcement()

        return None

    def _find_absent_members(self, consecutive_weeks):
        """Find members absent for N consecutive Sundays."""
        sunday_type = AttendanceType.query.filter_by(
            name=AttendanceType.SUNDAY_SERVICE
        ).first()
        if not sunday_type:
            return 'Sunday Service attendance type not configured.'

        today = datetime.utcnow().date()
        absent = []
        members = Member.query.filter_by(membership_status='active', is_visitor=False).all()

        for member in members:
            missed = 0
            for week in range(consecutive_weeks):
                check_date = today - timedelta(weeks=week + 1)
                # Adjust to nearest Sunday
                check_date = check_date - timedelta(days=(check_date.weekday() + 1) % 7)
                attendance = Attendance.query.filter_by(
                    member_id=member.id,
                    attendance_type_id=sunday_type.id,
                    date=check_date
                ).first()
                if not attendance:
                    missed += 1
                else:
                    break
            if missed >= consecutive_weeks:
                absent.append(member.full_name)

        if not absent:
            return f'No members have missed {consecutive_weeks} consecutive Sunday services.'
        return f'Members absent for {consecutive_weeks}+ Sundays: {", ".join(absent[:15])}.'

    def _fastest_growing_department(self):
        """Identify fastest growing department."""
        year_start = datetime.utcnow().date().replace(month=1, day=1)
        results = []
        for dept in Department.query.filter_by(is_active=True).all():
            count = DepartmentMember.query.filter(
                DepartmentMember.department_id == dept.id,
                DepartmentMember.joined_date >= year_start,
                DepartmentMember.is_active == True  # noqa: E712
            ).count()
            results.append((dept.name, count))

        if not results:
            return 'No department growth data available.'
        results.sort(key=lambda x: x[1], reverse=True)
        top = results[0]
        return f"The fastest growing department is {top[0]} with {top[1]} new members this year."

    def _predict_attendance(self):
        """Simple attendance prediction based on recent averages."""
        sunday_type = AttendanceType.query.filter_by(
            name=AttendanceType.SUNDAY_SERVICE
        ).first()
        if not sunday_type:
            return 'Unable to predict — Sunday Service type not found.'

        four_weeks_ago = datetime.utcnow().date() - timedelta(weeks=4)
        avg = db.session.query(func.count(Attendance.id)).filter(
            Attendance.attendance_type_id == sunday_type.id,
            Attendance.date >= four_weeks_ago
        ).scalar() or 0
        avg = round(avg / 4)
        return f'Predicted next Sunday attendance: approximately {avg} members (based on 4-week average).'

    def _generate_announcement(self):
        """Generate a weekly announcement draft."""
        events = Event.query.filter(
            Event.start_date >= datetime.utcnow(),
            Event.start_date <= datetime.utcnow() + timedelta(days=7),
            Event.status == 'upcoming'
        ).all()

        event_text = ''
        if events:
            event_list = '\n'.join(
                f'- {e.title} ({e.start_date.strftime("%A, %b %d")})' for e in events
            )
            event_text = f'\n\nUpcoming Events:\n{event_list}'

        return (
            f"📢 Weekly Church Announcement\n\n"
            f"Beloved congregation, we greet you in the name of the Lord!\n\n"
            f"Join us this Sunday for worship and fellowship. "
            f"All are welcome to come as you are.{event_text}\n\n"
            f"May God bless you abundantly this week!"
        )

    def _fallback_response(self, question, context):
        """Fallback when OpenAI is unavailable."""
        return (
            f'AI assistant is running in offline mode. '
            f'Church snapshot: {context["total_members"]} active members, '
            f'{context["new_members_this_year"]} new this year. '
            f'Try asking about: new members, birthdays, finances, absent members, '
            f'department growth, or attendance predictions.'
        )
