"""Admin reservation management."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, RedisDep
from app.models.reservation import ReservationStatus
from app.repositories.reservation_repository import ReservationRepository
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.reservation import ReservationResponse, ReservationUpdate
from app.services.reservation_service import ReservationService
from app.services.locking_service import LockingService
from app.services.caching_service import CachingService
from app.repositories.branch_repository import BranchRepository
from app.repositories.table_repository import TableRepository

router = APIRouter(prefix="/reservations", tags=["admin-reservations"])


def _reservation_service(db: DbSession, redis: RedisDep) -> ReservationService:
    return ReservationService(
        session=db,
        branch_repo=BranchRepository(db),
        table_repo=TableRepository(db),
        reservation_repo=ReservationRepository(db),
        locking=LockingService(redis),
        caching=CachingService(redis),
    )


@router.get("", response_model=PaginatedResponse[ReservationResponse])
async def list_reservations(
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


@router.patch("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: UUID,
    body: ReservationUpdate,
    db: DbSession,
    redis: RedisDep,
) -> ReservationResponse:
    """Update reservation status or notes."""
    service = _reservation_service(db, redis)
    reservation = await service.update(reservation_id, body)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return reservation
