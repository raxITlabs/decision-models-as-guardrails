# Edition 2 smoke test

This is a compatibility check of the edition 2 adapters and the frozen e2 question sets. It is not a scored run. There
is no manifest and no freeze, and nothing here goes into a leaderboard. Rows come only from the public tune split in
`dataset/edition2/build/F*.tune.jsonl`. The script never reads test or private-slice rows, checks that no picked id is
in the private slice, and skips every id in the owner's `EXCLUDED.jsonl` lists.

Command: `uv run python benchmark/runs/e2_smoke.py plan | run | report`. Selection is seeded (`e2-smoke-2026-10-04`).
It takes 20 rows per adapter subtask, round-robin over (row tag, label), and prefers rows that need no owner review.
`word_filters/word` has only 11 tune rows, so it gets 11. The row ids are in `summary.json` under `row_ids`.

The ledgers (`<system>.jsonl`) hold row ids, labels, source names and system outputs. They hold no row text. The script
caps error strings and checks them for row text before writing them. `report` scans every ledger for 8-word runs of any
picked row's text and found 0 rows.

## Round 2, 3 to 4 October 2026 (UTC)

What changed since round 1:

- Word filters (F4) now have tune rows, so `word_filters/word` and `word_filters/profanity` ran for every system.
- Laya ran again on all eight subtasks through the adapter that reads the server's truncation report. Round 1's Laya
  ledger moved to `round1/laya.jsonl`.
- The AWS SSO session was valid this time, so Bedrock ran on every task it offers.
- The F2 rebuild changed the prompt-attack tune split. The seeded draw now picks 20 different rows, and every system
  ran them. The round 1 prompt-attack records stay in the ledgers. `report` leaves them out of the table and counts them
  under `superseded_records` (20 for each Noul system that ran in round 1).

The VM (g2-standard-24, two L4s, us-east4-a) was resumed by `make up` at 23:44 UTC on 3 October and stopped by
`make pause` at 23:53, about 9 minutes. `make status` then showed it TERMINATED. Jev and Bedrock ran before the VM
started. "Correct" is a sanity reading at the fixed 0.5 rule on at most 20 rows. It is not a score.

| System | Task | Rows | Failed | Not offered | Truncated (Laya, from usage) | Truncation reported | Correct |
|---|---|---|---|---|---|---|---|
| bedrock-guardrails | content/reply | 20 | 0 | 0 | n/a | n/a | 12/20 |
| bedrock-guardrails | content/request | 20 | 0 | 0 | n/a | n/a | 15/20 |
| bedrock-guardrails | denied_topics/topic | 20 | 0 | 20 | n/a | n/a | 0/0 |
| bedrock-guardrails | grounding/grounding | 20 | 0 | 0 | n/a | n/a | 16/20 |
| bedrock-guardrails | prompt_attacks/direct | 20 | 0 | 0 | n/a | n/a | 16/20 |
| bedrock-guardrails | sensitive_info/entity_detection | 20 | 0 | 0 | n/a | n/a | 18/20 |
| bedrock-guardrails | word_filters/profanity | 20 | 0 | 0 | n/a | n/a | 9/20 |
| bedrock-guardrails | word_filters/word | 11 | 0 | 0 | n/a | n/a | 11/11 |
| jev-1.13.0 | content/reply | 20 | 0 | 0 | n/a | n/a | 12/20 |
| jev-1.13.0 | content/request | 20 | 0 | 0 | n/a | n/a | 18/20 |
| jev-1.13.0 | denied_topics/topic | 20 | 0 | 0 | n/a | n/a | 20/20 |
| jev-1.13.0 | grounding/grounding | 20 | 0 | 0 | n/a | n/a | 19/20 |
| jev-1.13.0 | prompt_attacks/direct | 20 | 0 | 0 | n/a | n/a | 14/20 |
| jev-1.13.0 | sensitive_info/entity_detection | 20 | 0 | 0 | n/a | n/a | 20/20 |
| jev-1.13.0 | word_filters/profanity | 20 | 0 | 0 | n/a | n/a | 15/20 |
| jev-1.13.0 | word_filters/word | 11 | 0 | 0 | n/a | n/a | 10/11 |
| kev-0-8b | content/reply | 20 | 0 | 0 | n/a | n/a | 11/20 |
| kev-0-8b | content/request | 20 | 0 | 0 | n/a | n/a | 17/20 |
| kev-0-8b | denied_topics/topic | 20 | 0 | 0 | n/a | n/a | 10/20 |
| kev-0-8b | grounding/grounding | 20 | 0 | 0 | n/a | n/a | 14/20 |
| kev-0-8b | prompt_attacks/direct | 20 | 0 | 0 | n/a | n/a | 12/20 |
| kev-0-8b | sensitive_info/entity_detection | 20 | 0 | 0 | n/a | n/a | 14/20 |
| kev-0-8b | word_filters/profanity | 20 | 0 | 0 | n/a | n/a | 12/20 |
| kev-0-8b | word_filters/word | 11 | 0 | 0 | n/a | n/a | 6/11 |
| kev-4b | content/reply | 20 | 0 | 0 | n/a | n/a | 10/20 |
| kev-4b | content/request | 20 | 0 | 0 | n/a | n/a | 17/20 |
| kev-4b | denied_topics/topic | 20 | 0 | 0 | n/a | n/a | 20/20 |
| kev-4b | grounding/grounding | 20 | 0 | 0 | n/a | n/a | 16/20 |
| kev-4b | prompt_attacks/direct | 20 | 0 | 0 | n/a | n/a | 17/20 |
| kev-4b | sensitive_info/entity_detection | 20 | 0 | 0 | n/a | n/a | 14/20 |
| kev-4b | word_filters/profanity | 20 | 0 | 0 | n/a | n/a | 15/20 |
| kev-4b | word_filters/word | 11 | 0 | 0 | n/a | n/a | 7/11 |
| kev-9b | content/reply | 20 | 0 | 0 | n/a | n/a | 15/20 |
| kev-9b | content/request | 20 | 0 | 0 | n/a | n/a | 16/20 |
| kev-9b | denied_topics/topic | 20 | 0 | 0 | n/a | n/a | 19/20 |
| kev-9b | grounding/grounding | 20 | 0 | 0 | n/a | n/a | 15/20 |
| kev-9b | prompt_attacks/direct | 20 | 0 | 0 | n/a | n/a | 17/20 |
| kev-9b | sensitive_info/entity_detection | 20 | 0 | 0 | n/a | n/a | 18/20 |
| kev-9b | word_filters/profanity | 20 | 0 | 0 | n/a | n/a | 14/20 |
| kev-9b | word_filters/word | 11 | 0 | 0 | n/a | n/a | 6/11 |
| laya | content/reply | 20 | 0 | 0 | 6 | 0/20 | 13/20 |
| laya | content/request | 20 | 0 | 0 | 2 | 0/20 | 14/20 |
| laya | denied_topics/topic | 20 | 0 | 0 | 0 | 0/20 | 10/20 |
| laya | grounding/grounding | 20 | 0 | 0 | 12 | 0/20 | 10/20 |
| laya | prompt_attacks/direct | 20 | 0 | 0 | 4 | 0/20 | 11/20 |
| laya | sensitive_info/entity_detection | 20 | 0 | 0 | 2 | 0/20 | 13/20 |
| laya | word_filters/profanity | 20 | 0 | 0 | 0 | 0/20 | 10/20 |
| laya | word_filters/word | 11 | 0 | 0 | 0 | 0/11 | 7/11 |
| open-jev-2b | content/reply | 20 | 0 | 0 | n/a | n/a | 17/20 |
| open-jev-2b | content/request | 20 | 0 | 0 | n/a | n/a | 16/20 |
| open-jev-2b | denied_topics/topic | 20 | 0 | 0 | n/a | n/a | 19/20 |
| open-jev-2b | grounding/grounding | 20 | 0 | 0 | n/a | n/a | 11/20 |
| open-jev-2b | prompt_attacks/direct | 20 | 0 | 0 | n/a | n/a | 10/20 |
| open-jev-2b | sensitive_info/entity_detection | 20 | 0 | 0 | n/a | n/a | 19/20 |
| open-jev-2b | word_filters/profanity | 20 | 0 | 0 | n/a | n/a | 10/20 |
| open-jev-2b | word_filters/word | 11 | 0 | 0 | n/a | n/a | 8/11 |

