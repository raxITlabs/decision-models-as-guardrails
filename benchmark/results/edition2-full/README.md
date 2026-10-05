# Edition 2 full run (test split and unpublished slice)

Eleven systems answered every edition 2 test row on 5 October 2026 (UTC): 6,475 public test rows and the 1,633-row
unpublished slice, 8,108 rows per system. `leaderboard_v2` scored the answers in frozen mode under the signed
contract v2.0, at the fixed 0.5 rule, against the freeze manifest committed before the first test call.
`leaderboard.json` reports `valid_for_publication: true` with no publication blocker.

The owner signed the contract, approved the run and its spend, and allowed the unpublished slice to go to Perplexity
(ruling 21, `docs/benchmark/29-owner-rulings-2026-10-03.md`).

```
uv run python benchmark/runs/e2_full.py plan          # rows per subtask and the cost forecast
uv run python benchmark/runs/e2_full.py freeze        # the freeze manifest, committed before any call
uv run python benchmark/runs/e2_full.py all           # hosted systems and the VM session, with retry passes
uv run python benchmark/runs/e2_full.py score         # leaderboard.json, public ledgers, privacy check
uv run --with matplotlib python benchmark/runs/e2_full_plots.py
uv run python benchmark/runs/site_results.py --leaderboard-v2 benchmark/results/edition2-full/leaderboard.json
```

## Scores

Balanced accuracy x 100 at the fixed 0.5 rule. The six suites have equal weight in the overall score. Custom words is
a pass/fail sanity check (pass at 95 or higher) outside the overall. DRIVER_ID is unscored. Prompt attacks are
provisional. Tiers come from Holm-adjusted paired bootstrap tests against each tier's leader (2,000 replicates, seed
20260923).

| Rank | System | Overall (95% interval) | Tier | Rank interval | Content | Prompt attacks (provisional) | Denied topics | Profanity | PII | Grounding | Custom words |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pplx-decider-v1-27b | 90.0 (89.3 to 90.6) | 1 | 1-1 | 84.7 | 80.0 | 98.6 | 90.2 | 98.2 | 88.1 | fail (73) |
| 2 | Clef | 88.9 (88.2 to 89.6) | 2 | 2-2 | 81.5 | 81.7 | 98.8 | 87.7 | 98.2 | 85.5 | fail (89) |
| 3 | Jev 1.13.0 | 88.0 (87.3 to 88.7) | 2 | 3-3 | 79.3 | 78.6 | 97.1 | 83.7 | 98.2 | 91.2 | fail (90) |
| 4 | Kev-4B | 82.5 (81.7 to 83.3) | 3 | 4-6 | 79.4 | 77.1 | 97.8 | 78.9 | 96.1 | 65.8 | fail (61) |
| 5 | Kev-9B | 82.2 (81.4 to 83.1) | 3 | 4-6 | 81.1 | 77.6 | 91.8 | 77.2 | 97.3 | 68.5 | fail (58) |
| 6 | Clef-flash | 82.0 (81.1 to 82.8) | 3 | 4-6 | 80.1 | 76.8 | 84.3 | 83.9 | 97.7 | 69.0 | fail (66) |
| 7 | Bedrock Guardrails | 79.9 (79.0 to 80.8) | 4 | 7-7 | 79.8 | 77.5 | 84.6 | 71.6 | 98.2 | 67.7 | pass (100) |
| 8 | Strands Decider 2B | 76.4 (75.5 to 77.3) | 5 | 8-8 | 67.9 | 64.1 | 85.2 | 79.6 | 95.1 | 66.4 | fail (59) |
| 9 | Open-Jev-2B | 66.5 (65.8 to 67.2) | 6 | 9-10 | 62.7 | 52.4 | 81.4 | 59.4 | 89.9 | 53.1 | fail (69) |
| 10 | Kev-0.8B | 66.2 (65.4 to 67.1) | 6 | 9-10 | 62.1 | 54.6 | 69.6 | 64.6 | 90.7 | 55.7 | fail (55) |
| 11 | Laya | 62.3 (61.3 to 63.3) | 7 | 11-11 | 68.3 | 63.6 | 63.0 | 65.9 | 71.7 | 41.4 | fail (59) |

