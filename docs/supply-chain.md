# Software supply-chain security

BreachAtlas treats its own supply chain as part of the attack surface. This covers what
goes *into* the artifacts (dependencies, base images), proving what's *in* them (SBOMs),
and proving *who built them* (signing).

## Dependencies

- **Pinned** — every Python and npm dependency is pinned (`requirements.txt`,
  `package-lock.json`); GitHub Actions and Docker base images are pinned to versions.
- **Audited in CI** — `pip-audit` (backend + fetcher), `npm audit` (frontend), and Trivy
  (filesystem + image) fail the build on HIGH/CRITICAL vulnerabilities.
- **Kept current** — `.github/dependabot.yml` opens grouped weekly PRs for Python, npm,
  GitHub Actions, and all three Dockerfiles, so upgrades are small and reviewable.

## SBOM

`syft` generates an SPDX software bill of materials per service in CI (`sbom` job), uploaded
as a build artifact. An SBOM is the ingredients list: if a new CVE lands tomorrow, you can
answer "are we affected?" without rebuilding.

## Image signing (Cosign, keyless)

The manual deploy pipeline (`.github/workflows/deploy.yml`) signs every image **by digest**
with [Cosign](https://docs.sigstore.dev/) keyless signing:

- **No private keys.** Signing uses the workflow's short-lived **GitHub OIDC** identity;
  Sigstore's Fulcio issues an ephemeral certificate and the signature + certificate are
  recorded in the **public Rekor transparency log**. There is no key to leak or rotate.
- **Tied to this repo.** Verification pins the certificate identity to
  `…/breachatlas/.github/workflows/deploy.yml` and the issuer to GitHub's OIDC — so a
  signature only counts if it was produced by *this* repo's deploy workflow.

Because signatures are published to a public, permanent log, signing runs **only on a real
deploy** (`confirm = DEPLOY`), never on ordinary CI.

Verify a deployed image yourself:

```bash
cosign verify \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github.com/raktimkakati01/breachatlas/.github/workflows/deploy.yml@.*$' \
  <registry>/breachatlas-demo/backend@sha256:<digest>
```

## Repository hardening

Enabled on `raktimkakati01/breachatlas`:

- **Secret scanning + push protection** — blocks pushes that contain detectable secrets.
- **Dependabot alerts** — GitHub flags known-vulnerable dependencies.
- **Private vulnerability reporting** — see `SECURITY.md`.
- **CODEOWNERS** — the maintainer is auto-requested on pull requests.

Branch protection on `main` (require CI to pass before changes land) is documented as an
optional next step; it is left off here so direct pushes to `main` stay convenient on a
solo repository.
