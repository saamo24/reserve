"""Reservation model."""

import enum
from datetime import date, time
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReservationStatus(str, enum.Enum):
    """Reservation status."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class Reservation(Base, TimestampMixin):
    """Customer reservation for a table at a branch."""

    __tablename__ = "reservations"

    __table_args__ = (
        Index("ix_reservations_branch_date", "branch_id", "reservation_date"),
        Index("ix_reservations_table_date", "table_id", "reservation_date"),
        Index(
            "ix_reservations_table_date_times",
            "table_id",
            "reservation_date",
            "start_time",
            "end_time",
        ),
        # Partial unique index: prevent duplicate active reservation for same slot
        Index(
            "uq_reservations_table_slot_active",
            "table_id",
            "reservation_date",
            "start_time",
            "end_time",
            unique=True,
            postgresql_where=text("status NOT IN ('CANCELLED')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=__import__("uuid").uuid4)
    guest_id: Mapped[UUID] = mapped_column(
        ForeignKey("guests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reservation_code: Mapped[str | None] = mapped_column(String(8), unique=True, nullable=True, index=True)
    branch_id: Mapped[UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_id: Mapped[UUID] = mapped_column(
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reservation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.CONFIRMED,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    qr_code_base64: Mapped[str | None] = mapped_column(Text, nullable=True)

    guest: Mapped["Guest"] = relationship("Guest", back_populates="reservations")
    branch: Mapped["Branch"] = relationship("Branch")
    table: Mapped["Table"] = relationship("Table", back_populates="reservations")

    @property
    def qr_code(self) -> str | None:
        """Alias for qr_code_base64 for API response (base64 PNG)."""
        return self.qr_code_base64

    def __repr__(self) -> str:
        return f"<Reservation(id={self.id}, branch_id={self.branch_id}, date={self.reservation_date})>"
