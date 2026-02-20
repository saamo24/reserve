"""Branch repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.repositories.base import AsyncRepository


class BranchRepository(AsyncRepository[Branch]):
    """Branch DB access."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Branch)

    async def get_by_id(self, id: UUID) -> Branch | None:
        """Get branch by id."""
        return await self.get(id)

    async def list_active(self) -> list[Branch]:
        """List all active branches."""
        result = await self._session.execute(
            select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.name)
        )
        return list(result.scalars().all())

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[Branch]:
        """List all branches with pagination."""
        result = await self._session.execute(
            select(Branch).offset(skip).limit(limit).order_by(Branch.name)
        )
        return list(result.scalars().all())

    async def create(self, branch: Branch) -> Branch:
        """Create a branch."""
        return await self.add(branch)

    async def update(self, branch: Branch) -> Branch:
        """Update (flush)."""
        await self._session.flush()
        await self._session.refresh(branch)
        return branch
