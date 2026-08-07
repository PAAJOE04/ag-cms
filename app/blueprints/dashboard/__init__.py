"""Dashboard blueprint."""
from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.member import Member
from app.models.attendance import Attendance, AttendanceType
from app.models.finance import Transaction
from app.models.event import Event
from app.models.communication import Announcement
from app.models.audit import AuditLog
from app.services.follow_up_service import FollowUpService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard."""
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    stats = {
        'total_members': Member.query.filter_by(
            membership_status='active', is_visitor=False
        ).count(),
        'new_members_month': Member.query.filter(
            Member.membership_date >= month_start,
            Member.is_visitor == False  # noqa: E712
        ).count(),
        'visitors_month': __import__('app.models.member', fromlist=['Visitor']).Visitor.query.filter(
            __import__('app.models.member', fromlist=['Visitor']).Visitor.visit_date >= month_start
        ).count(),
    }

    # Financial summary
    stats['monthly_income'] = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'income',
        Transaction.transaction_date >= month_start
    ).scalar() or 0)

    stats['monthly_expenses'] = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'expense',
        Transaction.transaction_date >= month_start
    ).scalar() or 0)

    # Attendance today
    sunday_type = AttendanceType.query.filter_by(name='Sunday Service').first()
    stats['attendance_today'] = 0
    if sunday_type:
        stats['attendance_today'] = Attendance.query.filter_by(
            date=today, attendance_type_id=sunday_type.id
        ).count()

    # Upcoming events
    upcoming_events = Event.query.filter(
        Event.start_date >= datetime.utcnow(),
        Event.status == 'upcoming'
    ).order_by(Event.start_date).limit(5).all()

    # Birthdays this week
    birthdays = []
    for i in range(7):
        check_date = today + timedelta(days=i)
        day_members = Member.query.filter(
            func.extract('month', Member.date_of_birth) == check_date.month,
            func.extract('day', Member.date_of_birth) == check_date.day,
            Member.membership_status == 'active'
        ).all()
        for m in day_members:
            birthdays.append({'member': m, 'date': check_date})

    # Recent announcements
    announcements = Announcement.query.filter_by(is_published=True).order_by(
        Announcement.publish_date.desc()
    ).limit(5).all()

    # Activity feed
    activities = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()

    # AI insights placeholder
    ai_insights = []
    absent = FollowUpService.detect_absent_members()
    if absent:
        ai_insights.append({
            'type': 'warning',
            'message': f'{len(absent)} members need follow-up for consecutive absences.',
        })
    if stats['new_members_month'] > 0:
        ai_insights.append({
            'type': 'success',
            'message': f'{stats["new_members_month"]} new members joined this month!',
        })

    return render_template(
        'dashboard/index.html',
        stats=stats,
        upcoming_events=upcoming_events,
        birthdays=birthdays[:8],
        announcements=announcements,
        activities=activities,
        ai_insights=ai_insights,
    )
