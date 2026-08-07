"""Admin & system management blueprint."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.user import User, Role, LoginHistory
from app.models.audit import AuditLog
from app.models.follow_up import FollowUp
from app.services.backup_service import BackupService
from app.services.follow_up_service import FollowUpService
from app.utils.decorators import permission_required, role_required
from app.utils.helpers import audit_action, paginate_query
from app.utils.permissions import get_permissions_for_role

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@login_required
@permission_required('admin:view')
def index():
    """Admin dashboard."""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'pending_followups': FollowUp.query.filter_by(status='pending').count(),
        'audit_logs_today': AuditLog.query.filter(
            AuditLog.created_at >= datetime.utcnow().replace(hour=0, minute=0)
        ).count(),
    }
    return render_template('admin/index.html', stats=stats)


@admin_bp.route('/users')
@login_required
@permission_required('users:view')
def users():
    """Manage users."""
    role_filter = request.args.get('role', '').strip()
    query = User.query
    if role_filter:
        query = query.join(Role).filter(Role.name == role_filter)
    users_list = paginate_query(query.order_by(User.created_at.desc()))
    roles = Role.query.all()
    return render_template(
        'admin/users.html',
        users=users_list,
        roles=roles,
        role_filter=role_filter,
    )


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@permission_required('users:create')
def create_user():
    """Create user account."""
    roles = Role.query.filter(Role.name != Role.DEVELOPER).all()
    if current_user.is_developer():
        roles = Role.query.all()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not request.form.get('first_name') or not request.form.get('last_name'):
            flash('All required fields must be filled in.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('That email is already registered.', 'danger')
        elif len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            role_id = request.form.get('role_id', type=int)
            role = Role.query.get(role_id) if role_id else None

            if not role:
                flash('Please select a role.', 'danger')
                return redirect(url_for('admin.create_user'))

            if role.name == Role.DEVELOPER and not current_user.is_developer():
                flash('Cannot assign Developer role.', 'danger')
                return redirect(url_for('admin.create_user'))

            user = User(
                username=username,
                email=email,
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                phone=request.form.get('phone'),
                role_id=role_id,
                created_by_id=current_user.id,
            )
            user.set_password(password)
            db.session.add(user)
            audit_action('create', 'admin', f'Created user {user.username}')
            db.session.commit()
            flash(f'User {user.username} created.', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/create_user.html', roles=roles)


@admin_bp.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
@permission_required('users:edit')
def reset_password(id):
    """Reset a user's password."""
    user = User.query.get_or_404(id)
    if not current_user.can_manage_user(user):
        flash('Cannot modify this user.', 'danger')
        return redirect(url_for('admin.users'))

    new_password = request.form.get('password', '')
    if len(new_password) < 8:
        flash('Password must be at least 8 characters.', 'danger')
        return redirect(url_for('admin.users'))

    user.set_password(new_password)
    audit_action('reset_password', 'admin', f'Reset password for user {user.username}')
    db.session.commit()
    flash(f'Password reset for {user.username}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:id>/toggle', methods=['POST'])
@login_required
@permission_required('users:edit')
def toggle_user(id):
    """Activate/deactivate user."""
    user = User.query.get_or_404(id)
    if not current_user.can_manage_user(user):
        flash('Cannot modify this user.', 'danger')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    audit_action('update', 'admin',
                 f'{"Activated" if user.is_active else "Deactivated"} user {user.username}')
    db.session.commit()
    flash(f'User {user.username} {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/audit-logs')
@login_required
@permission_required('admin:audit')
def audit_logs():
    """View audit logs."""
    logs = paginate_query(AuditLog.query.order_by(AuditLog.created_at.desc()))
    return render_template('admin/audit_logs.html', logs=logs)


@admin_bp.route('/follow-ups')
@login_required
@permission_required('admin:view')
def follow_ups():
    """Follow-up management."""
    followups = paginate_query(
        FollowUp.query.filter_by(status='pending').order_by(FollowUp.due_date)
    )
    return render_template('admin/follow_ups.html', followups=followups)


@admin_bp.route('/follow-ups/detect', methods=['POST'])
@login_required
@permission_required('admin:view')
def detect_followups():
    """Run follow-up detection."""
    absent = FollowUpService.detect_absent_members()
    visitors = FollowUpService.detect_pending_visitors()
    flash(f'Detected {len(absent)} absent members and {len(visitors)} pending visitors.', 'info')
    return redirect(url_for('admin.follow_ups'))


@admin_bp.route('/backups')
@login_required
@role_required('developer', 'super_admin')
def backups():
    """Backup management."""
    backups_list = BackupService.list_backups()
    return render_template('admin/backups.html', backups=backups_list)


@admin_bp.route('/backups/create', methods=['POST'])
@login_required
@role_required('developer', 'super_admin')
def create_backup():
    """Create database backup."""
    from flask import current_app
    result = BackupService.create_backup(current_app._get_current_object())
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('admin.backups'))


@admin_bp.route('/settings')
@login_required
@role_required('developer', 'super_admin')
def settings():
    """System settings."""
    from flask import current_app
    return render_template('admin/settings.html', config=current_app.config)
