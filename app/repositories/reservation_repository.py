"""Reservation repository."""

from datetime import date, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reservation import Reservation, ReservationStatus
from app.repositories.base import AsyncRepository


class ReservationRepository(AsyncRepository[Reservation]):
    """Reservation DB access."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Reservation)

    async def get_by_id(
        self,
        id: UUID,
        *,
        load_branch: bool = False,
        load_table: bool = False,
    ) -> Reservation | None:
        """Get reservation by id."""
        q = select(Reservation).where(Reservation.id == id)
        if load_branch:
            q = q.options(selectinload(Reservation.branch))
        if load_table:
            q = q.options(selectinload(Reservation.table))
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def get_by_id_and_guest_id(
        self,
        id: UUID,
        guest_id: UUID,
        *,
        load_branch: bool = False,
        load_table: bool = False,
    ) -> Reservation | None:
        """Get reservation by id only if it belongs to the given guest. Returns None otherwise."""
        q = select(Reservation).where(
            Reservation.id == id,
            Reservation.guest_id == guest_id,
        )
        if load_branch:
            q = q.options(selectinload(Reservation.branch))
        if load_table:
            q = q.options(selectinload(Reservation.table))
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def get_by_id_and_code(
        self,
        id: UUID,
        code: str,
        *,
        load_branch: bool = False,
        load_table: bool = False,
    ) -> Reservation | None:
        """Get reservation by id and reservation_code (for success page / link sharing)."""
        q = select(Reservation).where(
            Reservation.id == id,
            Reservation.reservation_code == code,
        )
        if load_branch:
            q = q.options(selectinload(Reservation.branch))
        if load_table:
            q = q.options(selectinload(Reservation.table))
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def list_by_guest_id(
        self,
        guest_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Reservation], int]:
        """List reservations for a guest, newest first (date desc, start_time desc). Returns (items, total)."""
        base = select(Reservation).where(Reservation.guest_id == guest_id)
        count_q = select(func.count(Reservation.id)).where(
            Reservation.guest_id == guest_id
        )
        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one() or 0
        base = (
            base.order_by(
                Reservation.reservation_date.desc(),
                Reservation.start_time.desc(),
            )
            .offset(skip)
            .limit(limit)
            .options(
                selectinload(Reservation.branch),
                selectinload(Reservation.table),
            )
        )
        result = await self._session.execute(base)
        items = list(result.scalars().all())
        return items, total

    async def has_overlapping(
        self,
        table_id: UUID,
        reservation_date: date,
        start_time: time,
        end_time: time,
        exclude_reservation_id: UUID | None = None,
    ) -> bool:
        """Return True if there is an active reservation overlapping the given slot."""
        q = select(Reservation.id).where(
            Reservation.table_id == table_id,
            Reservation.reservation_date == reservation_date,
            Reservation.status.not_in([ReservationStatus.CANCELLED]),
            Reservation.start_time < end_time,
            Reservation.end_time > start_time,
        )
        if exclude_reservation_id is not None:
            q = q.where(Reservation.id != exclude_reservation_id)
        result = await self._session.execute(q)
        return result.scalar_one_or_none() is not None

    async def list_reservations_for_branch_date(
        self,
        branch_id: UUID,
        reservation_date: date,
    ) -> list[Reservation]:
        """Load all active reservations for a branch on a date (for slot computation)."""
        result = await self._session.execute(
            select(Reservation)
            .where(
                Reservation.branch_id == branch_id,
                Reservation.reservation_date == reservation_date,
                Reservation.status.not_in([ReservationStatus.CANCELLED]),
            )
        )
        return list(result.scalars().all())

    async def list_reserved_table_ids_for_slot(
        self,
        branch_id: UUID,
        reservation_date: date,
        start_time: time,
        end_time: time,
    ) -> list[UUID]:
        """Return table IDs that have an active reservation overlapping the given slot."""
        result = await self._session.execute(
            select(Reservation.table_id).where(
                Reservation.branch_id == branch_id,
                Reservation.reservation_date == reservation_date,
                Reservation.status.not_in([ReservationStatus.CANCELLED]),
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            )
        )
        return list({row[0] for row in result.all()})

    async def create(self, reservation: Reservation) -> Reservation:
        """Create reservation. Raises IntegrityError if partial unique violated."""
        return await self.add(reservation)

    async def update(self, reservation: Reservation) -> Reservation:
        """Update (flush)."""
        await self._session.flush()
        await self._session.refresh(reservation)
        return reservation

    async def list_with_filters(
        self,
        *,
        branch_id: UUID | None = None,
        reservation_date: date | None = None,
        status: ReservationStatus | None = None,
        phone_number: str | None = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "reservation_date",
        order_desc: bool = False,
    ) -> tuple[list[Reservation], int]:
        """List reservations with filters and pagination. Returns (items, total)."""
        base = select(Reservation)
        count_q = select(func.count(Reservation.id))

        if branch_id is not None:
            base = base.where(Reservation.branch_id == branch_id)
            count_q = count_q.where(Reservation.branch_id == branch_id)
        if reservation_date is not None:
            base = base.where(Reservation.reservation_date == reservation_date)
            count_q = count_q.where(Reservation.reservation_date == reservation_date)
        if status is not None:
            base = base.where(Reservation.status == status)
            count_q = count_q.where(Reservation.status == status)
        if phone_number is not None and phone_number.strip():
            base = base.where(Reservation.phone_number.ilike(f"%{phone_number.strip()}%"))
            count_q = count_q.where(Reservation.phone_number.ilike(f"%{phone_number.strip()}%"))

        total_result = await self._session.execute(count_q)
        total = total_result.scalar_one() or 0

        # Order
        order_col = getattr(Reservation, order_by, Reservation.reservation_date)
        if order_desc:
            base = base.order_by(order_col.desc())
        else:
            base = base.order_by(order_col.asc())
        base = base.offset(skip).limit(limit).options(
            selectinload(Reservation.branch),
            selectinload(Reservation.table),
        )
        result = await self._session.execute(base)
        items = list(result.scalars().all())
        return items, total
