"""QR code generation service."""
import io
import os

import qrcode
from flask import current_app, url_for


class QRService:
    """Generate QR codes for member check-in."""

    @staticmethod
    def generate_member_qr(member):
        """Generate QR code image for a member."""
        check_in_url = url_for(
            'attendance.qr_checkin',
            qr_code=member.qr_code,
            _external=True
        )

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(check_in_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color='#1E3A8A', back_color='white')

        qr_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qr_codes')
        os.makedirs(qr_dir, exist_ok=True)
        filepath = os.path.join(qr_dir, f'{member.membership_id}.png')
        img.save(filepath)

        return f'qr_codes/{member.membership_id}.png'

    @staticmethod
    def generate_qr_bytes(data):
        """Generate QR code as bytes for inline display."""
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1E3A8A', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
