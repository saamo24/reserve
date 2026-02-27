"""Public reservation endpoints: create, get by id (guest-verified), and list my reservations."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, GuestIdDep, RedisDep
from app.core.config import get_settings
from app.schemas.reservation import ReservationCreate, ReservationResponsePublic
from app.services import ConflictError, LockedError, NotFoundError
from app.services.reservation_service import ReservationService
from app.services.locking_service import LockingService
from app.services.tg_service import TelegramService
from app.services.caching_service import CachingService
from app.repositories.branch_repository import BranchRepository
from app.repositories.guest_repository import GuestRepository
from app.repositories.table_repository import TableRepository
from app.repositories.reservation_repository import ReservationRepository

router = APIRouter(prefix="/reservations", tags=["public-reservations"])
logger = logging.getLogger(__name__)


def _reservation_service(db: DbSession, redis: RedisDep) -> ReservationService:
    return ReservationService(
        session=db,
        branch_repo=BranchRepository(db),
        table_repo=TableRepository(db),
        reservation_repo=ReservationRepository(db),
        guest_repo=GuestRepository(db),
        locking=LockingService(redis),
        caching=CachingService(redis),
    )


@router.post("", response_model=ReservationResponsePublic, status_code=201)
async def create_reservation(
    body: ReservationCreate,
    db: DbSession,
    redis: RedisDep,
    guest_id: GuestIdDep,
) -> ReservationResponsePublic:
    """Create a reservation. guest_id from signed cookie only; never from body."""
    service = _reservation_service(db, redis)
    try:
        reservation = await service.create(body, guest_id)
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LockedError as e:
        raise HTTPException(status_code=423, detail=str(e))


@router.get("/me", response_model=list[ReservationResponsePublic])
async def list_my_reservations(
    guest_id: GuestIdDep,
    db: DbSession,
    redis: RedisDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[ReservationResponsePublic]:
    """List reservations for the current guest (from cookie). Sorted by date/time descending. Empty list if none."""
    service = _reservation_service(db, redis)
    items, _ = await service.list_my_reservations(guest_id, skip=skip, limit=limit)
    return list(items)


@router.post("/{reservation_id}/attach", response_model=ReservationResponsePublic)
async def attach_reservation_to_guest(
    reservation_id: UUID,
    guest_id: GuestIdDep,
    db: DbSession,
    redis: RedisDep,
    code: str = Query(..., description="Reservation code to prove ownership"),
) -> ReservationResponsePublic:
    """Link a reservation to the current guest so it appears in My Reservations. Requires id+code."""
    service = _reservation_service(db, redis)
    reservation, guest_id_changed = await service.attach_to_guest(reservation_id, code, guest_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found or invalid code")
    # Only send Telegram confirmation if the reservation was newly attached (guest_id changed)
    # This prevents duplicate notifications when viewing the same reservation multiple times
    # Use phone number identification instead of guest relationship
    if guest_id_changed:
        reservation_repo = ReservationRepository(db)
        tg_chat_id = await reservation_repo.find_tg_chat_id_by_phone_number(
            reservation.phone_number
        )
        if tg_chat_id:
            telegram_service = TelegramService()
            try:
                # Create temporary guest object for Telegram service compatibility
                from types import SimpleNamespace
                original_guest = getattr(reservation, 'guest', None)
                reservation.guest = SimpleNamespace(tg_chat_id=tg_chat_id)
                try:
                    await telegram_service.send_reservation_confirmation(reservation)
                    logger.info(
                        f"Sent Telegram notification after attach for reservation {reservation_id} "
                        f"to chat_id {tg_chat_id} (phone_number={reservation.phone_number})"
                    )
                finally:
                    reservation.guest = original_guest
            except Exception as e:
                logger.warning(
                    "Failed to send Telegram confirmation after attach for reservation %s: %s",
                    reservation_id,
                    e,
                    exc_info=True,
                )
            finally:
                await telegram_service.close()
        else:
            logger.info(
                f"No tg_chat_id found for phone_number={reservation.phone_number} "
                f"for reservation {reservation_id} after attach"
            )
    return reservation


@router.post("/dev/attach/{reservation_id}", response_model=ReservationResponsePublic)
async def dev_attach_reservation_to_guest(
    reservation_id: UUID,
    guest_id: GuestIdDep,
    db: DbSession,
    redis: RedisDep,
) -> ReservationResponsePublic:
    """[Development only] Link a reservation to the current guest by ID (no code). Use for local testing."""
    if get_settings().app_env != "development":
        raise HTTPException(status_code=404, detail="Not found")
    service = _reservation_service(db, redis)
    reservation, guest_id_changed = await service.attach_to_guest_by_id(reservation_id, guest_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    # Only send Telegram confirmation if the reservation was newly attached (guest_id changed)
    # This prevents duplicate notifications when viewing the same reservation multiple times
    # Use phone number identification instead of guest relationship
    if guest_id_changed:
        reservation_repo = ReservationRepository(db)
        tg_chat_id = await reservation_repo.find_tg_chat_id_by_phone_number(
            reservation.phone_number
        )
        if tg_chat_id:
            telegram_service = TelegramService()
            try:
                # Create temporary guest object for Telegram service compatibility
                from types import SimpleNamespace
                original_guest = getattr(reservation, 'guest', None)
                reservation.guest = SimpleNamespace(tg_chat_id=tg_chat_id)
                try:
                    await telegram_service.send_reservation_confirmation(reservation)
                    logger.info(
                        f"Sent Telegram notification after dev attach for reservation {reservation_id} "
                        f"to chat_id {tg_chat_id} (phone_number={reservation.phone_number})"
                    )
                finally:
                    reservation.guest = original_guest
            except Exception as e:
                logger.warning(
                    "Failed to send Telegram confirmation after dev attach for reservation %s: %s",
                    reservation_id,
                    e,
                    exc_info=True,
                )
            finally:
                await telegram_service.close()
        else:
            logger.info(
                f"No tg_chat_id found for phone_number={reservation.phone_number} "
                f"for reservation {reservation_id} after dev attach"
            )
    return reservation


@router.get("/{reservation_id}", response_model=ReservationResponsePublic)
async def get_reservation(
    reservation_id: UUID,
    guest_id: GuestIdDep,
    db: DbSession,
    redis: RedisDep,
    code: str | None = Query(None, description="Reservation code from confirmation; allows loading without cookie match"),
) -> ReservationResponsePublic:
    """Get reservation by id. Allowed if it belongs to the current guest (cookie) or if code query param matches."""
    service = _reservation_service(db, redis)
    reservation = None
    if code:
        reservation = await service.get_by_id_and_code(reservation_id, code)
    if reservation is None:
        reservation = await service.get_by_id_and_guest(reservation_id, guest_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


@router.get("/{reservation_id}/confirm", response_model=ReservationResponsePublic)
async def confirm_reservation(
    reservation_id: UUID,
    db: DbSession,
    redis: RedisDep,
    token: str = Query(..., description="Confirmation token from email"),
) -> ReservationResponsePublic:
    """Confirm a reservation via email confirmation link."""
    service = _reservation_service(db, redis)
    try:
        reservation = await service.confirm_reservation(reservation_id, token)
        if reservation is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{reservation_id}/cancel", response_model=ReservationResponsePublic)
async def cancel_reservation(
    reservation_id: UUID,
    db: DbSession,
    redis: RedisDep,
    token: str = Query(..., description="Cancellation token from email"),
) -> ReservationResponsePublic:
    """Cancel a reservation via email cancellation link."""
    service = _reservation_service(db, redis)
    try:
        reservation = await service.cancel_reservation(reservation_id, token)
        if reservation is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
