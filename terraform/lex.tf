# =============================================================================
# Amazon Lex V2 Bot Configuration
# =============================================================================
# Creates a conversational bot for the AI Personal Tutor with:
# - WelcomeIntent: Greets users
# - CreateLessonPlan: Collects URL and creates lessons
# - StartLesson: Begins a specific lesson
# - HelpIntent: Provides assistance
# - FallbackIntent: Handles unrecognized input
# =============================================================================

# -----------------------------------------------------------------------------
# Lex Bot
# -----------------------------------------------------------------------------

resource "aws_lexv2models_bot" "tutor" {
  count = var.create_lex_bot ? 1 : 0

  name                        = var.lex_bot_name
  description                 = "AI Personal Tutor - Learn from any URL with podcast-style lessons"
  role_arn                    = aws_iam_role.lex_bot[0].arn
  idle_session_ttl_in_seconds = 300

  data_privacy {
    child_directed = false
  }

  tags = {
    Name = "${local.name_prefix}-lex-bot"
  }
}

# -----------------------------------------------------------------------------
# Bot Locale (English US)
# -----------------------------------------------------------------------------

resource "aws_lexv2models_bot_locale" "en_us" {
  count = var.create_lex_bot ? 1 : 0

  bot_id                           = aws_lexv2models_bot.tutor[0].id
  bot_version                      = "DRAFT"
  locale_id                        = var.lex_bot_locale
  n_lu_intent_confidence_threshold = 0.40

  voice_settings {
    voice_id = "Joanna"
    engine   = "neural"
  }
}

# -----------------------------------------------------------------------------
# Slot Types
# -----------------------------------------------------------------------------

resource "aws_lexv2models_slot_type" "lesson_number" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "LessonNumber"
  description = "Lesson number for selection"

  value_selection_setting {
    resolution_strategy = "TOP_RESOLUTION"
  }

  slot_type_values {
    slot_type_value {
      value = "1"
    }
    synonyms {
      value = "first"
    }
    synonyms {
      value = "one"
    }
  }

  slot_type_values {
    slot_type_value {
      value = "2"
    }
    synonyms {
      value = "second"
    }
    synonyms {
      value = "two"
    }
  }

  slot_type_values {
    slot_type_value {
      value = "3"
    }
    synonyms {
      value = "third"
    }
    synonyms {
      value = "three"
    }
  }
}

