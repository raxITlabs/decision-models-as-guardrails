# TypeSafe live docs, local copy

Pulled from https://docs.typesafe.ai on 18 September 2026 as Markdown (`<page>.md`). Re-fetch before relying on limits, pricing, or SDK signatures; the live site is the source of truth. `_index.md` is the full page index (`llms.txt`).

## Read first for the guardrails build

| File | Why |
|---|---|
| `api.md` | HTTP contract: `POST /v1/systemone`, request/answer shapes, error codes |
| `models.md` | `jev-1.13.0` limits: $0.042/Mtok input, 64k ctx, 32k state, 1,200 rpm, English-first |
| `cookbooks_llm_guardrails.md` | The vendor's own input/output guardrail battery and `route()` thresholds |
| `model-jaggedness_jev-1.13.md` | Known failure modes, including adversarial content and literal reading |
| `confidence.md` | Confidence vs probability; risk-scaled thresholds |
| `patterns_confidence-routing.md`, `patterns_fan-out.md` | Batch every policy into one call; gate by confidence |
| `cookbooks_consistency_*.md` | Routing uncertain results to human review |
| `cookbooks_classifying_rag_passages.md` | Prompt-injection detection in retrieved content |
| `cookbooks_pre_parsed_value_extraction_cookbook.md` | Regex candidates + Jev confirm, the PII pattern |
| `cookbooks_function_calling.md` | Typed argument extraction from a request, the ACTION gate pattern |

## SDK

- `sdk_javascript.md` plus `sdk-js-api/` (client, config, retry, request/result, `choice()`/`noul()`/`score()` helpers). Package `@typesafe-ai/sdk` v0.6.0, Node 20+.
- `sdk_python.md`, `sdk_python_usage.md`. Package `typesafe-sdk` from `https://pypi.typesafe.ai/`.

## Concepts and primitives

`introduction*.md`, `concepts_*.md`, `primitives*.md`, `patterns_*.md`, `cookbooks_parallel_questions.md`.
