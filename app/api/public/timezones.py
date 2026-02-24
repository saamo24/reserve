"""Public timezone endpoints."""

from fastapi import APIRouter

from app.utils.validators import get_available_timezones

router = APIRouter(prefix="/timezones", tags=["public-timezones"])


@router.get("")
async def list_timezones() -> list[str]:
    """Get all available IANA timezone names for dropdown selection."""
    return get_available_timezones()
