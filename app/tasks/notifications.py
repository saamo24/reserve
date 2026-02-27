"""Celery tasks for sending notifications."""

import asyncio
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.reservation import Reservation
from app.repositories.reservation_repository import ReservationRepository
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.services.tg_service import TelegramService

logger = get_logger(__name__)


def _run_async(coro):
    """
    Run async coroutine in Celery task.
    Handles event loop properly for Celery workers by always creating a fresh loop.
    """
    # Always create a new event loop for Celery tasks to avoid conflicts
    # This ensures clean async execution in worker processes
    try:
        # Close any existing loop if it exists
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.close()
        except RuntimeError:
            pass  # No loop exists, that's fine
        
        # Create and run a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    except Exception as e:
        logger.error(f"Error running async task: {e}", exc_info=True)
        raise


@celery_app.task(name="notifications.send_reservation_created", bind=True, max_retries=3)
def send_reservation_created_notification(self, reservation_id: str) -> None:
    """
    Celery task to send reservation creation notifications.

    Args:
        reservation_id: Reservation UUID as string
    """
    logger.info(f"Celery task send_reservation_created_notification started for reservation {reservation_id}")
    
    async def _send_notification() -> None:
        reservation_uuid = UUID(reservation_id)
        async with async_session_factory() as session:
            try:
                # Load reservation with branch and table (no need for guest relationship)
                reservation_repo = ReservationRepository(session)
                reservation = await reservation_repo.get_by_id(
                    reservation_uuid,
                    load_branch=True,
                    load_table=True,
                    load_guest=False,  # Don't need guest relationship - identify by phone number
                )

                if reservation is None:
                    logger.error(f"Reservation {reservation_id} not found")
                    return

                # Log reservation details for debugging
                logger.info(
                    f"Processing notification for reservation {reservation_id}: "
                    f"phone_number={reservation.phone_number}, status={reservation.status.value}"
                )

                # Find tg_chat_id by phone number (identify user by phone, not guest_id)
                logger.info(
                    f"Searching for tg_chat_id by phone number {reservation.phone_number} "
                    f"for reservation {reservation_id}"
                )
                tg_chat_id = await reservation_repo.find_tg_chat_id_by_phone_number(
                    reservation.phone_number
                )

                if tg_chat_id:
                    logger.info(
                        f"Found tg_chat_id {tg_chat_id} for phone number {reservation.phone_number} "
                        f"for reservation {reservation_id}"
                    )
                else:
                    logger.info(
                        f"No linked Telegram account found for phone number {reservation.phone_number}. "
                        f"User needs to link via /start command or Telegram link in email."
                    )

                # Create services and send notification
                email_service = EmailService()
                telegram_service = TelegramService()
                notification_service = NotificationService(
                    email_service=email_service,
                    telegram_service=telegram_service,
                )

                # Send notification using phone number identification (tg_chat_id if found)
                await notification_service.send_reservation_created_by_phone(
                    reservation, tg_chat_id
                )

                # Clean up telegram service client
                await telegram_service.close()

            except Exception as e:
                logger.error(
                    f"Failed to send reservation creation notification for {reservation_id}: {e}",
                    exc_info=True,
                )
                raise

    try:
        _run_async(_send_notification())
    except Exception as exc:
        logger.error(
            f"Task send_reservation_created_notification failed for {reservation_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="notifications.send_reservation_cancelled", bind=True, max_retries=3)
def send_reservation_cancelled_notification(
    self, reservation_id: str, old_status: str | None = None
) -> None:
    """
    Celery task to send reservation cancellation notifications.

    Args:
        reservation_id: Reservation UUID as string
        old_status: Previous status (optional)
    """
    async def _send_notification() -> None:
        reservation_uuid = UUID(reservation_id)
        async with async_session_factory() as session:
            try:
                # Load reservation with branch and table (no need for guest relationship)
                reservation_repo = ReservationRepository(session)
                reservation = await reservation_repo.get_by_id(
                    reservation_uuid,
                    load_branch=True,
                    load_table=True,
                    load_guest=False,  # Don't need guest relationship - identify by phone number
                )

                if reservation is None:
                    logger.error(f"Reservation {reservation_id} not found")
                    return

                # Log reservation details for debugging
                logger.info(
                    f"Processing cancellation notification for reservation {reservation_id}: "
                    f"phone_number={reservation.phone_number}, status={reservation.status.value}"
                )

                # Find tg_chat_id by phone number (identify user by phone, not guest_id)
                logger.info(
                    f"Searching for tg_chat_id by phone number {reservation.phone_number} "
                    f"for cancellation notification {reservation_id}"
                )
                tg_chat_id = await reservation_repo.find_tg_chat_id_by_phone_number(
                    reservation.phone_number
                )

                if tg_chat_id:
                    logger.info(
                        f"Found tg_chat_id {tg_chat_id} for phone number {reservation.phone_number} "
                        f"for cancellation notification {reservation_id}"
                    )
                else:
                    logger.info(
                        f"No linked Telegram account found for phone number {reservation.phone_number}. "
                        f"User needs to link via /start command or Telegram link in email."
                    )

                # Create services and send notification
                email_service = EmailService()
                telegram_service = TelegramService()
                notification_service = NotificationService(
                    email_service=email_service,
                    telegram_service=telegram_service,
                )

                # Send notification using phone number identification (tg_chat_id if found)
                await notification_service.send_reservation_cancelled_by_phone(
                    reservation, old_status, tg_chat_id
                )

                # Clean up telegram service client
                await telegram_service.close()

            except Exception as e:
                logger.error(
                    f"Failed to send reservation cancellation notification for {reservation_id}: {e}",
                    exc_info=True,
                )
                raise

    try:
        _run_async(_send_notification())
    except Exception as exc:
        logger.error(
            f"Task send_reservation_cancelled_notification failed for {reservation_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
