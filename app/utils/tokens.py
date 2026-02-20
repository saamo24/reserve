"""Token generation and verification for email confirmation links."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import get_settings


def _secret() -> str:
    """Get secret key for token signing."""
    settings = get_settings()
    return settings.secret_key or "change-me-in-production"


def create_reservation_token(reservation_id: UUID, action: str, expires_in_hours: int = 24) -> str:
    """
    Create a JWT token for reservation confirmation/cancellation.
    
    Args:
        reservation_id: The reservation UUID
        action: Either 'confirm' or 'cancel'
        expires_in_hours: Token expiration time in hours (default 24)
    
    Returns:
        JWT token string
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    payload = {
        "sub": str(reservation_id),
        "action": action,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "reservation_action",
    }
    return jwt.encode(
        payload,
        _secret(),
        algorithm=settings.jwt_algorithm,
    )


def verify_reservation_token(token: str, expected_action: str) -> UUID | None:
    """
    Verify and decode a reservation action token.
    
    Args:
        token: JWT token string
        expected_action: Expected action ('confirm' or 'cancel')
    
    Returns:
        Reservation UUID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[get_settings().jwt_algorithm],
        )
        
        # Verify token type and action
        if payload.get("type") != "reservation_action":
            return None
        
        if payload.get("action") != expected_action:
            return None
        
        reservation_id_str = payload.get("sub")
        if not reservation_id_str:
            return None
        
        return UUID(reservation_id_str)
    except (JWTError, ValueError):
        return None
