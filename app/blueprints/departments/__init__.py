"""Departments & ministries blueprint."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models.department import Department, DepartmentMember
from app.models.member import Member
from app.models.attendance import Attendance
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, paginate_query

departments_bp = Blueprint('departments', __name__)


@departments_bp.route('/')
@login_required
@permission_required('departments:view')
def index():
    """List departments."""
    depts = Department.query.filter_by(is_active=True).all()
    dept_stats = []
    for dept in depts:
        member_count = DepartmentMember.query.filter_by(
            department_id=dept.id, is_active=True
        ).count()
        dept_stats.append({'department': dept, 'member_count': member_count})
    return render_template('departments/index.html', dept_stats=dept_stats)


@departments_bp.route('/<int:id>')
@login_required
@permission_required('departments:view')
def view(id):
    """View department details."""
    dept = Department.query.get_or_404(id)

    # Department leaders can only see their own department
    if current_user.role_name == 'department_leader':
        if current_user.department_id != dept.id:
            flash('Access limited to your assigned department.', 'danger')
            return redirect(url_for('departments.index'))

    members = DepartmentMember.query.filter_by(
        department_id=dept.id, is_active=True
    ).all()
    all_members = Member.query.filter_by(
        membership_status='active'
    ).order_by(Member.last_name).all()
    return render_template(
        'departments/view.html',
        department=dept,
        members=members,
        all_members=all_members,
    )


@departments_bp.route('/<int:id>/add-member', methods=['POST'])
@login_required
@permission_required('departments:edit')
def add_member(id):
    """Add member to department."""
    dept = Department.query.get_or_404(id)
    member_id = request.form.get('member_id', type=int)
    role = request.form.get('role', 'member')

    existing = DepartmentMember.query.filter_by(
        department_id=dept.id, member_id=member_id
    ).first()
    if existing:
        existing.is_active = True
        existing.role = role
    else:
        dm = DepartmentMember(
            department_id=dept.id,
            member_id=member_id,
            role=role,
        )
        db.session.add(dm)

    db.session.commit()
    flash('Member added to department.', 'success')
    return redirect(url_for('departments.view', id=dept.id))


@departments_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('departments:edit')
def create():
    """Create a new department."""
    if request.method == 'POST':
        dept = Department(
            name=request.form['name'],
            description=request.form.get('description'),
            leader_id=request.form.get('leader_id', type=int) or None,
        )
        db.session.add(dept)
        audit_action('create', 'departments', f'Created department: {dept.name}')
        db.session.commit()
        flash(f'Department "{dept.name}" created.', 'success')
        return redirect(url_for('departments.view', id=dept.id))

    members = Member.query.filter_by(membership_status='active').order_by(Member.last_name).all()
    return render_template('departments/create.html', members=members)
