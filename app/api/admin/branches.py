"""Admin branch management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentAdmin, DbSession, RedisDep
from app.repositories.branch_repository import BranchRepository
from app.schemas.branch import BranchCreate, BranchResponse, BranchUpdate
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.services.caching_service import CachingService
from app.models.branch import Branch

router = APIRouter(prefix="/branches", tags=["admin-branches"])


@router.get("", response_model=PaginatedResponse[BranchResponse])
async def list_branches(
    admin: CurrentAdmin,
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[BranchResponse]:
    """List all branches with pagination."""
    from sqlalchemy import func, select

    repo = BranchRepository(db)
    skip = (page - 1) * page_size
    count_result = await db.execute(select(func.count()).select_from(Branch))
    total = count_result.scalar_one() or 0
    branches = await repo.list_all(skip=skip, limit=page_size)
    return PaginatedResponse(
        data=branches,
        meta=PaginationMeta(total=total, page=page, page_size=page_size),
    )


@router.post("", response_model=BranchResponse, status_code=201)
async def create_branch(
    body: BranchCreate,
    admin: CurrentAdmin,
    db: DbSession,
) -> BranchResponse:
    """Create a branch."""
    repo = BranchRepository(db)
    branch = Branch(
        name=body.name,
        address=body.address,
        opening_time=body.opening_time,
        closing_time=body.closing_time,
        slot_duration_minutes=body.slot_duration_minutes,
        is_active=body.is_active,
    )
    branch = await repo.create(branch)
    await db.commit()
    return branch


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: UUID,
    body: BranchUpdate,
    admin: CurrentAdmin,
    db: DbSession,
    redis: RedisDep,
) -> BranchResponse:
    """Update a branch. Invalidates cache for this branch."""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(branch, k, v)
    await repo.update(branch)
    await db.commit()
    caching = CachingService(redis)
    await caching.invalidate_tables(branch_id)
    # Invalidate slots for this branch (we don't have date range; invalidate by pattern would need keys scan)
    # For simplicity we don't invalidate slots per-branch here; they'll expire by TTL.
    return branch
