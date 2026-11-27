# One customer-managed KMS key encrypts everything that holds data at rest:
# RDS storage, the Secrets Manager secret, CloudWatch log groups, and ECR.
# A customer-managed key (vs. the AWS-managed default) gives us key rotation,
# an explicit key policy, and a single audit point in CloudTrail.
resource "aws_kms_key" "main" {
  description             = "${local.name} encryption key (RDS, Secrets, Logs, ECR)"
  enable_key_rotation     = true # annual automatic rotation
  deletion_window_in_days = 7
  policy                  = data.aws_iam_policy_document.kms.json
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name}"
  target_key_id = aws_kms_key.main.key_id
}

# Key policy: the account root can administer the key, and the CloudWatch Logs
# service in this region is allowed to use it to encrypt log groups.
data "aws_iam_policy_document" "kms" {
  # checkov:skip=CKV_AWS_111:Root-admin on the key is the AWS-recommended policy to avoid key lockout; not a principal grant.
  # checkov:skip=CKV_AWS_356:KMS key policies must scope to the key itself ("*" = this key); narrowing is not possible here.
  # checkov:skip=CKV_AWS_109:Account-root key administration is required so the key never becomes unmanageable.
  statement {
    sid       = "AccountAdmin"
    effect    = "Allow"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }

  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"
    actions = [
      "kms:Encrypt*",
      "kms:Decrypt*",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      "kms:Describe*",
    ]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${data.aws_region.current.name}.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"]
    }
  }
}
