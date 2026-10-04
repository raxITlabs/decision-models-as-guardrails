# Read at run time by goldrails_bench.bedrock_apply (terraform output -json), never copied into .env.
output "guardrails" {
  value = {
    topics    = { id = aws_bedrock_guardrail.topics.guardrail_id, version = aws_bedrock_guardrail_version.topics.version, topics = [for t in local.topics : t.name] }
    topics_e2 = { id = aws_bedrock_guardrail.topics_e2.guardrail_id, version = aws_bedrock_guardrail_version.topics_e2.version, topics = [for t in local.topics_e2 : t.name] }
    words     = { id = aws_bedrock_guardrail.words.guardrail_id, version = aws_bedrock_guardrail_version.words.version, words = local.words }
    grounding = { id = aws_bedrock_guardrail.grounding.guardrail_id, version = aws_bedrock_guardrail_version.grounding.version, thresholds = { grounding = var.grounding_threshold, relevance = var.relevance_threshold } }
    pii       = { id = aws_bedrock_guardrail.pii.guardrail_id, version = aws_bedrock_guardrail_version.pii.version, entities = var.pii_entities }
  }
}

output "region" {
  value = var.region
}
