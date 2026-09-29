# 18. Benchmark structure: six suites, one harness, one results format

> Superseded in part: [doc 19](19-evaluation-contract-v1.md) (draft, pending sign-off) replaces the plot's quality axis, the composite and missing-suite rules, and the placement of bias, masking and relevance.

22 September 2026. This replaces the single-question framing the pilot drifted into. The core question, from
VISION.md, sharpened: **across Bedrock Guardrails' six comparable capabilities, how competitive are decision-model
implementations on quality, cost and latency, and with what limitations?**

## Scope

Six suites. Each is a capability Bedrock sells and a decision model can plausibly attempt.

| Suite | Success means | Bedrock path |
|---|---|---|
| Content | Detect the specified violation while passing permitted content, including benign text that sounds dangerous | InvokeGuardrailChecks content filter; ApplyGuardrail content policy |
| Prompt attacks | Detect jailbreak, injection and leakage while passing legitimate instructions | InvokeGuardrailChecks prompt attack; ApplyGuardrail with input tagging |
| Denied topics | Apply a supplied topic definition, including its stated exceptions | ApplyGuardrail topic policy (not on InvokeGuardrailChecks) |
| Word filters | Match configured terms under the declared matching rules | ApplyGuardrail word policy |
| Sensitive information | Two separate results: (a) detection of the right entity types, (b) a complete masking implementation that redacts the right spans | InvokeGuardrailChecks returns detections with offsets and does not redact; ApplyGuardrail masks, blocks, and runs regex |
| Grounding and relevance | Flag claims a source does not support, and replies that do not answer the query | ApplyGuardrail contextual grounding, output side |

**Explicitly excluded: Automated Reasoning.** Formal verification against extracted rules is a different capability
from a decision model's typed answer, and agreement with a solver on test cases would not give a model the solver's
guarantees. Images, non-English languages, streaming, and deployment controls (enforcement policies, cross-account
pinning) are out of scope for v1 and listed as coverage differences.

Bias and agent-action tests from the earlier plan stay as extensions after the six suites exist.

## Current coverage, honestly (updated 22 September 2026, evening)

| Suite | Cases | Decision-model questions | Bedrock path | Smoke run |
|---|---|---|---|---|
| Content | Aegis 2.0, AILuminate demo, OpenAI moderation, OR-Bench, JBB goals | v1/v2 f1-bedrock5, f1-ailuminate12 | InvokeGuardrailChecks content | 7 arms, 20-row pilot |
| Prompt attacks | deepset, Gandalf, JBB attack artifacts, authored controls | v1 f2-attacks | InvokeGuardrailChecks promptAttack | 7 arms (Laya failed to connect) |
| Denied topics | authored cases against topics.json (BARRED planned) | v1 f3-topics (definitions verbatim) | ApplyGuardrail topic policy, versioned | Jev, Bedrock |
| Word filters | deterministic cases from words.json | v1 f4-words | ApplyGuardrail word policy, versioned; regex baseline is the reference | Jev, Bedrock, regex |
| Sensitive information | AI4Privacy (pinned), source PII-free chunks, authored controls | v2 f5-pii (shared supported-entity task) | InvokeGuardrailChecks sensitiveInformation (detect); ApplyGuardrail ANONYMIZE for the masking study (output side only) | 7 arms (Laya failed to connect); masking not yet scored |
| Grounding and relevance | RAGTruth test split, Summary and QA (pinned) | v1 f6-grounding | ApplyGuardrail contextual grounding, versioned | Jev, Bedrock; relevance has no label |

Open models still owe runs on denied topics, word filters and grounding. Every number so far is a tuning-split
smoke; nothing is a held-out result. The ApplyGuardrail guardrails live in `infra/aws` (four resources, four pinned
versions); their topic definitions and word list are read from the suite files so the guardrail and the question
sets cannot drift.

## One suite, five things

Every suite directory under `benchmark/suites/<suite>/` holds exactly these, and the harness reads nothing else.

