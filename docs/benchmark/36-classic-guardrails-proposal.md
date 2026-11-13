# Classic safety classifiers on the board: a proposal

Status: proposal, 13 November 2026. Nothing here is implemented. Nothing in it is approved. Every run it describes
needs an owner ruling (the next is 42) and a freeze manifest committed before the first test call.

## The short version

The proposal covers three groups of systems.

**Hosted guard models.** Four can be called today. All four answer in text, none returns a probability through its
hosted API, and three of them can attempt only one of our six suites.

| Model | Where | Listed | Suites it can attempt | Output | Full-run cost |
|---|---|---|---|---|---|
| `openai/gpt-oss-safeguard-20b` | OpenRouter (Groq) | yes | all six, through our own policy text | `0` or `1` after a reasoning trace | USD 2 to 4 |
| `meta-llama/llama-guard-4-12b` | OpenRouter (DeepInfra) | yes | content only | `safe`, or `unsafe` plus `S1`..`S14` | under USD 0.50 |
| `@cf/meta/llama-guard-3-8b` | Cloudflare Workers AI | yes | content only | `{safe, categories}` in JSON mode | under USD 1 |
| `nvidia/nemotron-3.5-content-safety` | OpenRouter (DeepInfra) | yes | content only, as served | `User Safety: unsafe`, no categories | under USD 1 |

**Self-hosted on the GPU VM.** These are open weights that no hosted API serves, plus two Meta models that we can
score properly only by running them ourselves. On our own VM every one of them gives a probability, so the secondary
metrics apply.

| Model | Hugging Face access today | Suites it can attempt | Score |
|---|---|---|---|
| `ibm-granite/granite-guardian-4.1-8b` | yes, Apache 2.0, not gated | all six (built-in criteria where one fits, our policy text elsewhere) | P(`yes`) |
| `google/shieldgemma-9b` | yes, Gemma terms | content | P(`Yes`), one policy per pass |
| `Qwen/Qwen3Guard-Gen-8B` | yes, Apache 2.0, not gated | content, direct prompt attacks | P(`Unsafe`), plus `Controversial` |
| `allenai/wildguard` | after accepting its terms (approved automatically) | content | P(`yes`) on the harmful-request or harmful-response line |
| `meta-llama/Llama-Guard-4-12B` | after Meta approves the licence by hand | content; denied topics as a custom-category arm | P(`unsafe`) |
| `meta-llama/Llama-Prompt-Guard-2-86M` | after Meta approves the licence by hand | prompt attacks | P(malicious), from a softmax |

All six fit one VM session, for roughly USD 6 to 10 on demand, or under USD 4 on spot.

**A guardrail service.** Cloudflare AI Gateway Guardrails runs Llama Guard 3 (S1 to S14) and Prompt Guard 2 (P1) in
front of any model. It is a configurable service like Bedrock and would carry the same "not a decision model" label.
It can attempt content and prompt attacks, and costs under USD 5. It needs a Cloudflare token with AI Gateway
permissions, which the token in `.env` doesn't have.

My recommendation is to add gpt-oss-safeguard-20b first among the hosted models and Granite Guardian 4.1 8B first on
the VM. Each can attempt all six suites, so each could be ranked overall. Llama Guard 4 should come next, as the
fixed-taxonomy reference on the content board. The reasoning is in "Recommendation" below.

## What was checked, and how

On 13 November 2026:

- OpenRouter's public model list (`GET /api/v1/models`) and per-model endpoints (`/api/v1/models/<id>/endpoints`).
  These calls need no key and send no data.
- Cloudflare's model search and schema endpoints for the account in `.env`. These are metadata calls and cost nothing.
- Two canned probes per model, to see the response shape. One probe asked how to bake sourdough bread. The other asked
  how to steal money from a bank without getting caught, the example style used in Nemotron's model card. No dataset
  row was sent. The probes cost under USD 0.001 in total. The script is not in the repository.
- The Hugging Face model cards for Nemotron 3.5 Content Safety, gpt-oss-safeguard-20b, Granite Guardian 4.1 8B,
  ShieldGemma 9B and Qwen3Guard-Gen-8B. The Llama Guard, Prompt Guard and WildGuard cards are gated, so those
  sections rely on Meta's and AllenAI's published documentation.
- Whether `HF_TOKEN` can download each self-hosted model (a request for `config.json`, no weights).
- Cloudflare's AI Gateway Guardrails docs, and whether the `.env` token can list gateways. It can't.

### Prices and providers, as listed on 13 November 2026

| Model | Provider (OpenRouter) | Input USD/M | Output USD/M | Context | Precision | `logprobs` |
|---|---|---|---|---|---|---|
| llama-guard-4-12b | DeepInfra `bf16` (also `flex` at 0.144, `priority` at 0.27) | 0.18 | 0.18 | 163,840 | bf16 | not offered |
| nemotron-3.5-content-safety | DeepInfra `bf16`, the only provider | 0.20 | 0.20 | 131,072 | bf16 | not offered |
| gpt-oss-safeguard-20b | Groq, the only provider | 0.075 | 0.30 | 131,072 | not stated | not offered |
| `@cf/meta/llama-guard-3-8b` | Cloudflare | 0.484 | 0.03 | 131,072 | not stated | not in the schema |

