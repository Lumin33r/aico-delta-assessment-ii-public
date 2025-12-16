# =============================================================================
# AI Personal Tutor - Terraform Configuration
# =============================================================================
# Main entry point for infrastructure deployment
#
# Components:
# - VPC with public/private subnets
# - EC2 instances (frontend + backend)
# - Amazon Lex bot for conversational UI
# - Cognito Identity Pool for unauthenticated Lex access
# - Lambda for Lex fulfillment
# - S3 for audio storage
# - IAM roles and policies
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Uncomment to use remote state
  # backend "s3" {
  #   bucket         = "ai-tutor-terraform-state"
  #   key            = "ai-tutor/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "ai-tutor-terraform-locks"
  #   encrypt        = true
  # }
}

# =============================================================================
# Providers
# =============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-personal-tutor"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Provider without tags for resources that don't support them
provider "aws" {
  alias  = "no_tags"
  region = var.aws_region
}

# =============================================================================
# Data Sources
# =============================================================================

# Current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# =============================================================================
# Random Resources
# =============================================================================

resource "random_id" "suffix" {
  byte_length = 4
}

# =============================================================================
# Local Variables
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    CreatedBy   = "terraform"
  }

  # Use 2 AZs for high availability
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # Account and region info
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}
