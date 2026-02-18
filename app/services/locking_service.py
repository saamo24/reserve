"""Redis distributed locking to prevent race conditions on reservation create."""

from datetime import date, time
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings

LOCK_KEY_PREFIX = "lock:branch:"
LOCK_VALUE_PREFIX = "lockval:"


def _lock_key(branch_id: UUID, table_id: UUID, reservation_date: date, start_time: time) -> str:
    """Build Redis key for the slot lock."""
    d = reservation_date.isoformat()
    t = start_time.strftime("%H:%M:%S")
    return f"{LOCK_KEY_PREFIX}{branch_id}:table:{table_id}:date:{d}:start:{t}"


class LockingService:
    """Non-blocking distributed lock per (branch, table, date, start_time)."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._settings = get_settings()
        self._ttl = self._settings.lock_ttl_seconds

    async def acquire(
        self,
        branch_id: UUID,
        table_id: UUID,
        reservation_date: date,
        start_time: time,
        request_id: str | None = None,
    ) -> tuple[bool, str]:
        """
        Acquire lock. Non-blocking.
        Returns (True, request_id) if acquired, (False, "") otherwise.
        Caller must call release with the same request_id.
        """
        import uuid

        rid = request_id or str(uuid.uuid4())
        key = _lock_key(branch_id, table_id, reservation_date, start_time)
        value = f"{LOCK_VALUE_PREFIX}{rid}"
        ok = await self._redis.set(key, value, nx=True, ex=self._ttl)
        return (bool(ok), rid if ok else "")

    async def release(
        self,
        branch_id: UUID,
        table_id: UUID,
        reservation_date: date,
        start_time: time,
        request_id: str,
    ) -> None:
        """Release lock only if we hold it (value matches request_id)."""
        key = _lock_key(branch_id, table_id, reservation_date, start_time)
        value = f"{LOCK_VALUE_PREFIX}{request_id}"
        # Lua: delete only if value matches
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        end
        return 0
        """
        await self._redis.eval(script, 1, key, value)