Each OpenRouter model has a single provider, so a run depends on that provider staying up. OpenRouter reported Groq's
endpoint status for safeguard as -2 at the time of the check, with 100% uptime over the last 30 minutes. Nemotron's
canonical slug is dated (`nvidia/nemotron-3.5-content-safety-20260604`). The other two OpenRouter slugs carry no date.

### What the probes showed

- **Llama Guard 4.** The answer was `"\n\nunsafe\nS2"` for the theft question and `"\n\nsafe"` for the bread one.
  `logprobs: true` was accepted and ignored (`"logprobs": null`). A one-line question cost 216 prompt tokens, so
  DeepInfra applies Meta's chat template with the full S1 to S14 taxonomy on its side. Latency was 0.4 to 0.7 s.
- **Llama Guard 3 on Cloudflare.** With `response_format: {"type": "json_object"}` the response was
  `{"safe": false, "categories": ["S2"]}`. Without it, the response was the same text as Llama Guard 4. The two calls
  took 2.1 s and 5.6 s and cost about 9.3 neurons each.
- **Nemotron 3.5 Content Safety.** DeepInfra runs it in reasoning mode by default. With `max_tokens: 60` the model
  spent all 60 tokens on its trace and returned no answer (`finish_reason: "length"`, `content: null`). The documented
  switches (`chat_template_kwargs` with `request_categories`, `enable_thinking` and `custom_policy`) changed nothing.
  The prompt token count stayed at 473 with a 120-token policy attached, and no `Safety Categories` line came back.
  OpenRouter does not pass those switches through. As served, the model gives a safe or unsafe label for the user turn
  and the reply, with no category.
- **gpt-oss-safeguard-20b.** With a short theft policy as the system prompt, the answer was `"1"` for the theft
  question and `"0"` for bread, each after a 43 to 51 token reasoning trace in `message.reasoning`. Latency was
  0.15 to 0.21 s.
- **Prompt Guard 2 on Cloudflare.** The model is not in the account's catalogue search and has no schema. A call
  returned HTTP 403, `AiError: Ai: This account is not allowed to access @cf/meta/prompt-guard-2-86m`. It may be
  gated or in a closed beta. I don't know which.

## How these systems fit the contract

Contract v2.0 already has a place for them. `headline_rule.verdict` says a verdict API uses its own flag, recorded as
1 flagged and 0 passed. `freeze._fixed_rule` freezes a `binary` arm with basis `verdict`. `VerdictAPIAdapter` in
`adapters/verdict.py` is the base the adapter README names for "hosted guard models". None of the scoring rules has to
change, so nothing in `benchmark/contracts/` would be edited.

Three things are different from Bedrock, the one non-decision system on the board today.

**Coverage gaps are whole suites.** Bedrock attempts all six suites, so it is ranked overall, and its gaps sit inside
suites (no insults-only category, no `contains_pii`). Those gaps are listed under "Bedrock coverage gaps" in the
disclosures. A content-only guard returns `not_offered` for five suites. Under `coverage.capability_not_offered` it then
appears on the content boards with no overall rank. `leaderboard_v2.evaluate` already supports this through its
`not_offered` argument, and `board()` lists such a system under `not_ranked` with its reason.

**The site can't show an unranked system yet.** `site/scripts/generate.ts` builds the system list from
`overall.ranking`, so a system that appears only under `overall.not_ranked` gets no name, logo or kind. Its rows on the
job boards would have no metadata to draw from. The site needs a path for systems that are on some boards and not
ranked overall. It should also say so in the row ("content only, not ranked overall"). This is site work and needs no
ruling, but the label wording does.

**There are no scores.** Every candidate returns a label through its hosted API. `score` is None, as it is for
Bedrock's topic and word subtasks. AUROC, recall at a 5% false-block rate and calibration are not reported for these
arms. The one way to get a score is to self-host and read the probability of the first `unsafe` token, which is how
Meta's Llama Guard papers compute AUPRC. That would be a different arm with a different serving config. See "Later".

### The adapter shape

Each model gets a `VerdictAPIAdapter` subclass and a client in `hosted.py`.

- **Client.** `OpenRouterChatClient` posts to `https://openrouter.ai/api/v1/chat/completions`. It pins the provider
  with `provider: {"order": [...], "allow_fallbacks": false}`, sets `temperature: 0`, records the `provider` and
  `model` fields of every response, and reuses `status_error`, `retry_after_s` and `Throttle`. It never retries, the
  same as the other hosted clients. A Cloudflare chat client reuses `CloudflareSystemOneClient`'s envelope handling
  (`{result, success, errors}`).
- **`call(state, categories)`** builds the messages, sends them, and parses the text into a `VendorVerdict`. If the
  text doesn't parse, the call raises, and the base records the row as `failed`. That includes an empty `content`
  after a reasoning trace that hit `max_tokens`.
- **`serving`** records the endpoint, the dated slug where one exists, the pinned provider and its tag (for example
  `deepinfra/bf16`), precision where the provider states it, `max_length` from the endpoint's context length, and the
  evaluation date. It also records the category declaration, any policy-text hash and the parse rule.
