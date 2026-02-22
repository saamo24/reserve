.PHONY: help build build-image run stop restart health clean clean-all \
	dc run-command \
	create-test-db drop-test-db migrate migrate-revision migrate-test-db db-shell db-shell-admin \
	run-tests run-tests-coverage quick-test tests tests-coverage \
	lint lint-fix format \
	shell python-shell \
	populate populate-local \
	generate-ssl run-https stop-https restart-nginx nginx-logs nginx-config-test

# Default target
.DEFAULT_GOAL := build

# Variables
COMPOSE := docker compose
COMPOSE_FILE := docker-compose.yml
API_SERVICE := api
DB_SERVICE := postgres
DB_NAME := reserve
DB_TEST_NAME := reserve_test
DB_USER := postgres
DB_PASSWORD := postgres
DB_ADMIN_DB := postgres
POPULATE_SCRIPT := scripts/seed.py
ALEMBIC_CMD := alembic
PYTEST_CMD := pytest
RUFF_CMD := ruff

# Docker Compose wrapper
dc:
	@$(COMPOSE) -f $(COMPOSE_FILE) $(ARGS)

# Run command in API container
run-command:
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) $(CMD)

# ============================================================================
# Core Targets
# ============================================================================

## Build Docker images
build build-image:
	@echo "Building Docker images..."
	@$(COMPOSE) -f $(COMPOSE_FILE) build

## Start all services
run:
	@echo "Starting services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) up
	@echo "Services started. Use 'make health' to check status."

## Stop all services
stop:
	@echo "Stopping services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) stop

## Restart all services
restart:
	@echo "Restarting services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) restart

## Check service health
health:
	@echo "Checking service health..."
	@$(COMPOSE) -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "Checking API health endpoint..."
	@curl -sf http://localhost:8000/health || echo "API not responding"

## Clean up containers and volumes
clean:
	@echo "Cleaning up containers and volumes..."
	@$(COMPOSE) -f $(COMPOSE_FILE) down -v

## Clean everything including images
clean-all:
	@echo "Cleaning up everything including images..."
	@$(COMPOSE) -f $(COMPOSE_FILE) down -v --rmi all

# ============================================================================
# Database Targets
# ============================================================================

## Create test database (waits for PostgreSQL readiness)
create-test-db:
	@echo "Waiting for PostgreSQL to be ready..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec -T $(DB_SERVICE) \
		pg_isready -U $(DB_USER) -d $(DB_ADMIN_DB) || \
		(echo "Waiting for PostgreSQL..." && sleep 2 && \
		$(COMPOSE) -f $(COMPOSE_FILE) exec -T $(DB_SERVICE) \
		pg_isready -U $(DB_USER) -d $(DB_ADMIN_DB))
	@echo "Creating test database '$(DB_TEST_NAME)'..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec -T $(DB_SERVICE) \
		psql -U $(DB_USER) -d $(DB_ADMIN_DB) -c \
		"SELECT 1 FROM pg_database WHERE datname = '$(DB_TEST_NAME)'" | \
		grep -q 1 || \
		$(COMPOSE) -f $(COMPOSE_FILE) exec -T $(DB_SERVICE) \
		psql -U $(DB_USER) -d $(DB_ADMIN_DB) -c \
		"CREATE DATABASE $(DB_TEST_NAME);"
	@echo "Test database '$(DB_TEST_NAME)' is ready."

## Drop test database
drop-test-db:
	@echo "Dropping test database '$(DB_TEST_NAME)'..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec -T $(DB_SERVICE) \
		psql -U $(DB_USER) -d $(DB_ADMIN_DB) -c \
		"DROP DATABASE IF EXISTS $(DB_TEST_NAME);"
	@echo "Test database dropped."

## Run database migrations
migrate:
	@echo "Running database migrations..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) $(ALEMBIC_CMD) upgrade head

## Create new migration revision (use: make migrate-revision MESSAGE="description")
migrate-revision:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE variable is required. Usage: make migrate-revision MESSAGE='description'"; \
		exit 1; \
	fi
	@echo "Creating new migration revision: $(MESSAGE)"
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) \
		$(ALEMBIC_CMD) revision --autogenerate -m "$(MESSAGE)"

## Run migrations on test database
migrate-test-db:
	@echo "Running migrations on test database..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm -e DATABASE_URL="postgresql+asyncpg://$(DB_USER):$(DB_PASSWORD)@$(DB_SERVICE):5432/$(DB_TEST_NAME)" \
		$(API_SERVICE) $(ALEMBIC_CMD) upgrade head

## Open database shell
db-shell:
	@echo "Opening database shell..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec $(DB_SERVICE) \
		psql -U $(DB_USER) -d $(DB_NAME)

## Open database admin shell (postgres database)
db-shell-admin:
	@echo "Opening database admin shell..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec $(DB_SERVICE) \
		psql -U $(DB_USER) -d $(DB_ADMIN_DB)

# ============================================================================
# Testing Targets
# ============================================================================

## Run tests
run-tests:
	@echo "Running tests..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) $(PYTEST_CMD)

## Run tests with coverage
run-tests-coverage:
	@echo "Running tests with coverage..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) \
		$(PYTEST_CMD) --cov=app --cov-report=term-missing --cov-report=html

## Run quick test (fail fast, no coverage)
quick-test:
	@echo "Running quick tests (fail fast)..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) \
		$(PYTEST_CMD) -x -v

## Full test lifecycle (create test DB, migrate, run tests, drop test DB)
tests: create-test-db migrate-test-db run-tests drop-test-db
	@echo "Full test lifecycle completed."

