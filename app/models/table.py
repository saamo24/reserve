"""Table model."""

import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TableLocation(str, enum.Enum):
    """Table location type."""

    INDOOR = "INDOOR"
    OUTDOOR = "OUTDOOR"
    VIP = "VIP"


class Table(Base, TimestampMixin):
    """Restaurant table belonging to a branch."""

    __tablename__ = "tables"

    __table_args__ = (
        UniqueConstraint("branch_id", "table_number", name="uq_tables_branch_table_number"),
        Index("ix_tables_branch_capacity", "branch_id", "capacity"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=__import__("uuid").uuid4)
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_number: Mapped[str] = mapped_column(String(32), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[TableLocation] = mapped_column(
        Enum(TableLocation),
        nullable=False,
        default=TableLocation.INDOOR,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="tables")
    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation",
        back_populates="table",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Table(id={self.id}, branch_id={self.branch_id}, number={self.table_number!r})>"
