"""Branch schemas."""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import validate_timezone


class BranchBase(BaseModel):
    """Base branch fields."""

    name: str = Field(..., min_length=1, max_length=255)
    address: str = Field(..., min_length=1, max_length=512)
    timezone: str = Field(default="UTC", max_length=64)
    opening_time: time
    closing_time: time
    slot_duration_minutes: int = Field(default=120, ge=15, le=480)
    is_active: bool = True

    @field_validator("timezone")
    @classmethod
    def tz_valid(cls, v: str) -> str:
        return validate_timezone(v)


class BranchCreate(BranchBase):
    """Schema for creating a branch."""

    pass


class BranchUpdate(BaseModel):
    """Schema for partial branch update."""

    name: str | None = Field(None, min_length=1, max_length=255)
    address: str | None = Field(None, min_length=1, max_length=512)
    timezone: str | None = Field(None, max_length=64)
    opening_time: time | None = None
    closing_time: time | None = None
    slot_duration_minutes: int | None = Field(None, ge=15, le=480)
    is_active: bool | None = None

    @field_validator("timezone")
    @classmethod
    def tz_valid(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_timezone(v)


class BranchResponse(BranchBase):
    """Branch response schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
