# DAST — Dynamic Application Security Testing (OWASP ZAP)

Static analysis (Semgrep, Trivy, Checkov) reads code and config. **DAST attacks the
running application** — it sends real HTTP requests and watches how the live service
responds. BreachAtlas uses [OWASP ZAP](https://www.zaproxy.org/) against the API.

## What runs, and where

`.github/workflows/dast.yml` (separate from the fast PR gate — a live scan takes minutes):

1. Installs the backend, migrates a throwaway **SQLite** database, and seeds the demo data.
2. Starts the API with `uvicorn` (rate limit lifted so ZAP isn't throttled into 429s).
3. Runs **`zap-api-scan.py`** against the live OpenAPI spec (`/openapi.json`), so ZAP knows
   every endpoint and exercises it — not just whatever a crawler can find.
4. Publishes the ZAP report (HTML + JSON + Markdown) as a build artifact and to the job summary.

Triggers: push to `main`, a weekly schedule, and `workflow_dispatch`.

## Why the app already scores well

The backend sets secure response headers on every response (see `services/backend/app/main.py`):
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a locked-down `Content-Security-Policy`,
`Referrer-Policy`, `Cross-Origin-Opener-Policy`, and `Permissions-Policy`. The public API is
read-only and rate-limited, and admin routes require authentication — so ZAP mostly confirms the
hardening rather than finding holes.

## Tuning (`.zap/rules.tsv`)

Noise is suppressed narrowly and with a stated reason, never blanket-disabled:

| Rule | Action | Why |
|---|---|---|
| 10035 (HSTS not set) | IGNORE | Only meaningful over HTTPS; enforced at the ALB/TLS layer in prod, not on the local HTTP scan |
| 10096 (Timestamp disclosure) | IGNORE | High false-positive rate — flags ordinary numbers in JSON |
| 10109 (Modern web application) | IGNORE | Informational, not a vulnerability |

## Report-only today; how to make it a hard gate

The CI step ends with `-I || true`, so the scan **reports** but does not fail the build yet — a
baseline so we can triage real findings before turning them into blockers. To promote it to a gate
once the report is clean: drop `-I`/`|| true` and let a ZAP `FAIL`-level alert fail the job (set
specific rules to `FAIL` in `.zap/rules.tsv`).

## Run it locally

Needs Docker running. With the API already up on `http://localhost:8000`:

```bash
docker run --network host -v "$PWD/.zap:/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py \
  -t http://localhost:8000/openapi.json -f openapi -c rules.tsv -r report.html
```

The report lands at `.zap/report.html`.

## Deploy pipeline (`deploy.yml`) — the DAST target in production

`.github/workflows/deploy.yml` is a **manual** CD template that builds the three images, pushes
them to ECR, and runs `terraform plan`/`apply` against the Phase-7 infrastructure. It:

- runs **only** on `workflow_dispatch` (never automatically);
- authenticates with **GitHub OIDC** (`AWS_DEPLOY_ROLE_ARN` secret) — no long-lived AWS keys;
- runs `terraform plan` by default and **applies only** when dispatched with `confirm = DEPLOY`,
  which creates real, billable AWS resources (~$90–110/mo).

It does nothing until the AWS role secret and a remote Terraform state backend are configured, so
it is safe to keep in the repo as the documented path from "green CI" to "running in AWS."
