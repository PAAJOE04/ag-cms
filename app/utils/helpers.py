"""General utility helpers."""
import os
import uuid
from datetime import datetime

from flask import current_app, request
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.audit import AuditLog


def allowed_file(filename):
    """Check if file extension is allowed."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower()
        in current_app.config['ALLOWED_EXTENSIONS']
    )


def save_upload(file, subfolder=''):
    """Save uploaded file and return relative path."""
    if not file or not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'{uuid.uuid4().hex}.{ext}'
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    return os.path.join(subfolder, filename).replace('\\', '/')


def audit_action(action, module, description=None, resource_type=None,
                 resource_id=None, old_values=None, new_values=None):
    """Log an audit action for the current user."""
    from flask_login import current_user

    user_id = current_user.id if current_user.is_authenticated else None
    AuditLog.log(
        user_id=user_id,
        action=action,
        module=module,
        description=description,
        ip_address=request.remote_addr,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values,
    )
    db.session.commit()


def paginate_query(query, page=None, per_page=None):
    """Paginate a SQLAlchemy query."""
    page = page or request.args.get('page', 1, type=int)
    per_page = per_page or current_app.config.get('ITEMS_PER_PAGE', 20)
    return query.paginate(page=page, per_page=per_page, error_out=False)


def format_currency(amount):
    """Format amount as currency string."""
    if amount is None:
        return '$0.00'
    return f'${float(amount):,.2f}'


def get_date_range(period):
    """Return start/end dates for a reporting period."""
    today = datetime.utcnow().date()
    if period == 'daily':
        return today, today
    if period == 'weekly':
        start = today - __import__('datetime').timedelta(days=today.weekday())
        return start, today
    if period == 'monthly':
        start = today.replace(day=1)
        return start, today
    if period == 'yearly':
        start = today.replace(month=1, day=1)
        return start, today
    return today, today
