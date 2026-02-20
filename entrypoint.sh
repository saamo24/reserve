#!/bin/bash
set -e
echo "Running migrations..."
alembic upgrade head

# If a command was passed (e.g. make populate, make migrate-revision), run it and exit
if [ $# -gt 0 ]; then
  exec "$@"
fi

echo "Starting API..."
exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 4 --access-logfile - --error-logfile -
