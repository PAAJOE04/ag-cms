"""Communication models."""
from datetime import datetime

from app.extensions import db


class Announcement(db.Model):
    """Church announcement."""

    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, emergency
    is_published = db.Column(db.Boolean, default=True)
    publish_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expiry_date = db.Column(db.DateTime)
    target_roles = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_by = db.relationship('User')

    CATEGORIES = ['general', 'news', 'emergency', 'meeting', 'event']

    def __repr__(self):
        return f'<Announcement {self.title}>'


class Notification(db.Model):
    """User notification."""

    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), default='info')
    is_read = db.Column(db.Boolean, default=False, index=True)
    link = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User')
