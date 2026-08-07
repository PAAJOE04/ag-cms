"""QR code generation service."""
import io

import qrcode


class QRService:
    """Generate QR codes."""

    @staticmethod
    def generate_qr_bytes(data, fill_color='#1E3A8A'):
        """Generate QR code as bytes for inline display."""
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
