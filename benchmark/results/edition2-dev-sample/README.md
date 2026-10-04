# Edition 2 dev-split sample (not a held-out result)

This is a dress rehearsal of the edition 2 full run. Every public dev row (1,422 rows in
`dataset/edition2/build/F*.dev.jsonl`) went to every system that could be reached, and `leaderboard_v2` scored the
answers in diagnostic mode at the contract's fixed 0.5 rule. No test row and no unpublished row was sent. The test split
stays untouched until the owner signs the freeze.

Read every number here as a dev-split sample. These rows were used to build, label and check the dataset (the
shortcut gate, the smoke tests), so they say how the pipeline behaves, not how the systems rank on held-out data.

The dev split was called tune when this ran, and this folder was `edition2-tune-sample`. The rename on 5 October 2026
moved no row (`dataset/edition2/README.md`, "Splits"). The ledgers record no split field and are unchanged.
`leaderboard.json` and the plots were regenerated with the renamed code: every score is identical, and only the
labels and the dataset hash inside each arm id changed, because the dev files now say `dev` in each row.

Run on 4 October 2026 (UTC). Commands:

```
uv run python benchmark/runs/e2_sample.py run --systems jev|clef|clef-flash|perplexity|bedrock
uv run python benchmark/runs/e2_sample.py vm up        # then make up, run --systems open,strands --only <name>, make pause
uv run python benchmark/runs/e2_sample.py report       # run summary and the row-text leak check
uv run python benchmark/runs/e2_sample.py score        # leaderboard.json
uv run python benchmark/runs/e2_sample_plots.py        # plots/
```

## Scores

Balanced accuracy x 100 at the fixed 0.5 rule. Suites have equal weight in the overall score. Custom words is a
pass/fail sanity check (pass at 95 or higher) and is not in the overall. DRIVER_ID is unscored. Prompt attacks are
provisional. Tiers come from Holm-adjusted paired bootstrap tests against each tier's leader (2,000 replicates, seed
20260923).

| Rank | System | Overall (95% interval) | Tier | Content | Prompt attacks (provisional) | Denied topics | Profanity | PII | Grounding | Custom words |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pplx-decider-v1-27b | 89.4 (87.8 to 91.0) | 1 | 78.0 | 83.4 | 99.3 | 85.1 | 99.2 | 91.5 | fail (92) |
| 2 | Clef | 88.0 (86.4 to 89.6) | 1 | 81.1 | 83.6 | 99.3 | 81.9 | 99.3 | 83.1 | fail (92) |
| 3 | Jev 1.13.0 | 87.4 (85.8 to 89.0) | 1 | 74.3 | 81.5 | 98.6 | 79.5 | 99.1 | 91.6 | fail (92) |
| 4 | Clef-flash | 82.8 (80.9 to 84.8) | 2 | 79.6 | 79.4 | 89.2 | 83.6 | 98.1 | 67.0 | fail (75) |
| 5 | Kev-9B | 81.7 (79.7 to 83.6) | 2 | 75.1 | 80.5 | 93.9 | 72.7 | 98.2 | 69.5 | fail (58) |
| 6 | Kev-4B | 81.1 (79.1 to 82.9) | 2 | 72.3 | 78.4 | 99.3 | 72.1 | 96.8 | 67.9 | fail (67) |
| 7 | Bedrock Guardrails | 78.3 (76.1 to 80.4) | 3 | 76.2 | 78.7 | 81.2 | 64.6 | 98.1 | 71.2 | pass (100) |
| 8 | Strands Decider 2B | 77.2 (74.9 to 79.5) | 3 | 67.7 | 67.2 | 88.1 | 77.2 | 92.9 | 70.4 | fail (67) |
| 9 | Kev-0.8B | 65.8 (63.8 to 68.0) | 4 | 61.9 | 55.8 | 67.8 | 59.3 | 91.7 | 58.6 | fail (58) |
| 10 | Open-Jev-2B | 65.1 (63.1 to 67.0) | 4 | 61.3 | 52.1 | 79.3 | 54.8 | 89.8 | 53.4 | fail (75) |
| 11 | Laya | 61.9 (59.3 to 64.2) | 4 | 65.0 | 63.2 | 64.5 | 63.2 | 71.7 | 43.6 | fail (65) |

