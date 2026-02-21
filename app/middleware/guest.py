"""Guest identification middleware: set or verify signed guest_id cookie and request.state.guest_id."""

import logging
from typing import Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.utils.guest_serializer import sign_guest_id, verify_guest_id

logger = logging.getLogger("app.guest")

# TODO: rate limit by IP for cookie issuance to prevent abuse
GUEST_COOKIE_NAME = "guest_id"


class GuestMiddleware(BaseHTTPMiddleware):
    """
    Ensure every request has request.state.guest_id set from a signed HTTP-only cookie.
    If the cookie is missing or invalid, generate a new guest_id, sign it, and set the cookie on the response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        cookie_value = request.cookies.get(GUEST_COOKIE_NAME)
        guest_id = None
        set_cookie_value: str | None = None

        if cookie_value:
            guest_id = verify_guest_id(cookie_value)
            if guest_id is None:
                logger.warning("Invalid guest_id cookie signature")
                # Fall through to generate new id and set cookie
                guest_id = None

        if guest_id is None:
            guest_id = uuid4()
            set_cookie_value = sign_guest_id(guest_id)

        request.state.guest_id = guest_id
        if set_cookie_value is not None:
            request.state._set_guest_cookie = set_cookie_value

        response = await call_next(request)

        if getattr(request.state, "_set_guest_cookie", None):
            # In development, use SameSite=None and Secure=True so the cookie is sent
            # on cross-origin requests (e.g. frontend localhost:3000 -> API localhost:8000).
            is_dev = settings.app_env == "development"
            response.set_cookie(
                key=GUEST_COOKIE_NAME,
                value=request.state._set_guest_cookie,
                max_age=settings.guest_cookie_max_age,
                secure=True if is_dev else settings.guest_cookie_secure,
                httponly=True,
                samesite="none" if is_dev else "lax",
                path="/",
            )
        return response
