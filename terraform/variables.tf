# =============================================================================
# Variables Configuration
# =============================================================================

# -----------------------------------------------------------------------------
# General Settings
# -----------------------------------------------------------------------------

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
  default     = "ai-tutor"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

# -----------------------------------------------------------------------------
# VPC Settings
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
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
# EC2 Settings
# -----------------------------------------------------------------------------

variable "instance_type" {
  description = "EC2 instance type for backend servers"
  type        = string
  default     = "t3.medium"
}

variable "key_name" {
  description = "SSH key pair name for EC2 instances"
  type        = string
  default     = ""
}

variable "ssh_allowed_cidr" {
  description = "CIDR block allowed for SSH access"
  type        = string
  default     = "0.0.0.0/0"
}

# -----------------------------------------------------------------------------
# Lex Bot Settings
# -----------------------------------------------------------------------------

variable "lex_bot_name" {
  description = "Name for the Lex bot"
  type        = string
  default     = "AITutor"
}

variable "lex_bot_locale" {
  description = "Locale for Lex bot"
  type        = string
  default     = "en_US"
}

# -----------------------------------------------------------------------------
# S3 Settings
# -----------------------------------------------------------------------------

variable "audio_bucket_name" {
  description = "S3 bucket name for audio storage (will have suffix added)"
  type        = string
  default     = "ai-tutor-audio"
}

# -----------------------------------------------------------------------------
# Ollama Settings
# -----------------------------------------------------------------------------

variable "ollama_model" {
  description = "Ollama model to use for generation"
  type        = string
  default     = "llama3.2"
}

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnet internet access"
  type        = bool
  default     = false
}

variable "enable_bastion" {
  description = "Enable bastion host for SSH access"
  type        = bool
  default     = false
}

variable "create_lex_bot" {
  description = "Create Amazon Lex bot resources"
  type        = bool
  default     = true
}

variable "create_cognito" {
  description = "Create Cognito Identity Pool for frontend Lex access"
  type        = bool
  default     = true
}
