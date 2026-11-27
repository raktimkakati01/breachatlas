# Private S3 bucket for ALB access logs. Public access fully blocked, versioned,
# encrypted, and lifecycle-expired so it never grows unbounded.
#
# NOTE on encryption: ALB access-log delivery supports SSE-S3 (AES256) only — it
# cannot write to a bucket encrypted with a customer-managed KMS key. So this one
# bucket uses AES256 while everything else uses our CMK. That is an AWS platform
# constraint, hence the documented Checkov skip below.
resource "aws_s3_bucket" "alb_logs" {
  # checkov:skip=CKV_AWS_145:ALB access-log delivery only supports SSE-S3 (AES256), not a customer-managed KMS key.
  # checkov:skip=CKV_AWS_18:This IS the access-log bucket; enabling access logging on it would recurse.
  # checkov:skip=CKV_AWS_144:Cross-region replication is unnecessary (and costly) for short-lived demo access logs.
  # checkov:skip=CKV2_AWS_62:Event notifications add no value for a write-only ALB log sink in a portfolio stack.
  bucket        = "${local.name}-alb-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # portfolio convenience so `destroy` empties the bucket
  tags          = { Name = "${local.name}-alb-logs" }
}

resource "aws_s3_bucket_public_access_block" "alb_logs" {
  bucket                  = aws_s3_bucket.alb_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  rule {
    object_ownership = "BucketOwnerEnforced" # ACLs disabled; policy-based delivery
  }
}

resource "aws_s3_bucket_versioning" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  rule {
    id     = "expire-logs"
    status = "Enabled"
    filter {}
    expiration {
      days = 90
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Allow the Elastic Load Balancing log-delivery principal to write logs.
data "aws_elb_service_account" "main" {}

data "aws_iam_policy_document" "alb_logs" {
  # Regional ELB account (older delivery path).
  statement {
    sid       = "AllowELBAccount"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.alb_logs.arn}/alb/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]
    principals {
      type        = "AWS"
      identifiers = [data.aws_elb_service_account.main.arn]
    }
  }

  # Modern log-delivery service principal.
  statement {
    sid       = "AllowLogDeliveryWrite"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.alb_logs.arn}/alb/AWSLogs/${data.aws_caller_identity.current.account_id}/*"]
    principals {
      type        = "Service"
      identifiers = ["logdelivery.elasticloadbalancing.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }

  statement {
    sid       = "AllowLogDeliveryAclCheck"
    effect    = "Allow"
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.alb_logs.arn]
    principals {
      type        = "Service"
      identifiers = ["logdelivery.elasticloadbalancing.amazonaws.com"]
    }
  }

  # Deny any non-TLS access to the bucket.
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.alb_logs.arn, "${aws_s3_bucket.alb_logs.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  policy = data.aws_iam_policy_document.alb_logs.json

  depends_on = [aws_s3_bucket_public_access_block.alb_logs]
}
