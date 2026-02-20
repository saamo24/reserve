"""JWT and password hashing for admin auth."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(plain: str) -> str:
    """Hash a plain password for storage (bcrypt)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _secret() -> str:
    settings = get_settings()
    return (settings.jwt_secret_key or settings.secret_key) or "change-me-in-production"


def create_access_token(subject: str | UUID) -> str:
    """Create a short-lived access JWT. Subject is admin id (str)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(
        payload,
        _secret(),
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str | UUID) -> str:
    """Create a long-lived refresh JWT. Subject is admin id (str)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        _secret(),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT. Returns payload dict or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[get_settings().jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
