# Amazon Bedrock Guardrails: feature and capability inventory

Verified against the live AWS docs on 18 September 2026. This is the "what does the incumbent actually do" list that 05 and 06 should be read against. Two things changed since 05 was written and both matter: AWS shipped a resourceless, score-returning API (InvokeGuardrailChecks, June 2026) and put guardrails inside AgentCore's Cedar policies (June 2026). Bedrock is no longer purely content-centric, and it now returns numeric scores. Section 10 covers what that does to our pitch.

## 1. Policy types (the seven safeguards)

| Policy | What it does | Config knobs | Actions |
|---|---|---|---|
| Content filters | Classifies text and images into Hate, Insults, Sexual, Violence, Misconduct, Prompt Attack. Model returns a confidence bucket per category (NONE, LOW, MEDIUM, HIGH). | Strength per category (NONE/LOW/MEDIUM/HIGH), separately for input and output. Modalities TEXT and/or IMAGE. Tier (Classic or Standard). | BLOCK or NONE (detect only) |
| Prompt attacks | A category inside content filters. Subtypes: Jailbreak, Prompt Injection, Prompt Leakage (Standard tier only). Input only. Requires input tagging on InvokeModel or nothing gets checked. Does not evaluate tool results or tool definitions. | Strength, tier | BLOCK or NONE |
| Denied topics | Natural-language topic definitions. Up to 30 topics. Definition 200 chars (Classic) or 1,000 chars (Standard). Up to 5 sample phrases of 100 chars each. Docs warn topic ordering can change outcomes. | Per-topic input/output enable and action, tier | BLOCK or NONE |
| Word filters | Exact-match. Managed profanity list plus up to 10,000 custom words or phrases of up to three words. Console accepts .txt, .csv, or S3 upload. | Per-word input/output enable and action | BLOCK or NONE |
| Sensitive information filters | Probabilistic, context-dependent PII detection over 31 built-in entity types, plus custom regex (no lookarounds, 500-char pattern). Works inside code (variable names, string literals, comments). Does not evaluate tool call arguments, tool results, or tool definitions. Masking replaces with `{NAME}`, `{EMAIL}` etc. Trace still contains the raw match. | Per-entity and per-regex input/output enable and action | BLOCK, ANONYMIZE, or NONE |
| Contextual grounding checks | Output only. Two scores, grounding (is the response supported by the source) and relevance (does it answer the query), each thresholded 0 to 0.99. Needs source, query, and response tagged. Limits: source 100k chars, query 1k, response 5k. Summarisation, paraphrase, and QA only; conversational QA unsupported. | Grounding threshold, relevance threshold | BLOCK or NONE |
| Automated Reasoning checks | Formal-logic validation of a response against rules extracted from a source document (5 MB, 50k chars). Uses LLMs to translate text to SMT-LIB logic, then a solver to prove. Returns findings: VALID, INVALID, SATISFIABLE, IMPOSSIBLE, TRANSLATION_AMBIGUOUS, TOO_COMPLEX, NO_TRANSLATIONS, each with premises, claims, supporting or contradicting rules, and a translation confidence. Detect mode only. English only. No streaming. Not allowed in cross-account enforcement. | Policy version, confidence threshold | Findings only, never blocks |

### The 31 PII entity types

General: ADDRESS, AGE, NAME, EMAIL, PHONE, USERNAME, PASSWORD, DRIVER_ID, LICENSE_PLATE, VEHICLE_IDENTIFICATION_NUMBER.
Finance: CREDIT_DEBIT_CARD_CVV, CREDIT_DEBIT_CARD_EXPIRY, CREDIT_DEBIT_CARD_NUMBER, PIN, INTERNATIONAL_BANK_ACCOUNT_NUMBER, SWIFT_CODE.
IT: IP_ADDRESS, MAC_ADDRESS, URL, AWS_ACCESS_KEY, AWS_SECRET_KEY.
USA: US_BANK_ACCOUNT_NUMBER, US_BANK_ROUTING_NUMBER, US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER, US_PASSPORT_NUMBER, US_SOCIAL_SECURITY_NUMBER.
Canada: CA_HEALTH_NUMBER, CA_SOCIAL_INSURANCE_NUMBER.
UK: UK_NATIONAL_HEALTH_SERVICE_NUMBER, UK_NATIONAL_INSURANCE_NUMBER, UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER.

### Filter strength semantics

Strength is a threshold on the classifier's confidence bucket. LOW strength blocks only HIGH-confidence detections. MEDIUM blocks HIGH and MEDIUM. HIGH blocks HIGH, MEDIUM, and LOW. There are four buckets, not a continuous score, on the ApplyGuardrail path.

## 2. Safeguard tiers

