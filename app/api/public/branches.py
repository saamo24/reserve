"""Public branch and slot endpoints."""

from datetime import date, time
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession, RedisDep
from app.repositories.branch_repository import BranchRepository
from app.repositories.reservation_repository import ReservationRepository
from app.repositories.table_repository import TableRepository
from app.schemas.branch import BranchResponse
from app.schemas.layout import LayoutDocument, layout_from_dict_any
from app.schemas.table import TableResponse
from app.services.caching_service import CachingService
from app.services.timeslot_service import TimeslotService

router = APIRouter(prefix="/branches", tags=["public-branches"])


@router.get("", response_model=list[BranchResponse])
async def list_branches(db: DbSession) -> list:
    """List active branches."""
    repo = BranchRepository(db)
    branches = await repo.list_active()
    return branches


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(branch_id: UUID, db: DbSession) -> BranchResponse:
    """Get branch by id."""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.get("/{branch_id}/slots")
async def get_slots(
    branch_id: UUID,
    db: DbSession,
    redis: RedisDep,
    reservation_date: date = Query(..., alias="date", description="Reservation date"),
) -> list[dict]:
    """Get available time slots for a branch on a date."""
    branch_repo = BranchRepository(db)
    reservation_repo = ReservationRepository(db)
    caching = CachingService(redis)
    service = TimeslotService(db, branch_repo, reservation_repo, caching)
    slots = await service.get_available_slots(branch_id, reservation_date)
    return slots


@router.get("/{branch_id}/tables", response_model=list[TableResponse])
async def list_tables(branch_id: UUID, db: DbSession) -> list:
    """List active tables for a branch."""
    repo = TableRepository(db)
    tables = await repo.list_by_branch(branch_id, active_only=True)
    return tables


@router.get("/{branch_id}/layout")
async def get_layout(branch_id: UUID, db: DbSession) -> LayoutDocument:
    """Get floor plan layout for a branch (read-only, v1 or v2). Returns empty v1 layout if none."""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    return layout_from_dict_any(branch.layout_json)


@router.get("/{branch_id}/reserved-tables")
async def get_reserved_tables(
    branch_id: UUID,
    db: DbSession,
    reservation_date: date = Query(..., alias="date"),
    start_time: time = Query(..., description="Slot start time (HH:MM or HH:MM:SS)"),
    end_time: time = Query(..., description="Slot end time (HH:MM or HH:MM:SS)"),
) -> list[str]:
    """Return table IDs (UUIDs as strings) reserved for the given slot."""
    branch_repo = BranchRepository(db)
    reservation_repo = ReservationRepository(db)
    branch = await branch_repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    ids = await reservation_repo.list_reserved_table_ids_for_slot(
        branch_id, reservation_date, start_time, end_time
    )
    return [str(i) for i in ids]
