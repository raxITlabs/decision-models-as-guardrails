# Jev primer

Source: docs.typesafe.ai, read 18 September 2026. Vendor material unless marked otherwise.

## What it is

TypeSafe AI came out of stealth on 15 September 2026 with a $40M seed led by DCVC. Founder Diogo Almeida worked on RLHF and InstructGPT at OpenAI. Jev is the first of what TypeSafe calls System One models. You send it state (text or JSON) and a set of typed questions. It returns, for each question, a probability distribution over the options you supplied plus a confidence number. It generates no text.

The pitch in one line from their docs: "Jev is built for software that needs a judgment, not a paragraph."

## The three question types

| Type | Answers | Returns | Use when |
|---|---|---|---|
| Choice | Which of these options? | selected option, probability per option, confidence | closed set, no order (routing, classification) |
| Score | Which level on this scale? | score, probability per level, confidence | ordered levels you describe (severity, risk) |
| Noul | Is this true? | probability of yes, 0 to 1, no separate confidence | one condition per label |

Rules that matter for design work:

- Question IDs are for code and are not sent to the model. Put the full meaning in the instructions.
- Every question in one request sees the same state and runs in parallel. Extra questions cost tokens, not latency. Ask speculative questions up front and read only the answers you need.
- Reference nested state with backticked paths such as `ticket.messages[0].text`.
- Include a "none" or "other" option when nothing may fit.
- A Noul near 0.5 means equal probability of yes and no, not medium intensity.
- Confidence on Choice and Score summarises how peaked the distribution is. It is not a truth score.

## Pricing and limits (jev-1.13.0)

- $0.042 per million input tokens. Output tokens are free.
- 250,000 tokens per second, 1,200 requests per minute, and TypeSafe says these are changing without notice while they scale.
- 64k tokens per request total, 32k for state plus the longest question.
- Text only. No image, audio, or video. Convert first.
- Not fine-tunable. You shape behaviour through state, instructions, and criteria.
- Not trained on customer requests. Zero data retention is available on enterprise plans.
- Available on Vercel AI Gateway and Cloudflare AI Gateway since the launch week.

Vendor speed claims: 70 to 500 ms end to end, "20 to 200x faster and 40 to 400x cheaper" than frontier LLMs on classification tasks. Nobody outside TypeSafe had reproduced these at the time of writing.

## Known weaknesses, from TypeSafe's own jaggedness page

This page matters more than the marketing. Reviewed 17 September 2026 for jev-1.13.

1. Literal reading. It answers the question you wrote, not the one you meant. Put boundary cases in the criteria.
2. Math and counting. Keep arithmetic in code. Do not use Score expectations as numbers.
3. Dates. It reads dates as text. Extract parts as Choices, compare in code.
4. Indirection. Double negatives and multi-hop questions lose accuracy.
5. Large irrelevant state. Accuracy falls as unrelated content grows. Filter first.
6. Adversarial content. Quoted from the page: state "does not treat it as hostile by default" and injected text "can move the answer." For a guardrail product this is the weakness that has to be designed around, not ignored.
7. Contradictory instructions and criteria confuse it.
8. Structural invariants are not guaranteed. The same question as a Noul and as a yes/no Choice can disagree. Ask each decision one way.
9. No generation. Use an LLM for text.

## Cookbooks that map onto guardrail work

- Guardrails for LLMs: one request per message with one Noul per hazard and a Score for severity, thresholds in code, tested on the in-the-wild jailbreak dataset.
- Pre-parsed value extraction: regex finds candidate spans, Jev selects the intended one, code normalises. This is the PII pattern.
- Double-checking citations: Choice on whether the source supports the claim. This is the contextual grounding pattern.
- Classifying RAG passages: Score each retrieved passage, drop ones carrying injected instructions.
- Confidence-gated routing, speculative fan-out, and composite scoring patterns.

## SDKs

Official Python (`uv add typesafe-sdk`) and JavaScript/TypeScript (`@typesafe-ai/sdk`). Community SDKs for Rust, Elixir, Ruby, PHP, and .NET appeared within days. HTTP API is `POST /v1/systemone`. Set `TYPESAFE_API_KEY`.