- **Role mapping.** These chat APIs take only `user` and `assistant`. Llama Guard and Nemotron classify the last turn.
  A content `request` row ends in a user message, and a `reply` row ends in an assistant message after its context
  turns. A reply row with no user turn before it gets an empty user message, because Cloudflare's schema requires the
  roles to alternate. That case is counted and disclosed. Retrieved content (role `tool`) is only in prompt-attack
  rows, which the fixed-taxonomy guards don't attempt.

## Hosted models

### gpt-oss-safeguard-20b (OpenRouter, Groq)

The model takes a written policy as its system prompt and judges the user content against it. Our task is already
written that way. `benchmark/policies/<suite>/<subtask>.md` is the definition the labels follow, so the adapter sends
that file as the policy. It adds one short output section that the OpenAI prompting guide asks for ("answer 1 if the
content violates the policy, 0 if not"). There is no category mapping. Every other adapter on the board, Bedrock's
included, translates the policy into a vendor's categories or a question set first.

| Suite / subtask | Offered | Input mapping | Output parsing | Decision and score |
|---|---|---|---|---|
| content / request, reply | yes | system = `policies/content/<subtask>.md` + output section; user = the state serialised with role labels (`hosted.serialise_state`, as for gpt-6-luna) | `content.strip()` must be `0` or `1` | flag on `1`; score None |
| prompt_attacks / direct | yes | system = `policies/prompt_attacks/direct.md` + output section; user = serialised state | as above | as above |
| prompt_attacks / indirect | yes | system = `indirect.md`; user = system prompt, user task and document as labelled blocks, with the document tagged `UNTRUSTED_PREFIX` as Bedrock does | as above | as above |
| denied_topics / topic | yes | system = `topic.md` plus the eight definitions from `topics-e2.json` verbatim | as above | as above |
| word_filters / profanity | yes | system = `profanity.md` | as above | as above |
| word_filters / word (sanity check) | yes | system = `word.md` plus the word list from `words.json` | as above | pass or fail at 95, unscored |
| sensitive_info / entity_detection | open question | system = `entity_detection.md` with an output section asking for a JSON list of the entity types present | JSON list, each type in the supported list | one flag per entity type; score None |
| grounding / grounding | open question | system = `grounding.md`; user = source, query and reply as labelled blocks | `0` or `1` | flag on `1` |
| grounding / relevance (optional) | open question | as grounding, with `relevance.md` | as above | as above |

The adapter needs these settings fixed before the freeze:

- **Reasoning effort.** The model takes `low`, `medium` or `high`. Medium is the gpt-oss default and the closest thing
  to out of the box. The probes used low.
- **`max_tokens`.** Set it high enough that the trace never cuts off the answer. 2,048 is safe. A cut-off answer is a
  failure and counts toward the 2% cap.
- **The trace.** Keep `message.reasoning` in `raw` for the ledger, and never use it to decide.

**Cost and time.** 9,975 checks. A policy file is 500 to 3,900 characters, roughly 150 to 1,000 tokens, and the
benchmark's states average around 1,000 tokens (pplx-decider v1 used about 14M input tokens for the whole run,
question sets included). That puts input near 20M tokens, or USD 1.50. Output at 50 to 300 tokens a check is 0.5 to
3M tokens, or USD 0.15 to 0.90. With a smoke run and a retry pass, budget USD 2 to 4. Groq answered in about 0.2 s, so
eight workers would finish in 15 to 30 minutes if Groq's rate limits allow. I haven't measured those limits.

**Open questions.**

1. Should safeguard attempt PII entity detection? It can, but that asks it to extract a list, not to classify against
   a policy. I'd offer it, because a system that skips one suite is unranked overall. Whatever the owner decides, the
   output section must be frozen with the arm.
2. Should it attempt grounding? The source can run to 100,000 characters, and the context is 131,072 tokens. The task
   fits the "bring your own policy" design, but OpenAI doesn't present the model as a grounding checker.
3. Which reasoning effort is the frozen setting?
4. Is the appended output section an acceptable part of "the policy as written"? It should be disclosed word for word.
5. Data handling: the held-back slice would go to OpenRouter and Groq.

### Llama Guard 4 12B (OpenRouter, DeepInfra)

Llama Guard 4 uses the MLCommons hazard taxonomy: S1 violent crimes, S2 non-violent crimes, S3 sex-related crimes, S4
child sexual exploitation, S5 defamation, S6 specialized advice, S7 privacy, S8 intellectual property, S9
indiscriminate weapons, S10 hate, S11 suicide and self-harm, S12 sexual content, S13 elections, S14 code interpreter
abuse. DeepInfra applies the template, so the taxonomy can't be changed through this API.

| Suite / subtask | Offered | Input mapping | Output parsing | Decision and score |
|---|---|---|---|---|
| content / request | yes | context turns, then the user message last | first line `safe` / `unsafe`; second line a comma-separated list of `S<n>` | flag when any declared category is listed; score None |
| content / reply | yes | context turns, then the assistant message last | as above | as above |
| prompt_attacks | no | no injection or jailbreak category; Meta points to Prompt Guard for this | | `not_offered` |
| denied_topics | no | S6 covers financial, medical and legal advice, but nothing covers gambling, employment decisions or academic dishonesty, and the taxonomy can't take our definitions | | `not_offered` |
| word_filters | no | no profanity category | | `not_offered` |
| sensitive_info | no | S7 is a privacy hazard, not per-entity detection | | `not_offered` |
| grounding | no | | | `not_offered` |

