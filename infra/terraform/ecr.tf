# One ECR repository per image. Settings applied to all three:
#   - scan_on_push: Trivy/ECR scans every pushed image for CVEs.
#   - IMMUTABLE tags: a tag can never be overwritten, so a deployed digest is
#     exactly what was scanned and signed — no silent "latest" drift.
#   - KMS encryption at rest with our customer-managed key.
#   - A lifecycle policy expires untagged images to control storage cost.
locals {
  ecr_repos = {
    backend  = "${local.name}/backend"
    fetcher  = "${local.name}/fetcher"
    frontend = "${local.name}/frontend"
  }
}

resource "aws_ecr_repository" "repo" {
  for_each = local.ecr_repos

  name                 = each.value
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true # portfolio convenience so `destroy` removes images too

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.main.arn
  }

  tags = { Name = each.value }
}

resource "aws_ecr_lifecycle_policy" "repo" {
  for_each   = aws_ecr_repository.repo
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire untagged images after 14 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 14
      }
      action = { type = "expire" }
    }]
  })
}
