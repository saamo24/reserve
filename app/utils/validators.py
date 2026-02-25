"""Validation helpers for phone, email, date/time."""

import re
from datetime import date, time
from zoneinfo import ZoneInfo

# E.164-ish: optional +, digits, spaces, dashes, parentheses
PHONE_REGEX = re.compile(r"^\+?[\d\s\-\(\)]{10,20}$")


def validate_phone(value: str) -> str:
    """Validate phone number format. Raises ValueError if invalid."""
    if not value or not value.strip():
        raise ValueError("Phone number is required")
    cleaned = value.strip()
    if not PHONE_REGEX.match(cleaned):
        raise ValueError("Invalid phone number format")
    return cleaned


def validate_email(value: str | None) -> str | None:
    """Return trimmed email or None. Use Pydantic EmailStr in schemas for format."""
    if value is None or not value.strip():
        return None
    return value.strip()


def validate_date_not_in_past(d: date) -> date:
    """Raise ValueError if date is in the past."""
    if d < date.today():
        raise ValueError("Date cannot be in the past")
    return d


def time_in_range(t: time, opening: time, closing: time) -> bool:
    """Return True if t is within [opening, closing). Handles overnight (e.g. 22:00-02:00)."""
    if opening <= closing:
        return opening <= t < closing
    return t >= opening or t < closing


def get_now_in_timezone(tz_name: str) -> time:
    """Return current time in the given timezone as time (no date)."""
    from datetime import datetime

    z = ZoneInfo(tz_name)
    return datetime.now(z).time()


def validate_timezone(tz_name: str) -> str:
    """Validate timezone name. Raises ValueError if invalid."""
    try:
        ZoneInfo(tz_name)
        return tz_name
    except Exception:
        raise ValueError(f"Invalid timezone: {tz_name!r}")


def get_available_timezones() -> list[str]:
    """Get all available IANA timezone names, sorted alphabetically."""
    try:
        from zoneinfo import available_timezones
        return sorted(available_timezones())
    except ImportError:
        # Fallback for older Python versions or missing tzdata
        # Return a common subset
        return sorted([
            "UTC",
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Yerevan",
            "Australia/Sydney",
        ])
