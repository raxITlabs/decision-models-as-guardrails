# 32. How saturated is edition 2?

Status: analysis, 24 October 2026. Offline, no model call. Nothing here changes a published number.

Two of the eight jobs are saturated. PII and denied topics have six or seven systems tied at the top, within about a
point of 100, and almost no rows left that separate them. Two jobs still have room. Direct prompt attacks top out at
74.4 and content requests at 86.8. The other four sit in between. Their top scores run from 91 to 93, and they still
separate systems, but the top tier gets 72 to 88% of rows right in unison.

## How the numbers were made

`benchmark/runs/e2_saturation.py` reruns the published scoring path (`e2_msd1_run.score`) with every file write
switched off. It takes the scorer's own per-row state: the same rows, the labels after the ruling 32 amendment, and
the fixed 0.5 rule, for all 20 systems on every test row and the unpublished slice. Recomputed balanced accuracy
matches `site/data/board.json` to within 0.005 points for every system and job, so the per-row matrix is the
board's. The per-row matrix stays in `.scratch/` because it holds unpublished ids. The aggregate output is
[`32-saturation.json`](32-saturation.json).

```
uv run python benchmark/runs/e2_saturation.py capture
uv run python benchmark/runs/e2_saturation.py report
```

Terms used below.

- A **judgment** is one scored decision. For PII it is one row times one entity type, so PII has 5,760 judgments
  from far fewer rows.
- **Tier 1** is the published top tier (Holm-adjusted paired bootstrap, `board.json`).
- **Oracle** is the score tier 1 would get if a judgment counted as right whenever any tier-1 system got it right.
  It is a ceiling for what today's best systems already know between them. The gap between it and 100 is mostly rows
  nobody gets, some of them label disputes.
- **Discrimination** is the point-biserial correlation between getting a judgment right and a system's score on the
  job. A judgment with r of 0.3 or more tells strong systems from weak ones. One below 0 rewards weak systems.

## Per job

| Job | Judgments | Top | Tier 1 (systems, range) | Oracle | All 20 right | All tier 1 right | No tier-1 system right | Tier 1 disagree | Tiers |
|---|---|---|---|---|---|---|---|---|---|
| Sensitive information (PII) | 5,760 | 98.20 | 7, 97.66 to 98.20 | 99.92 | 70.3% | 94.1% | 0.1% | 5.8% | 6 |
| Denied topics | 718 | 98.84 | 6, 96.86 to 98.84 | 99.50 | 27.6% | 95.0% | 0.6% | 4.5% | 7 |
| Profanity | 704 | 93.60 | 4, 90.17 to 93.60 | 97.58 | 35.2% | 82.2% | 2.4% | 15.3% | 6 |
| Content: replies | 752 | 92.96 | 2, 89.85 to 92.96 | 95.31 | 28.3% | 87.5% | 4.7% | 7.9% | 6 |
| Grounding | 724 | 91.71 | 5, 88.10 to 91.71 | 98.90 | 15.3% | 72.0% | 1.1% | 26.9% | 7 |
| Prompt attacks: indirect | 1,412 | 90.73 | 3, 87.23 to 90.73 | 96.39 | 14.5% | 81.1% | 3.5% | 15.4% | 7 |
| Content: requests | 1,714 | 86.80 | 5, 84.81 to 86.80 | 96.96 | 36.9% | 71.0% | 3.1% | 25.9% | 5 |
| Prompt attacks: direct | 3,131 | 74.40 | 4, 72.73 to 74.40 | 89.89 | 10.8% | 54.7% | 10.8% | 34.5% | 7 |

"Tier 1 disagree" is the share of judgments where some tier-1 systems are right and others wrong. Only those rows can
reorder the top. "All tier 1 right", "No tier-1 system right" and "Tier 1 disagree" add to 100%.

Item difficulty and discrimination:

