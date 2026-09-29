# 22. Budget forecast: what has been spent, what the rest should cost, and where $100 stops being enough

23 September 2026, revised the same day after reconciling spend against the GCP audit logs. Work unit E of the
completion plan (`docs/reports/gold-rails-completion-plan.html`). The plan keeps the original $100 ceiling for API and
GPU spend as a constraint that needs a fresh forecast. This is that forecast. It authorises no run, no VM and no upload.

No figure here is a bill. Past GPU spend comes from Compute Engine audit logs multiplied by list prices. Past API spend
comes from the usage recorded in the ledgers multiplied by the dated tariffs. Future spend comes from per-row latency
and usage in the ledgers, checked against the VM run times in the audit logs.

## Summary

- Spent to date: $7.2 to $7.7, almost all of it on-demand GPU time. That is reconstructed, not billed. The Cloud
  Billing API did not answer from this machine, the project has no billing export, and the AWS SSO session had expired.
- Left of the $100: $92.3 at the top of that range. Every "fits" below is measured against $92.
- The core benchmark at 8,000 cases forecasts $45 to $75 on on-demand GPUs. It fits.
- "8,000 cases with bias" is not 8,000 cases. The bias tracks add about 6,000 cases on top of the 8,000 core cases,
  so the run is roughly 14,000 cases before the separate tuning and latency passes. It forecasts $64 to $108. The low
  end fits and the high end does not. With one frozen content question set and the VM torn down between phases it
  comes to $54 to $87, which fits with about $5 to spare at the top.
- A smaller core of 6,000 cases forecasts $39 to $64.
- Spot VMs are no longer the easy saving the first draft assumed. The g2-standard-24 spot price in us-east4 was $1.064
  an hour on 23 September, not $0.62, and all six spot requests on 22 September failed for lack of capacity.
- Jev and Bedrock together come to under $4 at any size here. The money goes on GPU hours.
- Human review time is not in the $100 and nothing in the repository says it is funded.

## Reconciled spend to date

| Line | Amount | Source | Uncertainty |
|---|---|---|---|
| g2-standard-24 on-demand VM, us-east4-a, 166 to 177 minutes running over 8 sessions | $5.53 to $5.87 | Audit logs × $1.9943 an hour list price | The range is the gap between an operation's first and last log entry. List price only: no credits, tax or currency conversion |
| g2-standard-24 on-demand VM, us-central1-a, 36 to 39 minutes across two short-lived instances | $1.19 to $1.28 | Audit logs × $2.0008 an hour list price | Same |
| 200 GB pd-balanced boot disks, 11.8 disk-hours from insert to delete | $0.35 | Audit logs × $0.11 per GB-month in us-east4, $0.10 in us-central1 | The disk bills while the VM is stopped. That is included |
| Ephemeral external IPv4 while the VM ran | under $0.02 | Audit logs × about $0.005 an hour | I did not re-read this rate today |
| Amazon Bedrock Guardrails | $0.08 | Ledger-derived. Text units in every Bedrock row ever committed to `benchmark/results`, across git history, × `tariffs.json` | Lower bound. Runs never committed are missing. The 20 pilot content rows recorded no usage, which adds about $0.01 at 1.5 units a row |
| TypeSafe Jev | $0.03 | Ledger-derived. 771,781 input tokens in every Jev row ever committed × $0.042 per million. Output tokens are free | Lower bound. The TypeScript spikes of 21 September left no usage record. At this price it takes 24 million tokens to reach $1 |
| **Total** | **$7.2 to $7.7** | Estimate, not billing | Plan against $7.7 spent and $92.3 left |

How the GPU line was built. `gcloud logging read` on `compute.googleapis.com` for `gold-rails-serve` since
21 September returned every insert, start, stop and delete. One user account made all of them. There were no system
events, so no preemption and no guest-initiated shutdown. The VM ran in ten sessions on 22 September, times in UTC:

| Zone | Running (UTC) | Minutes | What happened |
|---|---|---|---|
| us-central1-a | 04:05 to 04:29 | 24.0 | First instance, deleted and recreated |
| us-central1-a | 04:31 to 04:42 | 11.8 | Second instance, deleted |
| us-east4-a | 04:47 to 06:24 | 96.9 | First bring-up: drivers, weights and eight metadata-and-reset rounds |
| us-east4-a | 08:20 to 08:28 | 7.9 | Notebook 04 content pilot, commit `03343a9` |
| us-east4-a | 09:10 to 09:14 | 4.0 | No ledger rows |
| us-east4-a | 11:25 to 11:30 | 5.1 | Prompt attacks, `dfc4443` |
| us-east4-a | 11:34 to 11:40 | 5.6 | Prompt attacks, `63f9b3f` |
| us-east4-a | 11:54 to 12:14 | 19.4 | Prompt attacks and PII, `4743c5b`, with Laya failing |
| us-east4-a | 13:11 to 13:31 | 19.9 | Topics, words and grounding, `7e7fb7e` and `7561048` |
| us-east4-a | 14:21 to 14:29 | 7.4 | Frozen prompt-attack, PII and grounding rows, `aec5a8e` |