| | Standard | Classic |
|---|---|---|
| Applies to | Content filters, prompt attacks, denied topics | Same |
| Languages | Roughly 80 for content filters, 100 for denied topics, with a subset "optimized" (English, French, Spanish, German, Arabic, Chinese, Hindi, Japanese, Korean, and others) | English, French, Spanish |
| Prompt leakage | Yes | No |
| Code domain | Harmful content and denied topics detected inside comments, identifiers, and string literals | No |
| Cross-Region inference | Required | Not supported |
| Denied topic definition length | 1,000 chars | 200 chars |

PII filters support 17 languages regardless of tier. Contextual grounding and word filters: English, French, Spanish only. Automated Reasoning: English only.

## 3. Modalities

- Text: all policies.
- Images: content filters only (all six categories including prompt attack). PNG and JPEG, 4 MB each, 8000x8000 max, 20 images per request, 25 images per second account-wide. Priced per image.
- Nothing for audio or video.

## 4. Handling and modes

- Block: replace with configured `blockedInputMessaging` or `blockedOutputsMessaging`.
- Mask: PII only. Not supported in asynchronous streaming.
- Detect (action NONE): evaluate and report in trace, take no action. This is how you tune without affecting users.
- Input and output are enabled and configured independently per policy.
- Layered enforcement: if an org-level, account-level, and request-level guardrail all apply, all three run and the most restrictive wins.

## 5. APIs and integration points

| Path | Notes |
|---|---|
| InvokeModel / InvokeModelWithResponseStream | Guardrail id and version in headers. Input tagging via `<amazon-bedrock-guardrails-guardContent_SUFFIX>` with a per-request random suffix (docs call out injection risk with static suffixes). Untagged content is skipped when any tag is present. |
| Converse / ConverseStream | `guardrailConfig` in body. Content blocks carry `guardContent` with qualifiers `guard_content`, `grounding_source`, `query`. |
| ApplyGuardrail | Model-agnostic. `source: INPUT` or `OUTPUT`, content blocks, optional `outputScope: FULL` to include non-detections. Returns `action: NONE | GUARDRAIL_INTERVENED`, `outputs`, per-policy `assessments`, `usage` in text units, `guardrailCoverage`, and `guardrailProcessingLatency`. This is the shape 06 clones. |
| InvokeGuardrailChecks (new, June 2026) | Resourceless. No guardrail id. You pass `messages` (roles system/user/assistant, up to 10 text blocks each) and a `checks` object naming which of contentFilter, promptAttack, sensitiveInformation to run, with categories or entities inline. Detect only. Returns a `severityScore` per category in discrete steps {0, 0.2, 0.4, 0.6, 0.8, 1.0} for content and prompt attack, and a `confidenceScore` plus character offsets for each PII hit. Prompt attack is its own check here, split into JAILBREAK, PROMPT_INJECTION, PROMPT_LEAKAGE. 1,500 requests per minute. Seven regions. Docs explicitly position it for "before executing a tool the model wants to call, after a tool returns a result". Denied topics, word filters, grounding, and Automated Reasoning are not available on this path. |
| Bedrock Agents | `guardrailConfiguration` on CreateAgent / UpdateAgent. |
| Knowledge Bases | On RetrieveAndGenerate. |
| Flows | On prompt nodes and knowledge base nodes. |
| AgentCore Policy (new, June 2026) | Cedar policies at the AgentCore Gateway call InvokeGuardrailChecks and compare scores. `forbid ... when guardrails { BedrockGuardrails::PromptAttack(["PROMPT_INJECTION"], [context.input.prompt])["PROMPT_INJECTION"].confidenceScore.greaterThan(decimal("0.6")) }` denies a tool call. A new `suppressOutput` effect evaluates a tool's return value and drops it, for example on a US_SOCIAL_SECURITY_NUMBER hit. Aggregations `maxConfidenceScore()`, `minConfidenceScore()`, `count()`. Default thresholds 0.2 content, 0.4 prompt attack, 0.2 PII. Runs on MCP targets (`tools/call`), HTTP runtime targets, and inference targets. Cannot mix guardrail conditions with ordinary Cedar conditions in the same policy. Has a LOG_ONLY mode for threshold calibration. |
| Cross-account enforcement (GA April 2026) | AWS Organizations `BEDROCK_POLICY` type. Management account pins a guardrail ARN and version; it applies to every InvokeModel/Converse call in the targeted OUs or accounts. Model include/exclude lists. `selective` vs `comprehensive` controls decide whether caller tagging is honoured. Account-level variant via `PutEnforcedGuardrailConfiguration`. Automated Reasoning excluded. |

## 6. Streaming

