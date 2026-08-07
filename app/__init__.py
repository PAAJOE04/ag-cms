"""AG CMS application factory."""
import os
from datetime import datetime

from flask import Flask

from app.config import config
from app.extensions import csrf, db, login_manager, migrate


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    _ensure_directories(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_context_processors(app)
    _register_error_handlers(app)

    return app


def _ensure_directories(app):
    """Create required runtime directories."""
    for folder in (app.config['UPLOAD_FOLDER'], 'backups', 'instance'):
        os.makedirs(folder, exist_ok=True)


def _init_extensions(app):
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


def _register_blueprints(app):
    """Register application blueprints."""
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.members import members_bp
    from app.blueprints.attendance import attendance_bp
    from app.blueprints.finance import finance_bp
    from app.blueprints.events import events_bp
    from app.blueprints.departments import departments_bp
    from app.blueprints.communication import communication_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.ai import ai_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(members_bp, url_prefix='/members')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(finance_bp, url_prefix='/finance')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(departments_bp, url_prefix='/departments')
    app.register_blueprint(communication_bp, url_prefix='/communication')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/v1')


def _register_context_processors(app):
    """Register Jinja2 context processors."""

    @app.context_processor
    def inject_globals():
        return {
            'church_name': app.config.get('CHURCH_NAME', 'AG CMS'),
            'current_year': datetime.utcnow().year,
            'currency_symbol': app.config.get('CURRENCY_SYMBOL', 'GH₵'),
        }


def _register_error_handlers(app):
    """Register HTTP error handlers."""
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500