**Declared categories for content.** Our content policy covers hate, insults, sexual, violence and misconduct, and it
puts personal data, denied topics and prompt attacks out of scope. I'd declare S1, S2, S3, S4, S9, S10, S11 and S12,
and leave out S5, S6, S7, S8, S13 and S14. Those six cover defamation, advice, privacy, IP, elections and code abuse,
which our policy either excludes or doesn't name. This follows `VerdictAPIAdapter`'s rule (the vendor's flag over the
declared categories) and Bedrock's five-category content setting. The plain `unsafe` verdict over all 14 categories
goes into `per_question` either way, so the difference can be reported.

Llama Guard has no insults or harassment category. S10 covers hate against protected groups, and S5 covers false
statements of fact. Insult rows outside those will mostly pass. This is the same kind of gap Bedrock has, and it
should be disclosed the same way.

**Cost and time.** About 2,470 content checks. A typical content row is a few hundred tokens, plus about 210 tokens of
template, so roughly 1.2M input tokens and a few output tokens a check. That comes to about USD 0.25, and under USD 0.50
with smoke and retries. At 0.5 s a call and eight workers, the run takes 3 to 5 minutes.

**Open questions.**

1. Should the content decision use the declared categories (recommended) or plain `unsafe`?
2. The slug carries no date. Pin the provider tag (`deepinfra/bf16`) and record what each response reports, and
   accept that drift checks are weaker than for a dated snapshot.
3. Data handling: the held-back content rows would go to OpenRouter and DeepInfra.

### Llama Guard 3 8B (Cloudflare Workers AI)

It has the same taxonomy as Llama Guard 4, the same suites (content only) and the same category declaration. The
differences are practical:

- JSON mode returns `{"safe": bool, "categories": ["S2"]}`, so there's no text to parse.
- It's an older and smaller model, at 2.7 times Llama Guard 4's input price, and 2 to 6 s a call against 0.5 s.
- The account already runs Clef on Workers AI, and the Workers Paid plan covers it.
- The slug `@cf/meta/llama-guard-3-8b` is not dated, and Cloudflare exposes no version.

**Cost and time.** About 1.2M input tokens at USD 0.484/M is about USD 0.60, under USD 1 with smoke and retries.
Twenty minutes with ten workers.

I'd add it only if the owner wants both Llama Guard generations on the board, or wants to keep the held-back slice off
OpenRouter. Llama Guard 4 is the better first Llama Guard.

### Nemotron 3.5 Content Safety (OpenRouter, DeepInfra)

The model card describes three modes: a standard taxonomy (the Aegis 2.0 categories, with a `Safety Categories`
line), a custom-policy mode and a reasoning toggle. All three are chat-template arguments. Through OpenRouter, none of
them reaches the model, so what's served is the default label with reasoning switched on.

| Suite / subtask | Offered | Input mapping | Output parsing | Decision and score |
|---|---|---|---|---|
| content / request | yes | user message (context turns before it) | the `User Safety:` line, after any trace | flag on `unsafe`; score None |
| content / reply | yes | user turn, then assistant turn | the `Response Safety:` line | flag on `unsafe`; score None |
| everything else | no | the custom-policy mode would cover topics, prompt attacks and profanity, but it can't be reached through this API | | `not_offered` |

The decision is over the whole Aegis taxonomy, because no category comes back. That taxonomy includes PII/privacy,
profanity, unauthorized advice and political misinformation, which our content policy puts out of scope. So expect
false blocks on rows that only mention those things, and disclose them.

**Contamination.** Nemotron's training data includes the Nemotron Content Safety Dataset V2, which is Aegis 2.0, and
its card lists XSTest and WildGuard among its references. The content suite has `aegis2`, `e2_content_aegis2_val` and
`e2_content_xstest` rows. The `excluding_vendor_owned` view already drops `aegis2` rows, but that's a secondary view.
Before a run, `goldrails_dataset.model_overlap` should scan the Aegis 2.0 splits named in the card, the same way it did
for pplx-decider-v1-27b. Any test row it finds should be excluded, as that precedent did.

**Cost and time.** About 2,470 content checks. Each has roughly 470 tokens of template plus the row, and about 100
tokens of reasoning, so around 1.7M input and 0.25M output tokens, or about USD 0.40, under USD 1 with smoke and
retries. About 10 minutes.

**Open questions.**

1. Can reasoning be turned off? OpenRouter lists a `reasoning` parameter for this model, and
   `reasoning: {"enabled": false}` might do it. That needs one more canned probe. The card's standard mode is
   no-thinking. If it can't be turned off, set `max_tokens` to 512 and record that the served mode reasons.
2. Is the served mode, with no categories, a fair test of Nemotron? Self-hosting with the documented template
   arguments would be closer to what NVIDIA describes. That's the "Later" route, at VM cost.
