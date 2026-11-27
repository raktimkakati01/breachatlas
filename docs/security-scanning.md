# Security scanning pipeline

Every push and pull request runs `.github/workflows/ci.yml`. All jobs use **least-privilege
permissions** (`permissions: {}` by default; each job opts into only what it needs), and all
GitHub Actions are **pinned to specific versions**. Scanner results are uploaded to GitHub code
scanning as **SARIF** where supported.

## Stages

| Stage | Tool | What it catches | Gate |
|---|---|---|---|
| Secret scanning | gitleaks (+ pre-commit hook) | Committed secrets/keys/tokens (full history) | Fail on any finding |
| SAST | Semgrep (`p/python`, `p/security-audit`, `p/secrets`) | Insecure code patterns | `--error` (fail on findings) → SARIF |
| SCA (Python) | pip-audit | Known CVEs in pinned Python deps (backend + fetcher) | Fail on any vuln |
| SCA (filesystem) | Trivy `fs` | Dep vulns, misconfig, secrets | HIGH/CRITICAL → exit 1, SARIF |
| Dockerfile lint | Hadolint | Dockerfile anti-patterns (per service) | `failure-threshold: error` → SARIF |
| Container scan | Trivy `image` | Vulns in built backend/fetcher images | HIGH/CRITICAL → exit 1, SARIF |
| SBOM | Syft | Software bill of materials (SPDX) per service | Uploaded as build artifact |
| Tests | pytest | Unit/integration — **incl. SSRF guard + admin authorization** | Fail on any failure |
| IaC scan | Checkov | Terraform misconfig | Fail on failed policy → SARIF (16 documented skips) |
| DAST | OWASP ZAP (`zap-api-scan`) | Runtime vulns on the **live** API (OpenAPI-driven) | Report-only baseline → HTML/JSON/MD artifact (`.github/workflows/dast.yml`) |
| SCA (npm) | `npm audit` | Frontend dep vulns | Added in Phase 9 (dependency hardening) |

DAST runs in its own `dast.yml` workflow (on push to `main`, weekly, and on demand) rather than
the fast PR gate, because a live scan takes minutes — see `docs/dast.md`. Image signing (Cosign
keyless, Phase 9) runs in the manual `deploy.yml`.

**Portable:** the same gates are mirrored in a declarative `Jenkinsfile` at the repo root (each
tool in its pinned container via `docker run`), so the pipeline is not locked to GitHub Actions —
see ADR-0016.

## Handling false positives

Suppressions are allowed but must be **narrow, justified, and dated**. Never blanket-disable a
scanner.

- **gitleaks** — add a path or regex to the `[allowlist]` in `.gitleaks.toml` with a comment.
- **Semgrep** — add `# nosemgrep: <rule-id>` on the specific line with a reason, or a path to
  `.semgrepignore` for non-source dirs.
- **Trivy** — add the CVE id to `.trivyignore` with a one-line justification + date.
- **pip-audit** — pass `--ignore-vuln <ID>` in CI only with a documented reason; prefer upgrading.

Every suppression should name *why* it is safe and *when* it was reviewed, so it can be re-checked.

## Real finding fixed during setup

Standing up this pipeline immediately paid off: pip-audit flagged **7 CVEs in `starlette`
0.41.3** (pulled in transitively by FastAPI). We **remediated by upgrading** the web stack
(FastAPI/Starlette/Uvicorn/Pydantic) rather than suppressing — all tests stayed green and
pip-audit/Trivy are now clean. That is the intended workflow: prefer a fix over an ignore.

## Running locally

```bash
pipx install pre-commit && pre-commit install   # gitleaks, ruff, hadolint, hygiene hooks
pre-commit run --all-files
```

Running Semgrep locally needs `setuptools<81` (newer setuptools dropped `pkg_resources`, which
Semgrep's bundled OpenTelemetry imports); CI avoids this by running Semgrep in its official image.
