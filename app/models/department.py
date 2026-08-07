"""Department and ministry models."""
from datetime import datetime

from app.extensions import db


class Department(db.Model):
    """Church department or ministry."""

    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    leader_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leader = db.relationship('Member', foreign_keys=[leader_id])
    members = db.relationship(
        'DepartmentMember', back_populates='department', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    events = db.relationship('Event', back_populates='department', lazy='dynamic')

    DEFAULT_DEPARTMENTS = [
        'Choir', 'Ushers', 'Media', 'Youth Ministry',
        "Children's Ministry", "Women's Ministry", "Men's Ministry",
        'Evangelism', 'Prayer Team',
    ]

    def __repr__(self):
        return f'<Department {self.name}>'


class DepartmentMember(db.Model):
    """Member assignment to a department."""

    __tablename__ = 'department_members'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey('departments.id'), nullable=False
    )
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    role = db.Column(db.String(50), default='member')  # member, leader, assistant
    joined_date = db.Column(db.Date, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    department = db.relationship('Department', back_populates='members')
    member = db.relationship('Member', back_populates='department_memberships')

    __table_args__ = (
        db.UniqueConstraint('department_id', 'member_id', name='uq_dept_member'),
    )