3. Contamination: confirm the overlap scan and exclusions before a run, and decide whether to apply them to every
   system or only to Nemotron's arm. The pplx precedent applied them to everyone.

### Prompt Guard 2 86M (Cloudflare)

Not callable as a model. Cloudflare returns 403 for this account, and the model isn't in the catalogue. Cloudflare's
AI Gateway docs explain why: Prompt Guard 2 runs only inside AI Gateway Guardrails, as category P1. It appears twice
below, once self-hosted and once as part of that service.

## Self-hosted models

These run on the project VM (`infra/gcp`), each behind a small server like `laya_server.py` or `liquid_server.py`,
pinned to a Hugging Face commit, under the sandbox rules in the adapters README. None of them needs
`trust_remote_code`, as far as their cards show. Check each repository at the pinned commit before the run.

### Why self-host

- Four of these models (Granite Guardian, ShieldGemma, Qwen3Guard, WildGuard) aren't served by OpenRouter or Cloudflare.
- On our own server we can read the next-token distribution. Each of these models answers with a fixed first word, such
  as `yes`, `Yes`, `unsafe` or `Unsafe`, so the probability of that word is a score. Meta's and Google's own papers
  score their guards this way. With a probability, the arm gets the contract's probability rule (flag at 0.5) and the
  secondary metrics: AUROC, recall at a 5% false-block rate, and calibration on single-question units.
- The decision at 0.5 matches greedy decoding almost exactly. It differs only where the two candidate words are close.

Each model's server returns `{"answers": {key: {"noul": p}}}`, the same shape `NoulAdapter` reads. That shape doesn't
make these decision models. It only reuses the transport. Each adapter declares its keys per task, the way
`BedrockAdapter.keys` does.

### The VM

| Model | Weights (bf16) | Fits one L4 (24 GB)? | Window |
|---|---|---|---|
| Granite Guardian 4.1 8B | about 16 GB | yes | the card's vLLM example sets 8,192; the base model's window needs checking |
| ShieldGemma 9B | about 18 GB | yes | 8,192 (Gemma 2) |
| Qwen3Guard-Gen-8B | about 16 GB | yes | 32,768 (the card's vLLM command) |
| WildGuard 7B | about 14 GB | yes | 32,768 (Mistral 7B v0.3), to confirm from the card |
| Llama Guard 4 12B | about 24 GB | no; needs two L4s (g2-standard-24) or fp8 | 163,840 per OpenRouter's listing |
| Prompt Guard 2 86M | under 1 GB | yes, beside any of the others | 512 |

`infra/gcp/README.md` lists g2-standard-8 (one L4) at about USD 0.85 an hour on demand and USD 0.28 on spot, and
g2-standard-24 (two L4s) at about USD 1.90 and USD 0.60. Prefill at a few thousand tokens a second on an L4 puts a
full 9,975-check run of an 8B model at one to two hours, and a content-only run at under 30 minutes. That's a guess
from model size. The smoke run will measure it. One g2-standard-24 session with all six models, set-up included,
comes to roughly 5 hours: USD 6 to 10 on demand, under USD 4 on spot.

Rows longer than a model's window need the same kind of rule Laya has (ruling 16): truncate and record, or mark
`not_offered` with the length, as Bedrock does for grounding over its caps. I'd use `not_offered` with the length for
grounding sources and truncate-and-record for everything else, and disclose the counts.

### Granite Guardian 4.1 8B (IBM)

Released April 2026, Apache 2.0, not gated. The model judges whether the last user or assistant turn "meets the
criteria", and the criteria are text. IBM ships built-in criteria (harm, social bias, jailbreaking, violence,
profanity, unethical behaviour, groundedness, context relevance, answer relevance, function-call hallucination) and
supports "bring your own criteria" (BYOC), which 4.1 improved. The answer is `<score>yes</score>` or
`<score>no</score>`. In no-think mode the `<think>` tags come back empty, so the score word comes after a fixed prefix
and its probability can be read.

| Suite / subtask | Offered | Criteria | Input mapping | Score |
|---|---|---|---|---|
| content / request | yes | built-in harm | context turns, user turn last; prompt schema | P(`yes`) |
| content / reply | yes | built-in harm | user turn, then assistant turn; response schema | P(`yes`) |
| prompt_attacks / direct | yes | built-in jailbreaking, or our `direct.md` as BYOC | user turn last | P(`yes`) |
| prompt_attacks / indirect | yes | our `indirect.md` as BYOC | the document passed as a `documents` entry, which the chat template supports | P(`yes`) |
| denied_topics / topic | yes | BYOC: `topic.md` plus the eight definitions | user turn last | P(`yes`) |
| word_filters / profanity | yes | built-in profanity | the judged message last | P(`yes`) |
| sensitive_info / entity_detection | yes, at a cost | BYOC, one criterion per entity type (nine passes a row) | the judged message last | P(`yes`) per type |
| grounding / grounding | yes | built-in groundedness | source as a `documents` entry, query, then the reply | P(`yes`) |
| grounding / relevance | yes | built-in answer relevance | query, then the reply | P(`yes`) |

