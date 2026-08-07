"""Database seed script — creates roles, default data, and admin accounts."""
import os
import sys
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.member import Member, Visitor
from app.models.attendance import AttendanceType
from app.models.finance import TransactionCategory
from app.models.department import Department
from app.models.event import Event
from app.models.communication import Announcement
from app.utils.permissions import get_permissions_for_role

RECEIPT_CATEGORIES = {'Donations', 'Building Fund', 'Church Projects'}


def seed_roles():
    """Create RBAC roles."""
    roles_data = [
        (Role.DEVELOPER, 'System Developer', get_permissions_for_role('developer')),
        (Role.SUPER_ADMIN, 'Super Admin / Senior Pastor', get_permissions_for_role('super_admin')),
        (Role.CHURCH_ADMIN, 'Church Administrator', get_permissions_for_role('church_admin')),
        (Role.FINANCE_OFFICER, 'Finance Officer', get_permissions_for_role('finance_officer')),
        (Role.DEPT_LEADER, 'Department Leader', get_permissions_for_role('department_leader')),
        (Role.ATTENDANCE_OFFICER, 'Attendance Officer', get_permissions_for_role('attendance_officer')),
        (Role.MEMBER, 'Member', get_permissions_for_role('member')),
    ]
    for name, desc, perms in roles_data:
        if not Role.query.filter_by(name=name).first():
            db.session.add(Role(name=name, description=desc, permissions=perms))
    db.session.commit()
    print('✓ Roles seeded')


def seed_users():
    """Create default user accounts."""
    users = [
        ('developer', 'developer@agcms.local', 'Developer', 'Admin', Role.DEVELOPER, 'dev123456'),
        ('pastor', 'pastor@church.org', 'John', 'Mensah', Role.SUPER_ADMIN, 'admin123456'),
        ('secretary', 'secretary@church.org', 'Mary', 'Osei', Role.CHURCH_ADMIN, 'admin123456'),
        ('finance', 'finance@church.org', 'Kwame', 'Asante', Role.FINANCE_OFFICER, 'admin123456'),
        ('usher', 'usher@church.org', 'Ama', 'Boateng', Role.ATTENDANCE_OFFICER, 'admin123456'),
    ]
    for username, email, first, last, role_name, password in users:
        if not User.query.filter_by(username=username).first():
            role = Role.query.filter_by(name=role_name).first()
            user = User(
                username=username, email=email,
                first_name=first, last_name=last, role_id=role.id,
            )
            user.set_password(password)
            db.session.add(user)
    db.session.commit()
    print('✓ Users seeded')


def seed_attendance_types():
    """Create default attendance types."""
    types = [
        AttendanceType.SUNDAY_SERVICE, AttendanceType.MIDWEEK,
        AttendanceType.PRAYER_MEETING, AttendanceType.DEPT_MEETING,
        AttendanceType.CONFERENCE,
    ]
    for name in types:
        if not AttendanceType.query.filter_by(name=name).first():
            db.session.add(AttendanceType(name=name))
    db.session.commit()
    print('✓ Attendance types seeded')


def seed_transaction_categories():
    """Create income and expense categories."""
    for name in TransactionCategory.INCOME_CATEGORIES:
        cat = TransactionCategory.query.filter_by(name=name).first()
        if not cat:
            db.session.add(TransactionCategory(
                name=name, type='income',
                requires_receipt=name in RECEIPT_CATEGORIES,
            ))
    for name in TransactionCategory.EXPENSE_CATEGORIES:
        cat = TransactionCategory.query.filter_by(name=name).first()
        if not cat:
            db.session.add(TransactionCategory(
                name=name, type='expense',
                requires_receipt=name in RECEIPT_CATEGORIES,
            ))
    for name in RECEIPT_CATEGORIES:
        cat = TransactionCategory.query.filter_by(name=name).first()
        if cat and not cat.requires_receipt:
            cat.requires_receipt = True
    db.session.commit()
    print('✓ Transaction categories seeded')


def ensure_category_receipt_column():
    """Add requires_receipt column to transaction_categories if missing."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if 'transaction_categories' not in inspector.get_table_names():
        return
    columns = [col['name'] for col in inspector.get_columns('transaction_categories')]
    if 'requires_receipt' in columns:
        return
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text(
            'ALTER TABLE transaction_categories '
            'ADD COLUMN IF NOT EXISTS requires_receipt BOOLEAN'
        ))
    else:
        db.session.execute(text(
            'ALTER TABLE transaction_categories ADD COLUMN requires_receipt BOOLEAN'
        ))
    db.session.commit()
    print('✓ Added requires_receipt column')


def seed_departments():
    """Create default departments."""
    for name in Department.DEFAULT_DEPARTMENTS:
        if not Department.query.filter_by(name=name).first():
            db.session.add(Department(name=name))
    db.session.commit()
    print('✓ Departments seeded')


def seed_sample_members():
    """Create sample member records."""
    if Member.query.count() > 0:
        return

    first_names = ['Emmanuel', 'Grace', 'Samuel', 'Abigail', 'Daniel', 'Ruth',
                   'Joseph', 'Esther', 'David', 'Hannah', 'Michael', 'Sarah']
    last_names = ['Mensah', 'Osei', 'Asante', 'Boateng', 'Owusu', 'Agyemang',
                  'Appiah', 'Darko', 'Amoah', 'Frimpong']

    for i in range(30):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        member = Member(
            membership_id=f'AG-{datetime.utcnow().year}-{i+1:05d}',
            first_name=fn, last_name=ln,
            gender=random.choice(['Male', 'Female']),
            email=f'{fn.lower()}.{ln.lower()}@email.com',
            phone=f'+233-{random.randint(20,59)}-{random.randint(1000000,9999999)}',
            membership_status='active',
            membership_date=datetime.utcnow().date() - timedelta(days=random.randint(30, 1000)),
            date_of_birth=datetime(1970 + random.randint(0, 40), random.randint(1, 12), random.randint(1, 28)).date(),
        )
        db.session.add(member)
    db.session.commit()
    print('✓ Sample members seeded')


def seed_sample_data():
    """Create sample events, announcements, and transactions."""
    if Event.query.count() == 0:
        db.session.add(Event(
            title='Annual Church Conference 2026',
            description='Join us for three days of worship, teaching, and fellowship.',
            event_type='Conference',
            location='Main Auditorium',
            start_date=datetime.utcnow() + timedelta(days=30),
            end_date=datetime.utcnow() + timedelta(days=33),
            is_registration_required=True,
            created_by_id=1,
        ))
        db.session.add(Event(
            title='Youth Revival Service',
            event_type='Crusade',
            location='Youth Center',
            start_date=datetime.utcnow() + timedelta(days=14),
            created_by_id=1,
        ))

    if Announcement.query.count() == 0:
        db.session.add(Announcement(
            title='Welcome to AG CMS',
            content='We are excited to launch our new church management system. All members are encouraged to update their profiles.',
            category='news', priority='normal', created_by_id=1,
        ))

    db.session.commit()
    print('✓ Sample data seeded')


def main():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    with app.app_context():
        db.create_all()
        ensure_category_receipt_column()
        seed_roles()
        seed_users()
        seed_attendance_types()
        seed_transaction_categories()
        seed_departments()
        seed_sample_members()
        seed_sample_data()
        print('\n✅ Database seeded successfully!')
        print('\nDefault login credentials:')
        print('  Developer:  developer / dev123456')
        print('  Pastor:     pastor / admin123456')
        print('  Secretary:  secretary / admin123456')
        print('  Finance:    finance / admin123456')
        print('  Usher:      usher / admin123456')


if __name__ == '__main__':
    main()
