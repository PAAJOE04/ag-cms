"""Member and family models."""
import uuid
from datetime import datetime

from app.extensions import db


class Family(db.Model):
    """Family grouping for members."""

    __tablename__ = 'families'

    id = db.Column(db.Integer, primary_key=True)
    family_name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('Member', back_populates='family', lazy='dynamic')

    def __repr__(self):
        return f'<Family {self.family_name}>'


class Member(db.Model):
    """Church member record."""

    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    membership_id = db.Column(
        db.String(20), unique=True, nullable=False, index=True
    )
    qr_code = db.Column(db.String(64), unique=True, default=lambda: str(uuid.uuid4()))
    first_name = db.Column(db.String(80), nullable=False, index=True)
    last_name = db.Column(db.String(80), nullable=False, index=True)
    middle_name = db.Column(db.String(80))
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    marital_status = db.Column(db.String(20))
    email = db.Column(db.String(120), index=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    occupation = db.Column(db.String(120))
    photo = db.Column(db.String(255))
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    membership_status = db.Column(
        db.String(20), default='active', index=True
    )  # active, inactive, transferred, deceased
    membership_date = db.Column(db.Date)
    baptism_date = db.Column(db.Date)
    baptism_place = db.Column(db.String(120))
    confirmation_date = db.Column(db.Date)
    confirmation_place = db.Column(db.String(120))
    notes = db.Column(db.Text)
    is_visitor = db.Column(db.Boolean, default=False)
    converted_from_visitor = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    family = db.relationship('Family', back_populates='members')
    emergency_contacts = db.relationship(
        'EmergencyContact', back_populates='member', cascade='all, delete-orphan'
    )
    department_memberships = db.relationship(
        'DepartmentMember', back_populates='member', lazy='dynamic'
    )
    attendances = db.relationship('Attendance', back_populates='member', lazy='dynamic')
    user_account = db.relationship(
        'User', back_populates='member', uselist=False,
        foreign_keys='User.member_id',
    )
    follow_ups = db.relationship('FollowUp', back_populates='member', lazy='dynamic')

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = datetime.utcnow().date()
        return (
            today.year - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @staticmethod
    def generate_membership_id():
        """Generate unique membership ID."""
        prefix = f'AG-{datetime.utcnow().year}-'
        ids = Member.query.filter(
            Member.membership_id.like(f'{prefix}%')
        ).with_entities(Member.membership_id).all()
        numbers = [
            int(row[0][len(prefix):])
            for row in ids
            if row[0][len(prefix):].isdigit()
        ]
        seq = (max(numbers) if numbers else 0) + 1
        return f'{prefix}{seq:05d}'

    def __repr__(self):
        return f'<Member {self.membership_id}: {self.full_name}>'


class EmergencyContact(db.Model):
    """Member emergency contact."""

    __tablename__ = 'emergency_contacts'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    relationship = db.Column(db.String(50))
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    is_primary = db.Column(db.Boolean, default=False)

    member = db.relationship('Member', back_populates='emergency_contacts')


class Visitor(db.Model):
    """First-time visitor tracking."""

    __tablename__ = 'visitors'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))
    visit_date = db.Column(db.Date, nullable=False, index=True)
    invited_by = db.Column(db.String(120))
    how_heard = db.Column(db.String(120))
    follow_up_status = db.Column(db.String(20), default='pending')
    converted_member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    converted_member = db.relationship('Member', foreign_keys=[converted_member_id])
