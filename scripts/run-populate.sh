#!/bin/bash
# Run migrations then populate (seed). Use as a one-off on Render or locally:
#   docker run --rm ... ./scripts/run-populate.sh
#   Or set RUN_POPULATE=1 in the API service so the normal entrypoint runs it on startup.
set -e
echo "Running migrations..."
alembic upgrade head
echo "Running populate (seed)..."
python scripts/seed.py
echo "Done."
