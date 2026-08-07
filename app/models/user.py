"""User and role models."""
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Role(db.Model):
    """RBAC role definition."""

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    permissions = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', back_populates='role', lazy='dynamic')

    # Role constants
    DEVELOPER = 'developer'
    SUPER_ADMIN = 'super_admin'
    CHURCH_ADMIN = 'church_admin'
    FINANCE_OFFICER = 'finance_officer'
    DEPT_LEADER = 'department_leader'
    ATTENDANCE_OFFICER = 'attendance_officer'
    MEMBER = 'member'

    ROLE_HIERARCHY = {
        DEVELOPER: 100,
        SUPER_ADMIN: 90,
        CHURCH_ADMIN: 70,
        FINANCE_OFFICER: 60,
        DEPT_LEADER: 50,
        ATTENDANCE_OFFICER: 40,
        MEMBER: 10,
    }

    def has_permission(self, permission):
        """Check if role grants a specific permission."""
        perms = self.permissions or {}
        if perms.get('all'):
            return True
        module, action = permission.split(':') if ':' in permission else (permission, 'view')
        module_perms = perms.get(module, [])
        return 'all' in module_perms or action in module_perms

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """Application user account."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20))
    avatar = db.Column(db.String(255))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), unique=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    role = db.relationship('Role', back_populates='users')
    member = db.relationship(
        'Member', back_populates='user_account', uselist=False,
        foreign_keys=[member_id],
    )
    department = db.relationship('Department', foreign_keys=[department_id])
    login_history = db.relationship('LoginHistory', back_populates='user', lazy='dynamic')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def role_name(self):
        return self.role.name if self.role else None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_developer(self):
        return self.role_name == Role.DEVELOPER

    def is_super_admin(self):
        return self.role_name == Role.SUPER_ADMIN

    def has_permission(self, permission):
        if not self.is_active or self.is_locked:
            return False
        if not self.role:
            return False
        if self.role_name == Role.DEVELOPER:
            return True
        return self.role.has_permission(permission)

    def can_manage_user(self, target_user):
        """Check if this user can manage another user."""
        if self.is_developer():
            return True
        if target_user.is_developer():
            return False
        my_level = Role.ROLE_HIERARCHY.get(self.role_name, 0)
        target_level = Role.ROLE_HIERARCHY.get(target_user.role_name, 0)
        return my_level > target_level

    def __repr__(self):
        return f'<User {self.username}>'


class LoginHistory(db.Model):
    """Login attempt audit trail."""

    __tablename__ = 'login_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))
    success = db.Column(db.Boolean, default=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', back_populates='login_history')
