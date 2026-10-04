# New decision models: research notes

Status: parked, 2 October 2026. Revisit after edition 2 is approved (see `26-edition-2-plan.md`). Sequence agreed with the owner: approve edition 2 → onboard these models with smoke tests → one full run with every system together.

Four research agents gathered this on 2 October. Facts carry their source; anything marked "inference" was not checked against the vendor.

## Candidates

| Model | Access | Same request format as Jev | How we'd run it | Main risk |
|---|---|---|---|---|
| Cloudflare Clef (27B), Clef-flash (9B) | Open now | Yes | Cloudflare hosted API | Clef-flash weak on grounding; long input silently truncated |
| Amazon Strands Decider 2B | Open weights | Yes | Our GCP VM | 4,096-token window; trained on Civil Comments |
| Perplexity pplx-decider-v1-27b | Open now | Yes | Perplexity hosted API | Retention undocumented for Decisions API; RAGTruth possibly in training |
| OpenAI Decisions API | Limited preview | Probably | OpenAI API once access arrives | No docs; 30-day retention by default |

Not in scope for this round, by owner decision: OpenAI Moderation API and gpt-oss-safeguard.

## Cloudflare Clef

- Clef (Qwen3.8-27B base, about 27.4B params) and Clef-flash (Qwen3.5-9B base, about 9.4B), announced 1 October 2026. Apache-2.0. Source: https://blog.cloudflare.com/clef-decision-models/
- Weights: `Cloudflare/clef` @ `2f3de3dd85f379784083b0814d997ab627200f0c`, `Cloudflare/clef-flash` @ `17f0b0ad64efb65d273590632833508766b2aae6`.
- Hosted: Workers AI, `@cf/cloudflare/clef` and `@cf/cloudflare/clef-flash`, `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/cloudflare/clef`, bearer token. Docs: https://developers.cloudflare.com/workers-ai/models/clef/
- Interface: model card says "fully compatible with Jev and SystemOne". `state` + 1–64 typed questions (noul, choice, score); returns per-question probabilities. 65,536-token context hosted; self-host code truncates at 16,384 by default.
- Price: $0.24 per million input tokens (Clef), $0.09 (Clef-flash), no output charge. https://developers.cloudflare.com/workers-ai/platform/pricing/
- Retention: Cloudflare says it does not store or train on requests unless you use fine-tuning or route through a storage service (AI Gateway logging counts). No signed zero-retention term found. https://developers.cloudflare.com/workers-ai/platform/data-usage/
- Rate limit (inference): 300 requests/min if the "Text Generation" category limit applies.
- Benchmarks: Cloudflare's own Decision Index 0.2.1 run (https://clef-evals.workers-ai-mle.workers.dev): Clef RAGTruth 79.4 vs Jev 76.5; Clef-flash RAGTruth 35.6. Median latency Clef 209 ms, Clef-flash 39 ms, Jev 524 ms. Not on the community Jev Decision Index (index generated 28 September).
- Self-host: custom `joint_schema_model.py`, no vLLM. Clef bf16 about 55 GB (needs A100/H100 80GB). Clef-flash about 19 GB, tight on one L4.
- Plan: hosted API behind a thin `CloudflareSystemOneClient` (different URL path, probably a `{result, success}` envelope), then the existing NoulAdapter. Record model id, endpoint and call date.
- Needed from owner: Cloudflare account ID and a Workers AI token. Keep AI Gateway logging off.

## Amazon Strands Decider 2B

- `StrandsAgents/strands-decider-2B-hobson-v19` @ `bb282d786bc251fd4e3068de3ada9ddbb38127cd`, released 1 October 2026 by AWS Strands Labs (Marc Brooker, Mike Chambers, Fabio Nonato de Paula). Apache-2.0. Sources: https://strandsagents.com/blog/introducing-strands-decider/ and https://huggingface.co/StrandsAgents/strands-decider-2B-hobson-v19
- Qwen3.5-2B-Base + rank-16 LoRA + about 1M-parameter readout head; no text generation. Code: https://github.com/strands-labs/strands-decider @ `aa92b07`, PyPI `strands-decider` 0.1.0 (experimental).
- No hosted API (not on Bedrock). Self-host only, so private rows stay on our VM.
- Interface: `strands-decider serve` exposes `POST /v1/systemone`; noul, choice (up to 24 options), score (2–10 levels); per-question probabilities. 4,096-token window; question cut from the front and state from the right, with no truncation flag.
- Benchmarks (vendor): JevBench public 72.3%, Brier 0.348, ECE 0.050. Not on the Jev Decision Index. The index's "Decider 2B" is Mapika's unrelated model.
- Self-host: transformers >= 5.15, peft >= 0.21; no `trust_remote_code`; no vLLM. About 5 GB bf16, fits easily beside the Kev models.
- Plan: own uv environment on the VM, pinned revision, bind 0.0.0.0 via `create_app` + uvicorn, existing NoulAdapter unchanged.
- Risks: grounding rows may exceed 4,096 tokens (log token counts, flag rows over about 3,500); trained on civil_comments and measuring-hate-speech, so run the overlap check against our profanity and content suites; model card says question wording is read less closely than the document.