The instance was deleted at 15:56 UTC and its disk went with it. `gcloud compute instances list` and `disks list`
show nothing left. Every successful instance was g2-standard-24 on the standard provisioning model, which is on-demand. The six spot
requests, three for g2-standard-48 and three for g2-standard-24 in us-central1, all failed with
`ZONE_RESOURCE_POOL_EXHAUSTED`. So did three on-demand inserts in us-central1 and fifteen on-demand starts in
us-east4-a. A seventh spot request named a machine type that us-central1-f does not offer.

Prices. Google's pricing pages render their tables in the browser from the Cloud Billing catalog, and that API timed
out from this machine. The VM prices come from Spare Cores at `sparecores.com/server/gcp/g2-standard-24`, which tracks
the GCP catalog and showed an observation time of 2026-09-23 00:32 UTC: $1.9943 on-demand and $1.064 spot in
us-east4, $2.0008 and $1.2003 in us-central1. These include both L4 GPUs. The disk price comes from
`gcloud-compute.com/diskpricing.html`, last updated 21 September 2026. Both are third-party copies. I added them to
`tariffs.json` under their own hardware keys, marked as such, so the leaderboard's self-hosted costs stay null until
someone reads Google's own list.

What could not be checked:

- `gcloud billing projects describe raxit-ai` hung, and `cloudbilling.googleapis.com` timed out. Logging and Compute
  answered normally. BigQuery is disabled in the project, so no billing export exists there.
- `aws ce get-cost-and-usage` was not reached. The SSO token for the profile in `.env` had expired and could not be
  refreshed. `aws sso login` would fix that.
- The TypeSafe usage page needs a browser login. I did not try it.

## What the ledgers measured

Per row, from `benchmark/results/*.jsonl` as they stood on 23 September. Latency is the mean `latency_s` over rows
that succeeded. Tokens and units are what the provider reported.

| Suite | Jev input tokens per row | Bedrock cost per 1,000 rows | Kev 0.8B s | Kev 4B s | Kev 9B s | Open-Jev 2B s | Laya s |
|---|---|---|---|---|---|---|---|
| Content (pilot, four question sets) | 3,974 | usage not recorded in the pilot | 2.37 | 7.66 | 10.09 | 7.60 | 5.34 |
| Prompt attacks | 611 | $0.08 | 0.41 | 0.46 | 0.56 | 1.83 | 1.77 |
| Denied topics | 834 | $0.15 | 0.57 | 0.65 | 0.88 | 2.17 | 1.75 |
| Word filters | 742 | $0.00, word policy is free | 0.45 | 0.48 | 0.65 | 1.83 | 1.69 |
| Sensitive information | 1,162 | $0.10 | 0.65 | 2.18 | 2.85 | 1.96 | 1.59 |
| Grounding | 1,212 | $0.42 | 0.63 | 0.89 | 1.14 | 1.76 | 1.51 |

Grounding is $0.19 per 1,000 if you average over every ledger row, because 30 of 120 Bedrock calls failed validation
and billed nothing. The leaderboard's clean-arm figure is $0.42, and I use that. Bedrock content usage is still
unmeasured. I assume 1.5 text units a row, about $0.11 per 1,000 rows.

Errors. The ledgers hold 125 Laya rows refused by a service that was not running, a venv defect since fixed, and the
30 grounding validation failures. Neither kind is transient, so neither would be retried. No transient error appears
in the other 3,600 or so rows.

## Throughput: what the audit logs settled

The first draft had one wall-clock measurement and a factor-of-two range. The audit logs add four clean sessions where
the VM started, ran one batch of rows and stopped. Set each session's running time against the latency the rows
recorded:

| Session (UTC) | Running | Self-hosted rows | Latency summed over all five models | Slowest model's sum | Lane model | Left for start-up and stop |
|---|---|---|---|---|---|---|
| 08:20 to 08:28 | 475 s | 100 | 661 s | 202 s, Kev 9B | 352 s | 273 s |
| 11:25 to 11:30 | 306 s | 225 | 244 s | 90 s, Open-Jev 2B | 133 s | 216 s |
| 11:34 to 11:40 | 336 s | 295 | 309 s | 116 s, Open-Jev 2B | 167 s | 220 s |
| 14:21 to 14:29 | 444 s | 634 | 766 s | 207 s, Open-Jev 2B | 430 s | 237 s |

The last session decides it. The VM was up for 444 seconds and the rows record 766 seconds of latency, so the five
models ran at the same time. The lane model, which runs the models on each GPU one after another, would leave 14
seconds to boot a stopped VM and load five models. The other sessions show that takes closer to four minutes. So VM
time is about the slowest model's latency sum, plus about four minutes per start. The lane model is a safe upper bound.

VM seconds per case:

| Suite | Central: slowest model | High: lane model | Latency pass: all five, one at a time |
|---|---|---|---|
| Content, pilot configuration | 10.1 | 17.6 | 33.1 |
| Prompt attacks | 1.8 | 2.7 | 5.0 |
| Denied topics | 2.2 | 3.4 | 6.0 |
| Word filters | 1.8 | 2.8 | 5.1 |
| Sensitive information | 2.9 | 4.8 | 9.2 |
| Grounding | 1.8 | 3.3 | 5.9 |
| Weighted core case | 4.1 | 7.0 | |

Two cautions. These are smoke rows, and final rows may be longer. And the pilot's content row asks four question sets.
A final run with one frozen set would take about half as long.

## Forecast

Assumptions, all adjustable:

- Core cases split across suites as content 25%, prompt attacks 20%, sensitive information 17.5%, grounding 17.5%,
  denied topics 12.5%, word filters 7.5%.
- 15% of cases are tuning cases and 85% are test cases. The tuning pass runs the tuning split twice, once as it stands
  and once after question and threshold edits. The final test pass runs the test split once. Every pass covers all
  seven systems.
- Bias adds about 6,000 cases. 3,000 are B1 and B2 guardrail rows on every system. B1 is scored on the content
  suite's categories, so I price each row as a content row with one question set: 5.0 s central, 8.8 s high. The
  other 3,000 are B3 decision rows on the decision models only, priced at twice a prompt-attack row. B4 smoke should
  replace both guesses. Bias cases split 15/85 like the core.
- The latency pass follows the contract: 300 rows a suite, one request at a time, each open model in turn, plus Jev
  and Bedrock on the same rows. 5.4 VM hours, on-demand in every option.
- Retries: up to 3 for transient infrastructure errors only, per `policy.py`. The ledgers show no transient errors, so
  I assume a 2% transient rate in the central case and 5% in the high case, each failing all three retries. That adds
  6% or 15% to the tuning and test passes.
- Setup and cold starts: two fresh bring-ups of 60 minutes in the central case, three of 97 minutes in the high case,
  since 97 minutes is what the first real bring-up took. Add 4 minutes for every start. `max_run_hours` stops the VM
  after 8 hours, so long passes restart.
- Storage: the 200 GB disk costs $0.030 an hour for as long as it exists, paused or not. 7 days in the central case,
  14 in the high case, plus the running IP address.
- GPU at $1.9943 an hour on-demand in us-east4, the zone in `terraform.tfvars`.

On-demand, central to high. Jev and Bedrock sit inside the pass lines: $2.4 for core 8,000, $3.7 with bias, $1.9 for
core 6,000. Rows may not add to the total because of rounding.

| Line | Core 8,000 | Core 8,000 + bias, about 14,000 | Core 6,000 |
|---|---|---|---|
| Tuning pass | $6 to $10 | $11 to $17 | $4 to $7 |
| Final test pass | $17 to $28 | $30 to $49 | $13 to $21 |
| Latency pass | $11 | $11 | $11 |
| Retries | $1 to $6 | $2 to $10 | $1 to $4 |
| Setup and cold starts | $5 to $10 | $5 to $11 | $4 to $10 |
| Storage | $5 to $10 | $5 to $10 | $5 to $10 |
| **Total** | **$45 to $75** | **$64 to $108** | **$39 to $64** |
| VM hours | 18 to 28 | 27 to 42 | 15 to 24 |
| Same run on spot at $1.064, latency pass on-demand | $33 to $51 | $43 to $69 | $29 to $45 |

For reference, 10,000 core cases come to $51 to $86, and 6,000 core plus bias to $58 to $97.

## Against the ceiling

$92.3 is left after the top of the reconciled spend.

