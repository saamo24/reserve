"""FastAPI application entry: lifespan, CORS, routers, health."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import admin_router as admin_router
from app.api.auth import router as auth_router
from app.api.public import public_router as public_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, get_redis
from app.middleware.guest import GuestMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init logging, check Redis. Shutdown: close Redis."""
    setup_logging()
    # Optional: verify Redis connectivity
    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:
        pass
    yield
    await close_redis()


app = FastAPI(
    title="Reserve",
    description="Enterprise-grade restaurant reservation system",
    version="0.1.0",
    lifespan=lifespan,
)
# Request logging first (outermost) so every request is logged
app.add_middleware(RequestLoggingMiddleware)

# With credentials (cookies), CORS cannot use "*"; must list explicit origins.
_settings = get_settings()
_cors_origins = [_settings.frontend_base_url]
try:
    from urllib.parse import urlparse
    parsed = urlparse(_settings.frontend_base_url)
    if parsed.port:
        # Next.js dev often serves on 0.0.0.0:port; allow that origin too.
        _cors_origins.append(f"http://0.0.0.0:{parsed.port}")
        # Allow 127.0.0.1 so cookies work when frontend is opened as 127.0.0.1 (same-origin for cookie send).
        if "localhost" in _settings.frontend_base_url or (parsed.hostname in ("localhost", "127.0.0.1")):
            _cors_origins.append(f"http://127.0.0.1:{parsed.port}")
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GuestMiddleware)

app.include_router(auth_router)
app.include_router(admin_router, prefix="/admin")
app.include_router(public_router)



def custom_openapi():
    """Custom OpenAPI schema with security definitions."""
    from fastapi.openapi.utils import get_openapi
    
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ensure components exist
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # Add or update security scheme - FastAPI auto-generates this from Security() dependencies
    # but we ensure it has a proper description
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
    
    # Update the HTTPBearer scheme with better description
    # FastAPI automatically creates this from Security(HTTPBearer()) in routes
    openapi_schema["components"]["securitySchemes"]["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter JWT access token. Get token from /api/v1/auth/login endpoint. Format: Bearer <your_token_here>",
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health")
async def health():
    """Health check for load balancer and Docker."""
    status = {}
    try:
        from sqlalchemy import text
        from app.core.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception:
        status["database"] = "error"
    try:
        redis = await get_redis()
        await redis.ping()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "error"
    return status
