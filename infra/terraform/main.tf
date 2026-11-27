# Shared data sources and computed locals used across the stack.

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

locals {
  name = "${var.name_prefix}-${var.environment}"

  # Pick the first N AZs in the region.
  azs = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  # Deterministic subnet CIDRs carved from the VPC block:
  #   public  -> 10.0.0.0/24, 10.0.1.0/24, ...
  #   private -> 10.0.10.0/24, 10.0.11.0/24, ...
  public_subnet_cidrs  = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnet_cidrs = [for i in range(var.az_count) : cidrsubnet(var.vpc_cidr, 8, i + 10)]

  # Whether to create the HTTPS listener (only when a certificate is supplied).
  enable_https = var.certificate_arn != ""
}
