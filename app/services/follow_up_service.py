"""Smart follow-up detection service."""
from datetime import datetime, timedelta

from app.extensions import db
from app.models.member import Member
from app.models.attendance import Attendance, AttendanceType
from app.models.follow_up import FollowUp
from app.models.member import Visitor


class FollowUpService:
    """Automated follow-up detection and management."""

    ABSENCE_THRESHOLD = 4  # consecutive Sundays

    @classmethod
    def detect_absent_members(cls):
        """Detect members absent for consecutive Sundays."""
        sunday_type = AttendanceType.query.filter_by(
            name=AttendanceType.SUNDAY_SERVICE
        ).first()
        if not sunday_type:
            return []

        today = datetime.utcnow().date()
        created = []
        members = Member.query.filter_by(
            membership_status='active', is_visitor=False
        ).all()

        for member in members:
            missed = 0
            for week in range(cls.ABSENCE_THRESHOLD):
                check_date = today - timedelta(weeks=week + 1)
                check_date = check_date - timedelta(days=(check_date.weekday() + 1) % 7)
                if not Attendance.query.filter_by(
                    member_id=member.id,
                    attendance_type_id=sunday_type.id,
                    date=check_date
                ).first():
                    missed += 1
                else:
                    break

            if missed >= cls.ABSENCE_THRESHOLD:
                existing = FollowUp.query.filter_by(
                    member_id=member.id,
                    type='absence',
                    status='pending'
                ).first()
                if not existing:
                    follow_up = FollowUp(
                        member_id=member.id,
                        type='absence',
                        reason=(
                            f'Absent for {missed} consecutive Sunday services'
                        ),
                        priority='high' if missed >= 6 else 'normal',
                        due_date=today + timedelta(days=3),
                    )
                    db.session.add(follow_up)
                    created.append(follow_up)

        if created:
            db.session.commit()
        return created

    @classmethod
    def detect_pending_visitors(cls):
        """Create follow-ups for unconverted visitors."""
        week_ago = datetime.utcnow().date() - timedelta(days=7)
        visitors = Visitor.query.filter(
            Visitor.follow_up_status == 'pending',
            Visitor.visit_date <= week_ago,
            Visitor.converted_member_id.is_(None)
        ).all()

        created = []
        for visitor in visitors:
            existing = FollowUp.query.filter_by(
                visitor_id=visitor.id,
                type='visitor',
                status='pending'
            ).first()
            if not existing:
                follow_up = FollowUp(
                    visitor_id=visitor.id,
                    type='visitor',
                    reason=f'Follow up with visitor {visitor.first_name} {visitor.last_name}',
                    priority='normal',
                    due_date=datetime.utcnow().date() + timedelta(days=2),
                )
                db.session.add(follow_up)
                created.append(follow_up)

        if created:
            db.session.commit()
        return created

    @classmethod
    def suggest_pastoral_care(cls):
        """Suggest members who may need pastoral care."""
        suggestions = []
        today = datetime.utcnow().date()

        # Members with recent bereavement notes or inactive status changes
        recent_inactive = Member.query.filter(
            Member.membership_status == 'inactive',
            Member.updated_at >= datetime.utcnow() - timedelta(days=30)
        ).limit(5).all()

        for member in recent_inactive:
            suggestions.append({
                'member': member,
                'reason': 'Recently marked inactive — may need pastoral visit',
            })

        # Elderly members without recent attendance
        elderly = Member.query.filter(
            Member.membership_status == 'active',
            Member.date_of_birth.isnot(None)
        ).all()
        for member in elderly:
            if member.age and member.age >= 70:
                suggestions.append({
                    'member': member,
                    'reason': f'Senior member (age {member.age}) — wellness check recommended',
                })

        return suggestions[:10]
