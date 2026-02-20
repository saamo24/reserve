"""Production-ready structured logging."""

import logging
import sys
from typing import Any

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure logging based on APP_ENV and LOG_LEVEL."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    format_string = (
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        if settings.app_env == "development"
        else '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    )

    logging.basicConfig(
        level=level,
        format=format_string,
        stream=sys.stdout,
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    # Request logging (app.middleware.request_logging) — always INFO
    logging.getLogger("app.request").setLevel(logging.INFO)
    # Uvicorn access log: INFO to log each request
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # Reduce SQLAlchemy noise unless in development
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.app_env == "development" else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name."""
    return logging.getLogger(name)
