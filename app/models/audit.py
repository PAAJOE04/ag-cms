"""Audit logging model."""
from datetime import datetime

from app.extensions import db


class AuditLog(db.Model):
    """System audit trail."""

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    module = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User')

    @staticmethod
    def log(user_id, action, module, description=None, **kwargs):
        """Create an audit log entry."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            module=module,
            description=description,
            **kwargs
        )
        db.session.add(entry)
        return entry
