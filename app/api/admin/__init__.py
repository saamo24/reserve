from fastapi import APIRouter

from app.api.admin.branches import router as admin_branches_router
from app.api.admin.dashboard import router as admin_dashboard_router
from app.api.admin.reservations import router as admin_reservations_router
from app.api.admin.tables import router as admin_tables_router


admin_router = APIRouter()
admin_router.include_router(admin_branches_router)
admin_router.include_router(admin_dashboard_router)
admin_router.include_router(admin_reservations_router)
admin_router.include_router(admin_tables_router)


__all__ = [
    "admin_router",
]