"""Attendance models."""
from datetime import datetime

from app.extensions import db


class AttendanceType(db.Model):
    """Attendance service/meeting type."""

    __tablename__ = 'attendance_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    attendances = db.relationship('Attendance', back_populates='attendance_type', lazy='dynamic')

    # Default types
    SUNDAY_SERVICE = 'Sunday Service'
    MIDWEEK = 'Midweek Service'
    PRAYER_MEETING = 'Prayer Meeting'
    DEPT_MEETING = 'Department Meeting'
    CONFERENCE = 'Conference'

    def __repr__(self):
        return f'<AttendanceType {self.name}>'


class Attendance(db.Model):
    """Member attendance record."""

    __tablename__ = 'attendances'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False, index=True)
    attendance_type_id = db.Column(
        db.Integer, db.ForeignKey('attendance_types.id'), nullable=False
    )
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    date = db.Column(db.Date, nullable=False, index=True)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    check_in_method = db.Column(db.String(20), default='manual')  # qr, manual, search
    notes = db.Column(db.String(255))
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    member = db.relationship('Member', back_populates='attendances')
    attendance_type = db.relationship('AttendanceType', back_populates='attendances')
    department = db.relationship('Department')
    event = db.relationship('Event')
    recorded_by = db.relationship('User')

    __table_args__ = (
        db.UniqueConstraint(
            'member_id', 'attendance_type_id', 'date',
            name='uq_member_attendance_date'
        ),
        db.Index('ix_attendance_date_type', 'date', 'attendance_type_id'),
    )

    def __repr__(self):
        return f'<Attendance {self.member_id} on {self.date}>'
