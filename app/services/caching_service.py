"""Redis caching for slots and tables."""

import json
from datetime import date
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings

SLOTS_KEY_PREFIX = "slots:"
TABLES_KEY_PREFIX = "tables:"


def _slots_key(branch_id: UUID, d: date) -> str:
    return f"{SLOTS_KEY_PREFIX}{branch_id}:{d.isoformat()}"


def _tables_key(branch_id: UUID) -> str:
    return f"{TABLES_KEY_PREFIX}{branch_id}"


class CachingService:
    """Cache for available slots and active tables per branch."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._settings = get_settings()
        self._slots_ttl = self._settings.cache_slots_ttl
        self._tables_ttl = self._settings.cache_tables_ttl

    async def get_slots(self, branch_id: UUID, d: date) -> list[dict] | None:
        """Return cached slots list or None if miss."""
        key = _slots_key(branch_id, d)
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_slots(self, branch_id: UUID, d: date, slots: list[dict]) -> None:
        """Cache slots list."""
        key = _slots_key(branch_id, d)
        await self._redis.set(key, json.dumps(slots), ex=self._slots_ttl)

    async def invalidate_slots(self, branch_id: UUID, d: date) -> None:
        """Invalidate slots cache for branch/date."""
        key = _slots_key(branch_id, d)
        await self._redis.delete(key)

    async def get_tables(self, branch_id: UUID) -> list[dict] | None:
        """Return cached tables list or None if miss."""
        key = _tables_key(branch_id)
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_tables(self, branch_id: UUID, tables: list[dict]) -> None:
        """Cache tables list."""
        key = _tables_key(branch_id)
        await self._redis.set(key, json.dumps(tables), ex=self._tables_ttl)

    async def invalidate_tables(self, branch_id: UUID) -> None:
        """Invalidate tables cache for branch."""
        key = _tables_key(branch_id)
        await self._redis.delete(key)
