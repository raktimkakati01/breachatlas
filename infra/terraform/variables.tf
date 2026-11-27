# All knobs live here so the stack can be re-pointed (region, sizes, image tags)
# without editing resource files. Defaults are cost-conscious — the smallest
# sizes that still run the stack — because this is a portfolio deployment.

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name, used in tags and resource names."
  type        = string
  default     = "demo"
}

variable "name_prefix" {
  description = "Prefix for all resource names."
  type        = string
  default     = "breachatlas"
}

# --- Networking ---
variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of Availability Zones to spread subnets across."
  type        = number
  default     = 2

  validation {
    condition     = var.az_count >= 2 && var.az_count <= 3
    error_message = "az_count must be 2 or 3 (ALB and RDS both require >= 2 AZs)."
  }
}

# --- Database ---
variable "db_instance_class" {
  description = "RDS instance class. db.t4g.micro is the cheapest Graviton option."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS storage in GB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "breachatlas"
}

variable "db_username" {
  description = "Master username for RDS. The password is generated and stored in Secrets Manager — never set here."
  type        = string
  default     = "breachatlas"
}

# --- Container images ---
# Default to :latest so `validate`/`plan` work before any image is pushed.
# In CI these are pinned to an immutable digest/tag per deploy.
variable "backend_image_tag" {
  description = "Tag for the backend/worker image in ECR."
  type        = string
  default     = "latest"
}

variable "fetcher_image_tag" {
  description = "Tag for the fetcher image in ECR."
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Tag for the frontend image in ECR."
  type        = string
  default     = "latest"
}

# --- HTTPS ---
# A real deployment needs a domain + ACM certificate. When this is empty the
# HTTPS listener and its routing are skipped so the config still validates and
# plans without a certificate. Set it to serve traffic for real.
variable "certificate_arn" {
  description = "ACM certificate ARN for the HTTPS listener. Empty = no HTTPS listener (artifact mode)."
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days. Defaults to 1 year (cheap storage, satisfies audit-retention baselines)."
  type        = number
  default     = 365
}

# --- Fetcher identity ---
variable "fetcher_user_agent" {
  description = "User-Agent the SSRF fetcher presents to upstreams (SEC/ICO require a real contact)."
  type        = string
  default     = "BreachAtlas-fetcher/0.1 (contact: set-me@example.com)"
}
