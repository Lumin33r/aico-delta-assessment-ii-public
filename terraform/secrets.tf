# =============================================================================
# AWS Secrets Manager Configuration
# =============================================================================
# Secure storage for database credentials
# =============================================================================

# -----------------------------------------------------------------------------
# Random Password Generator
# -----------------------------------------------------------------------------

resource "random_password" "postgres" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# -----------------------------------------------------------------------------
# Secrets Manager Secret
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret" "postgres" {
  name                    = "${var.project_name}-${var.environment}/postgres-credentials"
  description             = "PostgreSQL credentials for AI Tutor application"
  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-postgres-secret"
  })
}

# -----------------------------------------------------------------------------
# Secret Version (Contains Actual Credentials)
# -----------------------------------------------------------------------------

resource "aws_secretsmanager_secret_version" "postgres" {
  secret_id = aws_secretsmanager_secret.postgres.id
  secret_string = jsonencode({
    username = var.postgres_username
    password = random_password.postgres.result
    database = var.postgres_database
    port     = 5432
  })
}

# -----------------------------------------------------------------------------
# Outputs for Reference
# -----------------------------------------------------------------------------

output "postgres_secret_arn" {
  value       = aws_secretsmanager_secret.postgres.arn
  description = "ARN of the PostgreSQL credentials secret"
}

output "postgres_secret_name" {
  value       = aws_secretsmanager_secret.postgres.name
  description = "Name of the PostgreSQL credentials secret"
}
