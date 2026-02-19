"""Admin repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.repositories.base import AsyncRepository
from pydantic import EmailStr

class AdminRepository(AsyncRepository[Admin]):
    """Admin DB access."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Admin)

    async def get_by_id(self, id: UUID) -> Admin | None:
        """Get admin by id."""
        return await self.get(id)

    async def get_by_email(self, email: EmailStr) -> Admin | None:
        """Get admin by email."""
        result = await self._session.execute(
            select(Admin).where(Admin.email == email)
        )
        return result.scalar_one_or_none()
