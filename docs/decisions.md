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

## ADR-0007 — Reference datasets: pinned sources, committed derived subset

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 2

BreachAtlas loads three reference datasets and keeps them updatable:

- **MITRE ATT&CK Enterprise** — official STIX from `mitre-attack/attack-stix-data`, pinned to
  version **20.1** at commit `a8db2f52…` and verified by SHA-256. The raw bundle is ~55 MB, so
  it is **git-ignored**; a `scripts/build_reference.py` step extracts the ~243 KB subset we use
  (techniques, mitigations, and `mitigates` mappings) into `enterprise-attack-derived.json`,
  which **is** committed. `make ref-data` re-downloads and rebuilds it.
- **CISA KEV** — `known_exploited_vulnerabilities.json` from cisa.gov (~1.9 MB, U.S. public
  domain); small enough to commit directly.
- **CIS Controls v8** — see ADR-0008.

- **Why:** Pinning + checksums give supply-chain reproducibility; committing only the derived
  subset keeps the repo light while still working offline and in CI with no network. The raw
  55 MB blob in git history would bloat every clone forever.
- **Trade-off:** `make ref-data` needs network to refresh, and the derived subset must be
  rebuilt when bumping the ATT&CK version. Acceptable for a reference dataset.

---

## ADR-0008 — CIS Controls v8: curated IDs + titles only

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 2

`data/reference/cis/cis_controls_v8.json` contains all **18 controls and 153 safeguard
numbers + short titles**, with attribution — but **not** the full normative guidance text,
which is under a CIS license and not redistributed.

- **Why:** We only need safeguard identifiers/titles to map our prevention controls to CIS v8.
  Control/safeguard numbers and short titles are factual identifiers; the licensed prose stays
  at CIS.
- **Caveat:** Safeguard titles were transcribed for development and are flagged
  `"verified": false` in the file. They must be checked against the official CIS Controls v8
  before publication (Phase 12).
- **Mapping crosswalk:** `data/reference/crosswalk/mitigation_to_control.json` maps ATT&CK
  mitigations → our controls. It is our own **Analysis**, used only to *suggest* controls to a
  human reviewer — never to auto-publish.

---

## ADR-0009 — Admin auth, roles, review workflow, and audit log

**Date:** 2026-11-26 · **Status:** Accepted · **Phase:** 3

- **Sessions, not JWTs.** Login creates an opaque high-entropy token; only its **SHA-256 is
  stored** (`sessions.token_hash`), sent to the client as an httpOnly, SameSite=Lax cookie
  (Secure in production). This is instantly revocable (logout, disable user, expiry) and a DB
  leak cannot be replayed. JWTs were rejected for this phase because revocation needs a denylist.
- **Argon2** (`argon2-cffi`) for password hashing — memory-hard, modern default.
- **TOTP MFA** (`pyotp`): per-user enroll → verify → enforced at login. Login errors are
  **generic** ("Invalid credentials") so MFA failure doesn't reveal a correct password.
- **Roles:** `editor` (draft + submit), `reviewer` (approve/publish/reject), `admin` (+ user
  management + audit log). Enforced by a `require_role()` dependency; `admin` is always allowed.
- **Review state machine** (`app/services/review.py`): `draft → in_review → approved →
  published` (+ `changes_requested`, `rejected`). **Nothing auto-publishes** — `is_published`
  flips true only on an explicit `publish` from an `approved` record. Every transition writes a
  per-breach changelog entry *and* an audit entry.
- **Audit log** (`audit_log`) is distinct from the per-breach changelog: it records *who did
  what* across the whole admin surface (logins, user creation, transitions), with actor email
  denormalized so history survives user deletion.
- **First admin** is created via `python -m app.cli.create_user`; the password comes from an env
  var or a hidden prompt, never argv or the repo.

**Known limitations (documented for interviews / production hardening):**
- `users.mfa_secret` is stored unencrypted. Production should encrypt it at rest (e.g. app-level
  envelope encryption with a KMS key), since a DB read otherwise yields the TOTP seed.
- Login is covered by the global per-IP rate limit; a stricter per-route login throttle and
  account lockout are a future enhancement.
- Session cookie `Secure` is disabled outside production so local http dev works.

---

## Source terms-of-use / licensing notes

**Reference datasets (Phase 2):**
- **MITRE ATT&CK** — free under the ATT&CK Terms of Use (attribution required): https://attack.mitre.org/resources/legal-and-branding/terms-of-use/ . Checked 2026-11-26.
- **CISA KEV** — U.S. Government work, public domain; CISA requests attribution. Checked 2026-11-26.
- **CIS Controls v8** — © Center for Internet Security. We store only numbers + short titles for mapping/attribution; full text obtained separately from CIS. Checked 2026-11-26.

**Ingestion connectors (filled in per connector during Phase 4):**

> Before implementing each ingestion connector we check the source's current Terms of Use
> and `robots.txt`, record the findings here with the date checked, and skip any source
> whose terms forbid this use.

- **SEC EDGAR** — _pending Phase 4._
- **HHS OCR breach portal** — _pending Phase 4._
- **Maine AG breach notifications** — _pending Phase 4._
- **UK ICO enforcement** — _pending Phase 4._
- **News RSS (leads only)** — _pending Phase 4._
