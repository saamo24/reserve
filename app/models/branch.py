"""Branch model."""

from datetime import time
from uuid import UUID

from sqlalchemy import Index, String, Time
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.table import Table


class Branch(Base, TimestampMixin):
    """Restaurant branch with opening hours and slot configuration."""

    __tablename__ = "branches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=__import__("uuid").uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    opening_time: Mapped[time] = mapped_column(Time, nullable=False)
    closing_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(nullable=False, default=120)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    layout_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    tables: Mapped[list["Table"]] = relationship(
        "Table",
        back_populates="branch",
        lazy="selectin",
        foreign_keys="Table.branch_id",
    )

    def __repr__(self) -> str:
        return f"<Branch(id={self.id}, name={self.name!r})>"