## Full test lifecycle with coverage
tests-coverage: create-test-db migrate-test-db run-tests-coverage drop-test-db
	@echo "Full test lifecycle with coverage completed."

# ============================================================================
# Code Quality Targets
# ============================================================================

## Run linter
lint:
	@echo "Running linter..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) $(RUFF_CMD) check .

## Fix linting issues
lint-fix:
	@echo "Fixing linting issues..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) $(RUFF_CMD) check --fix .

## Format code
format:
	@echo "Formatting code..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) $(RUFF_CMD) format .

# ============================================================================
# Developer Tools
# ============================================================================

## Open shell in API container
shell:
	@echo "Opening shell in API container..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec $(API_SERVICE) /bin/bash

## Open Python shell in API container
python-shell:
	@echo "Opening Python shell in API container..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec $(API_SERVICE) python

# ============================================================================
# Data Targets
# ============================================================================

## Populate database with initial data (uses DB from docker-compose, runs in container)
populate:
	@echo "Populating database (Docker, local DB)..."
	@$(COMPOSE) -f $(COMPOSE_FILE) run --rm $(API_SERVICE) python $(POPULATE_SCRIPT)

## Populate database using .env (e.g. remote server DB); run from project root with deps installed
populate-local:
	@echo "Populating database using .env (DATABASE_URL from .env)..."
	@python $(POPULATE_SCRIPT)

# ============================================================================
# HTTPS / Nginx Targets
# ============================================================================

## Generate SSL certificates (self-signed)
generate-ssl:
	@echo "Generating self-signed SSL certificates..."
	@mkdir -p nginx/ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout nginx/ssl/nginx-selfsigned.key \
		-out nginx/ssl/nginx-selfsigned.crt \
		-subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
	@echo "SSL certificates generated in nginx/ssl/"

## Run services with HTTPS (requires nginx service in docker-compose)
run-https:
	@echo "Starting services with HTTPS..."
	@$(COMPOSE) -f $(COMPOSE_FILE) up
	@echo "Services started with HTTPS. Use 'make health' to check status."

## Stop HTTPS services
stop-https:
	@echo "Stopping HTTPS services..."
	@$(COMPOSE) -f $(COMPOSE_FILE) stop

## Restart Nginx service
restart-nginx:
	@echo "Restarting Nginx..."
	@$(COMPOSE) -f $(COMPOSE_FILE) restart nginx || \
		echo "Nginx service not found. Ensure nginx service is defined in docker-compose.yml"

## View Nginx logs
nginx-logs:
	@echo "Showing Nginx logs..."
	@$(COMPOSE) -f $(COMPOSE_FILE) logs -f nginx || \
		echo "Nginx service not found."

## Test Nginx configuration
nginx-config-test:
	@echo "Testing Nginx configuration..."
	@$(COMPOSE) -f $(COMPOSE_FILE) exec nginx nginx -t || \
		echo "Nginx service not found or not running."

# ============================================================================
# Help Target
# ============================================================================

## Show this help message
help:
	@echo "Available targets:"
	@echo ""
	@echo "Core:"
	@echo "  build, build-image  - Build Docker images"
	@echo "  run                 - Start all services"
	@echo "  stop                - Stop all services"
	@echo "  restart             - Restart all services"
	@echo "  health              - Check service health"
	@echo "  clean               - Clean up containers and volumes"
	@echo "  clean-all           - Clean everything including images"
	@echo ""
	@echo "Database:"
	@echo "  create-test-db      - Create test database (waits for PostgreSQL)"
	@echo "  drop-test-db        - Drop test database"
	@echo "  migrate             - Run database migrations"
	@echo "  migrate-revision    - Create new migration (use: make migrate-revision MESSAGE='desc')"
	@echo "  migrate-test-db     - Run migrations on test database"
	@echo "  db-shell            - Open database shell"
	@echo "  db-shell-admin      - Open database admin shell"
	@echo ""
	@echo "Testing:"
	@echo "  run-tests           - Run tests"
	@echo "  run-tests-coverage  - Run tests with coverage"
	@echo "  quick-test          - Run quick tests (fail fast)"
	@echo "  tests               - Full test lifecycle (create DB, migrate, test, drop DB)"
	@echo "  tests-coverage      - Full test lifecycle with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint                - Run linter"
	@echo "  lint-fix            - Fix linting issues"
	@echo "  format              - Format code"
	@echo ""
	@echo "Developer Tools:"
	@echo "  shell               - Open shell in API container"
	@echo "  python-shell        - Open Python shell in API container"
	@echo ""
	@echo "Data:"
	@echo "  populate            - Populate database (Docker, local DB)"
	@echo "  populate-local      - Populate database using .env (e.g. remote DB from host)"
	@echo ""
	@echo "HTTPS / Nginx:"
	@echo "  generate-ssl        - Generate self-signed SSL certificates"
	@echo "  run-https           - Run services with HTTPS"
	@echo "  stop-https          - Stop HTTPS services"
	@echo "  restart-nginx      - Restart Nginx service"
	@echo "  nginx-logs         - View Nginx logs"
	@echo "  nginx-config-test   - Test Nginx configuration"
	@echo ""
	@echo "Help:"
	@echo "  help                - Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make build                    - Build images"
	@echo "  make run                     - Start services"
	@echo "  make migrate-revision MESSAGE='add users table' - Create migration"
	@echo "  make tests                   - Run full test suite"
	@echo "  make populate                - Populate DB (Docker)"
	@echo "  make populate-local          - Populate DB from .env (e.g. server DB)"
