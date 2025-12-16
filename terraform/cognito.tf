# =============================================================================
# Cognito Identity Pool for Frontend Lex Access
# =============================================================================
# Provides unauthenticated access to Lex from the browser
# =============================================================================

resource "aws_cognito_identity_pool" "main" {
  count = var.create_cognito ? 1 : 0

  identity_pool_name               = "${local.name_prefix}-identity-pool"
  allow_unauthenticated_identities = true
  allow_classic_flow               = false

  tags = {
    Name = "${local.name_prefix}-identity-pool"
  }
}

# Attach roles to identity pool
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  count = var.create_cognito ? 1 : 0

  identity_pool_id = aws_cognito_identity_pool.main[0].id

  roles = {
    "unauthenticated" = aws_iam_role.cognito_unauth[0].arn
  }
}
