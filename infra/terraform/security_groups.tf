# =============================================================================
# Security groups — the cloud-enforced version of the docker-compose network
# split. Rules are written as individual resources (not inline) so each one
# carries its own description and the intent is auditable rule-by-rule.
#
# The property that matters: the FETCHER can reach the public internet (it must,
# to retrieve breach sources) but has NO egress rule to the database or any
# internal service, and the DATABASE accepts connections ONLY from the backend
# and worker. An SSRF in the fetcher therefore cannot reach the DB — the network
# makes it impossible, independent of any application-level SSRF guard.
# =============================================================================

# --- ALB: the only internet-facing security group ---
resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Public ALB: HTTP/HTTPS in from the internet."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTPS from the internet"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  # checkov:skip=CKV_AWS_260:Port 80 is open only to issue an HTTP->HTTPS 301 redirect; no plaintext app traffic is served.
  security_group_id = aws_security_group.alb.id
  description       = "HTTP from the internet (redirected to HTTPS)"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "alb_to_frontend" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward to the frontend tasks"
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
  referenced_security_group_id = aws_security_group.frontend.id
}

resource "aws_vpc_security_group_egress_rule" "alb_to_backend" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Forward to the backend tasks"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.backend.id
}

# --- Frontend (Next.js) ---
resource "aws_security_group" "frontend" {
  name        = "${local.name}-frontend"
  description = "Frontend tasks: traffic only from the ALB."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-frontend" }
}

resource "aws_vpc_security_group_ingress_rule" "frontend_from_alb" {
  security_group_id            = aws_security_group.frontend.id
  description                  = "App traffic from the ALB"
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "frontend_https" {
  security_group_id = aws_security_group.frontend.id
  description       = "Outbound HTTPS (ECR image pull, logs via NAT)"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

# --- Backend (FastAPI) ---
resource "aws_security_group" "backend" {
  name        = "${local.name}-backend"
  description = "Backend API tasks: traffic from the ALB; DB + AWS APIs out."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-backend" }
}

resource "aws_vpc_security_group_ingress_rule" "backend_from_alb" {
  security_group_id            = aws_security_group.backend.id
  description                  = "API traffic from the ALB"
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "backend_to_db" {
  security_group_id            = aws_security_group.backend.id
  description                  = "PostgreSQL to RDS"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.rds.id
}

resource "aws_vpc_security_group_egress_rule" "backend_https" {
  security_group_id = aws_security_group.backend.id
  description       = "Outbound HTTPS (Secrets Manager, ECR, logs via NAT)"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

# --- Worker (ingestion) — bridges DB and fetcher, no inbound ---
resource "aws_security_group" "worker" {
  name        = "${local.name}-worker"
  description = "Ingestion worker: reaches the DB and the fetcher; no inbound."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-worker" }
}

resource "aws_vpc_security_group_egress_rule" "worker_to_db" {
  security_group_id            = aws_security_group.worker.id
  description                  = "PostgreSQL to RDS"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.rds.id
}

resource "aws_vpc_security_group_egress_rule" "worker_to_fetcher" {
  security_group_id            = aws_security_group.worker.id
  description                  = "Call the isolated fetcher"
  ip_protocol                  = "tcp"
  from_port                    = 8001
  to_port                      = 8001
  referenced_security_group_id = aws_security_group.fetcher.id
}

resource "aws_vpc_security_group_egress_rule" "worker_https" {
  security_group_id = aws_security_group.worker.id
  description       = "Outbound HTTPS (AWS APIs, ECR, logs via NAT)"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

# --- Fetcher (SSRF-isolated) ---
# Reachable ONLY by the worker. Can call out to the internet to fetch sources,
# but has NO egress rule to the RDS security group or any internal service.
resource "aws_security_group" "fetcher" {
  name        = "${local.name}-fetcher"
  description = "SSRF-isolated fetcher: inbound only from worker; internet egress; NO path to the DB."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-fetcher" }
}

resource "aws_vpc_security_group_ingress_rule" "fetcher_from_worker" {
  security_group_id            = aws_security_group.fetcher.id
  description                  = "Fetch requests from the worker only"
  ip_protocol                  = "tcp"
  from_port                    = 8001
  to_port                      = 8001
  referenced_security_group_id = aws_security_group.worker.id
}

resource "aws_vpc_security_group_egress_rule" "fetcher_http" {
  security_group_id = aws_security_group.fetcher.id
  description       = "Fetch upstream sources over HTTP"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "fetcher_https" {
  security_group_id = aws_security_group.fetcher.id
  description       = "Fetch upstream sources over HTTPS (also ECR/logs via NAT)"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}
# NOTE: there is deliberately NO egress rule from the fetcher to rds / 5432.

# --- RDS (PostgreSQL) ---
# Ingress ONLY from backend and worker. The fetcher is absent by design.
resource "aws_security_group" "rds" {
  name        = "${local.name}-rds"
  description = "PostgreSQL: inbound 5432 only from backend and worker."
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${local.name}-rds" }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_backend" {
  security_group_id            = aws_security_group.rds.id
  description                  = "PostgreSQL from the backend"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.backend.id
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_worker" {
  security_group_id            = aws_security_group.rds.id
  description                  = "PostgreSQL from the worker"
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  referenced_security_group_id = aws_security_group.worker.id
}
