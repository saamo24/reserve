"""Public API (no auth): branches, slots, reservations."""

from fastapi import APIRouter

from app.api.public.branches import router as branches_router
from app.api.public.reservation import router as reservations_router

public_router = APIRouter()
public_router.include_router(branches_router)
public_router.include_router(reservations_router)
