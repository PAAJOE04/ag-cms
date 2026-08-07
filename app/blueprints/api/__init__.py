"""RESTful API blueprint."""
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models.member import Member
from app.models.attendance import Attendance, AttendanceType
from app.models.finance import Transaction
from app.models.event import Event
from app.utils.decorators import permission_required

api_bp = Blueprint('api', __name__)


@api_bp.route('/members')
@login_required
@permission_required('members:view')
def get_members():
    """GET /api/v1/members - List members."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')

    query = Member.query.filter_by(is_visitor=False, membership_status='active')
    if search:
        query = query.filter(
            db.or_(
                Member.first_name.ilike(f'%{search}%'),
                Member.last_name.ilike(f'%{search}%'),
            )
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'members': [{
            'id': m.id,
            'membership_id': m.membership_id,
            'full_name': m.full_name,
            'email': m.email,
            'phone': m.phone,
            'gender': m.gender,
            'membership_date': m.membership_date.isoformat() if m.membership_date else None,
        } for m in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    })


@api_bp.route('/members/<int:id>')
@login_required
@permission_required('members:view')
def get_member(id):
    """GET /api/v1/members/:id - Get member details."""
    member = Member.query.get_or_404(id)
    return jsonify({
        'id': member.id,
        'membership_id': member.membership_id,
        'full_name': member.full_name,
        'email': member.email,
        'phone': member.phone,
        'gender': member.gender,
        'date_of_birth': member.date_of_birth.isoformat() if member.date_of_birth else None,
        'address': member.address,
        'membership_status': member.membership_status,
        'baptism_date': member.baptism_date.isoformat() if member.baptism_date else None,
    })


@api_bp.route('/attendance', methods=['POST'])
@login_required
@permission_required('attendance:create')
def record_attendance():
    """POST /api/v1/attendance - Record attendance."""
    data = request.get_json()
    if not data or not data.get('member_id'):
        return jsonify({'error': 'member_id required'}), 400

    type_id = data.get('attendance_type_id')
    if not type_id:
        sunday = AttendanceType.query.filter_by(name='Sunday Service').first()
        type_id = sunday.id if sunday else None

    att_date = datetime.strptime(
        data.get('date', datetime.utcnow().date().isoformat()), '%Y-%m-%d'
    ).date()

    existing = Attendance.query.filter_by(
        member_id=data['member_id'],
        attendance_type_id=type_id,
        date=att_date,
    ).first()
    if existing:
        return jsonify({'error': 'Already checked in', 'id': existing.id}), 409

    record = Attendance(
        member_id=data['member_id'],
        attendance_type_id=type_id,
        date=att_date,
        check_in_method=data.get('method', 'api'),
        recorded_by_id=current_user.id,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'message': 'Attendance recorded', 'id': record.id}), 201


@api_bp.route('/stats/dashboard')
@login_required
def dashboard_stats():
    """GET /api/v1/stats/dashboard - Dashboard statistics."""
    from sqlalchemy import func
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    return jsonify({
        'total_members': Member.query.filter_by(membership_status='active').count(),
        'monthly_income': float(db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.type == 'income',
            Transaction.transaction_date >= month_start
        ).scalar() or 0),
        'upcoming_events': Event.query.filter(
            Event.start_date >= datetime.utcnow(),
            Event.status == 'upcoming'
        ).count(),
    })