1. **Task.** One paragraph: the capability, the side (request, reply, or both), what a positive is.
2. **Cases.** Versioned records in the shared schema: input, context, any policy or reference document the case
   depends on (a topic definition, a word list, a source passage), and provenance with the original id, version,
   licence, original label and every transformation applied.
3. **Expected outcome.** Labels, spans, decisions or verified findings, in the form the suite needs. Content and
   attacks: a label per property. PII: entity spans. Grounding: per-claim support. Never a single "harmful" bit
   where the capability is finer than that.
4. **System configuration.** For decision models, the question set and the decision rule that turns answers into
   the suite's outcome; for Bedrock, the guardrail configuration. Both frozen and hashed into every ledger record.
5. **Scoring.** What counts as success and which failures matter, written before any run.

Test cases and the questions asked of decision models are different things. Published datasets supply cases;
official feature definitions and our policy shape the questions.

## Sources per suite

| Suite | Cases from | Questions from |
|---|---|---|
| Content | AILuminate demo, Aegis 2.0, OpenAI moderation; OR-Bench for benign hard cases | Bedrock category definitions; AILuminate hazard definitions; policy v0.2 for the custom-policy study |
| Prompt attacks | Lakera PINT, deepset, Gandalf, maintained attack sets, paired benign instructions | Bedrock's three subtypes; OWASP definitions |
| Denied topics | AWS topic definition examples plus independently labelled in- and out-of-topic cases | The supplied topic definition, verbatim, as the question's criteria |
| Word filters | Official matching rules plus deterministic generated cases | Not a model question: a code baseline is the reference; a model is tested only if someone claims it can do this |
| Sensitive information | AWS entity definitions, span-labelled sets (PII Arena, PIIBench), controlled synthetic identifiers | One question per entity type; masking scored on spans, so a model needs an extraction step and that step is part of the implementation |
| Grounding and relevance | FACTS Grounding documents and queries with frozen candidate replies and verified support labels | Per-claim support and query-relevance questions |

Restructure the representation, keep the meaning. If a task or text changes, inherited labels are revalidated.
Human adjudication goes where it pays: ambiguous mappings, changed examples, and the custom-policy study. It does not
relabel every established example under our assistant policy.

## One results format

Every run appends to a ledger with the record shape the content pilot already uses, plus a `suite` field and the
suite's own expected-outcome block. Every record carries the config hash (system, model identity, endpoint, exact
questions or guardrail configuration), raw responses, latency, and usage. Cost is computed after the fact from usage
and a published tariff, or from allocated VM time for self-hosted systems, never guessed.

A point on the leaderboard is **a complete implementation at a frozen configuration**: model plus questions plus
decision rule plus any supporting code (regex, extraction, a cascade). Not a model name.

## The plot

- Y: quality on a fixed suite. For detection suites the default is violation recall at a threshold chosen on tuning
  rows for a stated false-positive budget, with the held-out false-positive rate printed beside it. PII masking adds
  span metrics; grounding adds per-claim precision and recall.
- X: measured dollars per 1,000 evaluations. Toggle to p95 latency.
- Filters: suite, dataset version, side, language, implementation type (hosted API, self-hosted, managed service).
- Tooltip: missed violations, false positives, failures, coverage, sample size, interval.
- Lines connect points only for an intentional configuration sweep (single pass vs cascade). A threshold change
  moves quality, not inference cost, and must not draw a cost curve.
- A composite comes later, with fixed suite weights and published criteria. A system scored on two suites never
  outranks one scored on six by leaving suites out; missing suites are shown as zero coverage, not omitted.

Self-hosted costs include allocated VM time and every supporting component; setup and cold start are shown apart
from steady state.

## Order of work

1. A modest source-backed smoke suite for each of the six, with adapters and receipts verified, before any suite
   scales. Prompt attacks first (data exists), then sensitive information as detection first and masking second (the
   decision models need a span-extraction and redaction step, which is part of their implementation and its cost),
   then denied topics, word filters and grounding, which need the AWS Terraform module. Benign controls are added
   with each suite, never postponed.
2. The custom-policy study (doc 17) continues in parallel as a small, separate result.
3. Freeze the broader held-out sample per suite, then run the comparison in VISION.md.
