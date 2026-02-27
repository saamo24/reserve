"""Unified notification service for sending notifications via multiple channels."""

from app.core.logging import get_logger
from app.models.reservation import Reservation, ReservationStatus
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

    async def send_reservation_created_by_phone(
        self, reservation: Reservation, tg_chat_id: int | None
    ) -> None:
        """
        Send reservation creation notifications via all available channels.
        Identifies user by phone number and tg_chat_id (not guest relationship).

        Args:
            reservation: Reservation instance with relations loaded (branch, table)
            tg_chat_id: Telegram chat ID found by phone number lookup, or None if not found
        """
        logger.info(
            f"Processing reservation creation notification for reservation {reservation.id}: "
            f"status={reservation.status.value}, phone_number={reservation.phone_number}, "
            f"tg_chat_id={tg_chat_id}"
        )
        
        # Send email if email exists
        if reservation.email:
            try:
                logger.info(f"Sending email notification for reservation {reservation.id} to {reservation.email}")
                await self._email_service.send_reservation_confirmation(reservation)
                logger.info(f"Email notification sent successfully for reservation {reservation.id}")
            except Exception as e:
                logger.error(
                    f"Failed to send reservation creation email for reservation {reservation.id}: {e}",
                    exc_info=True,
                )

        # Send Telegram notification if tg_chat_id was found by phone number
        if tg_chat_id:
            try:
                logger.info(
                    f"Sending Telegram notification for reservation {reservation.id} "
                    f"to chat_id {tg_chat_id} (identified by phone_number={reservation.phone_number})"
                )

                # For PENDING reservations, send confirmation request with buttons
                if reservation.status == ReservationStatus.PENDING:
                    keyboard = {
                        "inline_keyboard": [
                            [
                                {
                                    "text": "✅ Confirm",
                                    "callback_data": f"confirm:{reservation.id}",
                                },
                                {
                                    "text": "❌ Cancel",
                                    "callback_data": f"cancel:{reservation.id}",
                                },
                            ]
                        ]
                    }
                    message = self._telegram_service._format_reservation_confirmation_request(
                        reservation
                    )
                    await self._telegram_service.send_message(
                        tg_chat_id,
                        message,
                        reply_markup=keyboard,
                    )
                # For CONFIRMED reservations, send confirmation + QR (if any)
                elif reservation.status == ReservationStatus.CONFIRMED:
                    message = self._telegram_service._format_reservation_confirmation(reservation)
                    await self._telegram_service.send_message(tg_chat_id, message)
                    if reservation.qr_code_base64:
                        await self._telegram_service.send_photo(
                            tg_chat_id,
                            reservation.qr_code_base64,
                            caption="QR code for your reservation",
                        )
                # For CANCELLED reservations, send cancellation message
                elif reservation.status == ReservationStatus.CANCELLED:
                    message = self._telegram_service._format_reservation_cancellation(
                        reservation
                    )
                    await self._telegram_service.send_message(tg_chat_id, message)
                # For other statuses (e.g., COMPLETED), behave like CONFIRMED
                else:
                    message = self._telegram_service._format_reservation_confirmation(reservation)
                    await self._telegram_service.send_message(tg_chat_id, message)
                    if reservation.qr_code_base64:
                        await self._telegram_service.send_photo(
                            tg_chat_id,
                            reservation.qr_code_base64,
                            caption="QR code for your reservation",
                        )

                logger.info(
                    f"Telegram notification sent successfully for reservation {reservation.id} "
                    f"to chat_id {tg_chat_id}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send reservation creation Telegram notification for reservation {reservation.id}: {e}",
                    exc_info=True,
                )
        else:
            logger.info(
                f"Skipping Telegram notification for reservation {reservation.id}: "
                f"No tg_chat_id found for phone_number={reservation.phone_number}. "
                f"User needs to link via /start command or Telegram link in email."
            )

        # Always send admin notification
        try:
            await self._email_service.send_admin_notification(reservation)
        except Exception as e:
            logger.error(
                f"Failed to send admin notification for reservation {reservation.id}: {e}",
                exc_info=True,
            )

    async def send_reservation_created(self, reservation: Reservation) -> None:
        """
        Send reservation creation notifications via all available channels.

        Args:
            reservation: Reservation instance with relations loaded (branch, table, guest)
        """
        logger.info(
            f"Processing reservation creation notification for reservation {reservation.id}: "
            f"status={reservation.status.value}, guest_id={reservation.guest_id}, "
            f"guest_loaded={reservation.guest is not None}, "
            f"tg_chat_id={reservation.guest.tg_chat_id if reservation.guest else 'N/A'}"
        )
        
        # Send email if email exists
        if reservation.email:
            try:
                logger.info(f"Sending email notification for reservation {reservation.id} to {reservation.email}")
                await self._email_service.send_reservation_confirmation(reservation)
                logger.info(f"Email notification sent successfully for reservation {reservation.id}")
            except Exception as e:
                logger.error(
                    f"Failed to send reservation creation email for reservation {reservation.id}: {e}",
                    exc_info=True,
                )

        # Send Telegram notification if guest has tg_chat_id
        if not reservation.guest:
            logger.warning(
                f"Skipping Telegram notification for reservation {reservation.id}: guest not loaded. "
                f"guest_id={reservation.guest_id}"
            )
        elif not reservation.guest.tg_chat_id:
            logger.info(
                f"Skipping Telegram notification for reservation {reservation.id}: "
                f"guest_id={reservation.guest_id} has no tg_chat_id. "
                f"User needs to link account via /start command or Telegram link in email."
            )
        else:
            try:
                logger.info(
                    f"Sending Telegram notification for reservation {reservation.id} "
                    f"to chat_id {reservation.guest.tg_chat_id} (guest_id={reservation.guest_id})"
                )
                await self._telegram_service.send_reservation_confirmation(reservation)
                logger.info(
                    f"Telegram notification sent successfully for reservation {reservation.id} "
                    f"to chat_id {reservation.guest.tg_chat_id}"
                )
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

    async def send_reservation_cancelled_by_phone(
        self,
        reservation: Reservation,
        old_status: str | None = None,
        tg_chat_id: int | None = None,
    ) -> None:
        """
        Send reservation cancellation notifications via all available channels.
        Identifies user by phone number and tg_chat_id (not guest relationship).

        Args:
            reservation: Reservation instance with relations loaded (branch, table)
            old_status: Previous status (for email service compatibility)
            tg_chat_id: Telegram chat ID found by phone number lookup, or None if not found
        """
        logger.info(
            f"Processing cancellation notification for reservation {reservation.id}: "
            f"phone_number={reservation.phone_number}, status={reservation.status.value}, "
            f"tg_chat_id={tg_chat_id}"
        )
        
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

        # Send Telegram notification if tg_chat_id was found by phone number
        if tg_chat_id:
            try:
                logger.info(
                    f"Sending Telegram cancellation notification for reservation {reservation.id} "
                    f"to chat_id {tg_chat_id} (identified by phone_number={reservation.phone_number})"
                )
                # Create a temporary guest-like object for Telegram service
                from types import SimpleNamespace
                original_guest = getattr(reservation, 'guest', None)
                reservation.guest = SimpleNamespace(tg_chat_id=tg_chat_id)
                
                try:
                    await self._telegram_service.send_reservation_cancellation(reservation)
                    logger.info(
                        f"Telegram cancellation notification sent successfully for reservation {reservation.id} "
                        f"to chat_id {tg_chat_id}"
                    )
                finally:
                    # Restore original guest if it existed
                    reservation.guest = original_guest
            except Exception as e:
                logger.error(
                    f"Failed to send reservation cancellation Telegram notification for reservation {reservation.id}: {e}",
                    exc_info=True,
                )
        else:
            logger.info(
                f"Skipping Telegram cancellation notification for reservation {reservation.id}: "
                f"No tg_chat_id found for phone_number={reservation.phone_number}"
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
