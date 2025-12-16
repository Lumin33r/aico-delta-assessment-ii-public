# =============================================================================
# Terraform Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# VPC Outputs
# -----------------------------------------------------------------------------

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# -----------------------------------------------------------------------------
# ALB Outputs
# -----------------------------------------------------------------------------

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "api_url" {
  description = "Backend API URL"
  value       = "http://${aws_lb.main.dns_name}/api"
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "http://${aws_lb.main.dns_name}"
}

# -----------------------------------------------------------------------------
# S3 Outputs
# -----------------------------------------------------------------------------

output "audio_bucket_name" {
  description = "S3 bucket name for audio storage"
  value       = aws_s3_bucket.audio.bucket
}

output "audio_bucket_arn" {
  description = "S3 bucket ARN for audio storage"
  value       = aws_s3_bucket.audio.arn
}

# -----------------------------------------------------------------------------
# Lex Outputs
# -----------------------------------------------------------------------------

output "lex_bot_id" {
  description = "Lex bot ID"
  value       = var.create_lex_bot ? aws_lexv2models_bot.tutor[0].id : null
}

output "lex_bot_alias_id" {
  description = "Lex bot alias ID"
  value       = var.create_lex_bot ? aws_lexv2models_bot_alias.main[0].bot_alias_id : null
}

# -----------------------------------------------------------------------------
# Cognito Outputs
# -----------------------------------------------------------------------------

output "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID for frontend"
  value       = var.create_cognito ? aws_cognito_identity_pool.main[0].id : null
}

# -----------------------------------------------------------------------------
# Lambda Outputs
# -----------------------------------------------------------------------------

output "lex_fulfillment_lambda_arn" {
  description = "Lex fulfillment Lambda ARN"
  value       = aws_lambda_function.lex_fulfillment.arn
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
# Frontend Configuration (for .env file)
# -----------------------------------------------------------------------------

output "frontend_env_config" {
  description = "Environment variables for frontend .env file"
  value = var.create_cognito && var.create_lex_bot ? <<-EOT
    # Frontend Environment Configuration
    VITE_AWS_REGION=${var.aws_region}
    VITE_COGNITO_IDENTITY_POOL_ID=${aws_cognito_identity_pool.main[0].id}
    VITE_LEX_BOT_ID=${aws_lexv2models_bot.tutor[0].id}
    VITE_LEX_BOT_ALIAS_ID=${aws_lexv2models_bot_alias.main[0].bot_alias_id}
    VITE_API_URL=http://${aws_lb.main.dns_name}
  EOT
  : "Lex or Cognito not created"
}

# -----------------------------------------------------------------------------
# Backend Configuration
# -----------------------------------------------------------------------------

output "backend_env_config" {
  description = "Environment variables for backend"
  value = <<-EOT
    # Backend Environment Configuration
    AWS_REGION=${var.aws_region}
    S3_BUCKET=${aws_s3_bucket.audio.bucket}
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL=${var.ollama_model}
    PORT=8000
  EOT
}
