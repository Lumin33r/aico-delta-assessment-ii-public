# =============================================================================
# Lambda Function for Lex Fulfillment
# =============================================================================

# -----------------------------------------------------------------------------
# Lambda Package
# -----------------------------------------------------------------------------

data "archive_file" "lex_fulfillment" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/lex_fulfillment"
  output_path = "${path.module}/dist/lex_fulfillment.zip"
}

# -----------------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------------

resource "aws_lambda_function" "lex_fulfillment" {
  filename         = data.archive_file.lex_fulfillment.output_path
  function_name    = "${local.name_prefix}-lex-fulfillment"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.lex_fulfillment.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      BACKEND_URL = "http://${aws_lb.main.dns_name}"
      LOG_LEVEL   = "INFO"
    }
  }

  # VPC configuration for backend access
  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = {
    Name = "${local.name_prefix}-lex-fulfillment"
  }
}

# Lambda permission for Lex
resource "aws_lambda_permission" "lex" {
  count = var.create_lex_bot ? 1 : 0

  statement_id  = "AllowLexInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lex_fulfillment.function_name
  principal     = "lexv2.amazonaws.com"
  source_arn    = "arn:aws:lex:${local.region}:${local.account_id}:bot-alias/${aws_lexv2models_bot.tutor[0].id}/*"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.lex_fulfillment.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${local.name_prefix}-lambda-logs"
  }
}