Bedrock Guardrails ran on 5 October 2026 after a fresh AWS login (1,422 rows, 0 failed, 722 s). It is the only system that passes the custom-words check, because its word filter matches the listed phrases exactly.

| System | Catch rate | False-block rate | Wall time | USD per 1,000 checks | Total | p50 / p95 latency (s) | First-pass failures | Truncated rows |
|---|---|---|---|---|---|---|---|---|
| pplx-decider-v1-27b | 0.867 | 0.079 | 5.3 min | 0.058 | 0.08 | 0.80 / 1.48 | 0 | 0 |
| Clef | 0.889 | 0.128 | 3.7 min | 0.207 | 0.29 | 0.58 / 1.03 | 0 | 0 |
| Jev 1.13.0 | 0.878 | 0.129 | 0.7 min | 0.039 | 0.06 | 0.22 / 0.29 | 0 | 0 |
| Clef-flash | 0.803 | 0.147 | 2.3 min | 0.078 | 0.11 | 0.28 / 0.90 | 0 | 0 |
| Kev-9B | 0.730 | 0.097 | 17.3 min | 0.127 | 0.18 | 0.82 / 4.28 | 0 | 0 |
| Kev-4B | 0.720 | 0.097 | 31.9 min | 0.234 | 0.33 | 1.92 / 7.11 | 9 | 0 |
| Strands Decider 2B | 0.653 | 0.109 | 21.6 min | 0.159 | 0.23 | 1.30 / 5.93 | 0 | 0 |
| Kev-0.8B | 0.510 | 0.193 | 15.0 min | 0.110 | 0.16 | 0.83 / 3.70 | 0 | 0 |
| Open-Jev-2B | 0.354 | 0.052 | 32.6 min | 0.239 | 0.34 | 2.22 / 5.89 | 7 | 0 |
| Laya | 0.507 | 0.269 | 17.3 min | 0.127 | 0.18 | 1.67 / 1.94 | 0 | 318 |

Catch and false-block rates are the means over the six suites. Hosted cost is the measured input tokens times the list
price in `goldrails_bench/tariffs.json`. VM cost is the VM's up-to-paused time (2,517 s over two sessions) at the dated
g2-standard-24 on-demand rate ($1.9943/h) plus the disk, split across the six VM models by their share of run time. The
six VM models ran at the same time on two L4s, so their wall times overlap and their latencies include queueing behind
each other. Latency is per row under each system's own worker count, not a load test.

`leaderboard.json` also holds per-subtask catch rate, false-block rate, F1, AUROC, recall at 5% false blocks,
calibration where it applies, paired differences and rank intervals.

## What the rehearsal found

