# One encrypted, retention-bounded log group per service. ECS streams container
# stdout/stderr here via the awslogs driver (see ecs.tf).
locals {
  services = ["backend", "worker", "fetcher", "frontend"]
}

resource "aws_cloudwatch_log_group" "service" {
  for_each = toset(local.services)

  name              = "/${local.name}/ecs/${each.value}"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.main.arn
}