| Option | On-demand forecast | Fits $92? |
|---|---|---|
| Core 8,000 | $45 to $75 | Yes, at both ends. $17 spare at the top |
| Core 8,000 + bias, about 14,000 cases | $64 to $108 | Only at the low end. The top is $16 over |
| Core 8,000 + bias, with one content question set and the disk kept no more than 7 days | $54 to $87 | Yes. About $5 spare at the top, which is thin |
| Core 6,000 | $39 to $64 | Yes. $28 spare at the top |

Spot would bring 8,000 plus bias to $43 to $69, but I would not plan on it. Spot in us-east4 costs 53% of on-demand,
not the third that `infra/gcp/README.md` assumed. Every spot request on 22 September failed for lack of capacity, and
a preemption in the middle of a test pass makes a mess of the timing.

## Recommendation

Keep 8,000 core cases as the planning target, subject to subgroup coverage, and run on on-demand GPUs in us-east4. That
is $45 to $75.

Add the bias tracks only with two changes made up front. Freeze one content question set, which the final benchmark
needs anyway, and destroy the VM between the tuning and test phases so the disk does not sit for two weeks. That brings
the about-14,000-case run to $54 to $87. If the lead wants bias without those changes, the forecast is $64 to $108 and
does not fit.

The first draft's summary priced 8,000 cases with bias on spot at $18 to $27, and its recommendation said $25 to $35
for the same option. Neither holds now. The spot price was wrong, and the throughput range was too loose. Every figure in
this revision comes from the one forecast table.

If the forecast still exceeds what remains once real bills arrive, the contract says to cut before the run and write
the cut into the manifest. The cheapest cuts, in order: one content question set, which saves $10 to $16 at 8,000 core
cases; destroy the VM between phases; a 100-row latency pass, which saves about $7; one tuning pass instead of two,
which saves $3 to $5 on the core; fewer self-hosted models in B3; fewer cases. Nothing gets dropped mid-run to save
money.

## Sample-size envelope, in terms of what the numbers can show

The size decision is really about the benign floor. At 300 benign test cases and a true pass rate of 95%, the 95%
interval is about plus or minus 2.5 points, per docs/19.

| Core cases | Test cases at 85% | Benign test cases per suite, if half are benign | Floor of 300 met? |
|---|---|---|---|
| 6,000 | 5,100 | about 190 for word filters, 320 for denied topics, 640 for content | No for word filters; denied topics only just |
| 8,000 | 6,800 | about 255 for word filters, 425 for denied topics, 850 for content | No for word filters |
| 10,000 | 8,500 | about 320 for word filters, 530 for denied topics, 1,060 for content | Yes, only just for word filters |

At 8,000, give word filters and denied topics a fixed 600 test negatives each and take the difference from content.
That meets the floor everywhere without changing the budget much. A word-filter case costs 1.8 VM seconds against 10.1
for a content case, and Bedrock word checks are free. That is what "subject to subgroup coverage" means here. The
8,000 figure stands if the split can reach the floor in every suite, and grows if it cannot.

The source audit in docs/20 adds a caveat. Denied topics and word filters have no test rows today, and the only
negatives for jailbreak and leakage are authored controls that can never enter test. More cases from the same sources
will not fix that. The envelope assumes those cells get new sources first.

## Not in the $100

- Human review and annotation. Open work today: about 68 authored cases in three blind packets, at least two reviewers
  each; the bias B2 pair review; a relevance decision; and any Aegis LLM-jury sample. At roughly a minute a case per
  reviewer, the three existing packets are a few person-hours. The bias packet and any relabelling are more. Nothing
  in the repository says who does this or whether it is paid. The lead needs to decide.
- Engineering time.
- Hugging Face hosting. Public datasets are free to host.
- The raxit.ai results page, which is static.

## Decisions for the lead

1. Close the reconciliation with real bills: `aws sso login` and rerun Cost Explorer for Bedrock in us-east-1; open
   the GCP billing report for raxit-ai in the console, since the API did not answer from this machine; check the
   TypeSafe usage page. Replace the estimates above if they differ.
2. Pick a size. Recommended: 8,000 core cases on on-demand, with fixed 600-negative floors for word filters and denied
   topics. Add bias only with one content question set and teardown between phases.
3. Decide whether human review is funded, and by whom.
4. Read Google's own price list for g2-standard-24 in us-east4 on the day of the run and fill the null GPU entries
   in `benchmark/goldrails_bench/tariffs.json`. The third-party figures there are for forecasting only.
5. Ask the run owner to log wall-clock start and end per system and per pass. The audit logs gave four clean sessions.
   A real run can give many more.

## How to redo this