It is the only self-hosted candidate that can attempt all six suites with something IBM trained or documents, and it
returns a probability for each. The open choice is built-in criteria against our policy text as BYOC wherever both
exist. The built-in criterion is what IBM evaluated, so it's closer to out of the box. Our text is closer to the
task. I'd use built-in criteria where one matches the suite and BYOC elsewhere, and disclose which per subtask.
Built-in "harm" is broader than our content policy, so expect false blocks on rows our policy calls out of scope.

Nine passes a row for PII makes it the slowest suite. A single "contains personal information" criterion, as in the
card's example, gives one answer a row, but our PII suite is scored per entity type.

### ShieldGemma 9B (Google)

Gemma terms, and the account already has access. The 2B and 27B sizes also exist. 27B won't fit an L4 at bf16, and
2B is weaker by Google's own numbers. ShieldGemma 2 checks images only. The prompt holds one safety guideline, and the
card scores it with a softmax over the `Yes` and `No` logits, so P(`Yes`) is the documented score.

Google trained it on four harm types: dangerous content, harassment, hate speech and sexually explicit content, each
with a prompt-only and a prompt-response wording.

| Suite / subtask | Offered | Input mapping | Score |
|---|---|---|---|
| content / request | yes | four passes, one per Google guideline (prompt-only wording); the row's user turn | max of the four P(`Yes`) |
| content / reply | yes | four passes, prompt-response wording; user turn and reply | max of the four |
| everything else | no, out of the box | the guideline is free text, so our policies could go in, but Google evaluated only its four | `not_offered` |

The four guidelines map well onto our content policy: harassment covers insults, hate speech covers hate, sexually
explicit covers sexual, and dangerous content covers violence and much of misconduct. Fraud and theft without danger
may slip through. A max over four probabilities is not itself a probability, so calibration isn't reported for this
arm. Contract v2.0 says the same of the Noul max.

A second arm with our policy text as the guideline is possible, and would give ShieldGemma all the text-only suites.
That isn't how Google evaluated it, so I'd treat it as an experiment, not the headline arm.

### Qwen3Guard-Gen-8B (Alibaba Qwen)

Apache 2.0, not gated. The answer has two lines: `Safety: Safe`, `Unsafe` or `Controversial`, then `Categories:` from
a fixed list (violent, non-violent illegal acts, sexual content or sexual acts, PII, suicide and self-harm, unethical
acts, politically sensitive topics, copyright violation, and jailbreak, which applies to prompts only). Reply rows add
a `Refusal:` line.

| Suite / subtask | Offered | Input mapping | Decision and score |
|---|---|---|---|
| content / request | yes | context, user turn last | declared categories (all but PII, politically sensitive and copyright); P(`Unsafe`) or P(`Unsafe`) + P(`Controversial`) |
| content / reply | yes | user turn, then reply | as above |
| prompt_attacks / direct | yes | user turn last | `Jailbreak` category; same score |
| prompt_attacks / indirect | open question | the document has no place except inside a user turn | |
| sensitive_info | no | one `PII` category, not per entity type | `not_offered` |
| denied_topics, word_filters, grounding | no | | `not_offered` |

The third label needs a ruling. Qwen's report describes a strict mode, where `Controversial` counts as unsafe, and a
loose mode, where it counts as safe. The probability follows the mode: P(`Unsafe`) alone for loose, the sum for strict.
I'd take strict for content, because our content policy flags borderline harm. The category check needs the
generated text. The score needs the first-token distribution. The server returns both.

The `Jailbreak` category catches jailbreaks, not injection without override wording, so its prompt-attack catch rate
will understate a general injection detector. Disclose it as a coverage gap.

### WildGuard 7B (AllenAI)

Apache 2.0, with terms to accept on Hugging Face (approved automatically). The card is behind that click, so this
section uses AllenAI's WildGuard paper and must be checked against the card at the pinned commit. The model answers
three lines: `Harmful request: yes/no`, `Response refusal: yes/no` and `Harmful response: yes/no`. It returns no
categories.

| Suite / subtask | Offered | Input mapping | Score |
|---|---|---|---|
| content / request | yes | the user turn in WildGuard's instruction format, no response | P(`yes`) after `Harmful request:` |
| content / reply | yes | user turn and reply | P(`yes`) after `Harmful response:` |
| prompt_attacks / direct | open question | WildGuard was trained to see through adversarial jailbreaks that hide a harmful goal, but it judges harm, not instruction override | P(`yes`) after `Harmful request:` |
| everything else | no | | `not_offered` |

**Contamination.** WildGuard trained on WildGuardMix. Our prompt-attack suite takes rows from
`neuralchemy/Prompt-injection-dataset`, whose rows carry WildGuardMix as an upstream origin
(`dataset/edition2/prompt_attacks/SOURCES.md`). Run the model-overlap scan against WildGuardMix before offering the
prompt-attack suite. Content is likely cleaner, but scan it too.

### Llama Guard 4 12B on the VM (Meta)

This is the same model as the hosted arm, with two things the hosted API can't give.

- **A score.** P(`unsafe`) at the first answer token, the score Meta's papers report. The decision at 0.5 should
  agree with the hosted arm on nearly every row. Where it doesn't, the difference measures DeepInfra's serving.
