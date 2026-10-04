# One guardrail per suite that needs ApplyGuardrail (denied topics, word filters, grounding, PII masking), each with a
# numbered version, so a run can pin exactly what it was scored against. InvokeGuardrailChecks needs none of this.

locals {
  blocked_in  = "Blocked by Gold Rails benchmark guardrail (input)."
  blocked_out = "Blocked by Gold Rails benchmark guardrail (output)."
}

resource "aws_bedrock_guardrail" "topics" {
  name                      = "gold-rails-${var.env}-topics"
  description               = "Gold Rails denied-topics suite"
  blocked_input_messaging   = local.blocked_in
  blocked_outputs_messaging = local.blocked_out

  topic_policy_config {
    dynamic "topics_config" {
      for_each = local.topics
      content {
        name       = topics_config.value.name
        definition = topics_config.value.definition
        examples   = topics_config.value.examples
        type       = "DENY"
      }
    }
  }
}

resource "aws_bedrock_guardrail" "topics_e2" {
  name                      = "gold-rails-${var.env}-topics-e2"
  description               = "Gold Rails denied-topics suite, edition 2 (8 topics)"
  blocked_input_messaging   = local.blocked_in
  blocked_outputs_messaging = local.blocked_out

  topic_policy_config {
    dynamic "topics_config" {
      for_each = local.topics_e2
      content {
        name       = topics_config.value.name
        definition = topics_config.value.definition
        examples   = topics_config.value.examples
        type       = "DENY"
      }
    }
  }
}

resource "aws_bedrock_guardrail" "words" {
  name                      = "gold-rails-${var.env}-words"
  description               = "Gold Rails word-filters suite"
  blocked_input_messaging   = local.blocked_in
  blocked_outputs_messaging = local.blocked_out

  word_policy_config {
    managed_word_lists_config {
      type = "PROFANITY"
    }
    dynamic "words_config" {
      for_each = local.words
      content {
        text = words_config.value
      }
    }
  }
}

resource "aws_bedrock_guardrail" "grounding" {
  name                      = "gold-rails-${var.env}-grounding"
  description               = "Gold Rails contextual grounding and relevance suite"
  blocked_input_messaging   = local.blocked_in
  blocked_outputs_messaging = local.blocked_out

  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = var.grounding_threshold
    }
    filters_config {
      type      = "RELEVANCE"
      threshold = var.relevance_threshold
    }
  }
}

resource "aws_bedrock_guardrail" "pii" {
  name                      = "gold-rails-${var.env}-pii-mask"
  description               = "Gold Rails sensitive-information masking study"
  blocked_input_messaging   = local.blocked_in
  blocked_outputs_messaging = local.blocked_out

  sensitive_information_policy_config {
    dynamic "pii_entities_config" {
      for_each = var.pii_entities
      content {
        type   = pii_entities_config.value
        action = "ANONYMIZE"
      }
    }
  }
}

resource "aws_bedrock_guardrail_version" "topics" {
  guardrail_arn = aws_bedrock_guardrail.topics.guardrail_arn
  description   = "pinned for runs"
}
resource "aws_bedrock_guardrail_version" "topics_e2" {
  guardrail_arn = aws_bedrock_guardrail.topics_e2.guardrail_arn
  description   = "pinned for edition 2 runs"
}
resource "aws_bedrock_guardrail_version" "words" {
  guardrail_arn = aws_bedrock_guardrail.words.guardrail_arn
  description   = "pinned for runs"
}
resource "aws_bedrock_guardrail_version" "grounding" {
  guardrail_arn = aws_bedrock_guardrail.grounding.guardrail_arn
  description   = "pinned for runs"
}
resource "aws_bedrock_guardrail_version" "pii" {
  guardrail_arn = aws_bedrock_guardrail.pii.guardrail_arn
  description   = "pinned for runs"
}