## Perplexity pplx-decider-v1-27b

- `perplexity-ai/pplx-decider-v1-27b` @ `5117a6c7fe73b19308dc1a6b0fb529a40c2ecad4`, released 1 October 2026. Weights Apache-2.0, code MIT. Qwen3.8-27B base, 26.1B params bf16 (52.2 GB). https://huggingface.co/perplexity-ai/pplx-decider-v1-27b
- Hosted Decisions API, generally available: `POST https://api.perplexity.ai/v1/decisions`, `model: "pplx-decider-v1-27b"`, bearer key. https://docs.perplexity.ai/docs/decisions/quickstart
- Interface: `state` + 1–128 typed questions (noul, choice up to 255 options, score 2–10); per-question probabilities. Hosted limit 262,144 input tokens; self-host refuses over 8,192 tokens per question.
- Price: $0.04 per million input tokens, output free. Rate limit 10 requests/s per organisation. https://docs.perplexity.ai/docs/getting-started/pricing
- Retention: zero retention is documented only for Chat Completions, not the Decisions API. https://docs.perplexity.ai/docs/resources/privacy-security.md
- Jev Decision Index 0.2.1: balanced_skill 56.40 vs Jev 57.91; 3rd of 70 on breadth_skill; calibration ECE 0.018 vs Jev 0.074; zero errors on 120,340 requests (served self-hosted in bf16 there, not via the API).
- Plan: hosted API (like-for-like with Jev's vendor API; long context; pennies per run) via a thin `PerplexityDecisionsClient`, then the existing NoulAdapter. Throttle to 5 requests/s. Self-hosting needs an A100/H100 and is optional.
- Risks: get retention confirmed in writing before sending private rows; RAGTruth mentioned on the model card, so run the overlap check on grounding; hosted model not version-pinned; the open-source server answers to `jev-latest` / `jev-1.13.0`, so the adapter must record which model actually answered.
- Needed from owner: Perplexity API key and written retention confirmation.

## OpenAI Decisions API

- Announced at DevDay, 29 September 2026, powered by GPT-6 Luna. Limited preview, broader release "in the coming days". https://x.com/OpenAIDevs/status/2105003318917697873 and https://community.openai.com/t/devday-2026-announcements-and-developer-resources/1402006
- No official docs or pricing yet. Community reports (unverified): `POST /v1/decisions`, model `gpt-6-luna`, predicate/choice/score questions with probabilities; returns 403 "Decision API is not enabled for this user" without access. https://github.com/pydantic/pydantic-ai/issues/9633
- Retention: not listed in OpenAI's data-controls table; assume 30-day abuse-monitoring retention unless zero retention is approved. https://developers.openai.com/api/docs/guides/your-data
- Not on the Jev Decision Index.
- Plan once access arrives: confirm the schema, then a thin client around `/v1/decisions` and the existing NoulAdapter.

Draft access note for the owner (not sent):

> Hi, we run jev-as-a-guardrails, an open benchmark of guardrail and decision models across six suites (content, prompt attacks, denied topics, word filters, PII, grounding). We'd like to add the Decisions API in limited preview. We'd call gpt-6-luna with yes/no questions and report per-question probabilities against a fixed 0.5 threshold. Results are published with the serving config and date. Our test rows are private, so before sending any we need to know three things: can the endpoint run under Zero Data Retention, what is retained by default, and can we get preview pricing. Volume is about N thousand calls per run. Can you enable our org (ID: ...)?

## Smoke test for every new model

20 edition-2 tuning rows per suite, never test or private rows:

1. One request with the vendor's own example to confirm the response shape and record the model field.
2. All suites: assert outcome decided, probabilities in [0, 1], failures at most 2%; log latency, usage and token counts.
3. Flag rows near or above the model's context window.
4. Rerun 5 rows to check determinism and drift.
5. Run the overlap check against the vendor's published training data where known.
