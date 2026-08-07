"""Attendance management blueprint."""
from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models.member import Member
from app.models.attendance import Attendance, AttendanceType
from app.services.qr_service import QRService
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, get_date_range, paginate_query

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/')
@login_required
@permission_required('attendance:view')
def index():
    """Attendance dashboard."""
    today = datetime.utcnow().date()
    types = AttendanceType.query.filter_by(is_active=True).all()

    today_counts = {}
    for atype in types:
        count = Attendance.query.filter_by(
            date=today, attendance_type_id=atype.id
        ).count()
        today_counts[atype.name] = count

    recent = Attendance.query.order_by(
        Attendance.check_in_time.desc()
    ).limit(20).all()

    return render_template(
        'attendance/index.html',
        today_counts=today_counts,
        types=types,
        recent=recent,
        today=today,
    )


@attendance_bp.route('/checkin', methods=['GET', 'POST'])
@login_required
@permission_required('attendance:create')
def checkin():
    """Manual attendance check-in."""
    types = AttendanceType.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        member_id = request.form.get('member_id', type=int)
        type_id = request.form.get('attendance_type_id', type=int)
        date_str = request.form.get('date', datetime.utcnow().date().isoformat())

        member = Member.query.get_or_404(member_id)
        att_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        existing = Attendance.query.filter_by(
            member_id=member_id,
            attendance_type_id=type_id,
            date=att_date,
        ).first()
        if existing:
            flash(f'{member.full_name} already checked in for this service.', 'warning')
        else:
            record = Attendance(
                member_id=member_id,
                attendance_type_id=type_id,
                date=att_date,
                check_in_method='manual',
                recorded_by_id=current_user.id,
            )
            db.session.add(record)
            audit_action('create', 'attendance',
                         f'Checked in {member.full_name} on {att_date}')
            db.session.commit()
            flash(f'{member.full_name} checked in successfully.', 'success')

        return redirect(url_for('attendance.checkin'))

    return render_template('attendance/checkin.html', types=types)


@attendance_bp.route('/mobile', methods=['GET', 'POST'])
def mobile():
    """Self check-in page (public) — members scan the door QR to land here."""
    types = AttendanceType.query.filter_by(is_active=True).all()
    message = None
    message_class = None
    checked_in = False

    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()
        type_id = request.form.get('attendance_type_id', type=int)
        attendance_type = AttendanceType.query.get(type_id) if type_id else None

        if not identifier:
            message = 'Please enter your membership ID or phone number.'
            message_class = 'danger'
        elif not attendance_type:
            message = 'Please choose a service type.'
            message_class = 'danger'
        else:
            member = Member.query.filter(
                Member.membership_status == 'active',
                Member.is_visitor == False,  # noqa: E712
                db.or_(
                    Member.membership_id.ilike(f'%{identifier}%'),
                    Member.phone == identifier,
                )
            ).first()
            if not member:
                message = "We couldn't find your record. Check the ID on your card or see an usher for help."
                message_class = 'danger'
            else:
                today = datetime.utcnow().date()
                existing = Attendance.query.filter_by(
                    member_id=member.id,
                    attendance_type_id=attendance_type.id,
                    date=today,
                ).first()
                if existing:
                    message = (
                        f"You're already checked in to {attendance_type.name} "
                        f"today, {member.first_name}. Have a blessed service!"
                    )
                    message_class = 'warning'
                else:
                    record = Attendance(
                        member_id=member.id,
                        attendance_type_id=attendance_type.id,
                        date=today,
                        check_in_method='qr',
                        recorded_by_id=None,
                    )
                    db.session.add(record)
                    db.session.commit()
                    message = (
                        f"Welcome, {member.first_name}! You're checked in to "
                        f"{attendance_type.name}. God bless you."
                    )
                    message_class = 'success'
                    checked_in = True

    return render_template(
        'attendance/mobile_checkin.html',
        types=types,
        message=message,
        message_class=message_class,
        checked_in=checked_in,
    )


@attendance_bp.route('/poster')
@login_required
@permission_required('attendance:view')
def poster():
    """Door poster QR that members scan with their own phones."""
    check_in_url = url_for('attendance.mobile', _external=True)
    import base64
    qr_data = base64.b64encode(
        QRService.generate_qr_bytes(check_in_url).getvalue()
    ).decode()
    return render_template(
        'attendance/poster.html',
        qr_data=qr_data,
        check_in_url=check_in_url,
    )


@attendance_bp.route('/reports')
@login_required
@permission_required('attendance:view')
def reports():
    """Attendance reports."""
    period = request.args.get('period', 'weekly')
    type_id = request.args.get('type_id', type=int)
    start_date, end_date = get_date_range(period)

    query = Attendance.query.filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date,
    )
    if type_id:
        query = query.filter_by(attendance_type_id=type_id)

    records = paginate_query(query.order_by(Attendance.date.desc()))
    types = AttendanceType.query.filter_by(is_active=True).all()

    summary = db.session.query(
        Attendance.date,
        func.count(Attendance.id)
    ).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date,
    ).group_by(Attendance.date).order_by(Attendance.date).all()

    return render_template(
        'attendance/reports.html',
        records=records,
        types=types,
        period=period,
        type_id=type_id,
        summary=summary,
        start_date=start_date,
        end_date=end_date,
    )
