"""ASGI middleware to log every request and response status."""

import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, client ip, status code, and duration for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        client = request.client.host if request.client else "?"
        method = request.method
        path = request.url.path
        if request.url.query:
            path = f"{path}?{request.url.query}"

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %s %.2fms",
            client,
            method,
            path,
            response.status_code,
            duration_ms,
        )
        return response