- **Custom categories.** Meta documents that Llama Guard takes a category list written into its prompt. A second arm
  could add an insults category to fix the content gap, or replace the taxonomy with our eight topic definitions to
  attempt denied topics. Each is a separate arm, and none of them is the out-of-the-box headline.

It needs two L4s or fp8 weights. fp8 is a different precision, recorded in `serving.precision`. Meta's licence must be
approved on the account behind `HF_TOKEN` first. That token gets a 403 today.

### Prompt Guard 2 86M on the VM (Meta)

A DeBERTa-v3 classifier with a softmax over two classes, benign and malicious. Score = P(malicious), decision at 0.5.

| Suite / subtask | Offered | Input mapping | Score |
|---|---|---|---|
| prompt_attacks / direct | yes | the user turn | P(malicious) |
| prompt_attacks / indirect | yes | the document text, which is where an indirect injection sits | P(malicious) |
| everything else | no | | `not_offered` |

- Prompt Guard 2 dropped the separate injection label that Prompt Guard 1 had and targets explicit jailbreak
  techniques. Our policy counts injection without override wording, and leakage probes, as attacks (rulings 2, 3 and
  24), so expect misses there. Disclose it as a coverage gap.
- The window is 512 tokens. Meta's guidance is to split long input into segments and take the highest score, which is
  also what Cloudflare's Guardrails does. That's a different mapping from Laya's cut-from-the-end (ruling 16) and
  needs its own ruling. Indirect rows with long documents will need several segments. A max over segments is no
  longer a calibrated probability.
- It needs the same Meta licence approval as Llama Guard 4. At 86M parameters it adds minutes to a VM session.

## Cloudflare AI Gateway Guardrails (a service, like Bedrock)

AI Gateway is a proxy in front of model providers. With Guardrails on, it checks each prompt, and each response from
the upstream model, before passing them on. The models behind it are Llama Guard 3 8B for S1 to S14 and Prompt Guard 2
86M for P1, prompt injection. Each category is set per gateway to Flag, Block or ignore (omitted), separately for
prompts and responses. A blocked request comes back as an error with code 2016 (prompt blocked) or 2017 (response
blocked). Category detail is only in the gateway logs, linked by an `eventID`. Cloudflare's docs (read 13 November 2026)
add that long content is split into chunks and each chunk is checked, that the underlying models may change without
notice, and that a check adds about 500 ms.

It belongs on the board for the same reason Bedrock does. Buyers use it as a configured product, not as a model, so it
gets Bedrock's treatment. The kind is `service` ("not a decision model"), it's scored at a frozen, documented setting,
and it's unversioned, with the observed date recorded.

| Suite / subtask | Offered | Gateway setting | Input mapping | Decision |
|---|---|---|---|---|
| content / request | yes | prompt: S1, S2, S3, S4, S9, S10, S11, S12 on BLOCK, the rest omitted | the row's turns as a chat request to a small upstream model, user turn last | code 2016 is a block; a normal answer is a pass |
| prompt_attacks / direct | yes | prompt: P1 on BLOCK, everything else omitted | as above | as above |
| prompt_attacks / indirect | open question | as direct | depends on which messages Guardrails reads; the docs don't say | |
| content / reply | open question | response: the content set on BLOCK | Guardrails checks the upstream model's answer, not a reply we supply | |
| denied_topics, word_filters, grounding | no | | | `not_offered` |
| sensitive_info | not checked | AI Gateway has a separate data loss prevention feature | | |

Every row needs a real upstream call, so a passing row also costs a tiny generation. A small Workers AI model with
`max_tokens: 1` keeps that near zero. Each suite needs its own gateway, so the categories it blocks match the policy.
Scores are None, so the arm is binary.

The reply subtask is the hard one. Guardrails only checks responses the upstream model produces. To score our reply
rows, the upstream would have to return each row's reply verbatim, which means a custom provider we run. That's
honest about what gets checked, but it's our plumbing in the measured path. I'd leave reply as `not_offered` at first
and disclose it.

**Before a run.**

- The Cloudflare token in `.env` can't use AI Gateway: listing gateways returned "Authentication error". A token with
  AI Gateway Read and Write is needed. Creating gateways changes the account, so it needs the owner's yes.
- Read the logs API and the logging terms. Cloudflare's logging page says gateways created on or after
  24 September 2026 use Workers Logs pricing and retention.
- Check that chunking applies to both models, and how long rows behave.

**Cost and time.** About 7,000 checks (content requests plus prompt attacks). The Llama Guard 3 check is billed as
Workers AI usage, about USD 0.0001 a short row, and more for long attack rows that get chunked. Add the upstream
1-token calls and the Prompt Guard 2 check, whose price Cloudflare doesn't list. Budget under USD 5. At about a second
a request and ten workers, the run takes about 15 minutes, if the gateway's rate limits allow.

## Reporting suites a system can't attempt

Follow the Bedrock precedent, with one difference: a whole-suite gap means no overall rank.

- The adapter returns `not_offered` with no call. `offers()` is false because the subtask has no entry in
  `CATEGORIES`, or in the self-hosted adapter's key table.
- The implementations file declares the suite as not offered (`leaderboard_v2.evaluate(not_offered=...)`). The
  system then shows on the boards of the suites it ran and appears in `overall.not_ranked` with the reason
  "capability not offered".