The table counts only rows in the current selection. Reruns for the determinism check are not in it.

## What the smoke found

**No transport failures.** Every Noul call came back, and every decision answer was a probability in [0, 1].

**Bedrock grounding, rerun on 4 October.** The first run failed 6 of 20 grounding rows, all FaithDial rows with earlier
turns in `context`, which the adapter refused (`UnrepresentableState`). The adapter now folds those turns into the
query block as a role-labelled transcript, keeps the source block as the source alone, and marks a row over Bedrock's
documented character caps `not_offered` (none of these 20 is over). The rerun sent the 20 grounding rows again: 20
decided, 0 failed, 0 not offered, 16 of 20 correct. The first run's 20 grounding records are kept in
`round2/bedrock-guardrails.grounding.jsonl`. Bedrock says conversational QA is not a supported grounding use case, and
each result records the mapping in `serving.grounding_mapping`. Denied topics stay `not_offered` because the 8-topic
edition 2 guardrail does not exist yet.

**Laya's server on the VM does not report truncation yet.** All 151 Laya rows have `truncation_reported: false` and
`truncated: null`. The disk still holds the old `laya_server.py`, because `terraform plan` shows the new script only as
a pending in-place metadata update. Nobody applied it in this round. Laya still runs at the checkpoint's 512 tokens.
Startup passes no `--max-len`, so the new server would also use 512. Truncation can still be read from usage, which
caps at 512 times the question count: 26 of 151 rows hit the cap. The counts by task are grounding 12, content reply 6,
prompt attacks 4, content request 2 and PII 2. No topic or word-filter row hit it. To get the per-row report, run
`terraform apply` in `infra/gcp` while the VM is stopped (one in-place metadata change), then rerun Laya.

**Word filters work on every system.** 0 failures on 31 rows each. Bedrock's custom-words guardrail got 11/11 on the
words subtask but only 9/20 on profanity. Jev got 10/11 and 15/20.

**Determinism.** Re-sending 5 rows gave identical scores on Bedrock and all five self-hosted models. Jev moved by at most
0.02.

## Before the full run

1. Apply the pending metadata change so Laya's server reports truncation, and decide whether to raise its `--max-len`.
2. Done: Bedrock grounding rows that carry `context` now run (see above).
3. Create the 8-topic edition 2 Bedrock guardrail, or keep denied topics `not_offered` for Bedrock.
4. Terraform state for this VM lives in the worktree (`infra/gcp/terraform.tfstate`), not in the main checkout.
   Move it back before anyone runs `make down` from the main checkout, or that command will not see the VM.
