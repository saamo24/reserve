"""Example tests for guest_id signing (guest_serializer)."""

import pytest
from uuid import uuid4

from app.utils.guest_serializer import sign_guest_id, verify_guest_id


def test_sign_and_verify_roundtrip() -> None:
    """Sign a UUID and verify returns the same UUID."""
    guest_id = uuid4()
    signed = sign_guest_id(guest_id)
    assert isinstance(signed, str)
    assert len(signed) > 0
    verified = verify_guest_id(signed)
    assert verified == guest_id


def test_verify_tampered_returns_none() -> None:
    """Tampered or invalid cookie value returns None."""
    assert verify_guest_id("tampered") is None
    assert verify_guest_id("") is None
    assert verify_guest_id("x" * 20) is None
