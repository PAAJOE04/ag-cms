"""Communication blueprint."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.communication import Announcement, Notification
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, paginate_query

communication_bp = Blueprint('communication', __name__)


@communication_bp.route('/')
@login_required
@permission_required('communication:view')
def index():
    """Communication hub."""
    announcements = paginate_query(
        Announcement.query.filter_by(is_published=True).order_by(
            Announcement.publish_date.desc()
        )
    )
    return render_template('communication/index.html', announcements=announcements)


@communication_bp.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@permission_required('communication:create')
def create_announcement():
    """Create announcement."""
    if request.method == 'POST':
        announcement = Announcement(
            title=request.form['title'],
            content=request.form['content'],
            category=request.form.get('category', 'general'),
            priority=request.form.get('priority', 'normal'),
            is_published=bool(request.form.get('is_published', True)),
            created_by_id=current_user.id,
        )
        if request.form.get('expiry_date'):
            announcement.expiry_date = datetime.strptime(
                request.form['expiry_date'], '%Y-%m-%d'
            )
        db.session.add(announcement)
        audit_action('create', 'communication', f'Created announcement: {announcement.title}')
        db.session.commit()
        flash('Announcement published.', 'success')
        return redirect(url_for('communication.index'))

    return render_template('communication/create_announcement.html',
                           categories=Announcement.CATEGORIES)


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
