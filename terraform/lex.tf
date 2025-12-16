# =============================================================================
# Amazon Lex V2 Bot Configuration
# =============================================================================
# Creates a conversational bot for the AI Personal Tutor
# Handles: Welcome, URL collection, lesson navigation, help
# =============================================================================

# -----------------------------------------------------------------------------
# Lex Bot
# -----------------------------------------------------------------------------

resource "aws_lexv2models_bot" "tutor" {
  count = var.create_lex_bot ? 1 : 0

  name                        = "${var.project_name}-${var.environment}-tutor-bot"
  description                 = "AI Personal Tutor - Conversational interface for learning"
  role_arn                    = aws_iam_role.lex[0].arn
  idle_session_ttl_in_seconds = 300

  data_privacy {
    child_directed = false
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-tutor-bot"
  })
}

# -----------------------------------------------------------------------------
# Bot Locale (English US)
# -----------------------------------------------------------------------------

resource "aws_lexv2models_bot_locale" "en_us" {
  count = var.create_lex_bot ? 1 : 0

  bot_id                           = aws_lexv2models_bot.tutor[0].id
  bot_version                      = "DRAFT"
  locale_id                        = "en_US"
  n_lu_intent_confidence_threshold = 0.70

  voice_settings {
    voice_id = "Joanna"
    engine   = "neural"
  }
}

