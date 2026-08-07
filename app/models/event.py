"""Event models."""
from datetime import datetime

from app.extensions import db


class Event(db.Model):
    """Church event."""

    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    location = db.Column(db.String(255))
    start_date = db.Column(db.DateTime, nullable=False, index=True)
    end_date = db.Column(db.DateTime)
    max_attendees = db.Column(db.Integer)
    is_registration_required = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, ongoing, completed, cancelled
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    department = db.relationship('Department', back_populates='events')
    registrations = db.relationship(
        'EventRegistration', back_populates='event', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    volunteers = db.relationship(
        'EventVolunteer', back_populates='event', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    EVENT_TYPES = [
        'Conference', 'Seminar', 'Retreat', 'Wedding',
        'Funeral', 'Crusade', 'Service', 'Meeting', 'Other',
    ]

    def __repr__(self):
        return f'<Event {self.title}>'


class EventRegistration(db.Model):
    """Event attendee registration."""

    __tablename__ = 'event_registrations'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    guest_name = db.Column(db.String(120))
    guest_email = db.Column(db.String(120))
    guest_phone = db.Column(db.String(20))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='registered')

    event = db.relationship('Event', back_populates='registrations')
    member = db.relationship('Member')

    __table_args__ = (
        db.UniqueConstraint('event_id', 'member_id', name='uq_event_member'),
    )


class EventVolunteer(db.Model):
    """Event volunteer assignment."""

    __tablename__ = 'event_volunteers'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    role = db.Column(db.String(80))
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', back_populates='volunteers')
    member = db.relationship('Member')

    __table_args__ = (
        db.UniqueConstraint('event_id', 'member_id', name='uq_event_volunteer'),
    )
