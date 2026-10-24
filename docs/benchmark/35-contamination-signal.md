# 35. Can the scores show contamination?

Status: analysis, 24 October 2026. Offline, no model call.

No. A per-source score check cannot tell contamination from ordinary differences between systems, so edition 2 can
neither show nor rule out that systems trained on its sources.

## What is already done

- **Exact-text check against published training recipes.** Only two systems publish theirs: Strands Decider 2B and
  Perplexity's decider (`dataset/edition2/MODEL-TRAINING-OVERLAP.json`). Rows whose exact text is in Perplexity's
  training or development splits were removed: 416 public and 148 unpublished.
- **Vendor documentation check.** Rows whose text a benchmarked vendor printed in its own docs were removed
  (`dataset/edition2/VENDOR-OVERLAP.md`).
- **Nothing for the other 18 systems.** Their training data is not published.

## The check

`benchmark/runs/e2_contamination_signal.py` asks whether any system does unusually well on one upstream source. For
each job, source and system it takes the system's balanced accuracy on that source minus its accuracy on the job's
other rows. It then subtracts the median of that difference over all 20 systems, so a source that is easy for everyone
cancels out. A system that trained on a source should stand out there. Intervals come from 1,000 bootstrap resamples.
Aggregates only are in [`35-contamination-signal.json`](35-contamination-signal.json).

## Result

- **The known cases do not show up.** Perplexity's decider trained on Aegis 2.0 and Civil Comments, and Strands
  Decider 2B on Civil Comments. Their excess on those sources is between -3.5 and +0.1 points, and every interval
  includes zero. The exact rows they saw were already removed, so these are rows from the same distribution. The
  check does not detect training on a source's distribution.
- **72 of 480 cells pass the flag** (excess of at least 5 points with the interval above zero). They are spread over
  all 20 systems, one to six each. The largest are Microsoft-Decision-1 on Mosscap (+24.8) and four small models on the
  in-the-wild jailbreak prompts (+13 to +21).
- **Two of the 20 cells on raxIT-authored sources are flagged.** Those rows did not exist in public before October
  2026, so flags of this size happen without any contamination.

The flags line up with policy fit. Mosscap rows turn on whether a guess at a password counts as an attack (ruling 3).
The in-the-wild prompts turn on what counts as a jailbreak persona. Systems trained to a policy close to ours score
higher there, contaminated or not.

## What would work

| Test | What it shows | Cost |
|---|---|---|
| Fresh rows (edition 3) | Each system's gap between public rows and rows that never existed in public. The direct measure | Writing and labelling time; a run is USD 20 to 35 |
| Paraphrase test | Rewrite a sample of public rows by hand, keeping meaning and label. A system that memorised the wording drops on the rewrite; one that learned the task does not | About 300 rows of human rewriting; a run of about USD 3 to 5 |
| Recipe scan for every open model | Extend the exact-text check to Kev, Open-Jev, Laya and the Strands checkpoints, where their cards or repositories name training sets | Free; reading model cards and scanning upstream splits |
| Source-guessing classifier | If a simple classifier can tell sources apart from text alone, systems can score by source style. Used in "When Benchmarks Lie" (arXiv 2602.14161) | Free |

Disclosure in the meantime: the board should say that rows come from public datasets, that only two systems' training
data could be checked, and that results on public sources may favour systems trained on them.
