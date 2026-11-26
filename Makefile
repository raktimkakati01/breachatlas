# BreachAtlas — developer convenience targets.
.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down logs migrate seed test fmt lint destroy

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

up: ## Start postgres + backend (docker compose)
	$(COMPOSE) up -d --build

down: ## Stop all services
	$(COMPOSE) down

logs: ## Tail backend logs
	$(COMPOSE) logs -f backend

migrate: ## Apply database migrations (inside backend container)
	$(COMPOSE) run --rm backend alembic upgrade head

seed: ## Load clearly-marked DEMO fixture data
	$(COMPOSE) run --rm backend python -m app.db.seed

test: ## Run backend test suite (in-memory SQLite, no docker needed)
	cd services/backend && pytest -q

fmt: ## Format backend code
	cd services/backend && ruff format .

lint: ## Lint backend code
	cd services/backend && ruff check .

destroy: ## Tear down everything incl. the database volume (local)
	$(COMPOSE) down -v
