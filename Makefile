.PHONY: setup dev dev-api dev-web test test-api test-web migrate build clean

# ============================================================================
# Dog Breed Diet Planner — Developer Makefile
# ============================================================================

# Default target
help:
	@echo ""
	@echo "Dog Breed Diet Planner — Available Commands"
	@echo "============================================"
	@echo "  make setup       Install all dependencies (Python + Node)"
	@echo "  make dev         Start all local services (DB + Redis + API + Web)"
	@echo "  make dev-api     Start only the API (requires Docker services running)"
	@echo "  make dev-web     Start only the Next.js frontend"
	@echo "  make test        Run all tests (API only)"
	@echo "  make test-api    Run API tests with coverage"
	@echo "  make migrate     Apply Alembic migrations to local database"
	@echo "  make build       Build production Docker images"
	@echo "  make clean       Remove build artifacts and Docker volumes"
	@echo ""

# ============================================================================
# SETUP
# ============================================================================

setup: setup-api setup-web
	@echo "✓ Setup complete — copy apps/api/.env.example → apps/api/.env"
	@echo "  and apps/web/.env.example → apps/web/.env.local"

setup-api:
	@echo "→ Installing Python dependencies..."
	cd apps/api && python -m pip install --upgrade pip && pip install -r requirements-dev.txt

setup-web:
	@echo "→ Installing Node dependencies..."
	cd apps/web && npm ci

# ============================================================================
# DEVELOPMENT
# ============================================================================

dev:
	@echo "→ Starting Docker services (Postgres + Redis)..."
	docker compose -f docker-compose.dev.yml up -d
	@echo "→ Starting API and Web in parallel..."
	@$(MAKE) -j2 dev-api dev-web

dev-api:
	@echo "→ Starting API at http://localhost:8000"
	cd apps/api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	@echo "→ Starting Web at http://localhost:3000"
	cd apps/web && npm run dev

# ============================================================================
# TESTING
# ============================================================================

test: test-api

test-api:
	@echo "→ Running API tests..."
	cd apps/api && pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

# ============================================================================
# DATABASE
# ============================================================================

migrate:
	@echo "→ Applying Alembic migrations..."
	cd apps/api && alembic upgrade head

migrate-new:
	@echo "Usage: make migrate-new MSG='your migration message'"
	cd apps/api && alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	@echo "→ Rolling back last migration..."
	cd apps/api && alembic downgrade -1

# ============================================================================
# BUILD
# ============================================================================

build: build-api build-web

build-api:
	@echo "→ Building API Docker image..."
	docker build -t dog-diet-api:local apps/api/

build-web:
	@echo "→ Building Web Docker image..."
	docker build -t dog-diet-web:local apps/web/

# ============================================================================
# CLEANUP
# ============================================================================

clean:
	@echo "→ Stopping Docker services..."
	docker compose -f docker-compose.dev.yml down
	@echo "→ Removing Python cache..."
	find apps/api -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find apps/api -name "*.pyc" -delete 2>/dev/null || true
	@echo "→ Removing Node build artifacts..."
	rm -rf apps/web/.next apps/web/node_modules/.cache
