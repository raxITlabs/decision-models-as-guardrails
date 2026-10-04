# Adapters (contract v2.0)

From edition 2 the benchmark defines the task, and each system brings an adapter. A task is a suite policy
(`benchmark/policies/<suite>/<subtask>.md`) plus labelled rows. An adapter turns one row into one system's verdict:

```python
result = adapter.evaluate("content", "request", record)
result.decision      # True / False, or None unless decided
result.score         # continuous score where the system returns one, else None
result.per_question  # what the system said per question or category
result.outcome       # "decided" | "failed" | "not_offered"
result.serving       # endpoint, model_id, revision, precision, max_length, date, plus the rule used
```

## The adapters

| Adapter | Systems | Decision | Score |
|---|---|---|---|
| `NoulAdapter` | Jev, Kev, Open-Jev, Laya, any System One server | max over the frozen e2 set's decision Nouls >= 0.5 | that max |
| `BedrockAdapter` | Amazon Bedrock Guardrails | the service's verdict at `FROZEN_SETTING` | severity/confidence (checks), 1 - grounding (grounding), None (binary topics, words) |
| `VerdictAPIAdapter` | base for OpenAI moderation and other vendor APIs | the vendor's own flag | the vendor's category scores, where returned |

Hosted decision models that take System One's request at a different URL use `NoulAdapter` too, through a client in
`goldrails_bench/hosted.py` with the same `ask(state, questions)` shape as `SystemOneClient`:

| Client | System | Notes |
|---|---|---|
| `CloudflareSystemOneClient` | Clef, Clef-flash (Workers AI) | unwraps `{result, success, errors}`; marks `truncated` when `usage.input_tokens` reaches the 65,536-token context |
| `PerplexityDecisionsClient` | pplx-decider-v1-27b | 5 requests/s across threads; Retry-After on 429; 504 is final; fails a response that reports a Jev model name |
| `OpenAIDecisionsClient` | gpt-6-luna | unverified stub; 403 is `AccessPending` and stops further calls |

Strands Decider runs on the GCP VM and uses `SystemOneClient` unchanged. Its 4,096-token window comes from
`endpoints.KIND_MAX_LENGTH` into `serving.max_length`. Clients never retry. They name each transport failure
(`RateLimitError`, `InternalServerError`, `ReadTimeout`...) so the run's retry policy decides. Status and owner steps
are in `docs/benchmark/28-new-decision-models-research.md`, "Onboarding status".

The Noul question sets are the reference adapter for Noul models, not part of the task. They live in
`benchmark/question_sets/e2/` and are frozen for the edition. Bedrock and vendor APIs never see them.

## Outcomes

- `not_offered`: the system has no capability for the subtask. No call is made, the subtask is not evaluated for that
  system, and the system gets no overall rank.
- `failed`: a call was attempted and produced no decision. That covers transport errors after the run's retry
  policy, a row the API cannot represent, and an answer with nothing the rule can score. The scorer counts it as
  wrong, and a run with more than 2% failures is invalid.
- `decided`: `decision` is a bool.

## Serving config

Every result carries `serving`, including failed and not-offered ones. `endpoint`, `model_id`, `revision`,
`precision`, `max_length` and `date` are always present, and a field the system does not expose is `None`, so the
gap shows. `date` is the UTC evaluation date that v2.0 prints beside every score. Pin dated model ids. A vendor's
`-latest` alias makes drift checks meaningless.

## Input truncation (Laya)

Laya's English checkpoint (`convaiinnovations/laya` at the pinned revision) reads at most 512 tokens per question.
That is its own limit. `rl_agent_config.json` sets `max_len: 512` and `head_max_len: 192`, and the model card lists
its context as 512. The ModernBERT-large encoder underneath has 8192 positions, but Laya was trained and calibrated at
512, so the server keeps 512. `laya_server.py --max-len` exists for an experiment and makes a different arm. Each
question is one sequence. If the question and its options run past 192 tokens, the question text is shortened. If the
whole sequence runs past 512, the end of the state is dropped.

`infra/gcp/laya_server.py` measures both cuts on every request with the package's own sequence builder and returns
them in `metadata.truncation`: tokens before and after per question, state tokens kept, and `head_cut`. The tokens
after, summed, equal `usage.input_tokens`. `SystemOneClient` keeps that `metadata` object (the SDK's response model
drops it), and `NoulAdapter` copies it to the result:

- `result.truncated` is True or False for every Laya answer, and None for servers that do not report it.
- `result.truncation` holds the server's report.
- `serving.max_length` is the served 512 unless the identity pins one, with `served_max_length`, `head_max_length`
  and `truncation_reported` beside it. A Laya answer from a server that predates the report has
  `truncation_reported: False` and `truncated: None`, so it never passes as uncut.

On the edition 2 smoke rows, 26 of 120 Laya rows lose part of the state (12 of 20 in grounding), and the
`any_denied_topic` question in `e2-f3-topics` is shortened on every row. Contract v2.0 lists this under
`disclosures`.

## Hugging Face reproductions run sandboxed

A model loaded from the Hugging Face Hub runs in a throwaway VM or container that has no cloud credentials, no
repository secrets and no write access to the ledgers. Copy the outputs out afterwards. `trust_remote_code` stays
disabled. A repository that needs remote code runs only after someone reads the code at the pinned commit and
records the review. Build loader arguments with `sandbox.hf_load_kwargs`. It refuses a branch name as a revision,
and it refuses `trust_remote_code=True` without a review record for that exact commit. Put `sandbox.sandbox_record`
into the result's `serving` so the review travels with the score.

## Adding a vendor

A vendor that answers System One questions at its own URL gets a `HostedDecisionClient` subclass in `hosted.py`
(override `body`, `unwrap`, `on_status` or `check` as needed) and goes through `NoulAdapter`. A vendor with its own
categories gets a `VerdictAPIAdapter`, as below.

Subclass `VerdictAPIAdapter`. Set `CATEGORIES` to the vendor categories each suite policy covers, and leave out the
subtasks it cannot do. Implement `call(state, categories)` to return a `VendorVerdict`. Write tests against a fake
client, then run the compatibility check (20 rows per suite) before any full run.
