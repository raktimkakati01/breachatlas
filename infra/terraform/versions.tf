# Pin Terraform and provider versions so the same config produces the same
# plan on every machine and in CI. Loose version floors let patch releases in;
# the ~> operator keeps us on a known-good major/minor line.
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state is intentionally left to the operator. For a real deployment,
  # configure an encrypted, versioned S3 backend with a DynamoDB lock table:
  #
  #   backend "s3" {
  #     bucket         = "breachatlas-tfstate-<account-id>"
  #     key            = "breachatlas/terraform.tfstate"
  #     region         = "us-east-1"
  #     encrypt        = true
  #     dynamodb_table = "breachatlas-tf-locks"
  #   }
  #
  # It is commented out so `terraform validate` / `plan` work locally with the
  # default local backend and no live AWS resources.
}
