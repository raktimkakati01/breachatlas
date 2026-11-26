# Decision log (ADR-style)

Each entry records a choice, why it was made, and the trade-offs. Newest decisions
are appended. Source terms-of-use notes for ingestion connectors are recorded here
before each connector is built (Phase 4).

---

## ADR-0001 — Legal & ethical constraints (non-negotiable)

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 1

These are hard rules enforced throughout the codebase and data model:

1. **No leaked data, ever.** BreachAtlas stores only *metadata* derived from public
   reporting (who, when, what categories, how, which controls). It never stores,
   hosts, mirrors, links to, or helps anyone locate the leaked data itself.
2. **Original writing only.** All summaries and analysis are written in our own words
   and always cite + link their sources. No copied article/filing text beyond the
   minimum needed for internal review.
3. **Facts vs. analysis are labelled.** Every surfaced field carries a provenance
   confidence label — `Confirmed` (official source), `Reported` (credible news),
   `Analysis` (our assessment), or `Undisclosed`. This is enforced by the
   `provenance` table, not left to prose.
4. **Root cause defaults to "Undisclosed."** `breaches.root_cause_status` defaults to
   `undisclosed` and only becomes `disclosed` when an official or post-incident source
   states the cause. We never guess a root cause.

---

## ADR-0002 — Monorepo, per-service containers

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 1

One repository, one container per service (`backend`, `worker`, `fetcher`, `frontend`),
orchestrated locally with docker compose.

- **Why:** Clear security boundaries (the SSRF-prone fetcher is isolated in its own
  container in Phase 4), one CI pipeline, easy to reason about in interviews.
- **Trade-off:** A monorepo needs path-scoped CI jobs to stay fast; acceptable at this
  size. A polyrepo would isolate blast radius more but adds coordination overhead we
  don't need yet.

---

## ADR-0003 — Backend stack: FastAPI + SQLAlchemy 2.0 + PostgreSQL

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 1

- **FastAPI** — typed, async, auto-generates OpenAPI docs; strong input validation via
  Pydantic v2 (defends against malformed input).
- **SQLAlchemy 2.0 ORM** — parameterized queries by default (no string-built SQL →
  SQL-injection resistant), portable across Postgres (prod) and SQLite (fast tests).
- **PostgreSQL 16** — relational integrity matters here (many-to-many breach↔technique↔
  control graphs, per-field provenance, changelog).
- **Trade-off:** An ORM adds a learning surface and some query opacity vs. raw SQL, but
  the injection-safety and migration story are worth it for a security-focused project.

---

## ADR-0004 — Alembic for schema migrations (addition to original brief)

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 1

Alembic was not in the original tech-stack list; added deliberately.

- **Why:** The project's credibility rests on *auditable, accurate data* (feature #10 is
  a per-breach changelog). Versioned, reviewable schema migrations are the database-level
  equivalent of that promise, and are the standard companion to SQLAlchemy.
- **Trade-off:** One more tool to learn, but it replaces fragile hand-written DDL and
  makes schema evolution part of the reviewed git history.

---

## ADR-0005 — Licensing: Apache-2.0 (code) + CC BY-SA 4.0 (data)

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 1

- **Code → Apache-2.0.** Includes an explicit patent grant (valued by security/enterprise
  reviewers) and is permissive enough for a portfolio project. MIT was the simpler
  alternative; Apache-2.0 chosen for the patent clause and professional signal.
- **Curated data & written summaries → CC BY-SA 4.0.** Software licenses fit code, not
  factual compilations and prose. CC BY-SA requires attribution and share-alike, which
  fits an open, community-correctable breach dataset.
- Note: this split only governs *our* original metadata and writing — never any source's
  copyrighted text, which we do not redistribute (see ADR-0001).

---

## ADR-0006 — Per-field provenance model

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 1

Provenance is stored at the **field** level (`provenance(entity, entity_id, field_name,
confidence_label, source_id, date_retrieved)`), not just once per breach.

- **Why:** A single breach record routinely mixes a `Confirmed` disclosure date (from an
  SEC filing) with an `Analysis` root-cause assessment (ours) and `Reported` record counts
  (news). Field-level labels are the only honest way to show that mix, and directly support
  ADR-0001 rules 3 and 4.
- **Trade-off:** More rows and more work on write; worth it — it *is* the product's
  differentiator.

---

## Source terms-of-use notes (filled in per connector during Phase 4)

> Before implementing each ingestion connector we check the source's current Terms of Use
> and `robots.txt`, record the findings here with the date checked, and skip any source
> whose terms forbid this use.

- **SEC EDGAR** — _pending Phase 4._
- **HHS OCR breach portal** — _pending Phase 4._
- **Maine AG breach notifications** — _pending Phase 4._
- **UK ICO enforcement** — _pending Phase 4._
- **News RSS (leads only)** — _pending Phase 4._
