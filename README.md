# BreachAtlas

> **A searchable, visual database of publicly reported data breaches — mapped to _how_ they happened and _which security controls_ would have prevented them.**
>
> Other sites show *what leaked*. BreachAtlas shows *why it happened* and *what would have stopped it*.

This is a public portfolio project. The full README (architecture diagram, data-source
provenance model, pipeline-stage rationale, deploy/destroy guides) is written in **Phase 12**.
This stub covers how to run Phase 1 locally.

---

## ⚖️ Legal & ethical rules (non-negotiable)

- **Never** store, host, link to, or help anyone find leaked data itself — only *metadata* from public reporting.
- Summaries and analysis are **original writing**, never copied text. Always cite and link sources.
- Confirmed facts are clearly labelled vs. our own analysis (see the provenance model).
- Root cause defaults to **"Undisclosed"** unless an official / post-incident source states it. We never guess.

Full rationale and source terms-of-use notes live in [`docs/decisions.md`](docs/decisions.md).

---

## Phase 1 — what exists today

A FastAPI + PostgreSQL backend with the full data model, a **read-only** public API,
a small **clearly-labelled demo fixture dataset**, and a pytest suite. No cloud, no secrets,
no ingestion yet.

### Run locally (Docker)

```bash
cp .env.example .env        # edit POSTGRES_PASSWORD to a local value
make up                     # starts postgres + backend
make migrate                # applies the schema
make seed                   # loads DEMO fixtures (clearly marked demo data)
# API docs:  http://localhost:8000/docs
make down
```

### Run the tests (no Docker needed — uses in-memory SQLite)

```bash
cd services/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

---

## Repository layout

```
services/backend     FastAPI API, SQLAlchemy models, Alembic migrations, tests   (Phase 1)
services/worker      Ingestion scheduler                                          (Phase 4)
services/fetcher     SSRF-isolated URL fetcher                                    (Phase 4)
services/frontend    Next.js + Tailwind UI                                        (Phase 6)
data/reference       MITRE ATT&CK / CIS Controls v8 / CISA KEV                    (Phase 2)
infra/terraform      AWS infrastructure                                           (Phase 7)
.github/workflows    CI/CD security pipeline                                      (Phase 5)
docs/                Decisions, threat model, interview notes
```

## License

Code is licensed under **Apache-2.0** (see [`LICENSE`](LICENSE)). The curated breach data
and original written summaries are offered under **CC BY-SA 4.0** — see `docs/decisions.md`.
