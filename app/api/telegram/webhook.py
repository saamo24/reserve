"""Telegram webhook endpoint for handling callback queries."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.deps import DbSession, RedisDep
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.reservation import ReservationStatus
from app.repositories.reservation_repository import ReservationRepository
from app.services.reservation_service import ReservationService
from app.services.locking_service import LockingService
from app.services.caching_service import CachingService
from app.repositories.branch_repository import BranchRepository
from app.repositories.table_repository import TableRepository
from app.repositories.guest_repository import GuestRepository
from app.services.tg_service import TelegramService
from app.utils.tokens import verify_reservation_token

logger = get_logger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramUpdate(BaseModel):
    """Telegram Update object structure."""

    update_id: int
    callback_query: dict | None = None


class CallbackQuery(BaseModel):
    """Telegram callback query structure."""

    id: str
    from_user: dict
    message: dict | None = None
    data: str


def _reservation_service(db: DbSession, redis: RedisDep) -> ReservationService:
    """Create ReservationService instance."""
    return ReservationService(
        session=db,
        branch_repo=BranchRepository(db),
        table_repo=TableRepository(db),
        reservation_repo=ReservationRepository(db),
        guest_repo=GuestRepository(db),
        locking=LockingService(redis),
        caching=CachingService(redis),
    )


async def _handle_confirm_callback(
    callback_query_id: str,
    chat_id: int,
    token: str,
    db: DbSession,
    redis: RedisDep,
) -> None:
    """Handle confirm callback query."""
    telegram_service = TelegramService()

    try:
        # Verify token
        reservation_id = verify_reservation_token(token, "confirm")
        if reservation_id is None:
            await telegram_service.answer_callback_query(
                callback_query_id,
                text="❌ Invalid or expired confirmation token",
                show_alert=True,
            )
            return

        # Load and confirm reservation
        service = _reservation_service(db, redis)
        reservation = await service.confirm_reservation(reservation_id, token)

        if reservation is None:
            await telegram_service.answer_callback_query(
                callback_query_id,
                text="❌ Reservation not found",
                show_alert=True,
            )
            return

        # Auto-link guest to Telegram chat_id if not already linked
        if reservation.guest and reservation.guest.tg_chat_id != chat_id:
            guest_repo = GuestRepository(db)
            try:
                await guest_repo.update_tg_chat_id(reservation.guest_id, chat_id)
                logger.info(f"Linked guest {reservation.guest_id} to Telegram chat_id {chat_id}")
            except Exception as e:
                logger.warning(f"Failed to link guest {reservation.guest_id} to chat_id {chat_id}: {e}")

        # Send confirmation message
        confirmation_message = telegram_service._format_reservation_confirmation(reservation)
        await telegram_service.send_message(chat_id, confirmation_message)

        # Answer callback query
        await telegram_service.answer_callback_query(
            callback_query_id,
            text="✅ Reservation confirmed!",
        )

        await telegram_service.close()
        logger.info(f"Reservation {reservation_id} confirmed via Telegram")

    except ValueError as e:
        await telegram_service.answer_callback_query(
            callback_query_id,
            text=f"❌ {str(e)}",
            show_alert=True,
        )
        await telegram_service.close()
    except Exception as e:
        logger.error(f"Error handling confirm callback: {e}", exc_info=True)
        await telegram_service.answer_callback_query(
            callback_query_id,
            text="❌ An error occurred. Please try again later.",
            show_alert=True,
        )
        await telegram_service.close()


async def _handle_cancel_callback(
    callback_query_id: str,
    chat_id: int,
    token: str,
    db: DbSession,
    redis: RedisDep,
) -> None:
    """Handle cancel callback query."""
    telegram_service = TelegramService()

    try:
        # Verify token
        reservation_id = verify_reservation_token(token, "cancel")
        if reservation_id is None:
            await telegram_service.answer_callback_query(
                callback_query_id,
                text="❌ Invalid or expired cancellation token",
                show_alert=True,
            )
            return

        # Load and cancel reservation
        service = _reservation_service(db, redis)
        reservation = await service.cancel_reservation(reservation_id, token)

        if reservation is None:
            await telegram_service.answer_callback_query(
                callback_query_id,
                text="❌ Reservation not found",
                show_alert=True,
            )
            return

        # Auto-link guest to Telegram chat_id if not already linked
        if reservation.guest and reservation.guest.tg_chat_id != chat_id:
            guest_repo = GuestRepository(db)
            try:
                await guest_repo.update_tg_chat_id(reservation.guest_id, chat_id)
                logger.info(f"Linked guest {reservation.guest_id} to Telegram chat_id {chat_id}")
            except Exception as e:
                logger.warning(f"Failed to link guest {reservation.guest_id} to chat_id {chat_id}: {e}")

        # Send cancellation message
        cancellation_message = telegram_service._format_reservation_cancellation(reservation)
        await telegram_service.send_message(chat_id, cancellation_message)

        # Answer callback query
        await telegram_service.answer_callback_query(
            callback_query_id,
            text="❌ Reservation cancelled",
        )

        await telegram_service.close()
        logger.info(f"Reservation {reservation_id} cancelled via Telegram")

    except ValueError as e:
        await telegram_service.answer_callback_query(
            callback_query_id,
            text=f"❌ {str(e)}",
            show_alert=True,
        )
        await telegram_service.close()
    except Exception as e:
        logger.error(f"Error handling cancel callback: {e}", exc_info=True)
        await telegram_service.answer_callback_query(
            callback_query_id,
            text="❌ An error occurred. Please try again later.",
            show_alert=True,
        )
        await telegram_service.close()


async def _handle_start_command(
    chat_id: int,
    reservation_code: str | None,
    db: DbSession,
) -> None:
    """Handle /start command with optional reservation code to link guest."""
    telegram_service = TelegramService()

    try:
        reservation_repo = ReservationRepository(db)
        
        if not reservation_code:
            # No code provided, send welcome message with instructions
            await telegram_service.send_message(
                chat_id,
                "👋 Welcome! To link your account:\n\n"
                "1. Use the Telegram link from your reservation email, OR\n"
                "2. Send: /start YOUR_RESERVATION_CODE, OR\n"
                "3. Send: /start PHONE_NUMBER (e.g., /start +37494968897)"
            )
            await telegram_service.close()
            return

        # Try to find reservation by code first
        reservation = await reservation_repo.get_by_code(
            reservation_code,
            load_guest=True,
        )
        
        # If not found by code, try treating it as a phone number
        if reservation is None:
            # Check if it looks like a phone number (starts with + or is all digits)
            cleaned_code = reservation_code.replace(' ', '').replace('-', '')
            is_phone = reservation_code.startswith('+') or cleaned_code.isdigit()
            
            logger.info(f"Reservation not found by code '{reservation_code}', is_phone={is_phone}, trying phone lookup...")
            
            if is_phone:
                reservation = await reservation_repo.get_most_recent_by_phone_number(
                    reservation_code,
                    load_guest=True,
                )
                if reservation:
                    logger.info(f"Found reservation by phone number: {reservation_code}, reservation_id={reservation.id}")
                else:
                    logger.warning(f"No reservation found for phone number: {reservation_code}")

        if reservation is None:
            await telegram_service.send_message(
                chat_id,
                f"❌ Reservation not found for '{reservation_code}'.\n\n"
                "Please check:\n"
                "• Your reservation code from the email, OR\n"
                "• Your phone number (e.g., /start +37494968897)"
            )
            await telegram_service.close()
            logger.warning(f"Reservation not found for code/phone: {reservation_code}")
            return

        if not reservation.guest:
            await telegram_service.send_message(
                chat_id,
                "❌ Error: Guest information not found for this reservation."
            )
            await telegram_service.close()
            logger.error(f"Guest not found for reservation code: {reservation_code}")
            return

        # Link guest to Telegram chat_id
        guest_repo = GuestRepository(db)
        try:
            if reservation.guest.tg_chat_id == chat_id:
                # Already linked
                await telegram_service.send_message(
                    chat_id,
                    "✅ Your account is already linked! You'll receive reservation updates here."
                )
                logger.info(f"Guest {reservation.guest_id} already linked to chat_id {chat_id}")
            else:
                await guest_repo.update_tg_chat_id(reservation.guest_id, chat_id)
                await telegram_service.send_message(
                    chat_id,
                    "✅ Account linked successfully! You'll now receive reservation updates here via Telegram."
                )
                logger.info(f"Linked guest {reservation.guest_id} to Telegram chat_id {chat_id} via /start command")
                # Reload with branch/table for formatting; same as email: PENDING until user confirms/cancels in TG
                reservation = await reservation_repo.get_by_id(
                    reservation.id, load_branch=True, load_table=True, load_guest=True
                )
                if reservation.status == ReservationStatus.CONFIRMED:
                    reservation.status = ReservationStatus.PENDING
                    await reservation_repo.update(reservation)
                    await db.commit()
                await telegram_service.send_reservation_confirmation(reservation)
        except Exception as e:
            await telegram_service.send_message(
                chat_id,
                "❌ An error occurred while linking your account. Please try again later."
            )
            logger.error(f"Failed to link guest {reservation.guest_id} to chat_id {chat_id}: {e}", exc_info=True)

        await telegram_service.close()

    except Exception as e:
        logger.error(f"Error handling /start command: {e}", exc_info=True)
        try:
            await telegram_service.send_message(
                chat_id,
                "❌ An error occurred. Please try again later."
            )
            await telegram_service.close()
        except Exception:
            pass


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: DbSession,
    redis: RedisDep,
) -> dict:
    """
    Handle Telegram webhook updates (callback queries from inline keyboard buttons and messages).

    This endpoint receives updates from Telegram when users interact with bot buttons or send messages.
    """
    try:
        body = await request.json()
        
        # Optional: Verify webhook secret if configured
        settings = get_settings()
        if settings.telegram_webhook_secret:
            # Telegram doesn't send a secret header by default, but you can verify
            # the request comes from Telegram by checking the bot token in the update
            # For now, we'll skip this as Telegram's IP-based verification is sufficient
            pass
        
        # Handle callback queries (button clicks)
        callback_query = body.get("callback_query")
        if callback_query:
            callback_query_id = callback_query.get("id")
            from_user = callback_query.get("from", {})
            chat_id = from_user.get("id")
            data = callback_query.get("data", "")

            if callback_query_id and chat_id and data:
                # Parse callback data: format is "action:token"
                if ":" in data:
                    action, token = data.split(":", 1)
                    # Route to appropriate handler
                    if action == "confirm":
                        await _handle_confirm_callback(callback_query_id, chat_id, token, db, redis)
                    elif action == "cancel":
                        await _handle_cancel_callback(callback_query_id, chat_id, token, db, redis)
                    else:
                        logger.warning(f"Unknown callback action: {action}")
                else:
                    logger.warning(f"Invalid callback data format: {data}")
            else:
                logger.warning(f"Invalid callback query: {callback_query}")
            
            return {"ok": True}
        
        # Handle regular messages (e.g., /start command)
        message = body.get("message")
        if message:
            from_user = message.get("from", {})
            chat_id = from_user.get("id")
            text = message.get("text", "")
            
            logger.info(f"Received message from chat_id {chat_id}: {text}")
            
            if chat_id and text:
                # Handle /start command
                if text.startswith("/start"):
                    # Parse reservation code from /start command
                    # Format: /start or /start RESERVATION_CODE
                    parts = text.split(maxsplit=1)
                    reservation_code = parts[1] if len(parts) > 1 else None
                    
                    logger.info(f"Processing /start command from chat_id {chat_id} with code/phone: {reservation_code}")
                    await _handle_start_command(chat_id, reservation_code, db)
                else:
                    # Log other messages for debugging
                    logger.info(f"Received non-/start message from chat_id {chat_id}: {text[:50]}")
            else:
                logger.warning(f"Message missing chat_id or text: chat_id={chat_id}, text={text}")
            
            return {"ok": True}
        
        # Log other update types for debugging
        logger.debug(f"Received update type: {body.get('update_id')}")
        return {"ok": True}

    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
