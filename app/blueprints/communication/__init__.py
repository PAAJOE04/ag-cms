"""Communication blueprint."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models.communication import Announcement, Notification, SmsLog
from app.models.department import Department, DepartmentMember
from app.services.sms_service import notify_announcement
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, paginate_query

communication_bp = Blueprint('communication', __name__)


@communication_bp.route('/')
@login_required
@permission_required('communication:view')
def index():
    """Communication hub."""
    query = Announcement.query.filter_by(is_published=True)

    if not (current_user.is_developer() or current_user.is_super_admin()):
        department_ids = []
        if current_user.member_id:
            department_ids = [
                dm.department_id for dm in DepartmentMember.query.filter_by(
                    member_id=current_user.member_id, is_active=True
                ).all()
            ]
        query = query.filter(
            or_(
                Announcement.target_department_id.is_(None),
                Announcement.target_department_id.in_(department_ids),
            )
        )

    announcements = paginate_query(
        query.order_by(Announcement.publish_date.desc())
    )
    return render_template('communication/index.html', announcements=announcements)


@communication_bp.route('/sms-log')
@login_required
@permission_required('communication:create')
def sms_log():
    """SMS delivery log."""
    messages = paginate_query(
        SmsLog.query.order_by(SmsLog.created_at.desc())
    )
    return render_template('communication/sms_log.html', messages=messages)


@communication_bp.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@permission_required('communication:create')
def create_announcement():
    """Create announcement."""
    departments = Department.query.filter_by(is_active=True).order_by(
        Department.name
    ).all()

    if request.method == 'POST':
        announcement = Announcement(
            title=request.form['title'],
            content=request.form['content'],
            category=request.form.get('category', 'general'),
            priority=request.form.get('priority', 'normal'),
            is_published=bool(request.form.get('is_published', True)),
            target_department_id=request.form.get(
                'target_department_id', type=int
            ) or None,
            created_by_id=current_user.id,
        )
        if request.form.get('expiry_date'):
            announcement.expiry_date = datetime.strptime(
                request.form['expiry_date'], '%Y-%m-%d'
            )
        db.session.add(announcement)
        audit_action('create', 'communication', f'Created announcement: {announcement.title}')
        db.session.commit()
        sent = notify_announcement(announcement)
        if sent:
            flash(f'Announcement published. SMS queued to {sent} member(s).', 'success')
        else:
            flash(
                'Announcement published. No SMS sent (no members with phone '
                'numbers in the target group).',
                'success',
            )
        return redirect(url_for('communication.index'))

    return render_template(
        'communication/create_announcement.html',
        categories=Announcement.CATEGORIES,
        departments=departments,
    )


@communication_bp.route('/notifications')
@login_required
def notifications():
    """User notifications."""
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    return render_template('communication/notifications.html', notifications=notifs)


@communication_bp.route('/notifications/<int:id>/read', methods=['POST'])
@login_required
def mark_read(id):
    """Mark notification as read."""
    notif = Notification.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(notif.link or url_for('communication.notifications'))
