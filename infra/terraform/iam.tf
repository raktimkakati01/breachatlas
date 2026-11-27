# =============================================================================
# IAM — least privilege. Three kinds of role:
#   1. flow_log            : lets VPC Flow Logs write to CloudWatch.
#   2. ecs_execution       : used by the ECS agent to pull images, read the DB
#                            secret, and write logs (the "infrastructure" role).
#   3. ecs_task_<service>  : the role the CONTAINER runs as. Our app needs no
#                            AWS APIs at runtime, so these are empty trust-only
#                            roles — explicit, and ready to grant scoped perms
#                            later without widening the execution role.
# Policies are scoped to specific ARNs (this stack's secret, log groups, key),
# never "*".
# =============================================================================

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# --- VPC Flow Logs role ---
data "aws_iam_policy_document" "flow_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "flow_log" {
  name               = "${local.name}-flow-log"
  assume_role_policy = data.aws_iam_policy_document.flow_assume.json
}

data "aws_iam_policy_document" "flow_log" {
  statement {
    sid    = "WriteFlowLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogStreams",
    ]
    resources = ["${aws_cloudwatch_log_group.flow.arn}:*"]
  }
}

resource "aws_iam_role_policy" "flow_log" {
  name   = "write-flow-logs"
  role   = aws_iam_role.flow_log.id
  policy = data.aws_iam_policy_document.flow_log.json
}

# --- ECS task execution role ---
resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

# Baseline ECR pull + log write. This AWS-managed policy is scoped to those
# actions only; it grants no data-plane access.
resource "aws_iam_role_policy_attachment" "ecs_execution_managed" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Allow the execution role to read ONLY this stack's DB secret and decrypt it
# with ONLY this stack's KMS key — nothing else in the account.
data "aws_iam_policy_document" "ecs_execution_secrets" {
  statement {
    sid       = "ReadDbSecret"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.db.arn]
  }
  statement {
    sid       = "DecryptWithStackKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [aws_kms_key.main.arn]
  }
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name   = "read-db-secret"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution_secrets.json
}

# --- Per-service task roles (what the container itself can do) ---
resource "aws_iam_role" "ecs_task" {
  for_each           = toset(local.services)
  name               = "${local.name}-task-${each.value}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}
