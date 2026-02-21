"""Reservation schemas."""

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.reservation import ReservationStatus
from app.utils.validators import validate_date_not_in_past, validate_phone


class ReservationCreate(BaseModel):
    """Schema for creating a reservation (public flow)."""

    branch_id: UUID
    reservation_date: date
    start_time: time
    table_id: UUID | None = None  # optional: auto-assign if not provided
    full_name: str = Field(..., min_length=1, max_length=255)
    phone_number: str = Field(..., min_length=1, max_length=32)
    email: EmailStr | None = None
    notes: str | None = None

    @field_validator("phone_number")
    @classmethod
    def phone_format(cls, v: str) -> str:
        return validate_phone(v)

    @field_validator("reservation_date")
    @classmethod
    def date_not_past(cls, v: date) -> date:
        return validate_date_not_in_past(v)


class ReservationUpdate(BaseModel):
    """Schema for partial reservation update (admin)."""

    status: ReservationStatus | None = None
    notes: str | None = None


class ReservationResponse(BaseModel):
    """Reservation response schema. guest_id is not exposed."""

    id: UUID
    branch_id: UUID
    table_id: UUID
    full_name: str
    phone_number: str
    email: str | None
    reservation_date: date
    start_time: time
    end_time: time
    status: ReservationStatus
    notes: str | None
    reservation_code: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Admin list filters
class ReservationListFilters(BaseModel):
    """Query params for listing reservations."""

    branch_id: UUID | None = None
    reservation_date: date | None = None
    status: ReservationStatus | None = None
    phone_number: str | None = None