# -----------------------------------------------------------------------------
# Welcome Intent
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "welcome" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "WelcomeIntent"
  description = "Greets users and explains the service"

  sample_utterance {
    utterance = "hello"
  }
  sample_utterance {
    utterance = "hi"
  }
  sample_utterance {
    utterance = "hey"
  }
  sample_utterance {
    utterance = "start"
  }
  sample_utterance {
    utterance = "get started"
  }
  sample_utterance {
    utterance = "help me learn"
  }

  closing_setting {
    active = true
    closing_response {
      message_group {
        message {
          plain_text_message {
            value = "Welcome to AI Tutor! I'm here to help you learn from any web content. Just share a URL with me, and I'll create personalized podcast-style lessons with two AI hosts - Alex and Sam - who will explain the concepts in an engaging way. Ready to start? Just paste a URL!"
          }
        }
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Create Lesson Plan Intent
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "create_lesson" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "CreateLessonPlan"
  description = "Creates a lesson plan from a URL"

  sample_utterance {
    utterance = "create lessons from {SourceURL}"
  }
  sample_utterance {
    utterance = "I want to learn from {SourceURL}"
  }
  sample_utterance {
    utterance = "teach me about {SourceURL}"
  }
  sample_utterance {
    utterance = "make lessons from {SourceURL}"
  }
  sample_utterance {
    utterance = "{SourceURL}"
  }
  sample_utterance {
    utterance = "here's a URL {SourceURL}"
  }
  sample_utterance {
    utterance = "learn from this {SourceURL}"
  }

  fulfillment_code_hook {
    enabled = true
    active  = true
  }
}

# Source URL Slot
resource "aws_lexv2models_slot" "source_url" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  intent_id   = aws_lexv2models_intent.create_lesson[0].intent_id
  name        = "SourceURL"
  description = "URL to create lessons from"

  slot_type_id = "AMAZON.URL"

  value_elicitation_setting {
    slot_constraint = "Required"

    prompt_specification {
      max_retries                = 2
      allow_interrupt            = true
      message_selection_strategy = "Random"

      message_group {
        message {
          plain_text_message {
            value = "What URL would you like to learn from? Please paste the full web address."
          }
        }
      }

      message_group {
        message {
          plain_text_message {
            value = "I need a URL to create your lessons. What article, documentation, or webpage should I teach you about?"
          }
        }
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Start Lesson Intent
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "start_lesson" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "StartLesson"
  description = "Starts a specific lesson"

  sample_utterance {
    utterance = "start lesson {LessonNumber}"
  }
  sample_utterance {
    utterance = "play lesson {LessonNumber}"
  }
  sample_utterance {
    utterance = "begin lesson {LessonNumber}"
  }
  sample_utterance {
    utterance = "I want to hear lesson {LessonNumber}"
  }
  sample_utterance {
    utterance = "let's do lesson {LessonNumber}"
  }
  sample_utterance {
    utterance = "yes start"
  }
  sample_utterance {
    utterance = "yes"
  }
  sample_utterance {
    utterance = "start"
  }

  fulfillment_code_hook {
    enabled = true
    active  = true
  }
}

# Lesson Number Slot
resource "aws_lexv2models_slot" "lesson_number" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  intent_id   = aws_lexv2models_intent.start_lesson[0].intent_id
  name        = "LessonNumber"
  description = "Which lesson to start"

  slot_type_id = aws_lexv2models_slot_type.lesson_number[0].slot_type_id

  value_elicitation_setting {
    slot_constraint = "Required"

    default_value_specification {
      default_value_list {
        default_value = "1"
      }
    }

    prompt_specification {
      max_retries                = 2
      allow_interrupt            = true
      message_selection_strategy = "Random"

      message_group {
        message {
          plain_text_message {
            value = "Which lesson would you like to start? Say 1, 2, or 3."
          }
        }
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Help Intent
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "help" {
  count = var.create_lex_bot ? 1 : 0

  bot_id      = aws_lexv2models_bot.tutor[0].id
  bot_version = "DRAFT"
  locale_id   = aws_lexv2models_bot_locale.en_us[0].locale_id
  name        = "HelpIntent"
  description = "Provides help and instructions"

  sample_utterance {
    utterance = "help"
  }
  sample_utterance {
    utterance = "help me"
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

  closing_setting {
    active = true
    closing_response {
      message_group {
        message {
          plain_text_message {
            value = "Here's how I can help:\n\n1️⃣ Share a URL - Paste any webpage link and I'll create lessons from it\n2️⃣ Start a lesson - Say 'start lesson 1' to begin learning\n3️⃣ Ask questions - I'm here to help you understand the content\n\nThe lessons are presented as conversations between Alex (the expert) and Sam (the curious learner). Ready to try? Just paste a URL!"
          }
        }
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Fallback Intent
# -----------------------------------------------------------------------------

resource "aws_lexv2models_intent" "fallback" {
  count = var.create_lex_bot ? 1 : 0

  bot_id                  = aws_lexv2models_bot.tutor[0].id
  bot_version             = "DRAFT"
  locale_id               = aws_lexv2models_bot_locale.en_us[0].locale_id
  name                    = "FallbackIntent"
  description             = "Handles unrecognized input"
  parent_intent_signature = "AMAZON.FallbackIntent"

  closing_setting {
    active = true
    closing_response {
      message_group {
        message {
          plain_text_message {
            value = "I didn't quite catch that. You can share a URL to create lessons, say 'start lesson 1' to begin learning, or say 'help' for more options."
          }
        }
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Bot Version and Alias
# -----------------------------------------------------------------------------

resource "aws_lexv2models_bot_version" "main" {
  count = var.create_lex_bot ? 1 : 0

  bot_id = aws_lexv2models_bot.tutor[0].id

  locale_specification = {
    (var.lex_bot_locale) = {
      source_bot_version = "DRAFT"
    }
  }

  depends_on = [
    aws_lexv2models_intent.welcome,
    aws_lexv2models_intent.create_lesson,
    aws_lexv2models_intent.start_lesson,
    aws_lexv2models_intent.help,
    aws_lexv2models_intent.fallback,
    aws_lexv2models_slot.source_url,
    aws_lexv2models_slot.lesson_number
  ]
}

resource "aws_lexv2models_bot_alias" "main" {
  count = var.create_lex_bot ? 1 : 0

  bot_id         = aws_lexv2models_bot.tutor[0].id
  bot_version    = aws_lexv2models_bot_version.main[0].bot_version
  bot_alias_name = "production"

  bot_alias_locale_settings {
    locale_id = var.lex_bot_locale

    bot_alias_locale_setting {
      enabled = true

      code_hook_specification {
        lambda_code_hook {
          lambda_arn                  = aws_lambda_function.lex_fulfillment.arn
          code_hook_interface_version = "1.0"
        }
      }
    }
  }

  tags = {
    Name = "${local.name_prefix}-lex-alias"
  }
}
