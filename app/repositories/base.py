"""Generic async repository base."""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class AsyncRepository(Generic[ModelT]):
    """Generic async CRUD repository."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def get(self, id: UUID) -> ModelT | None:
        """Get a single record by id."""
        result = await self._session.execute(select(self._model).where(self._model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelT]:
        """Get multiple records with offset/limit."""
        result = await self._session.execute(
            select(self._model).offset(skip).limit(limit).order_by(self._model.id)
        )
        return list(result.scalars().all())

    async def add(self, instance: ModelT) -> ModelT:
        """Add and flush (no commit)."""
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance
