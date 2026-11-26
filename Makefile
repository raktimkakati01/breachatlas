# BreachAtlas — developer convenience targets.
.DEFAULT_GOAL := help
COMPOSE := docker compose

# Local backend virtualenv. Python 3.11–3.12 is required (3.13+ has no pydantic-core
# wheels yet). Override the interpreter with:  make venv PYTHON=python3.11
PYTHON ?= python3.12
BACKEND := services/backend
VENV := $(BACKEND)/.venv
VENV_PY := $(VENV)/bin/python

.PHONY: help venv up down logs migrate seed test fmt lint destroy

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

# Create the venv + install dev deps on first use; reused if it already exists.
$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r $(BACKEND)/requirements-dev.txt

venv: $(VENV) ## Create the backend virtualenv and install dev dependencies

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

test: | $(VENV) ## Run backend test suite (in-memory SQLite, no docker needed)
	cd $(BACKEND) && .venv/bin/python -m pytest -q

fmt: | $(VENV) ## Format backend code
	cd $(BACKEND) && .venv/bin/ruff format .

lint: | $(VENV) ## Lint backend code
	cd $(BACKEND) && .venv/bin/ruff check .

destroy: ## Tear down everything incl. the database volume (local)
	$(COMPOSE) down -v
