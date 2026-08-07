"""Finance models."""
from datetime import datetime

from app.extensions import db


class TransactionCategory(db.Model):
    """Income/expense category."""

    __tablename__ = 'transaction_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # income, expense
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    transactions = db.relationship('Transaction', back_populates='category', lazy='dynamic')

    INCOME_CATEGORIES = [
        'Tithes', 'Offerings', 'Donations', 'Welfare',
        'Building Fund', 'Thanksgiving',
    ]
    EXPENSE_CATEGORIES = [
        'Utilities', 'Maintenance', 'Salaries',
        'Church Projects', 'Events',
    ]

    def __repr__(self):
        return f'<TransactionCategory {self.name} ({self.type})>'


class Transaction(db.Model):
    """Financial transaction record."""

    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, index=True)
    type = db.Column(db.String(10), nullable=False, index=True)  # income, expense
    category_id = db.Column(
        db.Integer, db.ForeignKey('transaction_categories.id'), nullable=False
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255))
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
    payment_method = db.Column(db.String(30))  # cash, check, transfer, mobile
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    category = db.relationship('TransactionCategory', back_populates='transactions')
    member = db.relationship('Member')
    recorded_by = db.relationship('User')
    receipt = db.relationship('Receipt', back_populates='transaction', uselist=False)

    @staticmethod
    def generate_reference():
        count = Transaction.query.count() + 1
        return f'TXN-{datetime.utcnow().strftime("%Y%m%d")}-{count:05d}'

    def __repr__(self):
        return f'<Transaction {self.reference}: {self.amount}>'


class Budget(db.Model):
    """Department or category budget."""

    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    period = db.Column(db.String(20), default='monthly')  # monthly, quarterly, yearly
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    category = db.relationship('TransactionCategory')
    department = db.relationship('Department')


class Receipt(db.Model):
    """Generated receipt for transactions."""

    __tablename__ = 'receipts'

    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(30), unique=True, nullable=False)
    transaction_id = db.Column(
        db.Integer, db.ForeignKey('transactions.id'), unique=True, nullable=False
    )
    issued_to = db.Column(db.String(120))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    issued_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    transaction = db.relationship('Transaction', back_populates='receipt')

    @staticmethod
    def generate_number():
        count = Receipt.query.count() + 1
        return f'RCP-{datetime.utcnow().strftime("%Y%m%d")}-{count:05d}'
