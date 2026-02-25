"""Guest identification middleware: set or verify signed guest_id cookie and request.state.guest_id.
Also supports Authorization header token as fallback for Safari ITP."""

import logging
from typing import Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.security import create_guest_token, decode_guest_token
from app.utils.guest_serializer import sign_guest_id, verify_guest_id

logger = logging.getLogger("app.guest")

# TODO: rate limit by IP for cookie issuance to prevent abuse
GUEST_COOKIE_NAME = "guest_id"
GUEST_TOKEN_HEADER = "X-Guest-Token"  # Response header to send token to frontend


class GuestMiddleware(BaseHTTPMiddleware):
    """
    Ensure every request has request.state.guest_id set from a signed HTTP-only cookie.
    If the cookie is missing or invalid, generate a new guest_id, sign it, and set the cookie on the response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        guest_id = None

        # Try cookie first (preferred method)
        cookie_value = request.cookies.get(GUEST_COOKIE_NAME)
        if cookie_value:
            guest_id = verify_guest_id(cookie_value)
            if guest_id is None:
                logger.warning("Invalid guest_id cookie signature")

        # Fallback: Try Authorization header token (for Safari ITP workaround)
        if guest_id is None:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix
                guest_id = decode_guest_token(token)
                if guest_id is None:
                    logger.debug("Invalid guest token in Authorization header")

        # Generate new guest_id if neither cookie nor token worked
        if guest_id is None:
            guest_id = uuid4()

        request.state.guest_id = guest_id
        # Always sign the guest_id so we can set the cookie with correct attributes
        signed_cookie_value = sign_guest_id(guest_id)
        # Also create a token for frontend to store (Safari ITP fallback)
        guest_token = create_guest_token(guest_id)

        response = await call_next(request)

        # Always set cookie (works for desktop browsers)
        response.set_cookie(
            key=GUEST_COOKIE_NAME,
            value=signed_cookie_value,
            max_age=settings.guest_cookie_max_age,
            secure=True,
            httponly=True,
            samesite="none",  # lowercase "none" required for SameSite=None
            path="/",
        )
        
        # Also send token in response header for frontend to store in localStorage
        # Frontend can use this as fallback when cookies don't work (Safari ITP)
        response.headers[GUEST_TOKEN_HEADER] = guest_token
        
        return response