# -----------------------------------------------------------------------------
# Intent: Welcome
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "welcome" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "WelcomeIntent"
  description = "Greets the user and explains the tutor"

  sample_utterance {
    utterance = "hello"
  }
  sample_utterance {
    utterance = "hi"
  }
  sample_utterance {
    utterance = "hey"
  }
  # Note: "start" utterance moved to StartLessonIntent to avoid conflict
  sample_utterance {
    utterance = "help me learn"
  }
  sample_utterance {
    utterance = "I want to learn"
  }
  sample_utterance {
    utterance = "good morning"
  }
  sample_utterance {
    utterance = "good afternoon"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# Intent: Provide URL
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "provide_url" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "ProvideURLIntent"
  description = "User provides a URL to learn from"

  # Note: Utterances without slot references until SourceURL slot is created manually
  sample_utterance {
    utterance = "use this url"
  }
  sample_utterance {
    utterance = "learn from this"
  }
  sample_utterance {
    utterance = "here is a link"
  }
  sample_utterance {
    utterance = "I want to learn from this"
  }
  sample_utterance {
    utterance = "teach me from this"
  }
  sample_utterance {
    utterance = "create lessons from this"
  }
  sample_utterance {
    utterance = "use this"
  }
  sample_utterance {
    utterance = "provide url"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# DISABLED: aws_lexv2models_slot.source_url
# Due to AWS Terraform provider bug with prompt_attempts_specification
# Create this slot manually in AWS Console after deployment:
#   - Bot: AI Personal Tutor
#   - Intent: ProvideURLIntent
#   - Slot Name: SourceURL
#   - Slot Type: AMAZON.URL
#   - Constraint: Required
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Intent: Start Lesson
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "start_lesson" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "StartLessonIntent"
  description = "Start a specific lesson"

  # Note: Utterances without slot references until LessonNum slot is created manually
  sample_utterance {
    utterance = "start lesson"
  }
  sample_utterance {
    utterance = "play lesson"
  }
  sample_utterance {
    utterance = "begin lesson"
  }
  sample_utterance {
    utterance = "go to lesson"
  }
  sample_utterance {
    utterance = "start"
  }
  sample_utterance {
    utterance = "begin"
  }
  sample_utterance {
    utterance = "play"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# Slot: Lesson Number (for StartLesson intent)
# NOTE: Disabled due to AWS Terraform provider bug with prompt_attempts_specification
# Create this slot manually in AWS Console after deployment
# -----------------------------------------------------------------------------

# DISABLED: aws_lexv2models_slot.lesson_num
# Due to AWS Terraform provider bug with prompt_attempts_specification
# Create this slot manually in AWS Console after deployment:
#   - Bot: AI Personal Tutor
#   - Intent: StartLessonIntent
#   - Slot Name: LessonNum
#   - Slot Type: AMAZON.Number
#   - Constraint: Optional
#   - Default Value: 1
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Intent: Next Lesson
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "next_lesson" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "NextLessonIntent"
  description = "Continue to the next lesson"

  sample_utterance {
    utterance = "next"
  }
  sample_utterance {
    utterance = "next lesson"
  }
  sample_utterance {
    utterance = "continue"
  }
  sample_utterance {
    utterance = "keep going"
  }
  sample_utterance {
    utterance = "what's next"
  }
  sample_utterance {
    utterance = "move on"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# Intent: Repeat Lesson
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "repeat_lesson" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "RepeatLessonIntent"
  description = "Repeat the current lesson"

  sample_utterance {
    utterance = "repeat"
  }
  sample_utterance {
    utterance = "play again"
  }
  sample_utterance {
    utterance = "repeat lesson"
  }
  sample_utterance {
    utterance = "say that again"
  }
  sample_utterance {
    utterance = "one more time"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# Intent: Get Progress
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "get_progress" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "GetProgressIntent"
  description = "Check learning progress"

  sample_utterance {
    utterance = "how am I doing"
  }
  sample_utterance {
    utterance = "show progress"
  }
  sample_utterance {
    utterance = "my progress"
  }
  sample_utterance {
    utterance = "what have I learned"
  }
  sample_utterance {
    utterance = "status"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# Intent: Get Help (renamed to avoid conflict with built-in HelpIntent)
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "get_help" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "GetHelpIntent"
  description = "Provide help and instructions"

  sample_utterance {
    utterance = "help"
  }
  sample_utterance {
    utterance = "what can you do"
  }
  sample_utterance {
    utterance = "how does this work"
  }
  sample_utterance {
    utterance = "instructions"
  }
  sample_utterance {
    utterance = "I'm confused"
  }
  sample_utterance {
    utterance = "what should I do"
  }

  fulfillment_code_hook {
    enabled = true
  }
}

# -----------------------------------------------------------------------------
# Note: FallbackIntent
# -----------------------------------------------------------------------------
# FallbackIntent is automatically created by Lex when creating a bot locale.
# We don't need to create it manually - attempting to do so causes:
# "Intent with name FallbackIntent already exists"
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Bot Version
# -----------------------------------------------------------------------------

resource "aws_lexv2models_bot_version" "main" {
  count = var.create_lex_bot ? 1 : 0

  bot_id = aws_lexv2models_bot.tutor[0].id

  locale_specification = {
    "en_US" = {
      source_bot_version = "DRAFT"
    }
  }

  depends_on = [
    aws_lexv2models_intent.welcome,
    aws_lexv2models_intent.provide_url,
    aws_lexv2models_intent.start_lesson,
    aws_lexv2models_intent.next_lesson,
    aws_lexv2models_intent.repeat_lesson,
    aws_lexv2models_intent.get_progress,
    aws_lexv2models_intent.get_help
    # NOTE: Slots disabled due to AWS provider bug
    # aws_lexv2models_slot.source_url,
    # aws_lexv2models_slot.lesson_num
  ]
}

# -----------------------------------------------------------------------------
# IAM Role for Lex Bot
# -----------------------------------------------------------------------------

resource "aws_iam_role" "lex" {
  count = var.create_lex_bot ? 1 : 0

  name = "${var.project_name}-${var.environment}-lex-role"

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

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-lex-role"
  })
}

resource "aws_iam_role_policy" "lex_runtime" {
  count = var.create_lex_bot ? 1 : 0

  name = "${var.project_name}-${var.environment}-lex-runtime"
  role = aws_iam_role.lex[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "polly:SynthesizeSpeech",
          "comprehend:DetectSentiment"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Note: Lambda Permission for Lex is defined in lambda.tf
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Note: Bot Alias
# -----------------------------------------------------------------------------
# The aws_lexv2models_bot_alias resource is not yet available in the AWS provider.
# Bot aliases must be created manually in the AWS Console or via AWS CLI:
#
# aws lexv2-models create-bot-alias \
#   --bot-alias-name "prod" \
#   --bot-id "<bot-id>" \
#   --bot-version "<version-number>" \
#   --bot-alias-locale-settings '{"en_US":{"enabled":true,"codeHookSpecification":{"lambdaCodeHook":{"lambdaARN":"<lambda-arn>","codeHookInterfaceVersion":"1.0"}}}}'
#
# After creating the alias, update the frontend environment with the alias ID.
