"""QR code generation for reservations (base64 PNG)."""

import base64
import io
from uuid import UUID

import qrcode


def generate_reservation_qr_base64(
    reservation_id: UUID,
    reservation_code: str,
    frontend_base_url: str,
    box_size: int = 6,
    border: int = 2,
) -> str:
    """
    Generate a QR code encoding the reservation detail URL. Returns base64-encoded PNG (no data URI prefix).
    """
    url = f"{frontend_base_url.rstrip('/')}/admin/reservations/{reservation_id}?code={reservation_code}"
    qr = qrcode.QRCode(box_size=box_size, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")
