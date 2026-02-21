"""FastAPI dependencies: DB session, Redis, config, pagination, auth."""

from uuid import UUID
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models.admin import Admin
from app.repositories.admin_repository import AdminRepository


async def get_config() -> Settings:
    """Return application settings."""
    return get_settings()


def pagination_params(
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> tuple[int, int]:
    """Return (skip, limit) for repository and (page, page_size) for meta."""
    return (page - 1) * page_size, page_size


# Security scheme for OpenAPI documentation (enables Authorize in Swagger)
security_scheme = HTTPBearer(scheme_name="HTTPBearer", auto_error=True)


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Admin:
    """Validate JWT and return the current admin. Raises 401 if invalid or missing."""
    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        admin_id = UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    repo = AdminRepository(db)
    admin = await repo.get_by_id(admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin


async def get_guest_id(request: Request) -> UUID:
    """Read guest_id from request state (set by GuestMiddleware). Raises 401 if missing."""
    guest_id = getattr(request.state, "guest_id", None)
    if guest_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest identification required",
        )
    return guest_id


# Type aliases for injection
ConfigDep = Annotated[Settings, Depends(get_config)]
GuestIdDep = Annotated[UUID, Depends(get_guest_id)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]
