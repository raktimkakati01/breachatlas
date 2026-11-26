# BreachAtlas — developer convenience targets.
.DEFAULT_GOAL := help
COMPOSE := docker compose

# Local backend virtualenv. Python 3.11–3.12 is required (3.13+ has no pydantic-core
# wheels yet). Override the interpreter with:  make venv PYTHON=python3.11
PYTHON ?= python3.12
BACKEND := services/backend
FETCHER := services/fetcher
VENV := $(BACKEND)/.venv
VENV_PY := $(VENV)/bin/python
ABS_VENV_PY := $(CURDIR)/$(VENV)/bin/python
ABS_RUFF := $(CURDIR)/$(VENV)/bin/ruff

# Pinned upstream reference sources (see docs/decisions.md ADR-0007).
ATTACK_SHA := a8db2f52eb933c9c99060c123e088b3326d3a607
ATTACK_VER := 20.1
ATTACK_RAW := data/reference/attack/enterprise-attack-$(ATTACK_VER).json
KEV_RAW := data/reference/kev/known_exploited_vulnerabilities.json

.PHONY: help venv up down logs migrate seed load-ref ref-data create-admin ingest-edgar test test-fetcher fmt lint destroy

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

load-ref: ## Load reference datasets (ATT&CK / CIS v8 / CISA KEV) into the database
	$(COMPOSE) run --rm backend python -m app.reference

create-admin: ## Create first admin: make create-admin EMAIL=you@example.com (password prompted / env)
	$(COMPOSE) run --rm -e BREACHATLAS_ADMIN_PASSWORD backend python -m app.cli.create_user --email $(EMAIL) --role admin

ref-data: ## Re-download pinned upstream sources and rebuild the committed ATT&CK subset
	@echo ">> downloading pinned ATT&CK Enterprise v$(ATTACK_VER) (~55MB) and CISA KEV"
	curl -sSL "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/$(ATTACK_SHA)/enterprise-attack/enterprise-attack-$(ATTACK_VER).json" -o $(ATTACK_RAW)
	curl -sSL "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json" -o $(KEV_RAW)
	$(PYTHON) -I scripts/build_reference.py $(ATTACK_RAW) data/reference/attack
	@echo ">> rebuilt data/reference/attack/enterprise-attack-derived.json"

ingest-edgar: ## Run one LIVE SEC EDGAR ingestion pass (needs FETCHER_USER_AGENT with a contact)
	$(COMPOSE) run --rm worker python -c "from app.ingestion.scheduler import run_sec_edgar; print(run_sec_edgar())"

test: test-fetcher | $(VENV) ## Run backend + fetcher test suites (in-memory SQLite, no docker)
	cd $(BACKEND) && .venv/bin/python -m pytest -q

test-fetcher: | $(VENV) ## Run the isolated fetcher's SSRF test suite
	cd $(FETCHER) && $(ABS_VENV_PY) -m pytest -q

fmt: | $(VENV) ## Format backend + fetcher code
	cd $(BACKEND) && .venv/bin/ruff format .
	cd $(FETCHER) && $(ABS_RUFF) format .

lint: | $(VENV) ## Lint backend + fetcher code
	cd $(BACKEND) && .venv/bin/ruff check .
	cd $(FETCHER) && $(ABS_RUFF) check .

destroy: ## Tear down everything incl. the database volume (local)
	$(COMPOSE) down -v
