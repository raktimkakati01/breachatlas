# =============================================================================
# ECS on Fargate. One cluster, four services (backend, worker, fetcher,
# frontend). Each task runs in a private subnet with its own security group, so
# the network split from docker-compose is preserved exactly.
#
# Shared hardening on every container:
#   - secrets (DB URL) injected from Secrets Manager, never plaintext env
#   - read-only root filesystem + a small writable /tmp volume
#   - init process enabled (reaps zombies), logs to CloudWatch
#   - runs on FARGATE_SPOT by default to cut cost ~70% if applied
# =============================================================================

resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }
}

locals {
  backend_image  = "${aws_ecr_repository.repo["backend"].repository_url}:${var.backend_image_tag}"
  fetcher_image  = "${aws_ecr_repository.repo["fetcher"].repository_url}:${var.fetcher_image_tag}"
  frontend_image = "${aws_ecr_repository.repo["frontend"].repository_url}:${var.frontend_image_tag}"

  # The DB connection URL, pulled from the JSON secret's "url" field at launch.
  db_url_secret = "${aws_secretsmanager_secret.db.arn}:url::"

  # Log config fragment reused by every container definition.
  log_options = {
    for s in local.services : s => {
      "awslogs-group"         = aws_cloudwatch_log_group.service[s].name
      "awslogs-region"        = var.aws_region
      "awslogs-stream-prefix" = s
    }
  }
}

# --- Backend (FastAPI behind the ALB) ---
resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task["backend"].arn

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([{
    name                   = "backend"
    image                  = local.backend_image
    essential              = true
    readonlyRootFilesystem = true
    user                   = "app"
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "APP_ENV", value = "production" },
      { name = "REFERENCE_DATA_DIR", value = "/app/data/reference" },
      { name = "API_RATE_LIMIT", value = "60" },
      { name = "BACKEND_CORS_ORIGINS", value = "https://${aws_lb.main.dns_name}" },
    ]
    secrets          = [{ name = "DATABASE_URL", valueFrom = local.db_url_secret }]
    mountPoints      = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters  = { initProcessEnabled = true }
    logConfiguration = { logDriver = "awslogs", options = local.log_options["backend"] }
  }])
}

# --- Worker (ingestion; reaches DB + fetcher, no inbound) ---
resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task["worker"].arn

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([{
    name                   = "worker"
    image                  = local.backend_image # same image as backend, different command
    essential              = true
    readonlyRootFilesystem = true
    user                   = "app"
    command                = ["python", "-m", "app.ingestion.worker"]
    environment = [
      { name = "APP_ENV", value = "production" },
      { name = "FETCHER_URL", value = "http://fetcher.${aws_service_discovery_private_dns_namespace.main.name}:8001" },
    ]
    secrets          = [{ name = "DATABASE_URL", valueFrom = local.db_url_secret }]
    mountPoints      = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters  = { initProcessEnabled = true }
    logConfiguration = { logDriver = "awslogs", options = local.log_options["worker"] }
  }])
}

# --- Fetcher (SSRF-isolated; no DB secret, no DB reachability) ---
resource "aws_ecs_task_definition" "fetcher" {
  family                   = "${local.name}-fetcher"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task["fetcher"].arn

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([{
    name                   = "fetcher"
    image                  = local.fetcher_image
    essential              = true
    readonlyRootFilesystem = true
    user                   = "app"
    portMappings           = [{ containerPort = 8001, protocol = "tcp" }]
    environment = [
      { name = "FETCHER_USER_AGENT", value = var.fetcher_user_agent },
    ]
    # No DB secret here — the fetcher never touches the database.
    mountPoints      = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters  = { initProcessEnabled = true }
    logConfiguration = { logDriver = "awslogs", options = local.log_options["fetcher"] }
  }])
}

# --- Frontend (Next.js behind the ALB) ---
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task["frontend"].arn

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([{
    name                   = "frontend"
    image                  = local.frontend_image
    essential              = true
    readonlyRootFilesystem = true
    user                   = "node"
    portMappings           = [{ containerPort = 3000, protocol = "tcp" }]
    environment = [
      { name = "NODE_ENV", value = "production" },
      # NEXT_PUBLIC_* is inlined at build time; set the same value when building
      # the image. Kept here for parity and server-side reads.
      { name = "NEXT_PUBLIC_API_URL", value = "https://${aws_lb.main.dns_name}/api/v1" },
    ]
    mountPoints      = [{ sourceVolume = "tmp", containerPath = "/tmp", readOnly = false }]
    linuxParameters  = { initProcessEnabled = true }
    logConfiguration = { logDriver = "awslogs", options = local.log_options["frontend"] }
  }])
}

# --- Services ---
# A reusable network config: all tasks in private subnets, no public IP.
locals {
  common_deployment = {
    minimum_healthy_percent = 100
    maximum_percent         = 200
  }
}

resource "aws_ecs_service" "backend" {
  name            = "backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = local.common_deployment.minimum_healthy_percent
  deployment_maximum_percent         = local.common_deployment.maximum_percent
  health_check_grace_period_seconds  = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.frontend.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  deployment_minimum_healthy_percent = local.common_deployment.minimum_healthy_percent
  deployment_maximum_percent         = local.common_deployment.maximum_percent
  health_check_grace_period_seconds  = 60

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "worker" {
  name            = "worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = local.common_deployment.minimum_healthy_percent
  deployment_maximum_percent         = local.common_deployment.maximum_percent
}

resource "aws_ecs_service" "fetcher" {
  name            = "fetcher"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.fetcher.arn
  desired_count   = 1

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.fetcher.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.fetcher.arn
  }

  deployment_minimum_healthy_percent = local.common_deployment.minimum_healthy_percent
  deployment_maximum_percent         = local.common_deployment.maximum_percent
}