| System | Catch rate | False-block rate | USD per 1,000 checks | USD total | p50 / p95 latency (s) | Wall time | First-pass failures | Truncated rows |
|---|---|---|---|---|---|---|---|---|
| pplx-decider-v1-27b | 0.883 | 0.083 | 0.062 | 0.50 | 0.80 / 0.86 | 27 min | 0 | 0 |
| Clef | 0.905 | 0.128 | 0.216 | 1.75 | 0.59 / 1.13 | 18 min | 28 | 0 |
| Jev 1.13.0 | 0.886 | 0.126 | 0.040 | 0.32 | 0.22 / 0.30 | 4 min | 0 | 0 |
| Kev-4B | 0.735 | 0.085 | 0.277 | 2.24 | 1.77 / 5.65 | 211 min | 230 | 0 |
| Kev-9B | 0.741 | 0.096 | 0.134 | 1.09 | 0.90 / 4.46 | 103 min | 0 | 0 |
| Clef-flash | 0.808 | 0.169 | 0.081 | 0.66 | 0.41 / 1.03 | 14 min | 24 | 0 |
| Bedrock Guardrails | 0.712 | 0.115 | 0.116 | 0.94 | 0.50 / 0.65 | 67 min | 0 | 0 |
| Strands Decider 2B | 0.647 | 0.119 | 0.111 | 0.90 | 1.28 / 1.98 | 85 min | 0 | 0 |
| Open-Jev-2B | 0.375 | 0.045 | 0.305 | 2.47 | 2.22 / 4.65 | 233 min | 209 | 0 |
| Kev-0.8B | 0.511 | 0.187 | 0.181 | 1.47 | 0.87 / 3.50 | 138 min | 224 | 0 |
| Laya | 0.516 | 0.270 | 0.119 | 0.96 | 1.65 / 1.93 | 91 min | 0 | 1,903 |

Catch and false-block rates are the means over the six suites. Hosted cost is measured usage (tokens, or Bedrock text
units) times the dated list price in `goldrails_bench/tariffs.json`. VM cost is the VM's up-to-paused time (16,242 s
over five sessions) at the dated g2-standard-24 on-demand rate plus the disk, split across the six VM models by their
share of run time. Wall time is summed over each system's runs, including runs that a VM restart cut short. Every
system ended with 0 failed rows. Bedrock's three over-limit grounding rows (below) count as wrong.

## What the run found

pplx-decider-v1-27b leads on its own: tier 1, rank interval 1-1, and the paired tests separate it from Clef. It gets
there on the lowest false-block rate of the top three (0.083 against about 0.13) and the best content and profanity
scores. Clef and Jev share tier 2. Jev has the best grounding score of any system (91.2) and is the cheapest and
fastest system here (USD 0.04 per 1,000 checks, p95 0.30 s).

The order matches the dev-split rehearsal closely. The top three are the same and in the same order. Kev-4B, Kev-9B and
Clef-flash again form one tier, and Bedrock stays seventh. The test split has 5.7 times as many rows, so the intervals
are narrower and the tiers split further. On the dev rows the top three shared a tier.

Content is still the hardest suite, with no system above 85. The Bedrock-five view lifts every system by 0.6 to 2.5
points. Dropping the vendor-owned sources moves them by -1.4 to +0.3. Neither view changes who leads.

The small open models under-flag at 0.5. Open-Jev-2B catches 38% of positives with a 4.5% false-block rate, and its
prompt-attack score is 52.4. Kev-0.8B and Laya sit in the 60s. Their AUROCs in `leaderboard.json` show how much a
tuned threshold would recover. Under contract v2.0 no threshold is tuned.

Bedrock is the only system that passes the custom-words sanity check (100). Its word filter matches the listed terms
exactly. The best Noul score is 90 (Jev).

## The unpublished slice

Every system was also re-scored on the public test rows alone and on the unpublished slice alone. This is a
diagnostic, never ranked (owner ruling 15). A system that has seen the public rows should do better on them.

| System | Public rows | Unpublished slice | Difference |
|---|---|---|---|
| pplx-decider-v1-27b | 90.1 | 89.7 | -0.4 |
| Clef | 89.2 | 87.8 | -1.3 |
| Jev 1.13.0 | 88.3 | 86.5 | -1.8 |
| Kev-4B | 82.4 | 82.6 | +0.2 |
| Kev-9B | 82.2 | 81.8 | -0.4 |
| Clef-flash | 81.8 | 82.5 | +0.7 |
| Bedrock Guardrails | 79.9 | 79.6 | -0.3 |
| Strands Decider 2B | 76.4 | 76.0 | -0.4 |
| Open-Jev-2B | 66.5 | 66.7 | +0.2 |
| Kev-0.8B | 66.4 | 65.5 | -0.9 |
| Laya | 61.9 | 64.4 | +2.6 |

No system gains much on the public rows. The largest public-side gaps are Jev (1.8 points) and Clef (1.3). The slice
mixes suites differently (45% of it is prompt attacks, against 30% of the public rows), so a gap of a point or two is
expected without any contamination. `plots/unpublished-slice.png` draws the same numbers.

## Failures, retries and interruptions

- **Cloudflare quota.** Clef and Clef-flash hit HTTP 429 a few minutes in: the account had used its free allocation of
  10,000 neurons a day. We stopped both runs at 28 and 24 failed rows. The owner upgraded the account to Workers Paid,
  and both systems resumed with `--retry-failed`. That pass sent the failed rows and every row not yet sent, and none
  failed. A 429 check on the first resumed rows came back clean.
- **AWS session.** Bedrock's first attempt found an expired AWS SSO session and sent nothing
  (`bedrock-guardrails.blocked.json`). After the owner's `aws sso login` it ran all 8,108 rows with no failure.
- **VM servers on GPU 0.** About an hour into the first VM session, the three Noul servers on GPU 0 (Kev-0.8B,
  Kev-4B, Open-Jev-2B) began returning HTTP 500 and dropping connections on every row. Kev-9B and Laya on GPU 1 and
  Strands on GPU 0 kept working. We paused the VM. The next `make up` timed out with 3 of 6 servers reachable, so we
  started the VM by hand and checked the serial log (all six servers came up within four minutes), then ran a third
  session. That session finished every unsent row with no failure. Its retry pass, with all three GPU 0 models
  retrying at once, broke the same servers again within minutes. A fourth session ran the retries one model at a
  time, and every row came back decided. So 663 rows (Kev-0.8B 224, Kev-4B 230, Open-Jev-2B 209) failed on the first
  pass and all were recovered. The ledgers keep every record, and the score uses the latest. The likely cause is GPU 0
  memory under sustained load from three Noul servers. We could not open a shell on the VM to confirm it.
- **Bedrock service limits.** Bedrock's contextual grounding check takes a query of at most 1,000 characters. Three
  grounding rows are longer, so the adapter refused them before any call. They count as wrong in their class, as the
  contract's frozen row list scores an unlogged row. Each carries a marked local refusal time in place of an attempt
  time. That is 0.4% of grounding rows, under the 2% cap.

## Truncation

Laya reads at most 512 tokens per question (owner ruling 16). Its server reported a cut on 1,903 of 8,108 rows: every
denied-topics row (718), because the `any_denied_topic` question and its options exceed Laya's 192-token question head,
plus 397 grounding, 397 prompt-attack, 212 content-reply, 84 content-request and 95 PII rows. Laya's grounding score
(41.4) is its lowest.

Strands Decider 2B cuts silently at 4,096 tokens. No row was estimated over that window. Nine rows per Kev model and
for Strands came within 80% of the 4,096-token reference.

## Time and cost

The first test call went out at 04:27:55 UTC, 32 seconds after the freeze commit (04:27:23). The last VM pause was at
08:59:47. Hosted systems ran in parallel. Jev took 4 minutes, pplx-decider 27, Bedrock 67 and the Clef pair about 15
each. The VM was up 4 h 31 min across five sessions, including the restarts above.

The forecast before the run, from the dev-split measurements, was USD 10.57 (high 15.86, cap 30). Metered cost came to
USD 13.30: USD 4.17 hosted and USD 9.13 for the VM. The restarts made the VM run longer than forecast. On top of that,
the Cloudflare Workers Paid plan costs USD 5 a month at list. It is a subscription, so it is logged under
`run.fixed_costs` and not split per check. `infra/ctl.sh status` and `gcloud compute instances describe` both showed the
VM TERMINATED after the last pause.

## Privacy

The repository is public. The raw ledgers hold unpublished-slice ids and stay in the git-ignored `private/` folder.
The committed `<system>.jsonl` ledgers hold public test rows only: ids, labels, source names and outputs, never row
text. `score` checks every file in this folder for unpublished ids, for 8-word runs of any test row's text
(`e2_sample.fast_leak_check`), and with `e2_local.tracked_leaks`. All three came back clean, and the result is in
`leaderboard.json` under `privacy_check`. The leaderboard holds aggregates only.

## Caveats

- Prompt attacks are provisional (owner rulings 17 and 18). Their labels are partly predictable from source and style.
- Custom words is a sanity check outside the score, and DRIVER_ID is unscored.
- The scorer lists `e2-f1-bedrock5`, `e2-f4-*` and `e2-f6-grounding` as differing from the contract's `v1-` sets. They
  are copies with the same questions and decision lists (`full_run.question_set_names`), so those disclosures are about
  the name only.
- Latency is per row under each system's own worker count, not a load test. The VM models shared two L4 GPUs, and the
  GPU 0 failures above slowed their p95.
- The freeze lists the configurations the dev-split sample ran (`benchmark/subsets/edition2/freeze-manifest.json`).
  Nothing was fitted.

## Files

- `<system>.jsonl`: public test rows only, one ledger per system. Row ids, labels, source names and outputs.
- `private/` (git-ignored, never committed): the full ledgers with the unpublished slice.
- `leaderboard.json`: the frozen-mode leaderboard (tiers, paired differences, rank intervals, AUROC, recall at 5% false
  blocks, calibration where it applies, content views, disclosures), the run summary, cost, the unpublished-slice view
  and the privacy check.
- `run-log.json`: run timings, VM sessions, the forecast and fixed costs. Timings of runs cut short by a VM restart are
  rebuilt from their ledgers and marked `reconstructed_from_ledger`.
- `logs/`: console output of each run and of `make up`, `make pause` and `make status`.
- `plots/`: `overall`, `heatmap-subtasks`, `catch-vs-false-block`, `score-vs-cost-latency` and `unpublished-slice`, each
  as PNG and SVG.
