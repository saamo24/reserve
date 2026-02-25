# Reserve

Enterprise-grade, high-load optimized restaurant reservation system (multi-branch, no-auth customer flow, JWT-protected admin API, Redis locking/caching, Docker).

## Tech Stack

- Python 3.11+, FastAPI, Async SQLAlchemy 2.x, Alembic, Pydantic v2
- PostgreSQL (primary), Redis (distributed locking + caching)
- Gunicorn + Uvicorn workers, Docker & Docker Compose

## Run Instructions

A **Makefile** is provided: run `make help` to list targets (`setup`, `install`, `up`, `down`, `migrate`, `seed`, `run`, `lint`, `format`, etc.).

### Local (Docker Compose)

1. Set environment variables and start services:

```bash
# Set required environment variables (see docker-compose.yml for defaults)
# For custom config, export variables or set them in docker-compose.yml
docker compose up -d
# or: make up
```

2. Run migrations (if not using entrypoint): `make migrate`

3. Optional seed: `make seed`

4. API: http://localhost:8000  
   Docs: http://localhost:8000/docs

### Local development (no Docker)

1. Install dependencies and set environment variables:

```bash
pip install -e .

# Set environment variables (export or use your shell's method):
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reserve"
export REDIS_URL="redis://localhost:6379/0"
export APP_ENV="development"
# ... other variables as needed
```

2. Start Postgres and Redis locally, then:

```bash
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

**My Reservations (frontend):** With the frontend on a different port (e.g. Next.js on 3000, API on 8000), the app uses a guest cookie with `SameSite=None` in development so the cookie is sent cross-origin and "My Reservations" shows the correct list. Set `APP_ENV=development` as an environment variable for this behavior.

## Deploying to Render

- **Backend (Docker):** Use the root `Dockerfile`. The entrypoint runs migrations then `python scripts/seed.py` (populate) on every container start before starting the server. The seed script is idempotent (skips if data already exists). For a one-off run use: `./scripts/run-populate.sh` (migrations + seed then exit).
- **Frontend:** Set `NEXT_PUBLIC_API_URL` to your backend URL (e.g. `https://your-api.onrender.com`) and redeploy so the build uses it; otherwise the app will call `localhost:8000` and you’ll see `ERR_CONNECTION_REFUSED`.

## Scaling Notes

- **Horizontal scaling**: Run multiple API containers behind a load balancer. Use a single shared PostgreSQL and Redis; no in-memory locks.
- **Workers**: Tune `WORKERS` (Gunicorn) and `DB_POOL_SIZE` / `REDIS_POOL_SIZE` per instance.
- **Cache**: Slots and tables are cached in Redis (TTL 60–120s). Cache is invalidated on reservation create/cancel and table/branch updates.

## Performance Tuning

- **Indexes**: Reservations use `(branch_id, reservation_date)`, `(table_id, reservation_date)`, and a partial unique index for overlap prevention.
- **Connection pools**: Set `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `REDIS_POOL_SIZE` as environment variables.
- **Lock TTL**: `LOCK_TTL_SECONDS=10` for reservation slot locks; increase only if create flow is slow.

## Example cURL Requests

### Public

```bash
# List branches
curl -s http://localhost:8000/branches

# Get slots for a branch (replace BRANCH_ID and date)
curl -s "http://localhost:8000/branches/BRANCH_ID/slots?date=2025-12-01"

# Create reservation (replace IDs and date)
curl -s -X POST http://localhost:8000/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "branch_id": "BRANCH_UUID",
    "reservation_date": "2025-12-01",
    "start_time": "18:00:00",
    "full_name": "Jane Doe",
    "phone_number": "+15551234567",
    "email": "jane@example.com"
  }'

# Get reservation
curl -s http://localhost:8000/reservations/RESERVATION_ID
```

### Admin (JWT required)

Admin endpoints require a Bearer token. Obtain tokens via `/auth/login`, then use the `access_token` in the `Authorization` header. Use `/auth/refresh` to get new tokens when the access token expires.

```bash
# Login (get access and refresh tokens)
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
# Response: { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

# Refresh tokens
curl -s -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'

# Create branch (use token from login)
curl -s -X POST http://localhost:8000/admin/branches \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown",
    "address": "456 Main St",
    "opening_time": "11:00:00",
    "closing_time": "23:00:00",
    "slot_duration_minutes": 120,
    "is_active": true
  }'

# Create table
curl -s -X POST http://localhost:8000/admin/tables \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"branch_id": "BRANCH_UUID", "table_number": "1", "capacity": 4, "location": "indoor"}'

# List reservations (with filters)
curl -s "http://localhost:8000/admin/reservations?branch_id=BRANCH_UUID&page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Dashboard stats
curl -s http://localhost:8000/admin/dashboard/stats \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**First admin:** When using Docker, the entrypoint runs the seed script at startup, which creates the default admin if missing. Otherwise run `make seed` (or `python scripts/seed.py`) after migrations. Default: email `admin@example.com`, password `admin123` (configurable via `ADMIN_EMAIL` and `ADMIN_TEMP_PASSWORD`). Change the password in production.

## Response Format

List endpoints return:

```json
{
  "data": [...],
  "meta": {
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

## Status Codes

- `400` Validation error
- `404` Not found
- `409` Conflict (e.g. duplicate table number, slot taken)
- `423` Locked (slot lock not acquired; retry)
