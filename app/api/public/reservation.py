"""Public reservation endpoints: create and get by id."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, RedisDep
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services import ConflictError, LockedError, NotFoundError
from app.services.reservation_service import ReservationService
from app.services.locking_service import LockingService
from app.services.caching_service import CachingService
from app.repositories.branch_repository import BranchRepository
from app.repositories.table_repository import TableRepository
from app.repositories.reservation_repository import ReservationRepository

router = APIRouter(prefix="/reservations", tags=["public-reservations"])


def _reservation_service(db: DbSession, redis: RedisDep) -> ReservationService:
    return ReservationService(
        session=db,
        branch_repo=BranchRepository(db),
        table_repo=TableRepository(db),
        reservation_repo=ReservationRepository(db),
        locking=LockingService(redis),
        caching=CachingService(redis),
    )


@router.post("", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    body: ReservationCreate,
    db: DbSession,
    redis: RedisDep,
) -> ReservationResponse:
    """Create a reservation. Returns 400 validation, 404 not found, 409 conflict, 423 locked."""
    service = _reservation_service(db, redis)
    try:
        reservation = await service.create(body)
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except LockedError as e:
        raise HTTPException(status_code=423, detail=str(e))


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: UUID,
    db: DbSession,
    redis: RedisDep,
) -> ReservationResponse:
    """Get reservation by id."""
    service = _reservation_service(db, redis)
    reservation = await service.get_by_id(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


@router.get("/{reservation_id}/confirm", response_model=ReservationResponse)
async def confirm_reservation(
    reservation_id: UUID,
    db: DbSession,
    redis: RedisDep,
    token: str = Query(..., description="Confirmation token from email"),
) -> ReservationResponse:
    """Confirm a reservation via email confirmation link."""
    service = _reservation_service(db, redis)
    try:
        reservation = await service.confirm_reservation(reservation_id, token)
        if reservation is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    reservation_id: UUID,
    db: DbSession,
    redis: RedisDep,
    token: str = Query(..., description="Cancellation token from email"),
) -> ReservationResponse:
    """Cancel a reservation via email cancellation link."""
    service = _reservation_service(db, redis)
    try:
        reservation = await service.cancel_reservation(reservation_id, token)
        if reservation is None:
            raise HTTPException(status_code=404, detail="Reservation not found")
        return reservation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
