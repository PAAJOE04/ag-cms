"""Application configuration."""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.getenv('SESSION_TIMEOUT_MINUTES', 30))
    )
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION_MINUTES = int(os.getenv('LOCKOUT_DURATION_MINUTES', 15))

    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    CHURCH_NAME = os.getenv('CHURCH_NAME', 'Grace Community Church')
    CHURCH_ADDRESS = os.getenv('CHURCH_ADDRESS', '')
    CHURCH_PHONE = os.getenv('CHURCH_PHONE', '')
    CHURCH_EMAIL = os.getenv('CHURCH_EMAIL', '')

    CURRENCY_SYMBOL = os.getenv('CURRENCY_SYMBOL', 'GH₵')
    CURRENCY_CODE = os.getenv('CURRENCY_CODE', 'GHS')

    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

    SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'log')  # log, twilio
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER', '')

    ITEMS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 'sqlite:///ag_cms.db'
    )
    AUTO_SEED = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    AUTO_SEED = True

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError('DATABASE_URL must be set in production')


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
