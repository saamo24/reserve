"""Redis async client and connection pool."""

from typing import Annotated

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings

_settings = get_settings()

_redis_client: Redis | None = None


async def get_redis() -> Redis:
    """Return Redis client (uses connection pool from URL)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            _settings.redis_url,
            max_connections=_settings.redis_pool_size,
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection pool (call on app shutdown)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# Type alias for dependency injection
RedisClient = Annotated[Redis, "get_redis"]
