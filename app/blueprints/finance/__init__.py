"""Finance management blueprint."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models.finance import Transaction, TransactionCategory, Budget, Receipt
from app.utils.decorators import permission_required
from app.utils.helpers import audit_action, format_currency, get_date_range, paginate_query

finance_bp = Blueprint('finance', __name__)


@finance_bp.route('/')
@login_required
@permission_required('finance:view')
def index():
    """Financial dashboard."""
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)

    income = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'income',
        Transaction.transaction_date >= month_start
    ).scalar() or 0)

    expenses = float(db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'expense',
        Transaction.transaction_date >= month_start
    ).scalar() or 0)

    recent = Transaction.query.order_by(
        Transaction.transaction_date.desc()
    ).limit(10).all()

    # Category breakdown for charts
    income_by_cat = db.session.query(
        TransactionCategory.name,
        func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Transaction.type == 'income',
        Transaction.transaction_date >= month_start
    ).group_by(TransactionCategory.name).all()

    expense_by_cat = db.session.query(
        TransactionCategory.name,
        func.sum(Transaction.amount)
    ).join(Transaction).filter(
        Transaction.type == 'expense',
        Transaction.transaction_date >= month_start
    ).group_by(TransactionCategory.name).all()

    return render_template(
        'finance/index.html',
        income=income,
        expenses=expenses,
        net=income - expenses,
        recent=recent,
        income_by_cat=income_by_cat,
        expense_by_cat=expense_by_cat,
    )


@finance_bp.route('/transactions')
@login_required
@permission_required('finance:view')
def transactions():
    """List transactions."""
    tx_type = request.args.get('type', '')
    query = Transaction.query
    if tx_type:
        query = query.filter_by(type=tx_type)
    records = paginate_query(query.order_by(Transaction.transaction_date.desc()))
    return render_template('finance/transactions.html', records=records, tx_type=tx_type)


@finance_bp.route('/record', methods=['GET', 'POST'])
@login_required
@permission_required('finance:create')
def record():
    """Record a financial transaction."""
    categories = TransactionCategory.query.filter_by(is_active=True).all()
    from app.models.member import Member
    members = Member.query.filter(
        Member.is_visitor == False,  # noqa: E712
        Member.membership_status == 'active',
    ).order_by(Member.first_name, Member.last_name).all()

    if request.method == 'POST':
        category = TransactionCategory.query.get(
            request.form.get('category_id', type=int)
        )
        if category is None:
            flash('Please select a category before saving.', 'danger')
            return redirect(url_for('finance.record'))

        payer_name = request.form.get('payer_name', '').strip()
        wants_receipt = (
            category.requires_receipt
            and bool(request.form.get('generate_receipt'))
        )

        if (
            category.requires_name
            and category.type == 'income'
            and not payer_name
        ):
            flash(f'Please enter the name of the giver for {category.name}.', 'danger')
            return redirect(url_for('finance.record'))

        tx = Transaction(
            reference=Transaction.generate_reference(),
            type=request.form['type'],
            category_id=category.id,
            amount=request.form['amount'],
            description=request.form.get('description'),
            payer_name=payer_name,
            member_id=request.form.get('member_id', type=int) or None,
            payment_method=request.form.get('payment_method'),
            transaction_date=datetime.strptime(
                request.form['transaction_date'], '%Y-%m-%d'
            ).date(),
            recorded_by_id=current_user.id,
        )
        db.session.add(tx)
        db.session.flush()

        receipt_id = None
        if wants_receipt:
            receipt = Receipt(
                receipt_number=Receipt.generate_number(),
                transaction_id=tx.id,
                issued_to=payer_name,
                issued_by_id=current_user.id,
            )
            db.session.add(receipt)
            db.session.flush()
            receipt_id = receipt.id

        audit_action('create', 'finance', f'Recorded {tx.type} transaction {tx.reference}')
        db.session.commit()
        flash(f'Transaction {tx.reference} recorded.', 'success')
        if receipt_id:
            return redirect(url_for('finance.receipt', id=receipt_id))
        return redirect(url_for('finance.transactions'))

    return render_template(
        'finance/record.html',
        categories=categories,
        members=members,
        today=datetime.utcnow().date(),
    )


@finance_bp.route('/receipts')
@login_required
@permission_required('finance:view')
def receipts():
    """List issued receipts."""
    records = paginate_query(Receipt.query.order_by(Receipt.issued_at.desc()))
    return render_template('finance/receipts.html', records=records)


@finance_bp.route('/receipt/<int:id>')
@login_required
@permission_required('finance:view')
def receipt(id):
    """Preview / print a receipt."""
    receipt = Receipt.query.get_or_404(id)
    return render_template('finance/receipt.html', receipt=receipt)


@finance_bp.route('/budgets')
@login_required
@permission_required('finance:view')
def budgets():
    """Budget management."""
    year = request.args.get('year', datetime.utcnow().year, type=int)
    budgets_list = Budget.query.filter_by(year=year).all()
    categories = TransactionCategory.query.filter_by(type='expense', is_active=True).all()
    return render_template('finance/budgets.html', budgets=budgets_list, year=year, categories=categories)


@finance_bp.route('/budgets/create', methods=['POST'])
@login_required
@permission_required('finance:create')
def create_budget():
    """Create a budget entry."""
    budget = Budget(
        name=request.form['name'],
        category_id=request.form.get('category_id', type=int) or None,
        amount=request.form['amount'],
        period=request.form.get('period', 'monthly'),
        year=request.form.get('year', datetime.utcnow().year, type=int),
        month=request.form.get('month', type=int),
        notes=request.form.get('notes'),
        created_by_id=current_user.id,
    )
    db.session.add(budget)
    db.session.commit()
    flash('Budget created.', 'success')
    return redirect(url_for('finance.budgets'))
