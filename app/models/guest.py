"""Guest model."""

from uuid import UUID

from sqlalchemy import Integer, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Guest(Base, TimestampMixin):
    """Guest user identified by UUID. Can optionally have Telegram chat ID."""

    __tablename__ = "guests"

    __table_args__ = (
        Index("ix_guests_tg_chat_id", "tg_chat_id"),
        # Partial unique index: tg_chat_id must be unique when not null
        Index(
            "uq_guests_tg_chat_id",
            "tg_chat_id",
            unique=True,
            postgresql_where=text("tg_chat_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=__import__("uuid").uuid4)
    tg_chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation",
        back_populates="guest",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Guest(id={self.id}, tg_chat_id={self.tg_chat_id})>"
