"""Follow-up tracking models."""
from datetime import datetime

from app.extensions import db


class FollowUp(db.Model):
    """Member/visitor follow-up record."""

    __tablename__ = 'follow_ups'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), index=True)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitors.id'))
    type = db.Column(db.String(30), nullable=False)  # absence, pastoral_care, visitor, conversion
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending', index=True)
    priority = db.Column(db.String(20), default='normal')
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    member = db.relationship('Member', back_populates='follow_ups')
    visitor = db.relationship('Visitor')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])
    actions = db.relationship(
        'FollowUpAction', back_populates='follow_up', lazy='dynamic',
        cascade='all, delete-orphan'
    )


class FollowUpAction(db.Model):
    """Individual follow-up action taken."""

    __tablename__ = 'follow_up_actions'

    id = db.Column(db.Integer, primary_key=True)
    follow_up_id = db.Column(
        db.Integer, db.ForeignKey('follow_ups.id'), nullable=False
    )
    action_type = db.Column(db.String(30))  # call, visit, email, sms, prayer
    notes = db.Column(db.Text)
    outcome = db.Column(db.String(50))
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    performed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    follow_up = db.relationship('FollowUp', back_populates='actions')
    performed_by = db.relationship('User')
