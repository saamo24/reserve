"""Email service for sending reservation notifications."""

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.reservation import Reservation, ReservationStatus
from app.utils.tokens import create_reservation_token

logger = get_logger(__name__)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self) -> None:
        self.settings = get_settings()
        # Get template directory - relative to app directory
        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        """Send an email via SMTP."""
        if not self.settings.smtp_host:
            logger.warning("SMTP not configured, skipping email send")
            return

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.settings.smtp_from_email
        message["To"] = to_email

        # Add text and HTML parts
        if text_body:
            text_part = MIMEText(text_body, "plain")
            message.attach(text_part)
        
        html_part = MIMEText(html_body, "html")
        message.attach(html_part)

        smtp = None
        try:
            # Use SMTP client directly for better control over TLS/STARTTLS
            # For port 587: connect plain, then use STARTTLS if TLS is enabled
            # For port 465: use SSL connection from the start
            use_ssl = self.settings.smtp_port == 465
            
            smtp = aiosmtplib.SMTP(
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                use_tls=use_ssl,
                timeout=self.settings.smtp_timeout,
            )
            
            await smtp.connect(timeout=self.settings.smtp_timeout)
            
            # For port 587 with TLS enabled, upgrade connection with STARTTLS
            # Only if not already using SSL/TLS
            if self.settings.smtp_use_tls and self.settings.smtp_port == 587 and not use_ssl:
                try:
                    await smtp.starttls()
                except Exception as tls_error:
                    # If already using TLS, that's fine - continue
                    if "already using TLS" not in str(tls_error):
                        raise
            
            # Authenticate if credentials provided
            if self.settings.smtp_username and self.settings.smtp_password:
                await smtp.login(
                    self.settings.smtp_username,
                    self.settings.smtp_password,
                )
            
            # Send the message
            await smtp.send_message(message)
            await smtp.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            # Don't raise - email failures shouldn't break the reservation flow
            if smtp:
                try:
                    await smtp.quit()
                except Exception:
                    pass

    async def send_reservation_confirmation(self, reservation: Reservation) -> None:
        """Send confirmation email to user with confirm/cancel buttons."""
        if not reservation.email:
            return

        # Generate tokens for confirm and cancel actions
        confirm_token = create_reservation_token(reservation.id, "confirm")
        cancel_token = create_reservation_token(reservation.id, "cancel")

        # Build URLs - use frontend URL for user-facing links
        frontend_url = self.settings.frontend_base_url.rstrip("/")
        confirm_url = f"{frontend_url}/reservations/{reservation.id}/confirm?token={confirm_token}"
        cancel_url = f"{frontend_url}/reservations/{reservation.id}/cancel?token={cancel_token}"

        # Load and render template
        template = self.env.get_template("confirmation.html")
        html_body = template.render(
            reservation=reservation,
            confirm_url=confirm_url,
            cancel_url=cancel_url,
        )

        subject = f"Please confirm your reservation at {reservation.branch.name}"
        await self._send_email(
            to_email=reservation.email,
            subject=subject,
            html_body=html_body,
        )

    async def send_reservation_status_update(
        self,
        reservation: Reservation,
        old_status: ReservationStatus,
    ) -> None:
        """Send status update email to user and admin when reservation status changes."""
        # Only send if status actually changed and is a terminal state
        if reservation.status == old_status:
            return

        if reservation.status not in [
            ReservationStatus.CONFIRMED,
            ReservationStatus.CANCELLED,
            ReservationStatus.COMPLETED,
        ]:
            return

        # Send to user if email exists
        if reservation.email:
            template = self.env.get_template("status_update.html")
            html_body = template.render(
                reservation=reservation,
                status=reservation.status,
                old_status=old_status,
            )

            status_text = reservation.status.value.lower()
            subject = f"Reservation {status_text} - {reservation.branch.name}"
            await self._send_email(
                to_email=reservation.email,
                subject=subject,
                html_body=html_body,
            )

        # Always send status update to admin
        await self.send_admin_status_update(reservation, old_status)

    async def send_admin_notification(self, reservation: Reservation) -> None:
        """Send notification email to admin about new reservation."""
        admin_email = self.settings.admin_email
        if not admin_email:
            logger.warning("Admin email not configured, skipping admin notification")
            return

        # Load and render template
        # Use frontend URL for admin panel links
        frontend_url = self.settings.frontend_base_url.rstrip("/")
        template = self.env.get_template("admin_notification.html")
        html_body = template.render(
            reservation=reservation,
            app_base_url=frontend_url,
        )

        subject = f"New reservation at {reservation.branch.name}"
        await self._send_email(
            to_email=admin_email,
            subject=subject,
            html_body=html_body,
        )

    async def send_admin_status_update(
        self,
        reservation: Reservation,
        old_status: ReservationStatus,
        updated_by: str | None = None,
    ) -> None:
        """Send status update notification email to admin."""
        admin_email = self.settings.admin_email
        if not admin_email:
            logger.warning("Admin email not configured, skipping admin status update")
            return

        # Load and render admin-specific template
        # Use frontend URL for admin panel links
        frontend_url = self.settings.frontend_base_url.rstrip("/")
        template = self.env.get_template("admin_status_update.html")
        html_body = template.render(
            reservation=reservation,
            status=reservation.status,
            old_status=old_status,
            app_base_url=frontend_url,
            updated_by=updated_by,
        )

        status_text = reservation.status.value.lower()
        subject = f"Reservation {status_text}: {reservation.full_name} - {reservation.branch.name}"
        await self._send_email(
            to_email=admin_email,
            subject=subject,
            html_body=html_body,
        )