| Job | Mean share of systems right | Judgments 20/20 right | Judgments 0/20 right | Informative (not 0 or 20) | Median r, informative | r at least 0.3 | r below 0 |
|---|---|---|---|---|---|---|---|
| PII | 0.96 | 4,047 | 0 | 29.7% | 0.23 | 14.5% | 9.1% |
| Denied topics | 0.87 | 198 | 0 | 72.4% | 0.44 | 56.7% | 2.4% |
| Profanity | 0.81 | 248 | 3 | 64.4% | 0.45 | 40.8% | 12.2% |
| Content: replies | 0.78 | 213 | 0 | 71.7% | 0.40 | 39.5% | 17.0% |
| Grounding | 0.73 | 111 | 3 | 84.3% | 0.54 | 62.0% | 8.6% |
| Indirect | 0.72 | 204 | 4 | 85.3% | 0.37 | 45.4% | 9.4% |
| Content: requests | 0.81 | 633 | 5 | 62.8% | 0.30 | 31.3% | 24.3% |
| Direct | 0.67 | 338 | 22 | 88.5% | 0.28 | 42.5% | 31.7% |

## What this says, job by job

**PII is saturated.** Seven systems share tier 1 inside 0.54 points. Tier 1 agrees on 94% of judgments and the
oracle is 99.92, so the best systems already cover nearly every row between them. 70% of judgments are right for all
20 systems, the weakest included. The rows separate weak systems from strong ones and do nothing at the top. More
rows of this kind would not help.

**Denied topics is saturated at the top, healthy below it.** Six systems tie between 96.86 and 98.84 and the oracle
is 99.50. The 642 authored rows are nearly solved by tier 1 (3.3% of rows missed by at least one tier-1 system).
The 76 OASST2 rows are harder (19.7%). Discrimination below the top is the best of any job (median r 0.44, only 2.4%
of judgments reversed), so the suite still ranks the field. It no longer ranks the leaders.

**Profanity, content replies, indirect attacks and grounding still have some room.** Tier-1 scores sit at 90 to 93
and the oracle at 95 to 99. Grounding is the healthiest set in the benchmark: 84% of judgments are informative, median
r is 0.54, and tier 1 disagrees on 27% of judgments. Most of its headroom is rows some tier-1 system already gets,
so better systems should move it. Content replies has only two systems in tier 1 and a 4.7% band no tier-1 system
gets. Tier-1 misses fall at the same rate on BeaverTails and HarmBench rows (12 to 13%). In indirect attacks the misses are mostly attacks let through
(175 of 267 missed judgments are positives), concentrated in SEP.

**Content requests is not saturated, but its headroom is over-blocking.** Tier 1 tops out at 86.8. 320 of the 497
judgments some tier-1 system misses are benign rows it blocked. OR-Bench rows are missed by at least one tier-1
system 72% of the time, XSTest rows 21%. A quarter of judgments are reversed (r below 0), the second highest share.
The source of this is mostly calibration on benign-but-alarming requests.

**Direct prompt attacks is the hardest job, and some of that is the labels.** Top 74.4, oracle 89.9. 10.8% of
judgments get no tier-1 system right, and 31.7% reward weaker systems. The authored quote-frame benign rows (a real
jailbreak quoted inside a request to translate or classify it) are missed by at least one tier-1 system 95% of the
time, and 18 of the 22 judgments nobody gets right are from that source. Tier 1 here holds Clef, Clef Flash, Kev 4B
and Kev 9B, which block a lot of benign text (false-block rates 19 to 43%). The job measures where each system sits
on the catch versus false-block trade-off as much as how well it reads attacks. WildJailbreak, in-the-wild prompts
and Mosscap each get 38 to 46% of rows missed by some tier-1 system.

## What a harder set needs to fix

1. **Stop adding rows like the PII and topics rows.** They no longer move the top. Edition 3 should keep them as a
   regression check and spend new rows elsewhere.
2. **Make rows that reorder tier 1.** Today the share of rows where tier 1 disagrees ranges from 4.5% (topics) to
   34.5% (direct). A hard set should aim for at least 30% in every category, checked on the pilot.
3. **Keep benign twins.** Both open jobs are about false blocks as much as catches. Every hard attack needs a benign
   counterpart close enough that a system cannot win by blocking a style.
4. **Contamination is not measured.** Every row, the unpublished slice included, comes from public upstream data
   (ruling 15). The slice can show overfitting to our published rows. It cannot show training on the upstream sets.
   Only rows that never existed in public can.

[`33-edition-3-hard-set.md`](33-edition-3-hard-set.md) proposes that set.
