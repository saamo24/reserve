"""Reservation business logic: create, get, list, update with locking and cache invalidation."""

from datetime import date, time, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.models.reservation import Reservation, ReservationStatus
from app.models.table import Table
from app.repositories.branch_repository import BranchRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.table_repository import TableRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.caching_service import CachingService
from app.services.email_service import EmailService
from app.services.locking_service import LockingService
from app.services.timeslot_service import TimeslotService
from app.utils.validators import get_now_in_timezone, time_in_range


def _slot_end(start: time, duration_minutes: int) -> time:
    from datetime import datetime as dt
    d = date(2000, 1, 1)
    start_dt = dt.combine(d, start)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return end_dt.time()


class ReservationService:
    """Create and manage reservations with lock and cache invalidation."""

    def __init__(
        self,
        session: AsyncSession,
        branch_repo: BranchRepository,
        table_repo: TableRepository,
        reservation_repo: ReservationRepository,
        locking: LockingService,
        caching: CachingService,
    ) -> None:
        self._session = session
        self._branch_repo = branch_repo
        self._table_repo = table_repo
        self._reservation_repo = reservation_repo
        self._locking = locking
        self._caching = caching

    async def create(self, body: ReservationCreate) -> Reservation:
        """
        Create reservation. Validates date, branch, time in hours; acquires lock;
        creates in transaction; invalidates cache; releases lock in finally.
        Raises: ValueError (validation), 404 (branch/table not found), 409 (conflict), 423 (locked).
        """
        branch = await self._branch_repo.get_by_id(body.branch_id)
        if branch is None or not branch.is_active:
            raise NotFoundError("Branch not found or inactive")

        if body.reservation_date < date.today():
            raise ValueError("Date cannot be in the past")

        end_time = _slot_end(body.start_time, branch.slot_duration_minutes)
        if not time_in_range(body.start_time, branch.opening_time, branch.closing_time):
            raise ValueError("Start time must be within branch working hours")
        if not time_in_range(end_time, branch.opening_time, branch.closing_time):
            raise ValueError("Slot end time must be within branch working hours")

        table_id: UUID
        if body.table_id is not None:
            table = await self._table_repo.get_by_id(body.table_id)
            if table is None or table.branch_id != branch.id or not table.is_active:
                raise NotFoundError("Table not found or not in this branch")
            table_id = table.id
        else:
            # Auto-assign: find first free table for this slot
            tables = await self._table_repo.list_by_branch(branch.id, active_only=True)
            table_id = await self._pick_available_table(
                tables, body.reservation_date, body.start_time, end_time
            )
            if table_id is None:
                raise ConflictError("No table available for this slot")

        # Acquire lock
        acquired, request_id = await self._locking.acquire(
            body.branch_id, table_id, body.reservation_date, body.start_time
        )
        if not acquired:
            raise LockedError("Slot is currently being booked; try again")

        try:
            # Re-check overlap inside transaction
            overlap = await self._reservation_repo.has_overlapping(
                table_id, body.reservation_date, body.start_time, end_time
            )
            if overlap:
                raise ConflictError("This slot was just taken")

            # Set status: PENDING if email provided, CONFIRMED otherwise
            initial_status = (
                ReservationStatus.PENDING if body.email else ReservationStatus.CONFIRMED
            )

            reservation = Reservation(
                branch_id=body.branch_id,
                table_id=table_id,
                full_name=body.full_name,
                phone_number=body.phone_number,
                email=body.email,
                reservation_date=body.reservation_date,
                start_time=body.start_time,
                end_time=end_time,
                status=initial_status,
                notes=body.notes,
            )
            await self._reservation_repo.create(reservation)
            await self._session.commit()

            # Invalidate caches
            await self._caching.invalidate_slots(body.branch_id, body.reservation_date)
            await self._caching.invalidate_tables(body.branch_id)

            # Reload reservation with relations for email sending
            reservation_with_relations = await self._reservation_repo.get_by_id(
                reservation.id, load_branch=True, load_table=True
            )
            if reservation_with_relations is None:
                reservation_with_relations = reservation

            # Send emails (non-blocking, errors logged but don't fail reservation)
            email_service = EmailService()
            try:
                # Send confirmation email to user if email provided
                if body.email:
                    await email_service.send_reservation_confirmation(reservation_with_relations)
                # Always send admin notification
                await email_service.send_admin_notification(reservation_with_relations)
            except Exception:
                # Log but don't fail - email is not critical for reservation creation
                pass

            return reservation_with_relations
        except IntegrityError:
            await self._session.rollback()
            raise ConflictError("This slot was just taken or duplicate reservation")
        except (ValueError, NotFoundError, ConflictError, LockedError):
            await self._session.rollback()
            raise
        except Exception:
            await self._session.rollback()
            raise
        finally:
            await self._locking.release(
                body.branch_id, table_id, body.reservation_date, body.start_time, request_id
            )

    async def _pick_available_table(
        self,
        tables: list[Table],
        reservation_date: date,
        start_time: time,
        end_time: time,
    ) -> UUID | None:
        """Return first table id that has no overlapping reservation."""
        for table in tables:
            overlap = await self._reservation_repo.has_overlapping(
                table.id, reservation_date, start_time, end_time
            )
            if not overlap:
                return table.id
        return None

    async def get_by_id(self, id: UUID, load_relations: bool = True) -> Reservation | None:
        """Get reservation by id (with branch and table loaded)."""
        return await self._reservation_repo.get_by_id(
            id, load_branch=load_relations, load_table=load_relations
        )

    async def confirm_reservation(self, id: UUID, token: str) -> Reservation | None:
        """Confirm a reservation via email token."""
        from app.utils.tokens import verify_reservation_token

        reservation = await self._reservation_repo.get_by_id(id, load_branch=True, load_table=True)
        if reservation is None:
            return None

        # Verify token
        verified_id = verify_reservation_token(token, "confirm")
        if verified_id != id:
            raise ValueError("Invalid or expired confirmation token")

        # Only allow confirmation if status is PENDING
        if reservation.status != ReservationStatus.PENDING:
            raise ValueError(f"Cannot confirm reservation with status {reservation.status.value}")

        # Update status
        old_status = reservation.status
        reservation.status = ReservationStatus.CONFIRMED
        await self._reservation_repo.update(reservation)
        await self._session.commit()

        # Invalidate cache
        await self._caching.invalidate_slots(reservation.branch_id, reservation.reservation_date)
        await self._caching.invalidate_tables(reservation.branch_id)

        # Send status update email
        email_service = EmailService()
        try:
            await email_service.send_reservation_status_update(reservation, old_status)
        except Exception:
            pass

        return reservation

    async def cancel_reservation(self, id: UUID, token: str) -> Reservation | None:
        """Cancel a reservation via email token."""
        from app.utils.tokens import verify_reservation_token

        reservation = await self._reservation_repo.get_by_id(id, load_branch=True, load_table=True)
        if reservation is None:
            return None

        # Verify token
        verified_id = verify_reservation_token(token, "cancel")
        if verified_id != id:
            raise ValueError("Invalid or expired cancellation token")

        # Only allow cancellation if status is PENDING
        if reservation.status != ReservationStatus.PENDING:
            raise ValueError(f"Cannot cancel reservation with status {reservation.status.value}")

        # Update status
        old_status = reservation.status
        reservation.status = ReservationStatus.CANCELLED
        await self._reservation_repo.update(reservation)
        await self._session.commit()

        # Invalidate cache
        await self._caching.invalidate_slots(reservation.branch_id, reservation.reservation_date)
        await self._caching.invalidate_tables(reservation.branch_id)

        # Send status update email
        email_service = EmailService()
        try:
            await email_service.send_reservation_status_update(reservation, old_status)
        except Exception:
            pass

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
        """List reservations (admin). Returns (items, total)."""
        return await self._reservation_repo.list_with_filters(
            branch_id=branch_id,
            reservation_date=reservation_date,
            status=status,
            phone_number=phone_number,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_desc=order_desc,
        )

    async def update(self, id: UUID, body: ReservationUpdate) -> Reservation | None:
        """Update reservation status/notes (admin). Invalidates cache if status/date/table changed."""
        reservation = await self._reservation_repo.get_by_id(id, load_branch=True, load_table=True)
        if reservation is None:
            return None

        # Track old status for email notification
        old_status = reservation.status

        if body.status is not None:
            reservation.status = body.status
        if body.notes is not None:
            reservation.notes = body.notes

        await self._reservation_repo.update(reservation)
        await self._session.commit()

        await self._caching.invalidate_slots(reservation.branch_id, reservation.reservation_date)
        await self._caching.invalidate_tables(reservation.branch_id)

        # Send status update email if status changed
        if body.status is not None and body.status != old_status:
            email_service = EmailService()
            try:
                await email_service.send_reservation_status_update(reservation, old_status)
            except Exception:
                # Log but don't fail - email is not critical
                pass

        return reservation


class NotFoundError(Exception):
    """Resource not found (404)."""
    pass


class ConflictError(Exception):
    """Conflict e.g. duplicate slot (409)."""
    pass


class LockedError(Exception):
    """Lock not acquired (423)."""
    pass
