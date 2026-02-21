"""Admin layout (floor plan) endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentAdmin, DbSession
from app.models.branch import Branch
from app.models.table import Table
from app.models.table import TableLocation
from app.repositories.branch_repository import BranchRepository
from app.repositories.table_repository import TableRepository
from app.schemas.layout import LayoutPayload, LayoutTablePayload, layout_from_dict

router = APIRouter(prefix="/branches", tags=["admin-layout"])


def _layout_to_json(layout: LayoutPayload) -> dict:
    """Serialize layout to JSON-serializable dict for storage."""
    return {
        "width": layout.width,
        "height": layout.height,
        "tables": [
            {
                "id": str(t.id),
                "x": t.x,
                "y": t.y,
                "width": t.width,
                "height": t.height,
                "rotation": t.rotation,
                "shape": t.shape,
                "capacity": t.capacity,
                "table_number": t.table_number,
            }
            for t in layout.tables
        ],
    }


@router.get("/{branch_id}/layout", response_model=LayoutPayload)
async def get_layout(
    branch_id: UUID,
    admin: CurrentAdmin,
    db: DbSession,
) -> LayoutPayload:
    """Get layout JSON for a branch. Returns empty layout if none stored."""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    return layout_from_dict(branch.layout_json)


@router.put("/{branch_id}/layout", response_model=LayoutPayload)
async def put_layout(
    branch_id: UUID,
    body: LayoutPayload,
    admin: CurrentAdmin,
    db: DbSession,
) -> LayoutPayload:
    """Save layout JSON and sync Table rows (create/update by id)."""
    branch_repo = BranchRepository(db)
    table_repo = TableRepository(db)
    branch = await branch_repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")

    for t in body.tables:
        existing = await table_repo.get_by_id(t.id)
        if existing is not None:
            if existing.branch_id != branch_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Table {t.id} belongs to another branch",
                )
            existing.table_number = t.table_number
            existing.capacity = t.capacity
            await table_repo.update(existing)
        else:
            new_table = Table(
                id=t.id,
                branch_id=branch_id,
                table_number=t.table_number,
                capacity=t.capacity,
                location=TableLocation.INDOOR,
                is_active=True,
            )
            await table_repo.create(new_table)

    branch.layout_json = _layout_to_json(body)
    await branch_repo.update(branch)
    await db.commit()
    return body
