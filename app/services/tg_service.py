"""Telegram service for sending reservation notifications."""

import base64
from datetime import date, time
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.reservation import Reservation, ReservationStatus

logger = get_logger(__name__)


class TelegramService:
    """Service for sending Telegram notifications via Bot API."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.bot_token = self.settings.tg_bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> None:
        """
        Send a message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID
            text: Message text (HTML formatted)
            parse_mode: Parse mode (default: HTML)
            reply_markup: Optional inline keyboard markup

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        if not self.bot_token:
            logger.warning("Telegram bot token not configured, skipping Telegram message")
            return

        if not text or not text.strip():
            logger.warning("Skipping Telegram sendMessage: message text is empty")
            return

        client = await self._get_client()
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text.strip(),
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"Telegram message sent successfully to chat_id {chat_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.error(f"Bad request to Telegram API: {e.response.text}")
            elif e.response.status_code == 403:
                logger.warning(f"Bot blocked by user (chat_id {chat_id})")
            elif e.response.status_code == 429:
                logger.warning(f"Telegram API rate limit exceeded for chat_id {chat_id}")
            else:
                logger.error(f"Failed to send Telegram message to chat_id {chat_id}: {e}", exc_info=True)
            # Don't raise - Telegram failures shouldn't break the reservation flow
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram message to chat_id {chat_id}: {e}", exc_info=True)
            # Don't raise - Telegram failures shouldn't break the reservation flow

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> None:
        """
        Answer a callback query from an inline keyboard button.

        Args:
            callback_query_id: The callback query ID from Telegram
            text: Optional text to show to the user
            show_alert: If True, show as alert; if False, show as notification
        """
        if not self.bot_token:
            return

        client = await self._get_client()
        url = f"{self.base_url}/answerCallbackQuery"

        payload = {
            "callback_query_id": callback_query_id,
        }
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = True

        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to answer callback query {callback_query_id}: {e}", exc_info=True)

    def _reservation_url(self, reservation: Reservation) -> str:
        """Guest view-reservation URL (for Telegram message link)."""
        base = self.settings.frontend_base_url.rstrip("/")
        code = reservation.reservation_code or ""
        return f"{base}/view-reservation?id={reservation.id}&code={code}"

    async def send_photo(
        self,
        chat_id: int,
        image_base64: str,
        caption: str | None = None,
    ) -> None:
        """Send a photo to a Telegram chat (e.g. QR code). Decodes base64 and uses sendPhoto API."""
        if not self.bot_token:
            logger.warning("Telegram bot token not configured, skipping sendPhoto")
            return
        if not image_base64 or not image_base64.strip():
            logger.warning("Skipping Telegram sendPhoto: image is empty")
            return
        try:
            image_bytes = base64.b64decode(image_base64.strip())
        except Exception as e:
            logger.warning(f"Failed to decode base64 image for sendPhoto: {e}")
            return
        client = await self._get_client()
        url = f"{self.base_url}/sendPhoto"
        files = {"photo": ("qr.png", image_bytes, "image/png")}
        data: dict = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        try:
            response = await client.post(url, data=data, files=files)
            response.raise_for_status()
            logger.info(f"Telegram photo sent successfully to chat_id {chat_id}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.error(f"Bad request to Telegram sendPhoto: {e.response.text}")
            else:
                logger.error(f"Failed to send Telegram photo to chat_id {chat_id}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram photo to chat_id {chat_id}: {e}", exc_info=True)

    def _format_reservation_confirmation_request(self, reservation: Reservation) -> str:
        """Format reservation confirmation request message in HTML (with buttons)."""
        date_str = (
            reservation.reservation_date.strftime("%Y-%m-%d")
            if reservation.reservation_date
            else "N/A"
        )
        start_time_str = (
            reservation.start_time.strftime("%H:%M") if reservation.start_time else "N/A"
        )
        end_time_str = (
            reservation.end_time.strftime("%H:%M") if reservation.end_time else "N/A"
        )
        branch_name = reservation.branch.name if reservation.branch else "N/A"
        contact = reservation.phone_number if reservation.phone_number else "N/A"

        view_url = self._reservation_url(reservation).replace("&", "&amp;")
        message = f"""📋 <b>Please confirm your reservation</b>

📅 Date: {date_str}
🕐 Time: {start_time_str} - {end_time_str}
🏢 Branch: {branch_name}
📞 Contact: {contact}

Please confirm or cancel your reservation using the buttons below.

<a href="{view_url}">View reservation</a>"""

        return message

    def _format_reservation_confirmation(self, reservation: Reservation) -> str:
        """Format reservation confirmation message in HTML (after user confirmed)."""
        date_str = (
            reservation.reservation_date.strftime("%Y-%m-%d")
            if reservation.reservation_date
            else "N/A"
        )
        start_time_str = (
            reservation.start_time.strftime("%H:%M") if reservation.start_time else "N/A"
        )
        end_time_str = (
            reservation.end_time.strftime("%H:%M") if reservation.end_time else "N/A"
        )
        code = reservation.reservation_code or "N/A"
        branch_name = reservation.branch.name if reservation.branch else "N/A"
        contact = reservation.phone_number if reservation.phone_number else "N/A"

        view_url = self._reservation_url(reservation).replace("&", "&amp;")
        message = f"""✅ <b>Reservation Confirmed</b>

📅 Date: {date_str}
🕐 Time: {start_time_str} - {end_time_str}
🏢 Branch: {branch_name}
📞 Contact: {contact}

Reservation Code: <code>{code}</code>

<a href="{view_url}">View reservation</a>"""

        if reservation.email:
            message += f"\n📧 Email: {reservation.email}"

        return message

    def _format_reservation_cancellation(self, reservation: Reservation) -> str:
        """Format reservation cancellation message in HTML."""
        date_str = (
            reservation.reservation_date.strftime("%Y-%m-%d")
            if reservation.reservation_date
            else "N/A"
        )
        branch_name = reservation.branch.name if reservation.branch else "N/A"

        message = f"""❌ <b>Reservation Cancelled</b>

Your reservation for {date_str} at {branch_name} has been cancelled."""

        return message

    async def send_reservation_confirmation(self, reservation: Reservation) -> None:
        """
        Send reservation confirmation message via Telegram.
        For PENDING reservations, includes inline keyboard buttons for confirm/cancel.
        For CONFIRMED reservations, sends confirmation message without buttons.
        """
        if not reservation.guest:
            logger.info(f"Skipping Telegram confirmation for reservation {reservation.id}: guest not loaded")
            return
        
        if not reservation.guest.tg_chat_id:
            logger.info(f"Skipping Telegram confirmation for reservation {reservation.id}: guest_id={reservation.guest_id} has no tg_chat_id")
            return
        
        if not self.bot_token:
            logger.warning(f"Telegram bot token not configured (TG_BOT_TOKEN empty), skipping Telegram message for reservation {reservation.id}")
            return

        # For PENDING reservations, send confirmation request with buttons
        # callback_data is limited to 64 bytes; use reservation UUID (not JWT)
        if reservation.status == ReservationStatus.PENDING:
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Confirm", "callback_data": f"confirm:{reservation.id}"},
                        {"text": "❌ Cancel", "callback_data": f"cancel:{reservation.id}"},
                    ]
                ]
            }

            message = self._format_reservation_confirmation_request(reservation)
            await self.send_message(
                reservation.guest.tg_chat_id,
                message,
                reply_markup=keyboard,
            )
            # QR code is sent only after user confirms (in webhook), not with PENDING request
        elif reservation.status == ReservationStatus.CONFIRMED:
            # For CONFIRMED reservations, send confirmation message without buttons
            # Preserve CONFIRMED status - don't change it to PENDING
            message = self._format_reservation_confirmation(reservation)
            await self.send_message(reservation.guest.tg_chat_id, message)
            if reservation.qr_code_base64:
                await self.send_photo(
                    reservation.guest.tg_chat_id,
                    reservation.qr_code_base64,
                    caption="QR code for your reservation",
                )
        elif reservation.status == ReservationStatus.CANCELLED:
            # For CANCELLED reservations, send cancellation message
            message = self._format_reservation_cancellation(reservation)
            await self.send_message(reservation.guest.tg_chat_id, message)
        else:
            # For other statuses (e.g., COMPLETED), send confirmation message
            message = self._format_reservation_confirmation(reservation)
            await self.send_message(reservation.guest.tg_chat_id, message)
            if reservation.qr_code_base64:
                await self.send_photo(
                    reservation.guest.tg_chat_id,
                    reservation.qr_code_base64,
                    caption="QR code for your reservation",
                )

    async def send_reservation_cancellation(self, reservation: Reservation) -> None:
        """Send reservation cancellation message via Telegram."""
        if not reservation.guest:
            logger.info(f"Skipping Telegram cancellation for reservation {reservation.id}: guest not loaded")
            return
        
        if not reservation.guest.tg_chat_id:
            logger.info(f"Skipping Telegram cancellation for reservation {reservation.id}: guest_id={reservation.guest_id} has no tg_chat_id")
            return
        
        if not self.bot_token:
            logger.warning(f"Telegram bot token not configured (TG_BOT_TOKEN empty), skipping Telegram message for reservation {reservation.id}")
            return

        message = self._format_reservation_cancellation(reservation)
        await self.send_message(reservation.guest.tg_chat_id, message)
