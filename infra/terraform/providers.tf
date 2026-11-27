# The AWS provider. Region comes from a variable; credentials are never put in
# code — Terraform picks them up from the environment, a shared profile, or an
# instance role at run time. default_tags stamps every taggable resource so
# cost allocation and ownership are consistent across the whole stack.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "BreachAtlas"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Repository  = "raktimkakati01/breachatlas"
    }
  }
}

provider "random" {}
