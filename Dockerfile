# Production-ready Dockerfile for Reserve API
FROM python:3.11-slim

# Unbuffer stdout/stderr so logs appear immediately in docker logs
ENV PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application, scripts, and entrypoint
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY entrypoint.sh ./

RUN chmod +x entrypoint.sh && chmod +x scripts/*.sh 2>/dev/null || true
# Ownership
RUN chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
