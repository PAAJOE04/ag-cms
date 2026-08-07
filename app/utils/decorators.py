"""Custom decorators for access control."""
from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def permission_required(permission):
    """Require a specific permission to access a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not current_user.has_permission(permission):
                flash('You do not have permission to access this resource.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(*roles):
    """Require one of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role_name not in roles:
                flash('Access denied for your role.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
