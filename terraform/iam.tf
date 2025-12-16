# =============================================================================
# IAM Roles and Policies
# =============================================================================

# -----------------------------------------------------------------------------
# EC2 Instance Role (Backend)
# -----------------------------------------------------------------------------

resource "aws_iam_role" "backend_ec2" {
  name = "${local.name_prefix}-backend-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_instance_profile" "backend" {
  name = "${local.name_prefix}-backend-profile"
  role = aws_iam_role.backend_ec2.name
}

# Polly access for TTS
resource "aws_iam_role_policy" "backend_polly" {
  name = "${local.name_prefix}-polly-policy"
  role = aws_iam_role.backend_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech",
          "polly:DescribeVoices",
          "polly:GetLexicon",
          "polly:ListLexicons"
        ]
        Resource = "*"
      }
    ]
  })
}

# S3 access for audio storage
resource "aws_iam_role_policy" "backend_s3" {
  name = "${local.name_prefix}-s3-policy"
  role = aws_iam_role.backend_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.audio.arn,
          "${aws_s3_bucket.audio.arn}/*"
        ]
      }
    ]
  })
}

# CloudWatch Logs
resource "aws_iam_role_policy" "backend_cloudwatch" {
  name = "${local.name_prefix}-cloudwatch-policy"
  role = aws_iam_role.backend_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# SSM for parameter store access
resource "aws_iam_role_policy_attachment" "backend_ssm" {
  role       = aws_iam_role.backend_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# -----------------------------------------------------------------------------
# Lambda Execution Role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda basic execution
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda VPC access
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda Lex integration
resource "aws_iam_role_policy" "lambda_lex" {
  name = "${local.name_prefix}-lambda-lex-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lex:RecognizeText",
          "lex:RecognizeUtterance",
          "lex:DeleteSession",
          "lex:GetSession",
          "lex:PutSession"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lex Bot Role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lex_bot" {
  count = var.create_lex_bot ? 1 : 0
  name  = "${local.name_prefix}-lex-bot-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lexv2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lex_bot" {
  count = var.create_lex_bot ? 1 : 0
  name  = "${local.name_prefix}-lex-bot-policy"
  role  = aws_iam_role.lex_bot[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.lex_fulfillment.arn
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Cognito Unauthenticated Role
# -----------------------------------------------------------------------------

resource "aws_iam_role" "cognito_unauth" {
  count = var.create_cognito ? 1 : 0
  name  = "${local.name_prefix}-cognito-unauth-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main[0].id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "unauthenticated"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "cognito_unauth_lex" {
  count = var.create_cognito ? 1 : 0
  name  = "${local.name_prefix}-cognito-lex-policy"
  role  = aws_iam_role.cognito_unauth[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lex:RecognizeText",
          "lex:RecognizeUtterance",
          "lex:DeleteSession",
          "lex:GetSession",
          "lex:PutSession"
        ]
        Resource = var.create_lex_bot ? [
          "arn:aws:lex:${local.region}:${local.account_id}:bot-alias/${aws_lexv2models_bot.tutor[0].id}/*"
        ] : ["*"]
      }
    ]
  })
}
