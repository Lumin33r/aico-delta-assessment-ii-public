# =============================================================================
# Terraform Outputs
# =============================================================================
# Exports important values for use in other configurations, CI/CD, and frontend
# =============================================================================

# -----------------------------------------------------------------------------
# VPC Outputs
# -----------------------------------------------------------------------------

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

# -----------------------------------------------------------------------------
# Load Balancer Outputs
# -----------------------------------------------------------------------------

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "api_endpoint" {
  description = "API endpoint URL"
  value       = "http://${aws_lb.main.dns_name}"
}

# -----------------------------------------------------------------------------
# S3 Outputs
# -----------------------------------------------------------------------------

output "audio_bucket_name" {
  description = "Name of the S3 bucket for audio files"
  value       = aws_s3_bucket.audio.id
}

output "audio_bucket_arn" {
  description = "ARN of the S3 bucket for audio files"
  value       = aws_s3_bucket.audio.arn
}

# -----------------------------------------------------------------------------
# Cognito Outputs
# -----------------------------------------------------------------------------

output "cognito_identity_pool_id" {
  description = "ID of the Cognito Identity Pool"
  value       = var.create_cognito ? aws_cognito_identity_pool.main[0].id : null
}

# -----------------------------------------------------------------------------
# Lex Bot Outputs
# -----------------------------------------------------------------------------

output "lex_bot_id" {
  description = "ID of the Lex bot"
  value       = var.create_lex_bot ? aws_lexv2models_bot.tutor[0].id : null
}

output "lex_bot_version" {
  description = "Version of the Lex bot"
  value       = var.create_lex_bot ? aws_lexv2models_bot_version.main[0].bot_version : null
}

# Note: Bot alias must be created manually - see lex.tf for instructions
output "lex_bot_alias_instructions" {
  description = "Instructions to create Lex bot alias (not yet supported by Terraform)"
  value       = var.create_lex_bot ? "Create bot alias manually using AWS CLI. See terraform/lex.tf for instructions." : null
}

# -----------------------------------------------------------------------------
# Lambda Outputs
# -----------------------------------------------------------------------------

output "lambda_function_name" {
  description = "Name of the Lex fulfillment Lambda function"
  value       = aws_lambda_function.lex_fulfillment.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lex fulfillment Lambda function"
  value       = aws_lambda_function.lex_fulfillment.arn
}

# -----------------------------------------------------------------------------
# EC2/ASG Outputs
# -----------------------------------------------------------------------------

output "backend_asg_name" {
  description = "Name of the backend Auto Scaling Group"
  value       = aws_autoscaling_group.backend.name
}

output "backend_security_group_id" {
  description = "ID of the backend security group"
  value       = aws_security_group.backend.id
}

# -----------------------------------------------------------------------------
# Configuration Outputs
# -----------------------------------------------------------------------------

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# -----------------------------------------------------------------------------
# Frontend Environment Configuration
# -----------------------------------------------------------------------------

locals {
  frontend_env_with_lex = var.create_cognito && var.create_lex_bot ? join("\n", [
    "# Frontend Environment Configuration",
    "VITE_AWS_REGION=${var.aws_region}",
    "VITE_COGNITO_IDENTITY_POOL_ID=${aws_cognito_identity_pool.main[0].id}",
    "VITE_LEX_BOT_ID=${aws_lexv2models_bot.tutor[0].id}",
    "# VITE_LEX_BOT_ALIAS_ID=<create-alias-manually>",
    "VITE_API_URL=http://${aws_lb.main.dns_name}"
  ]) : null

  frontend_env_without_lex = join("\n", [
    "# Frontend Environment Configuration (Lex/Cognito not created)",
    "VITE_AWS_REGION=${var.aws_region}",
    "VITE_API_URL=http://${aws_lb.main.dns_name}"
  ])
}

output "frontend_env_config" {
  description = "Environment variables for frontend .env file"
  value       = local.frontend_env_with_lex != null ? local.frontend_env_with_lex : local.frontend_env_without_lex
}

# -----------------------------------------------------------------------------
# Backend Environment Configuration
# -----------------------------------------------------------------------------

output "backend_env_config" {
  description = "Environment variables for backend configuration"
  value = join("\n", [
    "# Backend Environment Configuration",
    "AWS_REGION=${var.aws_region}",
    "S3_BUCKET=${aws_s3_bucket.audio.id}",
    "OLLAMA_HOST=http://localhost:11434",
    "OLLAMA_MODEL=${var.ollama_model}"
  ])
}

# -----------------------------------------------------------------------------
# Connection Information
# -----------------------------------------------------------------------------

output "connection_info" {
  description = "Information for connecting to the deployed infrastructure"
  value = join("\n", [
    "=== AI Personal Tutor - Connection Info ===",
    "",
    "API Endpoint: http://${aws_lb.main.dns_name}",
    "Health Check: http://${aws_lb.main.dns_name}/health",
    "",
    "AWS Region: ${var.aws_region}",
    "Environment: ${var.environment}",
    "",
    "S3 Audio Bucket: ${aws_s3_bucket.audio.id}",
    var.create_lex_bot ? "Lex Bot ID: ${aws_lexv2models_bot.tutor[0].id}" : "Lex Bot: Not created",
    var.create_cognito ? "Cognito Pool: ${aws_cognito_identity_pool.main[0].id}" : "Cognito: Not created",
    "",
    var.create_lex_bot ? "NOTE: Create Lex bot alias manually - see terraform/lex.tf" : ""
  ])
}

# -----------------------------------------------------------------------------
# CLI Commands for Post-Deployment Setup
# -----------------------------------------------------------------------------

output "post_deployment_commands" {
  description = "Commands to run after Terraform apply"
  value = var.create_lex_bot ? join("\n", [
    "# Create Lex Bot Alias (required for frontend)",
    "aws lexv2-models create-bot-alias \\",
    "  --bot-alias-name prod \\",
    "  --bot-id ${aws_lexv2models_bot.tutor[0].id} \\",
    "  --bot-version ${aws_lexv2models_bot_version.main[0].bot_version} \\",
    "  --bot-alias-locale-settings '{\"en_US\":{\"enabled\":true,\"codeHookSpecification\":{\"lambdaCodeHook\":{\"lambdaARN\":\"${aws_lambda_function.lex_fulfillment.arn}\",\"codeHookInterfaceVersion\":\"1.0\"}}}}'"
  ]) : "No post-deployment commands needed."
}
