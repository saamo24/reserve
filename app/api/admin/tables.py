"""Admin table management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, RedisDep
from app.models.table import Table
from app.repositories.table_repository import TableRepository
from app.schemas.common import PaginatedResponse, PaginationMeta
from app.schemas.table import TableCreate, TableResponse, TableUpdate
from app.services.caching_service import CachingService

router = APIRouter(prefix="/tables", tags=["admin-tables"])


@router.get("", response_model=PaginatedResponse[TableResponse])
async def list_tables(
    db: DbSession,
    branch_id: UUID | None = Query(None, description="Filter by branch"),
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[TableResponse]:
    """List tables, optionally filtered by branch_id."""
    from sqlalchemy import func, select

    repo = TableRepository(db)
    if branch_id is not None:
        tables = await repo.list_by_branch(branch_id, active_only=False)
        total = len(tables)
        skip = (page - 1) * page_size
        tables = tables[skip : skip + page_size]
    else:
        count_result = await db.execute(select(func.count()).select_from(Table))
        total = count_result.scalar_one() or 0
        skip = (page - 1) * page_size
        tables = await repo.get_multi(skip=skip, limit=page_size)
    return PaginatedResponse(
        data=tables,
        meta=PaginationMeta(total=total, page=page, page_size=page_size),
    )


@router.post("", response_model=TableResponse, status_code=201)
async def create_table(
    body: TableCreate,
    db: DbSession,
    redis: RedisDep,
) -> TableResponse:
    """Create a table. Returns 409 if (branch_id, table_number) duplicate."""
    repo = TableRepository(db)
    table = Table(
        branch_id=body.branch_id,
        table_number=body.table_number,
        capacity=body.capacity,
        location=body.location,
        is_active=body.is_active,
    )
    try:
        table = await repo.create(table)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Table number already exists for this branch")
    caching = CachingService(redis)
    await caching.invalidate_tables(body.branch_id)
    return table


@router.patch("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: UUID,
    body: TableUpdate,
    db: DbSession,
    redis: RedisDep,
) -> TableResponse:
    """Update a table."""
    repo = TableRepository(db)
    table = await repo.get_by_id(table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(table, k, v)
    try:
        await repo.update(table)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Table number already exists for this branch")
    await CachingService(redis).invalidate_tables(table.branch_id)
    return table


@router.delete("/{table_id}", status_code=204)
async def delete_table(
    table_id: UUID,
    db: DbSession,
    redis: RedisDep,
) -> None:
    """Delete a table."""
    repo = TableRepository(db)
    table = await repo.get_by_id(table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")
    branch_id = table.branch_id
    await repo.delete(table)
    await db.commit()
    await CachingService(redis).invalidate_tables(branch_id)
