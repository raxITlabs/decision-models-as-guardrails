# Bias clarification: independent verification

Written 29 September 2026 against the uncommitted working tree on `main`, HEAD 40fda4b. The brief is
docs/benchmark/bias-distinction-developer-handoff.md. I edited nothing except this file. I made no model or API
calls, uploads, commits or pushes.

Verdict: every required check passes. Three items need a decision from the coordinator. They are listed at the end.

| Item | Result |
|---|---|
| 1. Test suites and checkers | PASS |
| 2. No historical record changed; overall equals leaderboard-final.json | PASS, with one flag: dataset/release/v1.3/known-issues.json |
| 3. Spot-check of numbers against bias.json | PASS, 14 of 14 |
| 4. Claims to avoid, "fairness score", generic "Bias" heading | PASS, with one residual note on the CSV download |
| 5. Completion criteria per part | PASS, table below |

## 1. Commands and exact outputs

| Command | Output | Result |
|---|---|---|
| `cd benchmark && uv run pytest -q` | `206 passed in 8.32s` | PASS |
| `cd dataset && uv run pytest -q` | `95 passed, 1 skipped in 0.85s` | PASS |
| `cd site/leaderboard && uv run --with pytest --with jsonschema pytest -q tests` | `18 passed in 1.58s` | PASS |
| `uv run python benchmark/runs/check_page.py` | 33 lines, all `PASS`, 0 other lines, exit 0 | PASS |
| `uv run python benchmark/runs/validate_extension_freeze.py` | `50 of 50 arms pass`, exit 0 | PASS |

The six new check_page lines all pass. They cover bias-parts.json built from this bias.json by sha256, the page
copying bias-parts.json and the audit counts, the three part names with no generic "Bias" heading, Bedrock not
applicable in decision-model bias, the overall unchanged with no combined number, and no forbidden claim.

check_page.py rewrites page-check.json. Its sha256 was 6a5bcbe0... before and after my run, so the run changed
nothing. `git status --porcelain` was identical before and after all five commands.

## 2. Historical records

`git diff HEAD` shows no change to any of these:

- benchmark/results/first-benchmark/bias.json. Its sha256 is f8c9791166b33cfea6a06f58df2382ea6da00a96b879a07ea99a09a3bdcbc5a5,
  the value bias-parts.json and results.json pin.
- All 8 tracked leaderboard*.json files, including leaderboard-final.json and leaderboard-v1.3.json.
- All 113 tracked *.jsonl files. No untracked *.jsonl exists under results or release.
- Freeze manifests. check_page reports them committed and unchanged.
- Approvals and contracts under benchmark/subsets.
- dataset/release/v1.3/manifest.json, dataset/frozen/**, and the ignored dataset/release/*/build directories. No file
  under those paths has a modification time after the last commit.

Two files carry a new mtime, dataset/release/v1.3/publication.json and
benchmark/results/first-benchmark/extension-freeze-validation.json. Their content is byte-identical to HEAD. The
staging run and the freeze validator rewrote them with the same bytes.

**Flag.** dataset/release/v1.3/known-issues.json is modified, +5 lines and no removals. It gains one entry,
`bias-three-parts`. The task's hard rules forbid edits under dataset/release/**, while the docs agent reports that its
own instructions allowed this one sidecar entry. No hash pins the file. publish.py reads it as descriptive metadata
and the file says it corrects metadata only. The manifest is untouched. The coordinator should confirm the exception
or revert the entry before committing.

dataset/release/rights-confirmation-2026-09-25.json is untracked. Its mtime is 25 September, so this task did not
create it.

**Six-suite overall.** In site/leaderboard/results.json, `entries`, `comparisons` and `implementations` are
identical to HEAD. For all 7 ranked implementations, the page overall equals leaderboard-final.json `overall` to the
page's 4-decimal rounding. That covers the score, both interval ends and each of the six suite task scores. Cost
matches to 5 decimals.

| Implementation | Page overall [95% interval] | leaderboard-final.json |
|---|---|---|
| bedrock | 81.0995 [78.7493, 83.2915] | 81.099541 [78.7493, 83.2915] |
| jev | 91.8776 [90.6152, 93.0445] | 91.877638 [90.6152, 93.0445] |
| kev-0-8b | 73.0556 [70.6035, 75.5705] | 73.05561 [70.6035, 75.5705] |
| kev-4b | 86.5043 [84.9536, 88.0131] | 86.504283 [84.9536, 88.0131] |
| kev-9b | 87.1136 [85.4783, 88.6165] | 87.113599 [85.4783, 88.6165] |
| laya | 69.6092 [67.2678, 71.7437] | 69.609231 [67.2678, 71.7437] |
| open-jev-2b | 73.3066 [70.9728, 75.5996] | 73.306552 [70.9728, 75.5996] |

No overall entry contains a bias suite. Compared with HEAD, results.json changes in only three places. It adds
`bias_parts`, rewords `benchmark.aggregation`, and rewords the `supports` and `limits` text of data_quality item 7,
the fairness and bias row.

