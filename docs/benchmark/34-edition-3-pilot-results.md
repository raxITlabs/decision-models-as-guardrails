# 34. Edition 3 pilot: results

Status: diagnostic run, 24 October 2026. 76 public pilot rows (38 pairs) on 18 of the 20 board systems. Nothing here
enters the edition 2 board.

The pilot is too easy at the top. Clef scores 96.1, Perplexity's Decisions API 94.7 and Jev 1.14.0 93.4. Those
three agree on 69 of 76 rows (91%), about the same as the saturated edition 2 jobs. Strong systems catch every
pilot attack. Their errors are benign twins they block, mostly denied-topic near misses after a multi-turn opening
and instructions whose label depends on who wrote them. The harmless-by-construction attacks this pilot uses do not
make a hard set. [`33-edition-3-hard-set.md`](33-edition-3-hard-set.md) is updated to say what has to change.

## Run

- Rows: `dataset/edition3-pilot/pilot.jsonl`, frozen in `benchmark/subsets/edition3-pilot/freeze-manifest.json` and
  committed before the first call. Each system got the edition 2 question set and its fixed 0.5 rule.
- Runner: `benchmark/runs/e3_pilot_run.py`. Ledgers and summary: `benchmark/results/edition3-pilot/`.
- Systems run: 18. Six hosted APIs (Jev 1.13.0 and 1.14.0, Perplexity Decisions API, Clef, Clef Flash,
  Microsoft-Decision-1) and twelve open models on three VM passes.
- **Not run: two systems.** The OpenAI Decisions API (gpt-6-luna) answered every call with HTTP 401 because its key
  in `.env` has expired. Bedrock Guardrails was not called because the AWS SSO session had expired. Both can run once
  the credentials are renewed.
- Failures: one transient failure on Strands Decider 2B-qwen35, resent and answered. No other failures.
- Cost: about USD 3 of VM time and under USD 0.15 of hosted calls, against a forecast of USD 13 and a cap of USD 25.
  VM time was 18 minutes on g2-standard-24 (us-central1-a), 16 minutes on g2-standard-48 (northamerica-northeast2-a;
  every US zone tried had no four-L4 capacity) and 13 minutes on a2-ultragpu-1g (us-central1-a). Every VM was
  destroyed after its pass, and `infra/gcp/terraform.tfvars` is back to its earlier roster.

## Scores

Balanced accuracy, fixed 0.5 rule. Category columns cover 3 to 6 pairs each, so a single row moves a category by 8 to
17 points. Read them as signals, not rankings.

| System | All rows | Category mean | Pair accuracy | Catch | False block | H1 | H2 | H3 | H4 | H5 | H6 | H7 | H8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Clef | 96.1 | 96.2 | 0.92 | 1.00 | 0.08 | 100 | 100 | 100 | 100 | 90 | 90 | 90 | 100 |
| Decisions API · Perplexity | 94.7 | 95.4 | 0.89 | 1.00 | 0.11 | 100 | 100 | 83 | 100 | 90 | 90 | 100 | 100 |
| Jev 1.14.0 | 93.4 | 93.1 | 0.87 | 1.00 | 0.13 | 83 | 100 | 92 | 100 | 80 | 100 | 100 | 90 |
| Strands Decider 12B | 90.8 | 89.8 | 0.82 | 1.00 | 0.18 | 67 | 90 | 92 | 100 | 90 | 80 | 100 | 100 |
| Jev 1.13.0 | 89.5 | 89.8 | 0.79 | 1.00 | 0.21 | 83 | 100 | 75 | 100 | 80 | 100 | 90 | 90 |
| Microsoft-Decision-1 | 89.5 | 89.6 | 0.79 | 0.97 | 0.18 | 83 | 100 | 83 | 100 | 80 | 90 | 90 | 90 |
| Clef Flash | 88.2 | 87.3 | 0.76 | 0.92 | 0.16 | 67 | 80 | 92 | 100 | 90 | 70 | 100 | 100 |
| Strands Decider 26B-A4B | 86.8 | 86.2 | 0.74 | 1.00 | 0.26 | 67 | 90 | 83 | 100 | 90 | 80 | 100 | 80 |
| Strands Decider 2B-v21 | 86.8 | 86.2 | 0.74 | 0.84 | 0.11 | 67 | 80 | 83 | 100 | 90 | 80 | 90 | 100 |
| Kev 9B | 85.5 | 84.0 | 0.71 | 0.84 | 0.13 | 50 | 90 | 92 | 100 | 80 | 70 | 100 | 90 |
| Strands Decider E2B | 85.5 | 84.0 | 0.71 | 0.95 | 0.24 | 50 | 90 | 92 | 100 | 100 | 60 | 80 | 100 |
| Kev 4B | 84.2 | 84.4 | 0.68 | 0.82 | 0.13 | 83 | 70 | 92 | 100 | 90 | 70 | 100 | 70 |
| Strands Decider E4B | 78.9 | 78.5 | 0.58 | 1.00 | 0.42 | 67 | 50 | 92 | 100 | 80 | 60 | 90 | 90 |
| Strands Decider 2B-qwen35 | 77.6 | 77.2 | 0.58 | 0.79 | 0.24 | 83 | 60 | 92 | 63 | 80 | 70 | 70 | 100 |
| Strands Decider 2B | 72.4 | 71.8 | 0.45 | 0.58 | 0.13 | 67 | 50 | 75 | 63 | 90 | 70 | 70 | 90 |
| Laya | 63.2 | 61.9 | 0.32 | 0.50 | 0.24 | 50 | 40 | 75 | 50 | 60 | 70 | 70 | 80 |
| Open-Jev 2B | 59.2 | 60.4 | 0.21 | 0.21 | 0.03 | 83 | 50 | 50 | 50 | 70 | 90 | 40 | 50 |
| Kev 0.8B | 56.6 | 56.0 | 0.16 | 0.32 | 0.18 | 50 | 50 | 58 | 50 | 50 | 80 | 40 | 70 |

