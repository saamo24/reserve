"""Sign and verify guest_id for HTTP-only cookie. Isolates signing logic and secret usage."""

import logging
from uuid import UUID

from itsdangerous import BadSignature, URLSafeSerializer

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_GUEST_SALT = "guest_id"


def _serializer() -> URLSafeSerializer:
    """Return URLSafeSerializer with app secret and fixed salt."""
    settings = get_settings()
    return URLSafeSerializer(
        secret_key=settings.secret_key or "change-me-in-production",
        salt=_GUEST_SALT,
    )


def sign_guest_id(guest_id: UUID) -> str:
    """
    Serialize and sign a guest UUID for use as cookie value.

    Args:
        guest_id: The guest UUID to sign.

    Returns:
        Signed string safe for use as cookie value.
    """
    ser = _serializer()
    return ser.dumps(str(guest_id))


def verify_guest_id(signed: str) -> UUID | None:
    """
    Verify and deserialize a signed guest_id cookie value.

    Args:
        signed: The signed string from the cookie.

    Returns:
        The guest UUID if signature is valid, None otherwise.
    """
    if not signed or not isinstance(signed, str):
        return None
    try:
        ser = _serializer()
        value = ser.loads(signed)
        return UUID(value)
    except (BadSignature, ValueError, TypeError) as e:
        logger.debug("Invalid guest_id cookie: %s", e)
        return None
