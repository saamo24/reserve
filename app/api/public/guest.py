"""Public guest endpoints: current guest profile (Telegram link status, bot username)."""

from fastapi import APIRouter

from app.api.deps import DbSession, GuestIdDep
from app.core.config import get_settings
from app.repositories.guest_repository import GuestRepository
from pydantic import BaseModel


class GuestMeResponse(BaseModel):
    """Current guest profile for frontend (Telegram link status and bot link)."""

    telegram_linked: bool
    tg_bot_username: str | None = None


router = APIRouter(prefix="/guest", tags=["public-guest"])


@router.get("/me", response_model=GuestMeResponse)
async def get_guest_me(
    guest_id: GuestIdDep,
    db: DbSession,
) -> GuestMeResponse:
    """Return whether the current guest has Telegram linked and the bot username for building the link."""
    settings = get_settings()
    guest_repo = GuestRepository(db)
    guest = await guest_repo.get_by_id(guest_id)
    telegram_linked = guest is not None and guest.tg_chat_id is not None
    tg_bot_username = settings.tg_bot_username or None
    return GuestMeResponse(
        telegram_linked=telegram_linked,
        tg_bot_username=tg_bot_username,
    )
