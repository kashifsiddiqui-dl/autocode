# =============================================================================
# Auto Code - Makefile
# =============================================================================
# Usage: make <target>
# =============================================================================

.DEFAULT_GOAL := help

COMPOSE_FILE := infra/docker/docker-compose.yml
COMPOSE_PROD_FILE := infra/docker/docker-compose.prod.yml
COMPOSE := docker compose -f $(COMPOSE_FILE)
COMPOSE_PROD := docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_PROD_FILE)

# Colors for terminal output
BLUE := \033[36m
RESET := \033[0m

## ---------------------------------------------------------------------------
## Development
## ---------------------------------------------------------------------------

.PHONY: dev
dev: ## Start all services in development mode
	$(COMPOSE) up --build

.PHONY: dev-detached
dev-detached: ## Start all services in detached mode
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop all services
	$(COMPOSE) down

.PHONY: build
build: ## Build all Docker images
	$(COMPOSE) build

.PHONY: logs
logs: ## Follow logs for all services
	$(COMPOSE) logs -f

.PHONY: logs-backend
logs-backend: ## Follow backend logs
	$(COMPOSE) logs -f backend

.PHONY: logs-frontend
logs-frontend: ## Follow frontend logs
	$(COMPOSE) logs -f frontend

.PHONY: restart
restart: ## Restart all services
	$(COMPOSE) restart

.PHONY: ps
ps: ## Show running containers
	$(COMPOSE) ps

## ---------------------------------------------------------------------------
## Database
## ---------------------------------------------------------------------------

.PHONY: migrate
migrate: ## Run database migrations (alembic upgrade head)
	$(COMPOSE) exec backend alembic upgrade head

.PHONY: migration
migration: ## Create a new migration (usage: make migration name="add users table")
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(name)"

.PHONY: migrate-down
migrate-down: ## Rollback last migration
	$(COMPOSE) exec backend alembic downgrade -1

.PHONY: seed
seed: ## Run database seed script
	$(COMPOSE) exec backend python -m app.scripts.seed

.PHONY: db-shell
db-shell: ## Open PostgreSQL shell
	$(COMPOSE) exec postgres psql -U autocode -d autocode

## ---------------------------------------------------------------------------
## Data Pipeline
## ---------------------------------------------------------------------------

.PHONY: ingest
ingest: ## Run ICD-10-CM data ingestion pipeline
	$(COMPOSE) exec backend python -m app.scripts.ingest

.PHONY: benchmark
benchmark: ## Run RAG benchmark suite
	$(COMPOSE) exec backend python -m app.scripts.benchmark

## ---------------------------------------------------------------------------
## Testing
## ---------------------------------------------------------------------------

.PHONY: test
test: test-backend test-frontend ## Run all tests

.PHONY: test-backend
test-backend: ## Run backend tests (pytest)
	$(COMPOSE) exec backend pytest -v --tb=short

.PHONY: test-backend-cov
test-backend-cov: ## Run backend tests with coverage
	$(COMPOSE) exec backend pytest -v --tb=short --cov=app --cov-report=term-missing

.PHONY: test-frontend
test-frontend: ## Run frontend tests (vitest)
	$(COMPOSE) exec frontend npm run test

.PHONY: test-frontend-cov
test-frontend-cov: ## Run frontend tests with coverage
	$(COMPOSE) exec frontend npm run test -- --coverage

## ---------------------------------------------------------------------------
## Linting & Formatting
## ---------------------------------------------------------------------------

.PHONY: lint
lint: lint-backend lint-frontend ## Run all linters

.PHONY: lint-backend
lint-backend: ## Run backend linter (ruff)
	$(COMPOSE) exec backend ruff check .
	$(COMPOSE) exec backend ruff format --check .

.PHONY: lint-frontend
lint-frontend: ## Run frontend linter (eslint)
	$(COMPOSE) exec frontend npm run lint

.PHONY: format
format: format-backend format-frontend ## Format all code

.PHONY: format-backend
format-backend: ## Format backend code (ruff)
	$(COMPOSE) exec backend ruff format .
	$(COMPOSE) exec backend ruff check --fix .

.PHONY: format-frontend
format-frontend: ## Format frontend code (prettier)
	$(COMPOSE) exec frontend npx prettier --write .

.PHONY: typecheck
typecheck: ## Run type checking (mypy + TypeScript)
	$(COMPOSE) exec backend mypy app/
	$(COMPOSE) exec frontend npm run build

## ---------------------------------------------------------------------------
## Production
## ---------------------------------------------------------------------------

.PHONY: prod
prod: ## Start production stack
	$(COMPOSE_PROD) up --build -d

.PHONY: prod-down
prod-down: ## Stop production stack
	$(COMPOSE_PROD) down

.PHONY: prod-logs
prod-logs: ## Follow production logs
	$(COMPOSE_PROD) logs -f

## ---------------------------------------------------------------------------
## Cleanup
## ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove all containers, volumes, and images
	$(COMPOSE) down -v --rmi local --remove-orphans
	docker system prune -f

.PHONY: clean-all
clean-all: ## Full cleanup including named volumes (WARNING: destroys data)
	$(COMPOSE) down -v --rmi all --remove-orphans
	docker volume rm -f $$(docker volume ls -q --filter name=autocode) 2>/dev/null || true
	docker system prune -af

## ---------------------------------------------------------------------------
## Utilities
## ---------------------------------------------------------------------------

.PHONY: shell-backend
shell-backend: ## Open a shell in the backend container
	$(COMPOSE) exec backend bash

.PHONY: shell-frontend
shell-frontend: ## Open a shell in the frontend container
	$(COMPOSE) exec frontend sh

.PHONY: help
help: ## Show this help message
	@echo "Auto Code - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
