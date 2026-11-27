# BreachAtlas — Infrastructure (Terraform)

Production-shaped AWS infrastructure for BreachAtlas, written as Terraform.

> **This is code, not a running system.** Nothing here is deployed. It costs
> **nothing** until someone runs `terraform apply`, and this project never does
> that automatically. You can read, validate, and security-scan the whole thing
> for free with **no AWS account**.

## Architecture

```
                 Internet
                    │  (HTTPS; HTTP 301-redirects up)
              ┌─────▼─────┐   public subnets (2 AZs)
              │    ALB     │   + NAT gateway
              └─────┬─────┘
        /api/* ─────┤───── else
   ┌──────────┐     │     ┌──────────┐    private subnets (2 AZs)
   │ backend  │     │     │ frontend │
   └────┬─────┘     │     └──────────┘
        │           │
   ┌────▼─────┐  ┌──▼────┐
   │   RDS    │◄─┤worker │──► fetcher ──► Internet (fetch sources)
   │ Postgres │  └───────┘        ✗  no path back to RDS
   └──────────┘
```

- **ECS Fargate** runs four services (backend, worker, fetcher, frontend) on
  Fargate Spot.
- **RDS PostgreSQL 16** in private subnets, encrypted, reachable only from the
  backend and worker security groups.
- **ALB** terminates TLS and routes `/api/*` to the backend, everything else to
  the frontend.
- **Security-group isolation** reproduces the docker-compose network split: the
  fetcher can reach the internet but has **no route to the database**.

## File map

| File | What it defines |
|------|-----------------|
| `versions.tf` / `providers.tf` | Pinned Terraform + AWS provider, default tags |
| `variables.tf` / `main.tf` | Inputs and computed locals (subnet CIDRs, AZs) |
| `kms.tf` | One customer-managed key (rotation on) for all encryption |
| `vpc.tf` | VPC, public/private subnets, NAT, routes, flow logs |
| `security_groups.tf` | The fetcher→no-DB isolation, rule by rule |
| `rds.tf` | PostgreSQL: encrypted, private, SSL-forced, IAM auth, logs |
| `secrets.tf` | Generated DB password → Secrets Manager (never in code) |
| `ecr.tf` | Immutable, scanned, KMS-encrypted image repos |
| `iam.tf` | Least-privilege execution role + per-service task roles |
| `logs.tf` | Encrypted CloudWatch log groups per service |
| `s3_logs.tf` | ALB access-log bucket (private, versioned, TLS-only) |
| `alb.tf` | Load balancer, target groups, HTTP→HTTPS, path routing |
| `servicediscovery.tf` | Cloud Map DNS so the worker finds the fetcher |
| `ecs.tf` | Cluster, task definitions, services |
| `outputs.tf` | ALB DNS, ECR URLs, RDS endpoint, secret ARN |

## Verify it (free — no AWS account, no cost)

```bash
cd infra/terraform
terraform init
terraform fmt -check
terraform validate
checkov -d . --framework terraform
```

Current Checkov result: **260 passed, 0 failed, 8 skipped** — every skip is an
inline `checkov:skip` comment that states why (see `ADR-0013` in
`docs/decisions.md`). The same scan runs in CI as the `iac-scan` job.

## If you ever want to deploy it (costs money — your choice)

> Running this stack costs roughly **$90–110/month** (NAT, ALB, 4 Fargate tasks,
> RDS). It is built to be stood up and torn down on demand.

```bash
cp terraform.tfvars.example terraform.tfvars   # edit region, etc.
terraform plan      # review EVERY resource before applying
terraform apply     # creates real, billable resources
# ... later ...
terraform destroy   # removes everything; the stack is designed to destroy cleanly
```

The DB password is generated and stored in Secrets Manager — you never set or
see it. To serve real HTTPS traffic, set `certificate_arn` to an ACM certificate
for your domain; without it the config plans in "artifact mode" (no HTTPS
listener).

## Portfolio vs. production

These are tuned for a cheap, destroyable demo and are called out in each file:
single-AZ RDS, deletion protection off, final snapshot skipped, one NAT gateway.
A production deployment flips those on and configures the commented S3 remote
state backend in `versions.tf`.
