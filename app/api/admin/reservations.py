"""Admin reservation management."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentAdmin, DbSession, RedisDep
from app.models.reservation import ReservationStatus
from app.repositories.branch_repository import BranchRepository
from app.repositories.guest_repository import GuestRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.table_repository import TableRepository
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.reservation import ReservationResponse, ReservationUpdate
from app.services.caching_service import CachingService
from app.services.locking_service import LockingService
from app.services.reservation_service import ReservationService

router = APIRouter(prefix="/reservations", tags=["admin-reservations"])


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


@router.get("", response_model=PaginatedResponse[ReservationResponse])
async def list_reservations(
    admin: CurrentAdmin,
    db: DbSession,
    redis: RedisDep,
    branch_id: UUID | None = Query(None),
    date: date | None = Query(None, alias="date"),
    status: ReservationStatus | None = Query(None),
    phone_number: str | None = Query(None),
    page: int = 1,
    page_size: int = 20,
    sort_by: str = Query("reservation_date", alias="sort_by"),
    order: str = Query("asc", alias="order"),
) -> PaginatedResponse[ReservationResponse]:
    """List reservations with filters and pagination."""
    service = _reservation_service(db, redis)
    skip = (page - 1) * page_size
    items, total = await service.list_with_filters(
        branch_id=branch_id,
        reservation_date=date,
        status=status,
        phone_number=phone_number,
        skip=skip,
        limit=page_size,
        order_by=sort_by,
        order_desc=order.lower() == "desc",
    )
    return PaginatedResponse(
        data=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size),
    )


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: UUID,
    admin: CurrentAdmin,
    db: DbSession,
    redis: RedisDep,
    code: str | None = Query(None, description="Reservation code for additional verification"),
) -> ReservationResponse:
    """Get reservation by id (admin only). Optionally verify with code."""
    service = _reservation_service(db, redis)
    reservation = await service.get_by_id(reservation_id, load_relations=True)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    # Optionally verify code if provided
    if code and reservation.reservation_code != code:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation


@router.patch("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: UUID,
    body: ReservationUpdate,
    admin: CurrentAdmin,
    db: DbSession,
    redis: RedisDep,
) -> ReservationResponse:
    """Update reservation status or notes."""
    service = _reservation_service(db, redis)
    reservation = await service.update(reservation_id, body)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation
