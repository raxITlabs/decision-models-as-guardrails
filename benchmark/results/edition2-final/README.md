# Edition 2 results: all six suites

Twelve systems, every edition 2 test row and the unpublished slice: 7,770 public test rows and 2,283 unpublished
rows, 10,053 rows per system. `leaderboard.json` reports `valid_for_publication: true` with no publication blocker.

Three runs feed it. The full run of 5 October 2026 (`../edition2-full/`) supplies content, denied topics, profanity,
PII and grounding for the first eleven systems. Their test files are byte-identical to that run's, so its answers are
reused as they are. Prompt attacks were rerun on 6 October 2026 on the r26 suite (`../edition2-attacks-r26/`), which
owner ruling 28 made the scored prompt-attack suite. gpt-6-luna, OpenAI's Decisions API model, ran all six suites on
7 October 2026 on the same rows (`../edition2-openai/`). `leaderboard_v2` scored all three in frozen mode at the fixed
0.5 rule, against the full run's freeze manifest and two extension manifests, each committed before its run's first
call (`benchmark/subsets/edition2/freeze-manifest-prompt-attacks-r26.json` and
`benchmark/subsets/edition2/freeze-manifest-gpt-6-luna.json`). Every record carries its own manifest's sha256 and
post-dates that manifest's commit. The scorer also checks the contract change from Git: the only suite that changed
since the first freeze is prompt attacks.

There is no latency here. The leaderboard compares accuracy and cost (owner ruling 22).

```
uv run python benchmark/runs/e2_attacks_rerun.py plan --source local       # prompt-attack rerun: rows and forecast
uv run python benchmark/runs/e2_attacks_rerun.py freeze --source local     # its extension manifest, committed first
uv run python benchmark/runs/e2_attacks_rerun.py all --source local        # hosted systems and the VM, retry passes
uv run python benchmark/runs/e2_openai_run.py plan --source local          # gpt-6-luna: rows and forecast
uv run python benchmark/runs/e2_openai_run.py freeze --source local        # its extension manifest, committed first
uv run python benchmark/runs/e2_openai_run.py all --source local           # all six suites, retry passes
uv run --with scikit-learn python benchmark/runs/e2_openai_run.py score --source local   # this folder's leaderboard.json
uv run --with matplotlib python benchmark/runs/e2_final_plots.py
uv run python benchmark/runs/site_results.py --leaderboard-v2 benchmark/results/edition2-final/leaderboard.json
```

## Scores

Balanced accuracy x 100 at the fixed 0.5 rule. The six suites weigh the same in the overall. Custom words is a
pass/fail sanity check (pass at 95 or higher) outside it, and DRIVER_ID is unscored. Tiers come from Holm-adjusted
paired bootstrap tests against each tier's leader (2,000 replicates, seed 20260923).

| Rank | System | Overall (95% interval) | Tier | Rank interval | Content | Prompt attacks | Denied topics | Profanity | PII | Grounding | Custom words |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pplx-decider-v1-27b | 89.5 (88.8 to 90.1) | 1 | 1-2 | 84.7 | 77.1 | 98.6 | 90.2 | 98.2 | 88.1 | fail (73) |
| 2 | gpt-6-luna | 89.2 (88.5 to 89.8) | 1 | 1-3 | 82.4 | 76.5 | 98.4 | 93.6 | 95.6 | 88.6 | fail (92) |
| 3 | Clef | 88.7 (87.9 to 89.3) | 1 | 2-3 | 81.5 | 80.3 | 98.8 | 87.7 | 98.2 | 85.5 | fail (89) |
| 4 | Jev 1.13.0 | 87.5 (86.8 to 88.2) | 2 | 4-4 | 79.3 | 75.4 | 97.1 | 83.7 | 98.2 | 91.2 | fail (90) |
| 5 | Clef-flash | 81.1 (80.2 to 81.9) | 3 | 5-6 | 80.1 | 71.6 | 84.3 | 83.9 | 97.7 | 69.0 | fail (66) |
| 6 | Kev-4B | 80.6 (79.9 to 81.4) | 3 | 5-6 | 79.4 | 65.9 | 97.8 | 78.9 | 96.1 | 65.8 | fail (61) |
| 7 | Kev-9B | 79.5 (78.7 to 80.3) | 4 | 7-7 | 81.1 | 61.3 | 91.8 | 77.2 | 97.3 | 68.5 | fail (58) |
| 8 | Bedrock Guardrails | 78.3 (77.5 to 79.2) | 4 | 8-8 | 79.8 | 68.1 | 84.6 | 71.6 | 98.2 | 67.7 | pass (100) |
| 9 | Strands Decider 2B | 74.8 (73.9 to 75.7) | 5 | 9-9 | 67.9 | 54.7 | 85.2 | 79.6 | 95.1 | 66.4 | fail (59) |
| 10 | Open-Jev-2B | 66.3 (65.6 to 67.1) | 6 | 10-11 | 62.7 | 51.3 | 81.4 | 59.4 | 89.9 | 53.1 | fail (69) |
| 11 | Kev-0.8B | 65.8 (64.9 to 66.7) | 6 | 10-11 | 62.1 | 51.8 | 69.6 | 64.6 | 90.7 | 55.7 | fail (55) |
| 12 | Laya | 60.7 (59.7 to 61.6) | 7 | 12-12 | 68.3 | 53.9 | 63.0 | 65.9 | 71.7 | 41.4 | fail (59) |

| System | Catch rate | False-block rate | USD per 1,000 checks | USD total | First-pass failures | Failed after retries | Truncated rows |
|---|---|---|---|---|---|---|---|
| pplx-decider-v1-27b | 0.871 | 0.082 | 0.056 | 0.56 | 0 | 0 | 0 |
| gpt-6-luna | 0.910 | 0.126 | 0.110 | 1.10 | 10 | 10 | 0 |
| Clef | 0.901 | 0.128 | 0.202 | 2.03 | 28 | 0 | 0 |
| Jev 1.13.0 | 0.871 | 0.122 | 0.039 | 0.39 | 0 | 0 | 0 |
| Clef-flash | 0.793 | 0.171 | 0.076 | 0.76 | 24 | 0 | 0 |
| Kev-4B | 0.701 | 0.089 | 0.228 | 2.29 | 122 | 0 | 0 |
| Kev-9B | 0.688 | 0.097 | 0.123 | 1.23 | 0 | 0 | 0 |
| Bedrock Guardrails | 0.676 | 0.109 | 0.112 | 1.13 | 0 | 0 | 0 |
| Strands Decider 2B | 0.620 | 0.123 | 0.123 | 1.24 | 0 | 0 | 0 |
| Open-Jev-2B | 0.373 | 0.047 | 0.275 | 2.76 | 185 | 0 | 0 |
| Kev-0.8B | 0.520 | 0.205 | 0.140 | 1.41 | 224 | 0 | 0 |
| Laya | 0.446 | 0.232 | 0.149 | 1.50 | 0 | 0 | 3,381 |

Catch and false-block rates are the means over the six suites. Hosted cost is measured usage (tokens, or Bedrock
text units) times the dated list price in `goldrails_bench/tariffs.json`. VM cost is the VM's up-to-paused time at
the dated g2-standard-24 rate plus the disk, split across the six VM models by their share of run time. The full
run's VM time is split over its five kept suites by each suite's share of a system's rows, since that run did not
time suites apart. Failure columns count every run. Every system but gpt-6-luna ended with 0 failed rows.
gpt-6-luna's 10 are refusals (see below); they count as wrong.

## Prompt attacks

Two subtasks with equal weight. Direct rows are one user message, tagged injection, jailbreak or leakage. Indirect
rows are a document the assistant reads (an email, a tool result, a passage) with the system prompt and the user's
task in the context. The tag columns re-score each system on that tag's rows alone, as a diagnostic. The last row is
the best full-text n-gram classifier from the build's confounds gate (grouped five-fold CV on test and unpublished
rows, balanced accuracy at probability 0.5): a reference for how much plain wording explains, not a system.

| System | Prompt attacks | Direct | Indirect | Injection | Jailbreak | Leakage | Indirect (tag) | Catch (direct / indirect) | False block (direct / indirect) |
|---|---|---|---|---|---|---|---|---|---|
| pplx-decider-v1-27b | 77.1 | 69.1 | 85.1 | 73.3 | 65.1 | 82.2 | 85.1 | 0.858 / 0.722 | 0.477 / 0.020 |
| gpt-6-luna | 76.5 | 66.7 | 86.2 | 73.3 | 63.0 | 78.1 | 86.2 | 0.831 / 0.765 | 0.496 / 0.041 |
| Clef | 80.3 | 71.2 | 89.4 | 73.7 | 66.8 | 85.1 | 89.4 | 0.869 / 0.860 | 0.445 / 0.073 |
| Jev 1.13.0 | 75.4 | 66.7 | 84.1 | 71.2 | 62.6 | 80.3 | 84.1 | 0.858 / 0.722 | 0.523 / 0.040 |
| Clef-flash | 71.6 | 70.1 | 73.1 | 75.1 | 70.3 | 73.5 | 73.1 | 0.785 / 0.481 | 0.383 / 0.019 |
| Kev-4B | 65.9 | 71.3 | 60.4 | 80.0 | 74.3 | 64.2 | 60.4 | 0.626 / 0.227 | 0.200 / 0.019 |
| Kev-9B | 61.3 | 70.3 | 52.3 | 81.1 | 70.8 | 67.1 | 52.3 | 0.644 / 0.056 | 0.239 / 0.009 |
| Bedrock Guardrails | 68.1 | 66.6 | 69.6 | 78.7 | 67.4 | 63.0 | 69.6 | 0.629 / 0.420 | 0.298 / 0.028 |
| Strands Decider 2B | 54.7 | 59.7 | 49.6 | 61.5 | 66.3 | 50.2 | 49.6 | 0.399 / 0.039 | 0.206 / 0.046 |
| Open-Jev-2B | 51.3 | 52.1 | 50.6 | 50.2 | 53.5 | 51.2 | 50.6 | 0.068 / 0.012 | 0.027 / 0.000 |
| Kev-0.8B | 51.8 | 53.3 | 50.3 | 51.8 | 53.3 | 55.0 | 50.3 | 0.127 / 0.212 | 0.062 / 0.207 |
| Laya | 53.9 | 56.3 | 51.5 | 56.6 | 55.3 | 62.6 | 51.5 | 0.831 / 0.120 | 0.705 / 0.090 |
| n-gram baseline (best full-text model) | - | - | - | 80.2 | 80.9 | 89.3 | 88.7 | - | - |

Interval and tier per subtask (95% bootstrap):

| Subtask | Tier 1 |
|---|---|
| Direct | Kev-4B 71.3 (69.6 to 73.1), Clef 71.2, Kev-9B 70.3, Clef-flash 70.1, pplx-decider 69.1 |
| Indirect | Clef 89.4 (86.8 to 91.5) |

## gpt-6-luna

gpt-6-luna ties for first. Its overall score, 89.2 (88.5 to 89.8), is 0.3 points behind pplx-decider-v1-27b and 0.5
ahead of Clef, and neither gap is significant (Holm-adjusted p 0.90 and 0.77), so all three share tier 1. It is 1.7
points ahead of Jev, a significant gap. It has the highest catch rate of the twelve (0.910) with a false-block rate
of 0.126, close to Clef's (0.901 and 0.128). It costs USD 0.110 per 1,000 checks, twice pplx-decider's 0.056 and about
half of Clef's 0.202.

Per suite it leads profanity (93.6) and is second on content (82.4) and grounding (88.6). Denied topics is 98.4, in
tier 1 with the other hosted models. PII is its weak suite: 95.6, eighth, in tier 3. Nine of its ten refusals are PII
rows, seven of them on the Social Security number question, and each refused row counts as wrong.

On prompt attacks it scores 76.5, close to pplx-decider (77.1) and Jev (75.4), behind Clef (80.3). Indirect attacks
come out at 86.2, second to Clef's 89.4, with a 4.1% false-block rate; the gap to Clef puts it in tier 2. Like
the other hosted models it struggles on direct attacks: 66.7, catching 83% of attacks but blocking half (49.6%) of
the benign direct rows. The n-gram baseline beats it on every direct tag.

### Content with and without OpenAI's own rows

208 public content test rows and 36 unpublished ones come from OpenAI's moderation evaluation set, all of them
request rows. OpenAI may have trained or tuned gpt-6-luna on that set, so content is also scored without those rows.
gpt-6-luna does better without them, 83.3 against 82.4. On the OpenAI rows alone it catches 81 of 87 harmful rows but
blocks 74 of 157 benign ones. So the vendor's own rows hold its score down rather than up. The view is secondary and
never ranked; the headline uses all rows.

| System | Content, all rows | Without OpenAI's rows | Difference | Without all vendor-owned rows |
|---|---|---|---|---|
| pplx-decider-v1-27b | 84.7 | 85.2 | +0.4 | 84.7 |
| gpt-6-luna | 82.4 | 83.3 | +0.9 | 82.8 |
| Clef | 81.5 | 81.6 | +0.1 | 80.2 |
| Jev 1.13.0 | 79.3 | 80.0 | +0.7 | 79.0 |
| Clef-flash | 80.1 | 80.0 | -0.1 | 78.7 |
| Kev-4B | 79.4 | 80.0 | +0.6 | 79.3 |
| Kev-9B | 81.1 | 81.8 | +0.7 | 81.4 |
| Bedrock Guardrails | 79.8 | 80.0 | +0.2 | 79.8 |
| Strands Decider 2B | 67.9 | 68.2 | +0.2 | 67.1 |
| Open-Jev-2B | 62.7 | 62.6 | -0.1 | 61.2 |
| Kev-0.8B | 62.1 | 62.5 | +0.3 | 61.4 |
| Laya | 68.3 | 68.3 | +0.0 | 67.8 |

## What the prompt-attack rerun found

pplx-decider-v1-27b still leads overall, but Clef now shares tier 1 with it. On the old prompt-attack suite Clef
scored 81.7; on r26 it scores 80.3 and is the best prompt-attack system, ahead of pplx-decider at 77.1. Jev drops to
tier 2 on its own. Clef-flash moves up to fourth, above Kev-4B and Kev-9B. Bedrock stays seventh and the bottom
four keep their order.

Indirect attacks split the field. Clef, pplx-decider and Jev score 84 to 89, with AUROC around 0.96, and false-block
rates of 2 to 7%. The small self-hosted models are at chance. Kev-9B, Strands, Laya, Kev-0.8B and Open-Jev-2B score
50 to 52 on indirect rows. Most of them pass nearly every document, attack or not; Kev-0.8B flags about a fifth of
attack and benign documents alike. Bedrock catches 42% of indirect attacks. Clef is the only system above the n-gram
baseline on indirect rows (89.4 against 88.7).

Direct attacks are hard for everyone. No system beats 72, and the n-gram baseline (80 to 89 per tag) beats every
system on every direct tag except Kev-9B on injection (81.1 against 80.2). pplx-decider, Clef and Jev catch about
86% of direct attacks but block 45 to 52% of the benign direct rows. Three kinds of benign row draw those blocks:
requests to translate, classify or discuss a quoted jailbreak (over 90% blocked), WildJailbreak prompts that wrap a
harmless request in jailbreak tactics (41 to 60%), and in-the-wild role and persona prompts that never ask to drop
the rules (about 70%). The policy counts all three as safe. Kev-4B and Kev-9B block 20 to 24% of benign direct rows,
so they score higher on direct rows while catching fewer attacks.

Injection has 151 attack and 167 benign public test rows, under the 250-row floor for each class; its interval is
wider than the other subtasks'. The tag scores above include the unpublished slice.

The public-versus-unpublished re-score moves no system by more than 2.4 points (Laya, which scores higher on the
unpublished slice). `unpublished_slice_view` in `leaderboard.json` has every number.

## Disclosures

- gpt-6-luna's Decisions API takes one text string or user messages, with no system, assistant or tool role. Each row
  goes to it as one string: earlier turns as `Role: text` lines, then the source document and the query when the row
  has them, then the text under review labelled with its role. Retrieved content (indirect prompt attacks) carries the
  `[Untrusted retrieved content]` tag, as Bedrock's does. Each yes/no question becomes a predicate made of the
  question's instructions and its true and false criteria, and all of a row's questions go in one request. Content's
  severity question is not sent: it is a score, outside every decision list.
- gpt-6-luna refused one question on 10 of its 10,053 rows (9 PII rows, 1 content row). The API answered
  `{"type": "refusal"}` with no probability, which its docs do not describe. Two retry passes got the same answer.
  The rows count as failures, wrong in their class: 0.1% of its rows and 1.25% of its PII rows, under the 2% cap.
- The unpublished slice was sent to OpenAI. Zero Data Retention is offered only to eligible customers under a separate
  agreement, so OpenAI's default API data retention applies to those rows. The owner's waiver of the data-retention
  check for Perplexity (ruling 21) is taken to cover OpenAI too.
- 244 content rows (208 public) come from OpenAI's moderation evaluation set. They stay in the score; the content view
  `excluding_openai_owned` leaves them out.
- gpt-6-luna is a hosted public-beta model with no version pin. Every response reported the model `gpt-6-luna`, and
  OpenAI sent no version header.
- Prompt-attack labels have an AI second label, not a human review: a model with no tools and no file access
  labelled a 400-row blind sample from the policy and the rows, and agreed with the reference label on 95.0% of them
  (Cohen's kappa 0.88).
- On indirect rows, Bedrock's prompt-attack check (InvokeGuardrailChecks) reads three messages: the system prompt,
  the user's task, and the document tagged `[Untrusted retrieved content]`, because the API has no tool role.
- Prompt attacks ran a day after the other suites, under a separate freeze manifest committed before the rerun.
- Laya reads at most 512 tokens per question (owner ruling 16). 3,381 of its 10,053 rows were cut, 1,478 of them
  prompt-attack rows. Strands Decider 2B cuts silently at 4,096 tokens.
- The unpublished slice can be rebuilt from public upstream data (owner ruling 15). It supports a contamination
  check, not a secret test.
- The e2 question-set names that differ from the contract's v1 names are copies with the same questions and decision
  lists.

## Run notes

gpt-6-luna ran on 7 October 2026: 10,053 rows in 17 minutes at 10 requests a second. Forecast: USD 1.11 (high
1.66, cap 30), from the smoke test's measured tokens. Metered cost: USD 1.10 for 11.0 million input tokens. Ten rows
failed on the first pass (refusals), and both retry passes resent them and got the same refusal. The smoke test before
the run sent 177 dev rows with no failure (`../edition2-smoke/gpt-6-luna.jsonl`). All three runs together: USD 16.40.

The prompt-attack rerun sent 4,600 rows to each system: 3,180 direct and 1,420 indirect, 1,381 of them in the
unpublished slice. No row failed in any system, so no retry pass ran. Forecast: USD 8.49 (high 12.73, cap 30).
Metered cost of the rerun: USD 6.06 (hosted USD 1.77, VM USD 4.29).

The VM hit a GPU stockout in us-east4-a. The first start never got a GPU, and that window is left out of the cost
(`vm_no_start` in the run log). Two later starts got a GPU but timed out waiting for the Open-Jev-2B tunnel: an
unrelated local process held port 8791. Those starts cost about 50 minutes of VM time, counted from each `make up`
(stockout retries before the GPU came up included), and they are billed here. Once the port was free, the six
models ran in parallel for 67 minutes and the VM was paused and confirmed TERMINATED.

## Files

- `leaderboard.json`: the frozen-mode result, with `full_run` (all three runs), `prompt_attacks` (per-tag view, n-gram
  baseline, floor exception), `unpublished_slice_view`, `run` (summaries and cost) and `privacy_check`.
- `plots/`: overall, subtask heatmap, catch against false block, score against cost, public against unpublished, and
  prompt attacks by tag.
- Public ledgers: `../edition2-full/<system>.jsonl` (five suites), `../edition2-attacks-r26/<system>.jsonl`
  (prompt attacks) and `../edition2-openai/gpt-6-luna.jsonl` (gpt-6-luna, all six suites). Raw ledgers with
  unpublished ids stay in each folder's git-ignored `private/`.
