"""Layout (floor plan) schemas."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


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


# ============================================================================
# Layout V1 (legacy: single canvas)
# ============================================================================


class LayoutV1Payload(BaseModel):
    """V1 layout: single canvas with tables (legacy format)."""

    width: float = Field(..., gt=0, le=5000)
    height: float = Field(..., gt=0, le=5000)
    tables: list[LayoutTablePayload] = Field(default_factory=list)


# ============================================================================
# Layout V2 (zones/floors)
# ============================================================================


class LayoutFloorPayload(BaseModel):
    """Floor within an indoor zone."""

    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    width: float = Field(..., gt=0, le=5000)
    height: float = Field(..., gt=0, le=5000)
    tables: list[LayoutTablePayload] = Field(default_factory=list)


class LayoutZonePayload(BaseModel):
    """Zone (indoor with floors, or outdoor with single canvas)."""

    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., pattern="^(indoor|outdoor)$")
    # Indoor: floors required, no top-level tables/width/height
    floors: list[LayoutFloorPayload] | None = Field(default=None)
    # Outdoor: width/height/tables required, no floors
    width: float | None = Field(default=None, gt=0, le=5000)
    height: float | None = Field(default=None, gt=0, le=5000)
    tables: list[LayoutTablePayload] | None = Field(default=None)

    @model_validator(mode="after")
    def validate_zone_structure(self) -> "LayoutZonePayload":
        """Enforce indoor vs outdoor structure rules."""
        if self.type == "indoor":
            if self.floors is None or len(self.floors) == 0:
                raise ValueError("Indoor zones must have at least one floor")
            if self.width is not None or self.height is not None or self.tables is not None:
                raise ValueError("Indoor zones cannot have top-level width/height/tables")
        elif self.type == "outdoor":
            if self.width is None or self.height is None or self.tables is None:
                raise ValueError("Outdoor zones must have width, height, and tables")
            if self.floors is not None:
                raise ValueError("Outdoor zones cannot have floors")
        return self


class LayoutV2Payload(BaseModel):
    """V2 layout: zones with floors (indoor) or single canvas (outdoor)."""

    zones: list[LayoutZonePayload] = Field(default_factory=list)


# ============================================================================
# Union type and parsers
# ============================================================================

LayoutDocument = LayoutV1Payload | LayoutV2Payload

# Backward compatibility alias
LayoutPayload = LayoutV1Payload


def layout_from_dict(raw: dict | None) -> LayoutPayload:
    """Build LayoutV1Payload from stored JSON dict. Returns empty layout if invalid.
    
    DEPRECATED: Use layout_from_dict_any() for v1/v2 support.
    """
    if not raw or not isinstance(raw, dict):
        return LayoutV1Payload(width=800, height=600, tables=[])
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
    return LayoutV1Payload(width=float(width), height=float(height), tables=tables)


def layout_from_dict_any(raw: dict | None) -> LayoutDocument:
    """Parse layout JSON (v1 or v2). Returns empty v1 layout if invalid."""
    if not raw or not isinstance(raw, dict):
        return LayoutV1Payload(width=800, height=600, tables=[])
    
    # Detect v2: has "zones" key
    if "zones" in raw:
        try:
            return LayoutV2Payload.model_validate(raw)
        except Exception:
            # Fallback to empty v1 if v2 validation fails
            return LayoutV1Payload(width=800, height=600, tables=[])
    
    # Otherwise parse as v1
    try:
        return LayoutV1Payload.model_validate(raw)
    except Exception:
        return LayoutV1Payload(width=800, height=600, tables=[])


def layout_to_json_any(payload: LayoutDocument) -> dict:
    """Serialize layout (v1 or v2) to JSON-serializable dict."""
    if isinstance(payload, LayoutV2Payload):
        return payload.model_dump(mode="json")
    # V1
    return {
        "width": payload.width,
        "height": payload.height,
        "tables": [
            {
                "id": str(t.id),
                "x": t.x,
                "y": t.y,
                "width": t.width,
                "height": t.height,
                "rotation": t.rotation,
                "shape": t.shape,
                "capacity": t.capacity,
                "table_number": t.table_number,
            }
            for t in payload.tables
        ],
    }
