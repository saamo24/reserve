"""Admin dashboard stats."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.models.reservation import Reservation, ReservationStatus
from sqlalchemy import func, select

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    db: DbSession,
    branch_id: UUID | None = Query(None),
    from_date: date | None = Query(None, alias="from_date"),
    to_date: date | None = Query(None, alias="to_date"),
) -> dict:
    """
    Dashboard stats: total reservations, active, upcoming, occupancy rate.
    Response: { data: {...}, meta: {} }
    """
    # Total reservations (optionally by branch and date range)
    q = select(func.count(Reservation.id)).where(Reservation.status != ReservationStatus.CANCELLED)
    if branch_id is not None:
        q = q.where(Reservation.branch_id == branch_id)
    if from_date is not None:
        q = q.where(Reservation.reservation_date >= from_date)
    if to_date is not None:
        q = q.where(Reservation.reservation_date <= to_date)
    total_result = await db.execute(q)
    total_reservations = total_result.scalar_one() or 0

    # Active (confirmed or pending) - same filters
    q_active = select(func.count(Reservation.id)).where(
        Reservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.PENDING])
    )
    if branch_id is not None:
        q_active = q_active.where(Reservation.branch_id == branch_id)
    if from_date is not None:
        q_active = q_active.where(Reservation.reservation_date >= from_date)
    if to_date is not None:
        q_active = q_active.where(Reservation.reservation_date <= to_date)
    active_result = await db.execute(q_active)
    active_reservations = active_result.scalar_one() or 0

    # Upcoming: today or future
    today = date.today()
    q_upcoming = select(func.count(Reservation.id)).where(
        Reservation.reservation_date >= today,
        Reservation.status.in_([ReservationStatus.CONFIRMED, ReservationStatus.PENDING]),
    )
    if branch_id is not None:
        q_upcoming = q_upcoming.where(Reservation.branch_id == branch_id)
    if from_date is not None:
        q_upcoming = q_upcoming.where(Reservation.reservation_date >= from_date)
    if to_date is not None:
        q_upcoming = q_upcoming.where(Reservation.reservation_date <= to_date)
    upcoming_result = await db.execute(q_upcoming)
    upcoming_reservations = upcoming_result.scalar_one() or 0

    # Occupancy rate: would need total slot capacity vs reserved slots in a period.
    # Simplified: occupancy = active_reservations / (some denominator). Use a placeholder.
    occupancy_rate = 0.0
    if total_reservations > 0:
        occupancy_rate = round(active_reservations / total_reservations * 100, 2)

    return {
        "data": {
            "total_reservations": total_reservations,
            "active_reservations": active_reservations,
            "upcoming_reservations": upcoming_reservations,
            "occupancy_rate_percent": occupancy_rate,
        },
        "meta": {},
    }
