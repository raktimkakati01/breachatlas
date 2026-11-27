# =============================================================================
# RDS PostgreSQL. Private subnets only, encrypted at rest with our KMS key,
# SSL enforced in transit, IAM auth enabled, query/connection logs shipped to
# CloudWatch, and reachable only from the backend and worker security groups.
#
# Two settings are deliberately portfolio-friendly rather than prod-grade and
# are flagged with Checkov skips that state WHY:
#   - single-AZ (cost), and
#   - deletion protection off + final snapshot skipped (so `destroy` is clean).
# A real production stack would flip all three.
# =============================================================================

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${local.name}-db-subnet-group" }
}

# Enforce TLS and connection logging at the engine level.
resource "aws_db_parameter_group" "main" {
  name_prefix = "${local.name}-pg16-"
  family      = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
  parameter {
    name  = "log_connections"
    value = "1"
  }
  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Enhanced monitoring role (OS-level metrics every 60s).
data "aws_iam_policy_document" "rds_monitoring_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["monitoring.rds.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "rds_monitoring" {
  name               = "${local.name}-rds-monitoring"
  assume_role_policy = data.aws_iam_policy_document.rds_monitoring_assume.json
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_db_instance" "main" {
  # checkov:skip=CKV_AWS_157:Single-AZ is a deliberate cost choice for this portfolio stack; flip multi_az=true for production.
  # checkov:skip=CKV_AWS_293:Deletion protection is off so the portfolio stack can be destroyed cleanly; enable for production.
  # checkov:skip=CKV_AWS_353:Performance Insights left off for cost; enable (with KMS) on db.t3.small+ for production.
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = "16.4"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 2 # autoscale headroom
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.main.arn

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  publicly_accessible    = false

  multi_az                            = false
  backup_retention_period             = 7
  backup_window                       = "03:00-04:00"
  maintenance_window                  = "Mon:04:00-Mon:05:00"
  copy_tags_to_snapshot               = true
  auto_minor_version_upgrade          = true
  iam_database_authentication_enabled = true
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn

  # Portfolio lifecycle: destroyable without leaving a protected DB or snapshot.
  deletion_protection       = false
  skip_final_snapshot       = true
  final_snapshot_identifier = null

  tags = { Name = "${local.name}-db" }
}
