"""Authentication blueprint."""
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models.user import LoginHistory, User
from app.utils.helpers import audit_action

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.is_locked and user.locked_until:
            if user.locked_until > datetime.utcnow():
                flash('Account is locked. Try again later.', 'danger')
                _log_attempt(user.id, False)
                return render_template('auth/login.html')

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return render_template('auth/login.html')

            user.failed_login_attempts = 0
            user.is_locked = False
            user.locked_until = None
            user.last_login = datetime.utcnow()
            user.last_login_ip = request.remote_addr
            db.session.commit()

            login_user(user, remember=bool(remember))
            _log_attempt(user.id, True)
            audit_action('login', 'auth', f'User {user.username} logged in')

            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))

        if user:
            user.failed_login_attempts += 1
            max_attempts = __import__('flask').current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
            if user.failed_login_attempts >= max_attempts:
                lockout = __import__('flask').current_app.config.get('LOCKOUT_DURATION_MINUTES', 15)
                user.is_locked = True
                user.locked_until = datetime.utcnow() + timedelta(minutes=lockout)
                flash(f'Account locked for {lockout} minutes due to failed attempts.', 'danger')
            else:
                flash('Invalid username or password.', 'danger')
            db.session.commit()
            _log_attempt(user.id, False)
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    audit_action('logout', 'auth', f'User {current_user.username} logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    """View user profile."""
    return render_template('auth/profile.html')


def _log_attempt(user_id, success):
    """Record login attempt."""
    entry = LoginHistory(
        user_id=user_id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:512] if request.user_agent else None,
        success=success,
    )
    db.session.add(entry)
    db.session.commit()
