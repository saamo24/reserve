"""Advanced time-slot engine: generate available slots per branch/date."""

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.repositories.branch_repository import BranchRepository
from app.repositories.reservation_repository import ReservationRepository
from app.services.caching_service import CachingService


def _slot_end(start: time, duration_minutes: int) -> time:
    """Compute end time of a slot."""
    from datetime import datetime as dt

    d = date(2000, 1, 1)
    start_dt = dt.combine(d, start)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return end_dt.time()


def _generate_slot_boundaries(
    opening_time: time,
    closing_time: time,
    slot_duration_minutes: int,
) -> list[tuple[time, time]]:
    """Generate (start, end) slot boundaries in local time. Exclude slots that end after closing."""
    from datetime import datetime as dt

    d = date(2000, 1, 1)
    slots: list[tuple[time, time]] = []
    start = datetime.combine(d, opening_time)
    end_bound = datetime.combine(d, closing_time)
    delta = timedelta(minutes=slot_duration_minutes)
    while start + delta <= end_bound:
        slot_end = (start + delta).time()
        slots.append((start.time(), slot_end))
        start += delta
    return slots


def _now_in_timezone(tz_name: str) -> datetime:
    """Current datetime in branch timezone."""
    return datetime.now(ZoneInfo(tz_name))


class TimeslotService:
    """Compute available time slots for a branch on a date."""

    def __init__(
        self,
        session: AsyncSession,
        branch_repo: BranchRepository,
        reservation_repo: ReservationRepository,
        caching: CachingService,
    ) -> None:
        self._session = session
        self._branch_repo = branch_repo
        self._reservation_repo = reservation_repo
        self._caching = caching

    async def get_available_slots(self, branch_id: UUID, d: date) -> list[dict]:
        """
        Return list of available slots for branch on date.
        Each slot: {"start_time": "HH:MM", "end_time": "HH:MM"}.
        Uses cache; invalidate on reservation create/cancel.
        """
        # Cache lookup
        cached = await self._caching.get_slots(branch_id, d)
        if cached is not None:
            return cached

        branch = await self._branch_repo.get_by_id(branch_id)
        if branch is None or not branch.is_active:
            return []

        opening = branch.opening_time
        closing = branch.closing_time
        duration = branch.slot_duration_minutes
        tz_name = branch.timezone

        boundaries = _generate_slot_boundaries(opening, closing, duration)
        now_dt = _now_in_timezone(tz_name)
        today_local = now_dt.date()

        # Past date
        if d < today_local:
            await self._caching.set_slots(branch_id, d, [])
            return []

        # Load all active reservations for this branch/date (one query)
        reservations = await self._reservation_repo.list_reservations_for_branch_date(
            branch_id, d
        )
        # Build set of (table_id, start_time, end_time) for overlap check
        occupied: set[tuple[UUID, time, time]] = set()
        for r in reservations:
            occupied.add((r.table_id, r.start_time, r.end_time))

        # Tables for this branch (we need table ids)
        from app.repositories.table_repository import TableRepository

        table_repo = TableRepository(self._session)
        tables = await table_repo.list_by_branch(branch_id, active_only=True)
        table_ids = {t.id for t in tables}
        if not table_ids:
            await self._caching.set_slots(branch_id, d, [])
            return []

        available: list[dict] = []
        for start_t, end_t in boundaries:
            # Filter out past slots (today only)
            if d == today_local:
                slot_start_dt = now_dt.replace(
                    hour=start_t.hour,
                    minute=start_t.minute,
                    second=0,
                    microsecond=0,
                )
                if slot_start_dt <= now_dt:
                    continue

            # Check if at least one table is free for this slot
            # Overlap: new_start < existing_end AND new_end > existing_start
            slot_free = False
            for tid in table_ids:
                any_overlap = False
                for (oid_tid, o_start, o_end) in occupied:
                    if oid_tid != tid:
                        continue
                    if start_t < o_end and end_t > o_start:
                        any_overlap = True
                        break
                if not any_overlap:
                    slot_free = True
                    break
            if slot_free:
                available.append({
                    "start_time": str(start_t.strftime("%H:%M")),
                    "end_time": str(end_t.strftime("%H:%M")),
                })

        await self._caching.set_slots(branch_id, d, available)
        return available
