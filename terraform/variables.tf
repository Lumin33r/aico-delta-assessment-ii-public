# =============================================================================
# Terraform Variables
# =============================================================================
# Input variables for the AI Personal Tutor infrastructure
# =============================================================================

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
  default     = "Troy-ai-tutor"
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "ai-personal-tutor"
    ManagedBy   = "terraform"
    Application = "podcast-tutor"
  }
}

# -----------------------------------------------------------------------------
# Networking Configuration
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# -----------------------------------------------------------------------------
# EC2 Configuration
# -----------------------------------------------------------------------------

variable "instance_type" {
  description = "EC2 instance type for backend servers"
  type        = string
  default     = "t3.medium"
}

variable "ami_id" {
  description = "AMI ID for EC2 instances (Amazon Linux 2023)"
  type        = string
  default     = "" # Will use data source if not specified
}

variable "key_name" {
  description = "Name of the SSH key pair for EC2 access"
  type        = string
  default     = "troy-west-2"
}

variable "min_instances" {
  description = "Minimum number of instances in ASG"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances in ASG"
  type        = number
  default     = 3
}

variable "desired_capacity" {
  description = "Desired number of instances in ASG"
  type        = number
  default     = 1
}

# -----------------------------------------------------------------------------
# Ollama Configuration
# -----------------------------------------------------------------------------

variable "ollama_model" {
  description = "Ollama model to use for content generation"
  type        = string
  default     = "llama3.2:1b"
}

# -----------------------------------------------------------------------------
# S3 Configuration
# -----------------------------------------------------------------------------

variable "audio_bucket_name" {
  description = "Name for the S3 bucket storing audio files (must be globally unique)"
  type        = string
  default     = "" # Will be auto-generated if not specified
}

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------

variable "create_lex_bot" {
  description = "Whether to create the Lex bot resources"
  type        = bool
  default     = true
}

variable "create_cognito" {
  description = "Whether to create Cognito resources for authentication"
  type        = bool
  default     = true
}

variable "enable_nat_gateway" {
  description = "Whether to create NAT Gateway for private subnets"
  type        = bool
  default     = false # Set to true for production
}

# -----------------------------------------------------------------------------
# Backend API Configuration
# -----------------------------------------------------------------------------

variable "backend_port" {
  description = "Port the backend API listens on"
  type        = number
  default     = 8000
}

variable "health_check_path" {
  description = "Path for ALB health checks"
  type        = string
  default     = "/health"
}

# -----------------------------------------------------------------------------
# Lambda Configuration
# -----------------------------------------------------------------------------

variable "lambda_timeout" {
  description = "Timeout in seconds for Lambda functions"
  type        = number
  default     = 30
}

variable "lambda_memory" {
  description = "Memory allocation for Lambda functions in MB"
  type        = number
  default     = 256
}

# -----------------------------------------------------------------------------
# Git Repository Configuration (for containerized deployment)
# -----------------------------------------------------------------------------

variable "git_repo_url" {
  description = "Git repository URL for cloning application code"
  type        = string
  default     = "https://github.com/Lumin33r/aico-delta-assessment-ii-public.git"
}

# -----------------------------------------------------------------------------
# Lex Bot Configuration (Manually Created Resources)
# -----------------------------------------------------------------------------
# The Lex bot alias must be created manually after initial terraform apply
# because the AWS provider doesn't fully support bot alias with Lambda hooks.
#
# After creating the alias via AWS CLI, update this value and run:
#   terraform apply -auto-approve
#   aws autoscaling start-instance-refresh --auto-scaling-group-name "<asg-name>" ...
# -----------------------------------------------------------------------------

variable "lex_bot_alias_id" {
  description = "Lex Bot Alias ID (created manually after initial deploy)"
  type        = string
  default     = "JBEV8XIGQG" # Updated 2025-12-20 - prod alias
}

# -----------------------------------------------------------------------------
# PostgreSQL Configuration
# -----------------------------------------------------------------------------

variable "postgres_username" {
  description = "PostgreSQL username"
  type        = string
  default     = "aitutor"
}

variable "postgres_database" {
  description = "PostgreSQL database name"
  type        = string
  default     = "aitutor"
}