GPU spend to date: read the audit logs with
`gcloud logging read 'protoPayload.serviceName="compute.googleapis.com" AND protoPayload.resourceName:"gold-rails-serve"' --freshness=5d`,
pair each successful insert or start with the next stop or delete, and multiply the minutes by the hourly rate for
the zone. Disk hours run from insert to delete.

API spend to date: for every commit that touched `benchmark/results`, read each ledger with `git show`, keep each
distinct Jev and Bedrock row once, and multiply tokens and text units by `tariffs.json`.

Forecast: per suite, multiply cases by VM seconds per case, sum, convert to hours and multiply by the hourly rate. Add
the latency pass, retries, setup and storage lines as set out in the assumptions. Jev is cases times tokens per case
times $0.042 per million. Bedrock is cases times the cost per 1,000 rows from the measured table. The leaderboard
module (`uv run python -m goldrails_bench.leaderboard benchmark/results/*.jsonl --mode smoke`) prints the per-arm
hosted cost it can measure from the same ledgers.

## First benchmark subset forecast (23 September 2026)

After the dataset-first handoff, the first benchmark runs on the `first-benchmark` subset of dataset v1.0, not on the
full release: 1,360 core and 300 bias test rows, 401 core and 90 bias tuning rows. Denied topics joins once its
drafted test cases are validated, as a small extra pass.

Method as above, with these subset choices: content tunes two candidate question sets and tests one; every other suite
has one; the tuning pass runs the tuning rows twice; the latency pass is 100 rows per suite, one request at a time;
the VM is deleted after the run, so the disk exists for 3 days (central) or 7 (high).

| Line | Central | High |
|---|---|---|
| Tuning and final test passes, all seven systems | $5.5 | $9.3 |
| Latency pass | $2.6 | $4.0 |
| Retries (2% or 5% transient failures, 3 retries) | $0.3 | $1.4 |
| Setup and cold starts (two or three fresh bring-ups) | $4.3 | $10.1 |
| Disk and IP | $2.2 | $5.0 |
| Jev and Bedrock usage | $0.5 | $1.0 |
| **Total** | **about $15** | **about $31** |

The later denied-topics pass adds about $1 of GPU time plus one bring-up ($2 to $3) if it runs in a separate session.

Against the ceiling: $92.3 remains after the top of the reconciled spend, so the subset fits with room for one full
rerun. These are forecasts from list prices and smoke-run throughput, not measured costs. Measured cost per 1,000
evaluations comes from the run's own usage and allocated serving time. No charge is incurred until the owner approves
this forecast.

## First benchmark actual spend (23 September 2026)

Measured after the run, against the approved $31 cap for the subset (the cap also covers the later denied-topics and
B2 pass).

| Line | Basis | Amount |
|---|---|---|
| VM g2-standard-24 (2x L4), us-east4-a | Audit log: created 04:39:48 UTC, deleted 07:47:19 UTC, 3.13 h x $1.9943/h on-demand | $6.23 |
| 200 GB pd-balanced boot disk | Same 3.13 h at list price | about $0.10 |
| Jev 1.13.0 (TypeSafe API) | Measured tokens x list price, every ledger (tune, test, bias, latency) | $0.10 |
| Bedrock Guardrails (us-east-1) | Measured text units x list price, every ledger | $0.25 |
| **Total** | | **about $6.7** |

The run covered the tuning pass, the frozen test, the 51-row correction rerun, the bias tracks B1 and B3, and a serial
latency pass over every suite. It came in under the central forecast because one bring-up served everything and the
VM was deleted straight after. About $24 of the $31 cap remains; the denied-topics and B2 pass is forecast at $2 to
$3. These are list prices; the billing statement has not been reconciled yet.

### How the VM time splits (reconciliation, 23 September 2026)

The VM ran 11,251 s according to the audit log. Serving windows rebuilt from the ledgers, one model at a time, account
for 9,417 s. The remaining 1,834 s is setup and idle time: boot, weight loading, and waiting while the hosted APIs
ran. That time is part of the $6.23 VM total above but is not charged to any arm's cost per 1,000.

| Stage | Serving seconds |
|---|---|
| Tuning (core and bias) | 1,802 |
| Frozen test | 4,443 |
| Correction rerun | 43 |
| Bias test | 745 |
| Serial latency pass (core and bias) | 2,383 |
| Setup and idle | 1,834 |

The windows come from completion times recorded to the second minus each attempt's latency, so each carries about a
second of uncertainty; overlaps under two seconds between neighbouring windows were split at the midpoint (21 s in
total). The window file is `benchmark/results/first-benchmark/serving-all.json`. The $6.70 total is list prices times
measured usage and has not yet been checked against the GCP and AWS bills.
