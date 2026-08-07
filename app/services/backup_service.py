"""Database backup service."""
import os
import shutil
from datetime import datetime


class BackupService:
    """Handle database backups."""

    @staticmethod
    def create_backup(app):
        """Create a backup of the SQLite database."""
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not db_uri.startswith('sqlite'):
            return {'success': False, 'message': 'Backup only supported for SQLite in dev mode'}

        db_path = db_uri.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            return {'success': False, 'message': 'Database file not found'}

        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'ag_cms_backup_{timestamp}.db')
        shutil.copy2(db_path, backup_path)

        return {
            'success': True,
            'message': f'Backup created: {backup_path}',
            'path': backup_path,
        }

    @staticmethod
    def list_backups():
        """List available backups."""
        backup_dir = 'backups'
        if not os.path.exists(backup_dir):
            return []
        return sorted(
            [f for f in os.listdir(backup_dir) if f.endswith('.db')],
            reverse=True
        )

    @staticmethod
    def restore_backup(backup_filename, app):
        """Restore from a backup file."""
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if not db_uri.startswith('sqlite'):
            return {'success': False, 'message': 'Restore only supported for SQLite'}

        backup_path = os.path.join('backups', backup_filename)
        if not os.path.exists(backup_path):
            return {'success': False, 'message': 'Backup file not found'}

        db_path = db_uri.replace('sqlite:///', '')
        shutil.copy2(backup_path, db_path)
        return {'success': True, 'message': f'Restored from {backup_filename}'}
