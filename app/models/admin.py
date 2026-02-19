"""Admin model for JWT-authenticated admin users."""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from pydantic import EmailStr
from app.models.base import Base, TimestampMixin


class Admin(Base, TimestampMixin):
    """Admin user with hashed password for admin API access."""

    __tablename__ = "admins"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[EmailStr] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"<Admin(id={self.id}, email={self.email!r})>"
