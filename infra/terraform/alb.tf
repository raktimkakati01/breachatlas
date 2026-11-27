# =============================================================================
# Application Load Balancer. Public, in the public subnets, with access logging,
# invalid-header dropping, and HTTP->HTTPS redirect. Path routing sends /api/* to
# the backend and everything else to the frontend.
#
# The HTTPS listener and routing exist only when a certificate ARN is supplied
# (local.enable_https). Without one ("artifact mode"), the config still validates
# and plans — there is just nothing to serve real traffic, which is expected for
# an un-applied portfolio stack.
# =============================================================================

resource "aws_lb" "main" {
  # checkov:skip=CKV_AWS_150:Deletion protection off so the portfolio stack is destroyable; enable for production.
  # checkov:skip=CKV2_AWS_28:A WAFv2 WebACL is recommended for production but omitted here to avoid its monthly cost in a portfolio stack.
  name                       = "${local.name}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  drop_invalid_header_fields = true
  enable_deletion_protection = false

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "alb"
    enabled = true
  }

  depends_on = [aws_s3_bucket_policy.alb_logs]
  tags       = { Name = "${local.name}-alb" }
}

# --- Target groups (ip targets, because Fargate uses awsvpc networking) ---
resource "aws_lb_target_group" "frontend" {
  # checkov:skip=CKV_AWS_378:ALB->task traffic is HTTP inside the private VPC; TLS terminates at the ALB (end-to-end TLS needs per-task certs).
  name        = "${local.name}-frontend"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = { Name = "${local.name}-frontend-tg" }
}

resource "aws_lb_target_group" "backend" {
  # checkov:skip=CKV_AWS_378:ALB->task traffic is HTTP inside the private VPC; TLS terminates at the ALB (end-to-end TLS needs per-task certs).
  name        = "${local.name}-backend"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/api/v1/health"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
  tags = { Name = "${local.name}-backend-tg" }
}

# --- HTTP listener: always redirect to HTTPS ---
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# --- HTTPS listener (only when a certificate is provided) ---
resource "aws_lb_listener" "https" {
  count             = local.enable_https ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06" # TLS 1.2+ only
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  count        = local.enable_https ? 1 : 0
  listener_arn = aws_lb_listener.https[0].arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*"]
    }
  }
}
