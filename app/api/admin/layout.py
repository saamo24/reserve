"""Admin layout (floor plan) endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentAdmin, DbSession
from app.models.branch import Branch
from app.models.table import Table
from app.models.table import TableLocation
from app.repositories.branch_repository import BranchRepository
from app.repositories.table_repository import TableRepository
from app.schemas.layout import (
    LayoutDocument,
    LayoutTablePayload,
    LayoutV1Payload,
    LayoutV2Payload,
    layout_from_dict_any,
    layout_to_json_any,
)

router = APIRouter(prefix="/branches", tags=["admin-layout"])


def _collect_all_tables_from_layout(layout: LayoutDocument) -> list[tuple[LayoutTablePayload, TableLocation]]:
    """Extract all tables from layout (v1 or v2) with their location."""
    tables: list[tuple[LayoutTablePayload, TableLocation]] = []
    
    if isinstance(layout, LayoutV1Payload):
        # V1: all tables are INDOOR (legacy)
        for t in layout.tables:
            tables.append((t, TableLocation.INDOOR))
    else:
        # V2: iterate zones
        for zone in layout.zones:
            if zone.type == "indoor":
                # Indoor: iterate floors
                if zone.floors:
                    for floor in zone.floors:
                        for t in floor.tables:
                            tables.append((t, TableLocation.INDOOR))
            elif zone.type == "outdoor":
                # Outdoor: top-level tables
                if zone.tables:
                    for t in zone.tables:
                        tables.append((t, TableLocation.OUTDOOR))
    
    return tables


@router.get("/{branch_id}/layout")
async def get_layout(
    branch_id: UUID,
    admin: CurrentAdmin,
    db: DbSession,
) -> LayoutDocument:
    """Get layout JSON for a branch (v1 or v2). Returns empty v1 layout if none stored."""
    repo = BranchRepository(db)
    branch = await repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")
    return layout_from_dict_any(branch.layout_json)


@router.put("/{branch_id}/layout")
async def put_layout(
    branch_id: UUID,
    body: LayoutDocument,
    admin: CurrentAdmin,
    db: DbSession,
) -> LayoutDocument:
    """Save layout JSON (v1 or v2) and sync Table rows (create/update by id).
    
    - Upserts all tables found in layout
    - Sets Table.location based on zone type (v2) or INDOOR (v1)
    - Sets Table.is_active=True for tables in layout
    - Sets Table.is_active=False for branch tables not in layout (delete semantics)
    """
    branch_repo = BranchRepository(db)
    table_repo = TableRepository(db)
    branch = await branch_repo.get_by_id(branch_id)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Collect all tables from layout with their locations
    layout_tables_with_location = _collect_all_tables_from_layout(body)
    layout_table_ids = {t[0].id for t in layout_tables_with_location}

    # Upsert tables from layout
    for table_payload, location in layout_tables_with_location:
        existing = await table_repo.get_by_id(table_payload.id)
        if existing is not None:
            if existing.branch_id != branch_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Table {table_payload.id} belongs to another branch",
                )
            existing.table_number = table_payload.table_number
            existing.capacity = table_payload.capacity
            existing.location = location
            existing.is_active = True
            await table_repo.update(existing)
        else:
            new_table = Table(
                id=table_payload.id,
                branch_id=branch_id,
                table_number=table_payload.table_number,
                capacity=table_payload.capacity,
                location=location,
                is_active=True,
            )
            await table_repo.create(new_table)

    # Deactivate tables that are no longer in the layout
    all_branch_tables = await table_repo.list_by_branch(branch_id, active_only=False)
    for db_table in all_branch_tables:
        if db_table.id not in layout_table_ids:
            db_table.is_active = False
            await table_repo.update(db_table)

    # Save layout JSON
    branch.layout_json = layout_to_json_any(body)
    await branch_repo.update(branch)
    await db.commit()
    return body
