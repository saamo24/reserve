"""Table repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.table import Table
from app.repositories.base import AsyncRepository


class TableRepository(AsyncRepository[Table]):
    """Table DB access."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Table)

    async def get_by_id(self, id: UUID) -> Table | None:
        """Get table by id."""
        return await self.get(id)

    async def list_by_branch(
        self,
        branch_id: UUID,
        *,
        active_only: bool = True,
    ) -> list[Table]:
        """List tables for a branch."""
        q = select(Table).where(Table.branch_id == branch_id)
        if active_only:
            q = q.where(Table.is_active.is_(True))
        q = q.order_by(Table.table_number)
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def create(self, table: Table) -> Table:
        """Create a table. Raises IntegrityError if (branch_id, table_number) duplicate."""
        return await self.add(table)

    async def update(self, table: Table) -> Table:
        """Update (flush)."""
        await self._session.flush()
        await self._session.refresh(table)
        return table

    async def delete(self, table: Table) -> None:
        """Hard delete table."""
        await self._session.delete(table)
        await self._session.flush()
