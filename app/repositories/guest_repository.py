"""Guest repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guest import Guest
from app.repositories.base import AsyncRepository


class GuestRepository(AsyncRepository[Guest]):
    """Guest DB access."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Guest)

    async def get_by_id(self, id: UUID) -> Guest | None:
        """Get guest by id."""
        return await self.get(id)

    async def get_or_create(self, id: UUID) -> Guest:
        """
        Get guest by id, or create if it doesn't exist.

        Args:
            id: Guest UUID

        Returns:
            Guest instance
        """
        guest = await self.get_by_id(id)
        if guest is None:
            guest = Guest(id=id)
            await self.add(guest)
            await self._session.commit()
            await self._session.refresh(guest)
        return guest

    async def update_tg_chat_id(self, guest_id: UUID, tg_chat_id: int) -> None:
        """
        Update guest's Telegram chat ID.

        Args:
            guest_id: Guest UUID
            tg_chat_id: Telegram chat ID
        """
        guest = await self.get_by_id(guest_id)
        if guest is None:
            raise ValueError(f"Guest {guest_id} not found")
        guest.tg_chat_id = tg_chat_id
        await self._session.commit()

    async def get_by_tg_chat_id(self, tg_chat_id: int) -> Guest | None:
        """Get guest by Telegram chat ID."""
        result = await self._session.execute(
            select(Guest).where(Guest.tg_chat_id == tg_chat_id)
        )
        return result.scalar_one_or_none()
