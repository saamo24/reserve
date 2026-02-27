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
        load_guest: bool = False,
    ) -> Reservation | None:
        """Get reservation by id."""
        q = select(Reservation).where(Reservation.id == id)
        if load_branch:
            q = q.options(selectinload(Reservation.branch))
        if load_table:
            q = q.options(selectinload(Reservation.table))
        if load_guest:
            q = q.options(selectinload(Reservation.guest))
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

    async def get_by_code(
        self,
        code: str,
        *,
        load_branch: bool = False,
        load_table: bool = False,
        load_guest: bool = False,
    ) -> Reservation | None:
        """Get reservation by reservation_code only. Returns most recent if multiple exist."""
        q = select(Reservation).where(Reservation.reservation_code == code)
        # Order by created_at desc to get most recent if multiple exist (shouldn't happen due to unique constraint)
        q = q.order_by(Reservation.created_at.desc())
        if load_branch:
            q = q.options(selectinload(Reservation.branch))
        if load_table:
            q = q.options(selectinload(Reservation.table))
        if load_guest:
            q = q.options(selectinload(Reservation.guest))
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

    async def get_most_recent_by_phone_number(
        self,
        phone_number: str,
        *,
        load_branch: bool = False,
        load_table: bool = False,
        load_guest: bool = False,
    ) -> Reservation | None:
        """
        Get the most recent reservation by phone number.
        Uses flexible matching (normalizes phone numbers for comparison).
        
        Args:
            phone_number: Phone number to search for
            load_branch: Whether to load branch relationship
            load_table: Whether to load table relationship
            load_guest: Whether to load guest relationship
            
        Returns:
            Most recent reservation with the given phone number, or None if not found
        """
        from sqlalchemy import func
        
        # Normalize phone number: remove spaces, dashes, parentheses, keep + and digits
        # Also normalize to handle optional leading + sign
        normalized_search = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').strip()
        # Try with and without leading + for comparison
        normalized_search_with_plus = normalized_search if normalized_search.startswith('+') else f'+{normalized_search}'
        normalized_search_without_plus = normalized_search.lstrip('+')
        
        # Try exact match first
        q = (
            select(Reservation)
            .where(Reservation.phone_number == phone_number)
            .order_by(Reservation.created_at.desc())
            .limit(1)
        )
        if load_branch:
            q = q.options(selectinload(Reservation.branch))
        if load_table:
            q = q.options(selectinload(Reservation.table))
        if load_guest:
            q = q.options(selectinload(Reservation.guest))
        result = await self._session.execute(q)
        reservation = result.scalar_one_or_none()
        
        # If not found with exact match, try normalized comparison using database functions
        if reservation is None:
            # Use PostgreSQL REPLACE function to normalize phone numbers in the database
            # Normalize: remove spaces, dashes, parentheses
            normalized_db_phone = func.replace(
                func.replace(
                    func.replace(
                        func.replace(Reservation.phone_number, ' ', ''),
                        '-', ''
                    ),
                    '(', ''
                ),
                ')', ''
            )
            
            # Try matching with the normalized search (with +)
            q = (
                select(Reservation)
                .where(normalized_db_phone == normalized_search)
                .order_by(Reservation.created_at.desc())
                .limit(1)
            )
            if load_branch:
                q = q.options(selectinload(Reservation.branch))
            if load_table:
                q = q.options(selectinload(Reservation.table))
            if load_guest:
                q = q.options(selectinload(Reservation.guest))
            result = await self._session.execute(q)
            reservation = result.scalar_one_or_none()
            
            # If still not found, try matching without leading + (in case DB has + but search doesn't, or vice versa)
            if reservation is None:
                # Remove leading + from both sides for comparison
                normalized_db_phone_no_plus = func.ltrim(normalized_db_phone, '+')
                
                q = (
                    select(Reservation)
                    .where(normalized_db_phone_no_plus == normalized_search_without_plus)
                    .order_by(Reservation.created_at.desc())
                    .limit(1)
                )
                if load_branch:
                    q = q.options(selectinload(Reservation.branch))
                if load_table:
                    q = q.options(selectinload(Reservation.table))
                if load_guest:
                    q = q.options(selectinload(Reservation.guest))
                result = await self._session.execute(q)
                reservation = result.scalar_one_or_none()
        
        return reservation

    async def find_tg_chat_id_by_phone_number(self, phone_number: str) -> int | None:
        """
        Find tg_chat_id by searching reservations with the same phone number.
        Uses normalized phone number comparison for flexible matching.
        
        Searches for all reservations with the given phone number, finds their guests,
        and returns the first non-null tg_chat_id found.
        
        Args:
            phone_number: Phone number to search for
            
        Returns:
            Telegram chat ID if found, None otherwise
        """
        from sqlalchemy import func
        from app.models.guest import Guest
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        
        # Normalize phone number: remove spaces, dashes, parentheses, keep + and digits
        # Also normalize to handle optional leading + sign
        normalized_search = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').strip()
        normalized_search_without_plus = normalized_search.lstrip('+')
        
        # Try exact match first
        q = (
            select(Reservation.guest_id)
            .where(Reservation.phone_number == phone_number)
            .distinct()
        )
        result = await self._session.execute(q)
        guest_ids = [row[0] for row in result.all()]
        
        # If not found with exact match, try normalized comparison using database functions
        if not guest_ids:
            # Use PostgreSQL REPLACE function to normalize phone numbers in the database
            # Normalize: remove spaces, dashes, parentheses
            normalized_db_phone = func.replace(
                func.replace(
                    func.replace(
                        func.replace(Reservation.phone_number, ' ', ''),
                        '-', ''
                    ),
                    '(', ''
                ),
                ')', ''
            )
            
            # Try matching with the normalized search (with +)
            q = (
                select(Reservation.guest_id)
                .where(normalized_db_phone == normalized_search)
                .distinct()
            )
            result = await self._session.execute(q)
            guest_ids = [row[0] for row in result.all()]
            
            # If still not found, try matching without leading + (in case DB has + but search doesn't, or vice versa)
            if not guest_ids:
                # Remove leading + from both sides for comparison
                normalized_db_phone_no_plus = func.ltrim(normalized_db_phone, '+')
                
                q = (
                    select(Reservation.guest_id)
                    .where(normalized_db_phone_no_plus == normalized_search_without_plus)
                    .distinct()
                )
                result = await self._session.execute(q)
                guest_ids = [row[0] for row in result.all()]
        
        if not guest_ids:
            logger.debug(
                f"No reservations found for phone number {phone_number} "
                f"(normalized: {normalized_search})"
            )
            return None
        
        # Load guests and find one with tg_chat_id
        guest_q = select(Guest).where(
            Guest.id.in_(guest_ids),
            Guest.tg_chat_id.isnot(None)
        ).limit(1)
        guest_result = await self._session.execute(guest_q)
        guest = guest_result.scalar_one_or_none()
        
        if guest:
            logger.info(
                f"Found tg_chat_id {guest.tg_chat_id} for phone number {phone_number} "
                f"(normalized: {normalized_search}) via guest {guest.id} "
                f"(searched {len(guest_ids)} guest_ids)"
            )
        else:
            logger.debug(
                f"No tg_chat_id found for phone number {phone_number} "
                f"(normalized: {normalized_search}) "
                f"(searched {len(guest_ids)} guest_ids, none have tg_chat_id)"
            )
        
        return guest.tg_chat_id if guest else None

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
