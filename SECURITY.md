# Security Policy

BreachAtlas is a public, educational project that documents publicly reported data
breaches. Security is a first-class concern of the project itself, so this repository
is also a demonstration of a hardened software supply chain.

## Reporting a vulnerability

Please report security issues **privately**, not in public issues or pull requests.

- Preferred: open a private report via **GitHub → Security → "Report a vulnerability"**
  (Private Vulnerability Reporting is enabled on this repository).

Please include steps to reproduce, affected component (`backend`, `fetcher`, `worker`,
`frontend`, or `infra`), and impact. You'll get an acknowledgement, and fixes to
confirmed issues are prioritised.

Please do **not**:
- run automated scanners or load/DoS tests against any hosted instance;
- access, modify, or exfiltrate data that is not yours;
- disclose the issue publicly before a fix is available.

## Supported versions

This is an actively developed portfolio project; only the latest `main` is supported.

## Security controls in this repository

Defense in depth is built in and enforced in CI (`.github/workflows/`):

- **Secret scanning** — gitleaks + GitHub secret scanning with push protection.
- **SAST** — Semgrep. **SCA** — pip-audit, Trivy (fs + image), `npm audit`. **IaC** — Checkov.
- **DAST** — OWASP ZAP against the live API (`dast.yml`).
- **SBOM** — Syft (SPDX) per service; **image signing** — Cosign keyless on deploy.
- **Dependencies** — Dependabot (Python, npm, Actions, Docker).
- **Runtime** — non-root containers, OS-patched base images, least-privilege IAM,
  the SSRF fetcher network-isolated from the database (see `docs/`).

See `docs/security-scanning.md`, `docs/dast.md`, and `docs/supply-chain.md` for detail.
