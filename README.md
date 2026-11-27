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

Requires **Python 3.11 or 3.12** (3.13+ has no `pydantic-core` wheels yet). The target
creates the backend virtualenv on first run, then reuses it:

```bash
make test
```

Override the interpreter if `python3.12` isn't your default: `make test PYTHON=python3.11`.
Prefer to drive it yourself?

```bash
cd services/backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

---

### Reference data (Phase 2)

BreachAtlas loads three reference datasets and maps breaches against them:

- **MITRE ATT&CK Enterprise** v20.1 — 706 techniques + 44 mitigations (committed as a compact
  243 KB derived subset; the raw ~55 MB STIX is git-ignored, rebuildable via `make ref-data`).
- **CIS Controls v8** — all 18 controls / 153 safeguards (IDs + titles; see `docs/decisions.md`).
- **CISA KEV** — the Known Exploited Vulnerabilities catalog.

```bash
make load-ref     # load ATT&CK / CIS / KEV into the database (docker)
make ref-data     # re-download pinned sources + rebuild the committed ATT&CK subset
```

Mapping logic (`app/mapping/`) turns a breach's ATT&CK techniques into **suggested** controls
(technique → ATT&CK mitigation → CIS-aligned control) and validates that every control points at
a real CIS safeguard. Suggestions are advisory only — a human reviewer confirms them (Phase 3).

### Admin area & review workflow (Phase 3)

An authenticated admin area (`/admin`) gates everything behind **server-side sessions**
(httpOnly cookie), **roles**, and optional **TOTP MFA**:

- **Roles**: `editor` (draft + submit), `reviewer` (approve / publish / reject), `admin`
  (+ user management + audit log).
- **Review workflow** — nothing publishes automatically:
  `draft → in_review → approved → published` (plus `changes_requested`, `rejected`). Publishing
  is an explicit reviewer/admin action; every transition is changelogged **and** audit-logged.
- **Audit log** (`/admin/audit`, admin-only) records every admin action (logins, user creation,
  transitions).

Create the first admin (password via env or hidden prompt — never committed):

```bash
BREACHATLAS_ADMIN_PASSWORD='choose-a-strong-one' make create-admin EMAIL=you@example.com
```

See `docs/decisions.md` (ADR-0009) for the auth design and its documented limitations.

### Ingestion: isolated fetcher + SEC EDGAR (Phase 4)

Ingestion is split for safety:

- **Fetcher** (`services/fetcher`, its own container) is the only component that dereferences
  external URLs. It is **SSRF-hardened** — http/https only; blocks private / loopback / link-local
  (incl. `169.254.169.254` metadata) / CGNAT / reserved addresses, resolving DNS and re-checking
  **every redirect hop**; caps redirects, size and time. In compose it runs on a network with **no
  route to the database**.
- **Worker** (`services/worker`, same image as backend, scheduler command) runs connectors on a
  schedule, calls the fetcher, deduplicates, and files candidates into the review queue as
  `in_review`. Nothing publishes automatically.
- **Connectors** (each with its own extractor behind a shared Protocol):
  - **SEC EDGAR** — 8-K filings citing **Item 1.05** (material cyber incidents) via the official
    full-text search API.
  - **HHS OCR** — US healthcare breaches affecting 500+ individuals (CSV breach portal; brings
    `records_affected` and sector).
  - **Maine AG** — Maine Attorney General breach notifications (CSV list; per-entity resident
    counts).

All are built/tested against recorded fixtures; a live SEC pass is opt-in:

```bash
# Set a real contact UA first (SEC blocks requests without one):
FETCHER_USER_AGENT='BreachAtlas/0.1 (you@example.com)' make ingest-edgar
```

UK ICO and news-RSS connectors follow in later Phase 4 iterations.

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
