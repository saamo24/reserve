"""Reservation business logic: create, get, list, update with locking and cache invalidation."""

import secrets
from datetime import date, time, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.models.reservation import Reservation, ReservationStatus
from app.models.table import Table
from app.repositories.branch_repository import BranchRepository
from app.repositories.guest_repository import GuestRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.table_repository import TableRepository
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.caching_service import CachingService
from app.services.locking_service import LockingService
from app.services.timeslot_service import TimeslotService
from app.core.config import get_settings
from app.utils.qr_code import generate_reservation_qr_base64
from app.utils.validators import time_in_range


def _generate_reservation_code() -> str:
    """Return an 8-character random string for reservation lookup."""
    return secrets.token_hex(4)


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
        guest_repo: GuestRepository,
        locking: LockingService,
        caching: CachingService,
    ) -> None:
        self._session = session
        self._branch_repo = branch_repo
        self._table_repo = table_repo
        self._reservation_repo = reservation_repo
        self._guest_repo = guest_repo
        self._locking = locking
        self._caching = caching

    async def create(self, body: ReservationCreate, guest_id: UUID) -> Reservation:
        """
        Create reservation. Validates date, branch, time in hours; acquires lock;
        creates in transaction; invalidates cache; releases lock in finally.
        guest_id is taken from signed cookie only (never from body).
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
        table: Table | None = None
        if body.table_id is not None:
            table = await self._table_repo.get_by_id(body.table_id)
            if table is None or table.branch_id != branch.id or not table.is_active:
                raise NotFoundError("Table not found or not in this branch")
            table_id = table.id
            # Validate number of guests against table capacity
            if body.number_of_guests > table.capacity:
                raise ValueError(
                    f"Number of guests ({body.number_of_guests}) exceeds table capacity ({table.capacity})"
                )
        else:
            # Auto-assign: find first free table for this slot that can accommodate the guests
            tables = await self._table_repo.list_by_branch(branch.id, active_only=True)
            # Filter tables by capacity first
            suitable_tables = [t for t in tables if t.capacity >= body.number_of_guests]
            if not suitable_tables:
                raise ValueError(
                    f"No table available that can accommodate {body.number_of_guests} guests"
                )
            table_id = await self._pick_available_table(
                suitable_tables, body.reservation_date, body.start_time, end_time
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

            # Ensure guest exists (create if needed)
            await self._guest_repo.get_or_create(guest_id)

            # Always PENDING on create; CONFIRMED only after user confirms via email or Telegram
            initial_status = ReservationStatus.PENDING

            reservation_code = _generate_reservation_code()
            reservation = Reservation(
                guest_id=guest_id,
                reservation_code=reservation_code,
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
            # Save reservation first to get the ID
            await self._reservation_repo.create(reservation)
            await self._session.flush()  # Flush to get the ID without committing
            
            # Now generate QR code with the actual reservation ID
            settings = get_settings()
            reservation.qr_code_base64 = generate_reservation_qr_base64(
                reservation.id,
                reservation_code,
                settings.frontend_base_url,
            )
            await self._session.commit()

            # Invalidate caches
            await self._caching.invalidate_slots(body.branch_id, body.reservation_date)
            await self._caching.invalidate_tables(body.branch_id)

            # Reload reservation with relations for notifications
            reservation_with_relations = await self._reservation_repo.get_by_id(
                reservation.id, load_branch=True, load_table=True
            )
            if reservation_with_relations is None:
                reservation_with_relations = reservation

            # Enqueue notification task via Celery (non-blocking)
            # Lazy import to avoid circular dependency
            from app.tasks.notifications import send_reservation_created_notification
            send_reservation_created_notification.delay(str(reservation.id))

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

    async def get_by_id_and_guest(
        self, id: UUID, guest_id: UUID, load_relations: bool = True
    ) -> Reservation | None:
        """Get reservation by id only if it belongs to the guest. Returns None otherwise."""
        return await self._reservation_repo.get_by_id_and_guest_id(
            id, guest_id, load_branch=load_relations, load_table=load_relations
        )

    async def get_by_id_and_code(
        self, id: UUID, code: str, load_relations: bool = True
    ) -> Reservation | None:
        """Get reservation by id and reservation_code (e.g. for success page link)."""
        return await self._reservation_repo.get_by_id_and_code(
            id, code, load_branch=load_relations, load_table=load_relations
        )

    async def attach_to_guest(
        self, reservation_id: UUID, code: str, guest_id: UUID
    ) -> Reservation | None:
        """Link a reservation to the current guest by proving ownership with id+code. Returns updated reservation or None."""
        reservation = await self._reservation_repo.get_by_id_and_code(
            reservation_id, code, load_branch=False, load_table=False
        )
        if reservation is None:
            return None
        reservation.guest_id = guest_id
        await self._reservation_repo.update(reservation)
        await self._session.commit()
        reservation = await self._reservation_repo.get_by_id(
            reservation_id, load_branch=True, load_table=True, load_guest=True
        )
        # Same as email: when sending to Telegram, keep PENDING until user confirms/cancels in TG
        if (
            reservation
            and reservation.guest
            and reservation.guest.tg_chat_id
            and reservation.status == ReservationStatus.CONFIRMED
        ):
            reservation.status = ReservationStatus.PENDING
            await self._reservation_repo.update(reservation)
            await self._session.commit()
            reservation = await self._reservation_repo.get_by_id(
                reservation_id, load_branch=True, load_table=True, load_guest=True
            )
        return reservation

    async def attach_to_guest_by_id(
        self, reservation_id: UUID, guest_id: UUID
    ) -> Reservation | None:
        """Link a reservation to the current guest by id only. For local dev only (no code check)."""
        reservation = await self._reservation_repo.get_by_id(
            reservation_id, load_branch=False, load_table=False
        )
        if reservation is None:
            return None
        reservation.guest_id = guest_id
        await self._reservation_repo.update(reservation)
        await self._session.commit()
        reservation = await self._reservation_repo.get_by_id(
            reservation_id, load_branch=True, load_table=True, load_guest=True
        )
        if (
            reservation
            and reservation.guest
            and reservation.guest.tg_chat_id
            and reservation.status == ReservationStatus.CONFIRMED
        ):
            reservation.status = ReservationStatus.PENDING
            await self._reservation_repo.update(reservation)
            await self._session.commit()
            reservation = await self._reservation_repo.get_by_id(
                reservation_id, load_branch=True, load_table=True, load_guest=True
            )
        return reservation

    async def list_my_reservations(
        self, guest_id: UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[Reservation], int]:
        """List reservations for the given guest, newest first. Returns (items, total)."""
        return await self._reservation_repo.list_by_guest_id(
            guest_id, skip=skip, limit=limit
        )

    async def confirm_reservation(self, id: UUID, token: str) -> Reservation | None:
        """Confirm a reservation via email token."""
        from app.utils.tokens import verify_reservation_token

        reservation = await self._reservation_repo.get_by_id(id, load_branch=True, load_table=True, load_guest=True)
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

        # Reload reservation with all relations and QR code to ensure we have complete data for notifications
        reservation = await self._reservation_repo.get_by_id(
            reservation.id, load_branch=True, load_table=True, load_guest=True
        )

        # Enqueue notification task via Celery (non-blocking)
        # Note: Status update notifications are handled by email service in the task
        # This is for confirmation, so we don't need a separate cancellation task here

        return reservation

    async def cancel_reservation(self, id: UUID, token: str) -> Reservation | None:
        """Cancel a reservation via email token."""
        from app.utils.tokens import verify_reservation_token

        reservation = await self._reservation_repo.get_by_id(id, load_branch=True, load_table=True, load_guest=True)
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

        # Reload reservation with relations for notifications
        reservation = await self._reservation_repo.get_by_id(
            reservation.id, load_branch=True, load_table=True, load_guest=True
        )

        # Enqueue cancellation notification task via Celery (non-blocking)
        # Lazy import to avoid circular dependency
        from app.tasks.notifications import send_reservation_cancelled_notification
        send_reservation_cancelled_notification.delay(
            str(reservation.id), old_status.value if old_status else None
        )

        return reservation

    async def confirm_reservation_by_telegram(
        self, reservation_id: UUID, chat_id: int
    ) -> Reservation | None:
        """Confirm a reservation via Telegram; verify by guest tg_chat_id."""
        reservation = await self._reservation_repo.get_by_id(
            reservation_id, load_branch=True, load_table=True, load_guest=True
        )
        if reservation is None:
            return None
        if not reservation.guest or reservation.guest.tg_chat_id != chat_id:
            return None
        if reservation.status != ReservationStatus.PENDING:
            raise ValueError(f"Cannot confirm reservation with status {reservation.status.value}")

        reservation.status = ReservationStatus.CONFIRMED
        await self._reservation_repo.update(reservation)
        await self._session.commit()

        await self._caching.invalidate_slots(reservation.branch_id, reservation.reservation_date)
        await self._caching.invalidate_tables(reservation.branch_id)

        return await self._reservation_repo.get_by_id(
            reservation.id, load_branch=True, load_table=True, load_guest=True
        )

    async def cancel_reservation_by_telegram(
        self, reservation_id: UUID, chat_id: int
    ) -> Reservation | None:
        """Cancel a reservation via Telegram; verify by guest tg_chat_id."""
        reservation = await self._reservation_repo.get_by_id(
            reservation_id, load_branch=True, load_table=True, load_guest=True
        )
        if reservation is None:
            return None
        if not reservation.guest or reservation.guest.tg_chat_id != chat_id:
            return None
        if reservation.status != ReservationStatus.PENDING:
            raise ValueError(f"Cannot cancel reservation with status {reservation.status.value}")

        old_status = reservation.status
        reservation.status = ReservationStatus.CANCELLED
        await self._reservation_repo.update(reservation)
        await self._session.commit()

        await self._caching.invalidate_slots(reservation.branch_id, reservation.reservation_date)
        await self._caching.invalidate_tables(reservation.branch_id)

        reservation = await self._reservation_repo.get_by_id(
            reservation.id, load_branch=True, load_table=True, load_guest=True
        )

        from app.tasks.notifications import send_reservation_cancelled_notification
        send_reservation_cancelled_notification.delay(
            str(reservation.id), old_status.value if old_status else None
        )

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

        # Reload reservation with relations for notifications
        reservation = await self._reservation_repo.get_by_id(
            reservation.id, load_branch=True, load_table=True
        )

        # Send status update notification via Celery if status changed to CANCELLED
        if body.status is not None and body.status != old_status:
            if body.status == ReservationStatus.CANCELLED:
                # Lazy import to avoid circular dependency
                from app.tasks.notifications import send_reservation_cancelled_notification
                send_reservation_cancelled_notification.delay(
                    str(reservation.id), old_status.value if old_status else None
                )

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
