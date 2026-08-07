"""Reports & analytics blueprint."""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func, extract

from app.extensions import db
from app.models.member import Member
from app.models.attendance import Attendance, AttendanceType
from app.models.finance import Transaction
from app.models.department import Department, DepartmentMember
from app.utils.decorators import permission_required
from app.utils.helpers import get_date_range

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
@permission_required('reports:view')
def index():
    """Analytics dashboard."""
    today = datetime.utcnow().date()
    year_start = today.replace(month=1, day=1)

    # Membership growth by month
    membership_growth = db.session.query(
        extract('month', Member.membership_date).label('month'),
        func.count(Member.id)
    ).filter(
        Member.membership_date >= year_start,
        Member.is_visitor == False  # noqa: E712
    ).group_by('month').order_by('month').all()

    # Gender distribution
    gender_dist = db.session.query(
        Member.gender, func.count(Member.id)
    ).filter(
        Member.membership_status == 'active',
        Member.is_visitor == False  # noqa: E712
    ).group_by(Member.gender).all()

    # Financial trend (last 6 months)
    financial_trend = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1)

        income = float(db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.type == 'income',
            Transaction.transaction_date >= month_start,
            Transaction.transaction_date < month_end,
        ).scalar() or 0)
        financial_trend.append({
            'month': month_start.strftime('%b %Y'),
            'income': income,
        })

    # Department performance
    dept_performance = []
    for dept in Department.query.filter_by(is_active=True).all():
        count = DepartmentMember.query.filter_by(
            department_id=dept.id, is_active=True
        ).count()
        dept_performance.append({'name': dept.name, 'members': count})

    return render_template(
        'reports/index.html',
        membership_growth=membership_growth,
        gender_dist=gender_dist,
        financial_trend=financial_trend,
        dept_performance=dept_performance,
    )


@reports_bp.route('/api/attendance-trend')
@login_required
@permission_required('reports:view')
def attendance_trend():
    """Attendance trend data for charts."""
    period = request.args.get('period', 'monthly')
    start_date, end_date = get_date_range(period)

    data = db.session.query(
        Attendance.date,
        func.count(Attendance.id)
    ).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date,
    ).group_by(Attendance.date).order_by(Attendance.date).all()

    return jsonify({
        'labels': [d[0].isoformat() for d in data],
        'values': [d[1] for d in data],
    })
