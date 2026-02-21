"""Layout (floor plan) schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class LayoutTablePayload(BaseModel):
    """Single table in a layout (canvas position + metadata)."""

    id: UUID
    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    width: float = Field(..., gt=0, le=1000)
    height: float = Field(..., gt=0, le=1000)
    rotation: float = Field(default=0, ge=-360, le=360)
    shape: str = Field(..., pattern="^(round|rect)$")
    capacity: int = Field(..., ge=1, le=100)
    table_number: str = Field(..., min_length=1, max_length=32)


class LayoutPayload(BaseModel):
    """Full layout: canvas size + list of tables."""

    width: float = Field(..., gt=0, le=5000)
    height: float = Field(..., gt=0, le=5000)
    tables: list[LayoutTablePayload] = Field(default_factory=list)


def layout_from_dict(raw: dict | None) -> LayoutPayload:
    """Build LayoutPayload from stored JSON dict. Returns empty layout if invalid."""
    if not raw or not isinstance(raw, dict):
        return LayoutPayload(width=800, height=600, tables=[])
    width = raw.get("width", 800)
    height = raw.get("height", 600)
    tables_raw = raw.get("tables") or []
    tables: list[LayoutTablePayload] = []
    for t in tables_raw:
        if not isinstance(t, dict):
            continue
        try:
            tables.append(
                LayoutTablePayload(
                    id=UUID(t["id"]),
                    x=float(t["x"]),
                    y=float(t["y"]),
                    width=float(t["width"]),
                    height=float(t["height"]),
                    rotation=float(t.get("rotation", 0)),
                    shape=str(t.get("shape", "rect")),
                    capacity=int(t["capacity"]),
                    table_number=str(t["table_number"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return LayoutPayload(width=float(width), height=float(height), tables=tables)
