variable "region" {
  description = "Bedrock Guardrails region. Contextual grounding and word filters are English-only and regional."
  type        = string
  default     = "us-east-1"
}

variable "profile" {
  description = "AWS CLI profile. Anyone cloning the repo sets their own; nothing account-specific is committed."
  type        = string
  default     = null
}

variable "env" {
  type    = string
  default = "dev"
}

# Denied topics: the suite's topic definitions, verbatim. Bedrock limits: 30 topics, definition 200 chars on the
# Classic tier (1,000 on Standard), up to 5 examples of 100 chars each.
# Denied topics and word filters are read from the suite files so the guardrail and the question sets can never drift.
variable "topics" {
  type = list(object({
    name       = string
    definition = string
    examples   = list(string)
  }))
  default = null
}

variable "words" {
  type    = list(string)
  default = null
}

locals {
  topics = var.topics != null ? var.topics : jsondecode(file("${path.module}/../../benchmark/suites/denied_topics/topics.json")).topics
  # Edition 2 (owner ruling 1): all 8 topics, in a separate guardrail so the v1 topics guardrail stays as it was.
  topics_e2 = jsondecode(file("${path.module}/../../benchmark/suites/denied_topics/topics-e2.json")).topics
  words  = var.words != null ? var.words : jsondecode(file("${path.module}/../../benchmark/suites/word_filters/words.json")).words
}

variable "grounding_threshold" {
  type    = number
  default = 0.5
}

variable "relevance_threshold" {
  type    = number
  default = 0.5
}

# Sensitive information for the masking study: every type the shared PII task uses, anonymised rather than blocked,
# so ApplyGuardrail returns the masked text.
variable "pii_entities" {
  type    = list(string)
  default = ["NAME", "EMAIL", "PHONE", "ADDRESS", "USERNAME", "PASSWORD", "IP_ADDRESS", "DRIVER_ID", "US_SOCIAL_SECURITY_NUMBER"]
}
