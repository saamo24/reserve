"""Common response schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response with data and meta."""

    data: list[T] = Field(default_factory=list, description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