## 3. Spot-check against bias.json

I read the values from all three files independently. BBQ totals are sums over bias.json categories.

| # | Value | bias.json | bias-parts.json | results.json page data |
|---|---|---|---|---|
| 1 | bedrock-checks B1 FPR | 0.04 | 0.04 | 0.04 |
| 2 | bedrock-checks B1 FNR interval high | 0.6667 | 0.6667 | 0.6667 |
| 3 | kev-4b B1 false negatives, of 50 | 21 | 21 | 21 |
| 4 | kev-9b "male" mentioned harmful n | 14 | 14 | 14 |
| 5 | kev-9b "male" FNR gap | -0.38655 | -0.38655 | -0.38655 |
| 6 | jev "female" FPR gap interval low | -0.37876 | -0.37876 | -0.37876 |
| 7 | open-jev-2b B2 paired correct rate | 0.5 | 0.5 | 0.5 |
| 8 | kev-0-8b B2 all_wrong | 1 | 1 | 1 |
| 9 | bedrock-checks B2 flip rate | 0.25 | 0.25 | 0.25 |
| 10 | jev BBQ disambiguated correct/n | 55/62 | 55/62 | 55/62 |
| 11 | kev-4b BBQ ambiguous correct/n | 83/88 | 83/88 | 83/88 |
| 12 | laya discrim-eval mean_p_yes | 0.670616 | 0.670616 | 0.670616 |
| 13 | kev-9b discrim-eval n | 50 | 50 | 50 |
| 14 | bedrock decision-bias status | not_applicable | not_applicable | not_applicable |

All 14 match at full precision. No page system entry carries discrim-eval `comparisons`, so the page shows no
group gap. The page's hate counts, 28 and 36 harmful, 13 benign and 560 content rows, equal bias-audit.json.

I recounted from the v1.3 subset manifest joined to dataset/release/v1.3/build/F1.test.jsonl. That gives 560 F1
test rows and 50 harmful rows in the taxonomy HATE category, 16 of them without a hate source label. Those match the
audit. The 28 depends on raw Aegis violated categories, which the build keeps only as the first-match
`source_label`. By `source_label` alone I get 18 Aegis rows. The audit's extra 3 are one Harassment or Profanity row
that also lists hate, plus 2 rows filed under other categories. That agrees with the audit's own breakdown. I did not
re-read the Hugging Face cache.

I also loaded the page from the local server on 8765. Its results.json has the same sha256 as the working file,
21edbe4b..., and the console shows no errors.

## 4. Claims to avoid, "fairness score", generic heading

I grepped 20 files: the 15 modified tracked files and the 5 new ones, which are 25-bias-audit.md, bias_parts.py,
test_bias_parts.py, bias-audit.json and bias-parts.json. The patterns were fairness percentage or score, bias score,
free of bias, bias-free, unbiased, no bias, equal treatment, treats groups equally, general-purpose bias, bias
detector, isolate demographic bias, fairness rating, "% fair", treated equally or fairly, "is fair" and "fair
across". I read every hit in context. None makes an affirmative forbidden claim.

- Negated statements of the brief's five claims, all correct: CORRECTIONS.md:215-217,
  dataset/goldrails_dataset/publish.py:613-615, dataset/publish/v1.3-full/README.md:133, KNOWN_ISSUES.md:13,
  dataset/release/v1.3/known-issues.json:51, docs/README.md:36, docs/teach/gold-rails-primer.html:282 and 461-463,
  docs/benchmark/25-bias-audit.md:65, 114, 203 and 206-207, benchmark/runs/site_results.py:788,
  site/leaderboard/results.json:617, bias-audit.json:197 and 249.
- "Bias score" appears only as the BBQ source metric, a per-category value from -1 to 1. No hit uses it as an
  overall percentage. The hits are site/leaderboard/index.html:858, the per-category BBQ table header;
  results.json:3381, 3554, 3727, 3900, 4073 and 4246; bias-parts.json:388, 972, 1502, 2026, 2610 and 3188;
  results.schema.json:1845; bias-audit.json:152 and 157; 25-bias-audit.md:172; and docs/benchmark/21-bias-evaluation.md:110 and 225.
- "Fairness score" appears only in negations: docs/benchmark/21-bias-evaluation.md:210, "never merged into one
  fairness score", and bias-parts.json:18026, "No single fairness score". The pattern list in check_page.py:61-63 and
  the check names in page-check.json:164 and 169 are the checker's own text.

**Generic heading.** The rendered page has no heading, summary, menu item or filter option that reads "Bias" alone.
Its headings are H2 "Hate detection, guardrail fairness and decision-model bias", plus one H3 for each exact part
name. The section menu reads "Hate, fairness & bias", followed by the three part names. The page leaves no element
with `data-suite="bias"`, so the old bias score chart and detail panel cannot be reached.

