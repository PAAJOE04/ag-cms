"""Attendance management blueprint."""
import re
from datetime import datetime

from flask import (
    Blueprint, current_app, flash, jsonify, redirect, render_template,
    request, url_for,
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


@attendance_bp.route('/qr/<qr_code>')
@login_required
@permission_required('attendance:create')
def qr_checkin(qr_code):
    """QR code based check-in (when the QR itself is scanned by a browser)."""
    member = Member.query.filter_by(qr_code=qr_code).first_or_404()
    type_id = request.args.get('type_id', type=int)
    if type_id:
        attendance_type = AttendanceType.query.get_or_404(type_id)
    else:
        attendance_type = AttendanceType.query.filter_by(
            name=AttendanceType.SUNDAY_SERVICE
        ).first()
        if not attendance_type:
            flash('Sunday Service type not configured.', 'danger')
            return redirect(url_for('attendance.checkin'))

    today = datetime.utcnow().date()
    existing = Attendance.query.filter_by(
        member_id=member.id,
        attendance_type_id=attendance_type.id,
        date=today,
    ).first()

    if existing:
        flash(f'{member.full_name} already checked in to {attendance_type.name} today.', 'info')
    else:
        record = Attendance(
            member_id=member.id,
            attendance_type_id=attendance_type.id,
            date=today,
            check_in_method='qr',
            recorded_by_id=current_user.id,
        )
        db.session.add(record)
        db.session.commit()
        flash(f'Welcome, {member.full_name}! Checked in via QR.', 'success')

    return redirect(url_for('attendance.checkin'))


@attendance_bp.route('/scanner')
@login_required
@permission_required('attendance:create')
def scanner():
    """QR scanner station for check-in."""
    types = AttendanceType.query.filter_by(is_active=True).all()
    return render_template('attendance/scanner.html', types=types)


@attendance_bp.route('/api/qr-checkin', methods=['POST'])
@login_required
@permission_required('attendance:create')
def api_qr_checkin():
    """Record attendance from a scanned QR code (JSON endpoint)."""
    data = request.get_json(silent=True) or {}
    scanned_text = (data.get('qr_code') or '').strip()
    try:
        type_id = int(data.get('attendance_type_id'))
    except (TypeError, ValueError):
        type_id = None
    date_str = data.get('date')

    match = re.search(r'/qr/([0-9a-f-]{8,64})', scanned_text)
    if match:
        scanned_text = match.group(1)

    member = Member.query.filter_by(qr_code=scanned_text).first()
    if not member:
        return jsonify(ok=False, error='QR code not recognized. This member is not registered.'), 404

    attendance_type = AttendanceType.query.get(type_id) if type_id else None
    if not attendance_type:
        return jsonify(ok=False, error='Please choose a service type first.'), 400

    try:
        att_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str \
            else datetime.utcnow().date()
    except ValueError:
        return jsonify(ok=False, error='Invalid date.'), 400

    existing = Attendance.query.filter_by(
        member_id=member.id,
        attendance_type_id=attendance_type.id,
        date=att_date,
    ).first()

    if existing:
        return jsonify(
            ok=False,
            already=True,
            member_name=member.full_name,
            error=f'{member.full_name} already checked in to {attendance_type.name} today.',
        )

    record = Attendance(
        member_id=member.id,
        attendance_type_id=attendance_type.id,
        date=att_date,
        check_in_method='qr',
        recorded_by_id=current_user.id,
    )
    db.session.add(record)
    audit_action('create', 'attendance',
                 f'QR check-in: {member.full_name} to {attendance_type.name} on {att_date}')
    db.session.commit()

    return jsonify(
        ok=True,
        member_name=member.full_name,
        attendance_type=attendance_type.name,
        date=att_date.isoformat(),
    )


@attendance_bp.route('/qr-image/<int:member_id>')
@login_required
def qr_image(member_id):
    """Serve a member's check-in QR code as a PNG (generated on the fly)."""
    member = Member.query.get_or_404(member_id)
    check_in_url = url_for(
        'attendance.qr_checkin',
        qr_code=member.qr_code,
        _external=True,
    )
    buffer = QRService.generate_qr_bytes(check_in_url)
    return current_app.response_class(buffer, mimetype='image/png')


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
