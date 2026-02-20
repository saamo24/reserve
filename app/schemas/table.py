"""Table schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.table import TableLocation


class TableBase(BaseModel):
    """Base table fields."""

    branch_id: UUID
    table_number: str = Field(..., min_length=1, max_length=32)
    capacity: int = Field(..., ge=1, le=100)
    location: TableLocation = TableLocation.INDOOR
    is_active: bool = True


class TableCreate(TableBase):
    """Schema for creating a table."""

    pass


class TableUpdate(BaseModel):
    """Schema for partial table update."""

    table_number: str | None = Field(None, min_length=1, max_length=32)
    capacity: int | None = Field(None, ge=1, le=100)
    location: TableLocation | None = None
    is_active: bool | None = None


class TableResponse(TableBase):
    """Table response schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