site/leaderboard/leaderboard.js:34 still has `label: "Bias"` in VIEWS. index.html:370 overrides it with LABEL.bias,
and the CSV `view` column uses the suite id, not this label. No page text shows it. The file is unchanged from HEAD.

**Em dashes.** Across site/leaderboard/, the only em dash is the owner-chosen "Profanity or obscenity — Civil
Comments" at index.html:370. It was already in HEAD, and the site test exempts it by name. The new files and added
lines contain no other em dash.

**Residual note, not a failure.** The frozen bias entries in results.json keep `quality.score`. For B1 this is 100
times balanced accuracy, for example 75.0 for jev. For B3 it is BBQ ambiguous accuracy, for example 100.0 for jev.
The CSV download still exports both in its `score` column, for rows `bias:guardrail_fairness` and
`bias:decision_bias`. The status_note in each row says "Not a fairness ranking". A CSV reader could still take the
75.0 as a fairness percentage. The rules require these entries to stay unchanged, so fixing it means leaving these
rows out of the CSV or relabelling the column. That is the coordinator's call.

## 5. Completion criteria per part

| | Hate and discrimination detection | Guardrail fairness diagnostics | Decision-model bias diagnostics |
|---|---|---|---|
| What was tested | Rows inside the 560 F1 content test rows. 28 harmful rows carry an identity-hate source label: Aegis 2.0 "Hate/Identity Hate" 21, split 8 prompts and 13 replies; OpenAI H or H2 3; AILuminate hte 4. The count is 36 with JailbreakBench's combined Harassment/Discrimination category, which adds 8. Another 13 benign rows sit on the same topic. | B1 is 100 Civil Comments rows, 50 toxic at 0.5 or above and 50 benign below 0.2, with 24 annotated identities. B2 is 8 rows, 4 identity-swapped test pairs in 3 clusters. | BBQ is 150 rows over 11 categories and 95 templates, 88 ambiguous and 62 disambiguated. discrim-eval is 50 rows over 31 scenarios. |
| What defines correctness | The source's binary harmful or safe label. The content score is any-harm versus none at the frozen content thresholds. The hate category is metadata and does not enter scoring. | B1 uses the Civil Comments toxicity label, not a hate or discrimination label. An identity mention sets the group and never the label. FPR and FNR are measured at the frozen request threshold. In B2 both texts share one expected action, drafted by a single AI reviewer. Consistency is the flip rate, correctness is the paired correct rate, and the page shows both. | BBQ uses the source's gold option, "unknown" for ambiguous contexts. discrim-eval has no correct answer. Its metric is p(yes), and group gaps come from logits. |
| Which systems are comparable | All 7 that have a content score: bedrock, jev, kev-0-8b, kev-4b, kev-9b, laya and open-jev-2b. | The same 7, including Bedrock. Regex is not applicable because it is not a content classifier. | The 6 decision models. Bedrock and regex are marked not applicable, never zero. |
| What the evidence supports | Moderation accuracy on these rows, counted once inside content, which is one sixth of the overall. It supports no separate hate score, which is not computed. 16 of the 50 taxonomy-HATE rows have no hate source label, and 21 of the 33 Aegis rows in that category have LLM-jury labels. Catching hate says nothing about fairness. | Each system's overall B1 FPR and FNR on general toxicity, with n = 50 and 50 and 95% intervals, and four individual B2 cases. Per-identity gaps are unsupported: 0 of 24 groups reach 30 rows and 15 identities have no rows. The page flags every group "Insufficient evidence" and B2 "Too few pairs". A zero gap would not show equal treatment. A B1 miss is a missed toxic comment, not missed hate. | BBQ accuracy by context condition on this sample. The prompt points the model at the "unknown" option, so the result does not compare with published BBQ, and per-category cells are too small. discrim-eval supports mean p(yes) only. Its group gaps compare different scenarios, so they do not isolate demographic bias. The page flags it "Insufficient evidence" and shows no gap. |

bias-parts.json, results.json `bias_parts` and docs/benchmark/25-bias-audit.md carry each cell of this table, and
check_page.py tests them. The primer, docs/README.md and the dataset card state the same split in shorter form.

## For the coordinator

1. Confirm or revert the `bias-three-parts` entry in dataset/release/v1.3/known-issues.json. It is the only change
   under dataset/release/**.
2. Decide whether the CSV download should keep the frozen bias `quality.score` values in its `score` column.
3. check_page's forbidden-claim regex, check_page.py:62-63, does not cover the fifth claim, a demographic difference
   on unmatched scenarios. The page passes because a separate check requires discrim-eval to show no gap, and my
   grep found only negated uses. Extending the regex would close the gap.
4. The audit's open findings still stand and this work only describes them. discrim-eval needs matched scenario sets,
   which means new model calls. The code and docs/21 disagree on the B1 comparison group. docs/21 open decisions 1
   and 2 are unresolved. The B2 male/female pair needs a human check.
5. If the card revision is uploaded, the staged CHANGELOG needs a second `--card-update` line, as the docs agent
   notes.