Synchronous mode buffers chunks until the scan completes, adding latency. Asynchronous mode emits chunks immediately and blocks later chunks once a violation is found, so users can see bad content before the cut. PII masking does not work in asynchronous mode. Contextual grounding on a stream can mark a response irrelevant only after it has fully streamed.

## 7. Lifecycle and operations

- Working draft plus immutable numbered versions. Versions are not resources and have no ARN.
- Console test window: pick a version, pick a model or none, run a prompt, view trace per policy for prompt and response.
- Trace: `X-Amzn-Bedrock-Trace: ENABLED` or `trace: enabled_full`. Returns per-policy assessments, latency, and text-unit usage.
- Blocked content appears as plain text in model invocation logs if logging is on. Masked PII is not masked in CloudWatch logs.
- CloudWatch metrics for interventions, CloudTrail for ApplyGuardrail calls.
- KMS customer-managed keys, resource tags, resource-based policies for sharing a guardrail across accounts.
- AWS updates the underlying classifier models without notice; docs tell you to keep re-testing.

## 8. Pricing (list, per 1,000 text units, one unit = 1,000 characters)

| Policy | ApplyGuardrail / inference path | InvokeGuardrailChecks |
|---|---|---|
| Content filters | $0.15 | $0.07 |
| Prompt attack | included in content filters | $0.08 |
| Denied topics | $0.15 | n/a |
| Sensitive information (ML) | $0.10 | $0.10 |
| Sensitive information (regex) | free | n/a |
| Word filters | free | n/a |
| Contextual grounding | $0.10 | n/a |
| Automated Reasoning | $0.17 per policy | n/a |
| Image content filters | $0.00075 per image | n/a |

Same price on Classic and Standard. Cross-Region inference is free. A blocked input still bills the guardrail but not the model. If three enforced guardrails apply to one call, you pay for all three.

## 9. Known gaps, from AWS's own docs

- Content filters, prompt attack, and PII filters skip `toolUse.input`, `toolResult`, and `toolSpec` on the Converse path. PII the model writes into a tool argument is neither masked nor blocked. AgentCore Policy is the workaround, and it needs the Gateway.
- Prompt attack detection needs input tags on InvokeModel or it silently does nothing.
- Denied topic results depend on topic order.
- Automated Reasoning has no injection protection, no off-topic detection, no streaming, English only, and can time out on non-linear arithmetic.
- Scores on the classic path are four buckets. Scores on InvokeGuardrailChecks are six discrete steps. Neither is a calibrated probability, and AWS says severity "is a property of the content, not the certainty of the model".
- No custom categories for content filters. You get five plus prompt attack.
- No per-request policy change on ApplyGuardrail; you swap guardrail ids or versions.

## 10. What this does to 05 and 06

- The "Bedrock does not check what the agent is about to do" line in 05 is now only half true. AgentCore Policy checks tool inputs and outputs with Cedar, and uses the same Cedar-plus-classifier split we proposed. Their limits: three safeguards only, discrete scores, Gateway required, and the Cedar policy cannot combine a guardrail score with ordinary attribute conditions in one statement. That last one is where "Jev extracts typed facts, Cedar decides on facts plus scores" is still differentiated.
- "Bedrock lacks confidence" in 05 needs rewording. It now returns numeric scores on the new API. The honest claim is calibration and question flexibility: Jev returns a probability for any question you write, not a six-step severity for five fixed categories.
- The cost comparison should use InvokeGuardrailChecks prices, since that is the path a buyer would compare against. Content plus prompt attack plus PII is $0.25 per 1,000 text units, roughly $1 per million characters. Jev at $0.042 per million tokens is still an order of magnitude cheaper on paper.
- The ApplyGuardrail clone in 06 should also offer an InvokeGuardrailChecks-shaped endpoint. It is the closer match to "Jev proposes, code decides" and it is what AgentCore calls under the hood.
- Denied topics, grounding, and word filters are still absent from the agentic path on Bedrock. That is a concrete gap we cover with one question set.

## Sources

- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-tiers.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-supported-languages.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-content-filters.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-prompt-attack.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-denied-topics.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-word-filters.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-automated-reasoning-checks.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/automated-reasoning-checks-concepts.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-code-domain.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-harmful-content-handling-options.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-streaming.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-tagging.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-independent-api.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-invoke-guardrail-checks.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-invoke-guardrail-checks-concepts.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-invoke-guardrail-checks-scores.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-invoke-guardrail-checks-quotas.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-enforcements.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-cross-region.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-test.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-mmfilter.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-guardrails-in-policies.html
- https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-bedrock-guardrails-api-ai/
- https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-bedrock-agentcore-policy-guardrails-generally-available/
- https://aws.amazon.com/about-aws/whats-new/2026/04/bedrock-guardrails-cross-account-safeguards/
- https://aws.amazon.com/bedrock/pricing/
