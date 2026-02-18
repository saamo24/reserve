"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator
from typing import Annotated

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    echo=_settings.app_env == "development",
    pool_pre_ping=True,
    # READ COMMITTED isolation (default in PostgreSQL; explicit for clarity)
    isolation_level="READ COMMITTED",
)

# For Alembic migrations we need a non-pooled engine when running in same process
# (e.g. in tests). Production uses pooled engine above.
async_engine_migrations = create_async_engine(
    _settings.database_url,
    poolclass=NullPool,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency yielding an async database session. Caller controls commit/rollback."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Type alias for dependency injection
DbSession = Annotated[AsyncSession, "get_db"]