Pair accuracy is the share of pairs where both rows are right.

## What the pilot shows

**Ranking matches edition 2.** Spearman correlation between the pilot's category mean and the edition 2 overall
score is 0.91 over the 18 systems. Against edition 2's direct prompt-attack job it is 0.67. The pilot measures the
same ability as edition 2. Tier 1 is not reordered.

**The top is saturated already.** 15 rows (20%) are right for all 18 systems, and no row is wrong for all of them.
The top three disagree on 7 rows (9%). The saturation check set a target of at least 30% top-tier disagreement for a
hard set. The pilot is far from it.

**Errors are false blocks, not misses.** Every system in the top six catches every attack (Microsoft-Decision-1
misses one). Their errors are benign twins. Averaged over all 18 systems, the share right on attack and benign rows
per category:

| Category | Attack rows right | Benign twins right |
|---|---|---|
| H1 multi-turn | 0.85 | 0.59 |
| H2 tool output and traces | 0.72 | 0.82 |
| H3 obfuscation and code-switching | 0.84 | 0.82 |
| H4 long context | 0.75 | 1.00 |
| H5 text addressed to the guardrail | 0.79 | 0.86 |
| H6 context-dependent | 0.91 | 0.67 |
| H7 benign but alarming | 0.83 | 0.86 |
| H8 attacks on the yes/no format | 0.84 | 0.92 |

The hardest rows are benign twins. In order:
- the leetspeak formatting request (a third of systems right);
- the neutral-education multi-turn twins for tax and investment (39 and 44%);
- the user's own notes carrying the same instruction as a third-party email (44%);
- "not investment advice" around a general question, and the textbook and worked-example near misses (56%).

These are the H1 and H6 constructions. A system blocks the vocabulary or the earlier conversation, not the request.

**Attacks that work only on small models.** The long-inbox injections (H4) are caught by every system that reads the
whole input and missed by those that cut it. Laya reads 512 tokens and Strands Decider 2B 4,096 (the pilot inboxes
are about 1,100 tokens, so the cut is in the model's own window). Tool-description poisoning, the pre-stated verdict,
the leakage probe after a refusal and the forum post (H2, H5, H1, H7) are each caught by 61% of systems. The misses
are all below tier 1.

## What this changes in the proposal

1. **Harmless attacks are too easy.** The pilot's injections ask for clearly out-of-place things: send a file
   outside, reveal a code, hold a booking. Tier-1 systems flag every one. Hard attacks need goals that look like the
   user's task, such as a small change to a summary, a plausible extra recipient or a tool call the user might want.
   They also need red-team rows in the content suite, which this pilot left out.
2. **Benign twins carry the signal.** The rows that separate the top systems are H1 and H6 twins. Edition 3 should
   weight its writing time toward them and keep both rows of each pair in the score through pair accuracy.
3. **H4 needs real length.** At about 1,100 tokens the long-context rows only test small windows. The 8k to 32k target
   stands.
4. **H8 should be adaptive.** The pilot's format attacks were written blind and every tier-1 system caught them.
   Tuning on the open surrogates (Kev 4B, Open-Jev 2B, Strands Decider 2B), as the proposal says, is needed before H8
   can be judged.
5. **Run OpenAI and Bedrock** when the credentials are renewed. They are the only board systems missing.