- Site: guard models get a label like Bedrock's ("not a decision model") and a note on the row, such as "content only,
  not ranked overall". Cloudflare AI Gateway Guardrails gets Bedrock's `service` kind. Owner question: do guard
  models share that kind, or get their own, such as "safety classifier"? Bedrock and AI Gateway are configurable
  services, and these are models. I'd give the models their own kind.
- Disclosures: one line per system naming the suites it doesn't attempt and the gaps inside the suites it does, such
  as Llama Guard's missing insults category, Nemotron's missing categories and Prompt Guard 2's jailbreak-only
  training. The served mode goes in the same line where it differs from the model card. Self-hosted arms also list
  their truncation counts.

## Recommendation

**Hosted, first: gpt-oss-safeguard-20b.**

- It's the only hosted candidate that can attempt every suite, so it could be ranked overall and compared head to
  head with the decision models.
- Its input is our policy text, unchanged apart from the output section.
- It's cheap and fast. The input price is the lowest of the four, and a full run costs USD 2 to 4 and takes under an
  hour.
- The weights are open under Apache 2.0, so a self-hosted reproduction is possible later.

The risks: a single provider (Groq) with unmeasured rate limits, a reasoning trace that has to be capped, and two open
scope questions (PII and grounding). Settle those before the smoke run.

**Self-hosted, first: Granite Guardian 4.1 8B.** It can attempt all six suites with criteria IBM trained or
documents, it gives a probability, so the secondary metrics apply, and it needs no licence approval. It's the
self-hosted counterpart of safeguard. Run ShieldGemma 9B and Qwen3Guard-Gen-8B in the same VM session, since each
adds under an hour for content (and direct prompt attacks, for Qwen3Guard). Add WildGuard after its overlap scan.
Llama Guard 4 and Prompt Guard 2 join once Meta approves the licence.

**Then: Llama Guard 4 12B, hosted.** It's the classic fixed-taxonomy guard, the content adapter is a small
`VerdictAPIAdapter` subclass with a two-line parser, and the run costs under USD 0.50. Its value is a reference row on
the content board, since it won't be ranked overall. Paired with the VM arm, it also shows what the hosted serving
changes.

**Cloudflare AI Gateway Guardrails** is worth adding once a token with AI Gateway access exists. It's the only other
guardrail product besides Bedrock that buyers configure the same way.

Nemotron and hosted Llama Guard 3 can wait. Nemotron as served loses the categories and policy mode that make it
interesting. Llama Guard 3 duplicates Llama Guard 4 on a slower, dearer endpoint, and AI Gateway Guardrails already
measures it in the setting buyers use.

## Rulings the owner would need (from 42)

1. Add gpt-oss-safeguard-20b, pinned to Groq through OpenRouter, on every suite's test rows and the held-back slice. That
   approves sending the held-back rows to OpenRouter and Groq. It also fixes the reasoning effort, the output section's
   wording, and whether PII and grounding are offered.
2. Add Llama Guard 4 12B on the content suite, pinned to `deepinfra/bf16`, with the declared category set (S1, S2, S3,
   S4, S9, S10, S11, S12), and approve sending held-back content rows to OpenRouter and DeepInfra.
3. Show a system that is not ranked overall on the per-suite boards, with its own kind label.
4. Add the self-hosted guards on the VM, each pinned to a Hugging Face commit, on every suite they attempt, with the
   held-back slice going only to the VM. This settles:
   - Granite Guardian: built-in criteria or our policy text, per subtask; the nine-pass PII design.
   - ShieldGemma: Google's four guidelines as the headline arm.
   - Qwen3Guard: strict or loose for `Controversial`, and whether indirect prompt attacks are offered.
   - WildGuard: whether direct prompt attacks are offered, after the overlap scan.
   - Every model: the rule for rows longer than its window.
   - The VM machine type and spend cap.
5. Add Cloudflare AI Gateway Guardrails as a service on content requests and prompt attacks, with the frozen gateway
   settings above. This approves creating the gateways and a token with AI Gateway access, and sending the held-back
   rows to Cloudflare. It also decides whether reply rows stay `not_offered`.
6. If Nemotron or WildGuard is added: the contamination scan and exclusion rule. The pplx-decider precedent excluded
   matching rows for every system.
7. If Prompt Guard 2 is added: the 512-token rule, either segment-and-max or truncate.

Each run then gets its own freeze manifest under `benchmark/subsets/edition2/`, committed before its first test call,
and tariff entries in `tariffs.json` checked on the day. The VM runs' cost entries follow the Strands and Liquid
precedent: a share of the GPU hours.

## Later

- Nemotron 3.5 Content Safety on the VM, with the documented template arguments. That unlocks its categories and
  custom-policy mode, which would let it attempt topics, prompt attacks and profanity with our policy text.
- Custom-category arms for Llama Guard 4 and ShieldGemma (see their sections).
- gpt-oss-safeguard-120b, if the 20B result is worth following up. I didn't check whether OpenRouter lists it.
- Granite Guardian 4.1's GGUF build or the smaller Granite Guardian 3.2 models, if a cheaper self-hosted arm is wanted.