The top three are not separable on these rows. pplx-decider-v1-27b, Clef and Jev share tier 1 and their intervals
overlap. They get there differently. pplx-decider has the lowest mean false-block rate of the three (0.079 against about
0.13), Clef leads content (81.1) and Jev and pplx-decider lead grounding (91.6 and 91.5, against Clef's 83.1).

Content is the hardest suite for everyone. No system clears 82. Jev's content reply score is 70.3, the lowest of the
top four. It catches 86% of harmful replies but blocks 45% of benign ones at 0.5. The Bedrock-five view (positives in Bedrock's five
categories only) lifts every system by 1.6 to 6.5 points, and dropping the vendor-owned sources lowers every system by 0.8
to 3.1 points. The ranking does not change in either view.

The small open models mostly under-flag at 0.5. Open-Jev-2B catches 35% of positives with a 5% false-block rate, and
its prompt-attack catch rate is 0.05. Kev-0.8B and Laya sit near chance on several suites. These look like calibration
problems at a fixed threshold as much as ranking problems; their AUROCs in `leaderboard.json` show how much a tuned
threshold could recover.

Every system fails the custom-words sanity check. The best score is 91.7 (Jev, Clef and pplx-decider), each with all
5 positives caught and 1 of 6 negatives blocked. With 11 rows, one row decides pass or fail. Check whether that negative
row is labelled the way the policy intends before the freeze.

The training-data overlap barely moves pplx-decider. Dropping the 82 dev rows that match its training or development
data (1 content, 62 prompt-attack, 19 profanity) changes its overall from 89.4 to 89.1. Prompt attacks fall 0.8 and
profanity 0.9. Its rank and tier stay the same. The other systems move by -0.5 to +0.5 points on the same reduced rows
(`pplx_overlap_sensitivity` in `leaderboard.json`, `plots/pplx-overlap.png`).

## Failures, retries and truncation

Bedrock Guardrails first failed on an expired AWS SSO session (`bedrock-guardrails.blocked.json`); it was rerun on 5 October 2026 after `aws sso login`, with no failures.

Sixteen VM rows failed on the first pass, all with HTTP 500 "model inference failed" after four attempts: Kev-4B on 9
PII rows, Open-Jev-2B on 5 PII rows and 2 grounding rows. Kev-4B's 9 of 118 is above the 2% cap, which would have made
its PII subtask invalid. The smoke runs had none of these. A second VM session that ran only those two models resent
just the 16 rows (`run --retry-failed`), and all 16 came back decided. So the failures came from load, most likely the
four models sharing GPU 0 at the same time. The ledgers keep both records, and the score uses the retry. For the full
run, run fewer VM models at once on GPU 0, or retry failures in a second pass as here.

Laya reads at most 512 tokens per question (owner ruling 16). Its server now reports truncation on every row, and 318
of 1,422 rows were cut. Every topic row (131) is cut because the `any_denied_topic` question with its options is longer
than Laya's 192-token question head. The other 187 had their state cut: 64 prompt attacks, 61 grounding, 36 content
replies, 13 content requests and 13 PII rows. Grounding has the most cut rows (61 of 119), and it is also Laya's lowest score
(43.6).

Strands Decider 2B cuts silently at 4,096 tokens. Its largest reported input was 2,145 tokens and no row was estimated
near the window, so nothing was cut on these rows.

No other system failed or truncated a row. `report` found no row text in any ledger.

## Time and cost

The hosted systems ran in parallel and finished in about 5 minutes. The VM was up from 19:33:57 to 20:10:58 UTC for the
main pass and from 20:12:28 to 20:17:24 for the retry, 42 minutes in all, and `make status` showed it TERMINATED after
each `make pause`. The whole sample cost about $1.96: $0.54 hosted and $1.42 for the VM.

## Caveats

- Dev split. These rows built and checked the dataset. This is a rehearsal, not a held-out result, and the file says
  so in its label (it is also in diagnostic mode, and the contract is unsigned).
- Sample size. 118 to 544 rows per suite, so suite intervals are a few points wide.
- Prompt attacks are provisional (owner rulings 17 and 18). Their labels are partly predictable from source and style.
- pplx-decider-v1-27b trained or tuned on 82 of these rows. See the sensitivity view above.
- Laya truncation, as above.
- Custom words is a sanity check outside the score, and DRIVER_ID is unscored.
- The scorer lists `e2-f1-bedrock5`, `e2-f4-*` and `e2-f6-grounding` as differing from the contract's `v1-` sets. They
  are copies with the same questions and decision lists (`sample.question_set_names`), so those disclosures are about
  the name only.

## Files

- `<system>.jsonl`: one ledger per system. Row ids, labels, source names and system outputs, never row text.
- `run-log.json`: wall time per run and the VM sessions. `logs/`: console output of each run, `make up` and `make pause`.
- `bedrock-guardrails.blocked.json`: why Bedrock's first attempt did not run.
- `leaderboard.json`: the diagnostic leaderboard, the run summary, cost, the content views and the pplx-decider
  sensitivity view.
- `plots/`: `overall`, `heatmap-subtasks`, `catch-vs-false-block`, `score-vs-cost-latency` and `pplx-overlap`, each as
  PNG and SVG.
