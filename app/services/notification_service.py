"""Unified notification service for sending notifications via multiple channels."""

from app.core.logging import get_logger
from app.models.reservation import Reservation
from app.services.email_service import EmailService
from app.services.tg_service import TelegramService

logger = get_logger(__name__)


class NotificationService:
    """Unified service for sending notifications via Email and Telegram."""

    def __init__(
        self,
        email_service: EmailService,
        telegram_service: TelegramService,
    ) -> None:
        self._email_service = email_service
        self._telegram_service = telegram_service

    async def send_reservation_created(self, reservation: Reservation) -> None:
        """
        Send reservation creation notifications via all available channels.

        Args:
            reservation: Reservation instance with relations loaded (branch, table, guest)
        """
        # Send email if email exists
        if reservation.email:
            try:
                await self._email_service.send_reservation_confirmation(reservation)
            except Exception as e:
                logger.error(
                    f"Failed to send reservation creation email for reservation {reservation.id}: {e}",
                    exc_info=True,
                )

        # Send Telegram notification if guest has tg_chat_id
        if not reservation.guest:
            logger.info(f"Skipping Telegram notification for reservation {reservation.id}: guest not loaded")
        elif not reservation.guest.tg_chat_id:
            logger.info(f"Skipping Telegram notification for reservation {reservation.id}: guest_id={reservation.guest_id} has no tg_chat_id")
        else:
            try:
                logger.info(f"Sending Telegram notification for reservation {reservation.id} to chat_id {reservation.guest.tg_chat_id}")
                await self._telegram_service.send_reservation_confirmation(reservation)
            except Exception as e:
                logger.error(
                    f"Failed to send reservation creation Telegram notification for reservation {reservation.id}: {e}",
                    exc_info=True,
                )

        # Always send admin notification
        try:
            await self._email_service.send_admin_notification(reservation)
        except Exception as e:
            logger.error(
                f"Failed to send admin notification for reservation {reservation.id}: {e}",
                exc_info=True,
            )

    async def send_reservation_cancelled(
        self,
        reservation: Reservation,
        old_status: str | None = None,
    ) -> None:
        """
        Send reservation cancellation notifications via all available channels.

        Args:
            reservation: Reservation instance with relations loaded (branch, table, guest)
            old_status: Previous status (for email service compatibility)
        """
        # Send email status update if email exists
        if reservation.email:
            try:
                from app.models.reservation import ReservationStatus

                # Convert old_status string to enum if provided
                old_status_enum = None
                if old_status:
                    try:
                        old_status_enum = ReservationStatus(old_status)
                    except ValueError:
                        pass

                await self._email_service.send_reservation_status_update(
                    reservation,
                    old_status_enum or reservation.status,
                )
            except Exception as e:
                logger.error(
                    f"Failed to send reservation cancellation email for reservation {reservation.id}: {e}",
                    exc_info=True,
                )

        # Send Telegram notification if guest has tg_chat_id
        if not reservation.guest:
            logger.info(f"Skipping Telegram cancellation notification for reservation {reservation.id}: guest not loaded")
        elif not reservation.guest.tg_chat_id:
            logger.info(f"Skipping Telegram cancellation notification for reservation {reservation.id}: guest_id={reservation.guest_id} has no tg_chat_id")
        else:
            try:
                logger.info(f"Sending Telegram cancellation notification for reservation {reservation.id} to chat_id {reservation.guest.tg_chat_id}")
                await self._telegram_service.send_reservation_cancellation(reservation)
            except Exception as e:
                logger.error(
                    f"Failed to send reservation cancellation Telegram notification for reservation {reservation.id}: {e}",
                    exc_info=True,
                )

        # Always send admin status update
        try:
            from app.models.reservation import ReservationStatus

            old_status_enum = None
            if old_status:
                try:
                    old_status_enum = ReservationStatus(old_status)
                except ValueError:
                    pass

            await self._email_service.send_admin_status_update(
                reservation,
                old_status_enum or reservation.status,
            )
        except Exception as e:
            logger.error(
                f"Failed to send admin status update for reservation {reservation.id}: {e}",
                exc_info=True,
            )
