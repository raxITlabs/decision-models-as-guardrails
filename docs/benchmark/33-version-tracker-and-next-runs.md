# Version tracker on the site, and the next version runs

Date: 24 October 2026. A proposal and a plan. Nothing in it has run. The findings it builds on are in
`32-version-progress.md`.

## 1. The site view

### Where it goes

On the leaderboard, each model shows its newest version. Under its name an underlined link, "2 earlier versions", opens the
older versions as indented rows with their own scores. Below them, one line per version step gives the score change with its
interval, catches and false blocks, each with a verdict word. A use-case view shows the change on that use case. A link goes to
`/versions` for the full comparison.

The rank column counts the rows on show, so the folded board reads 1, 2, 3 with no gaps, and tied systems share a number.
An opened earlier version has no rank of its own. Tiers stay exactly as published: they come from the board's tests over
all 20 systems, and re-ranking on newest versions only would change published numbers, which is a new release, not a display
change. Earlier versions are folded until the reader opens them. The scatter plot shows
newest versions only.

"Newest" is release order, not the best score. For Strands that puts the Qwen3.5 checkpoint first, though it blocks more benign
documents than v21.

`/versions` is no longer in the menu. The leaderboard rows link to it, and the sitemap lists it.

### What the /versions page shows for each model

One block per lineage, ruled off like the rest of the site, with no cards and no pill toggles.

1. **A version strip.** One dot per version, left to right in release order, at its overall score with its 95% interval as a thin
   line. A planned version gets a hollow marker and "not yet run". The question it answers is whether the model is getting better.
2. **A verdict line for each step.** "+1.88 points, better" or "+0.19 points, no clear change". The interval sits beside it in
   small type: "95% interval -0.27 to +0.65". The site uses three words:
   - **Better**: Holm-adjusted p below 0.05 and the score went up;
   - **Worse**: the same test, and the score went down;
   - **No clear change**: everything else. "Within noise" is our internal term; "no clear change" is plainer for readers.
   If the board cannot separate the two versions when we can, the line says so: "the leaderboard cannot tell these two apart".
   That applies to Strands 2B v21 to Qwen3.5.
3. **Catches and false blocks beside the score.** Two signed numbers per step, with the same three verdict words: "catches +1.3
   points, false blocks +0.9 points". Leave these out and Jev 1.14.0 reads as "no change" when it moved both ways.
4. **A per-use-case dot plot.** One line per use case, the eight the home page uses. An open dot marks the old score, a filled dot
   the new, joined by a short line. A use case with no clear change is drawn in muted ink, so the significant moves stand out. The
   change and verdict word sit at the right. This is the main chart.
5. **Fixed and broken.** One sentence: "1.14.0 fixed 221 checks that 1.13.0 got wrong and broke 199 it got right." It keeps the
   reader from treating a flat score as no change.
6. **Cost.** "Same price per check" for Jev. For self-hosted models the cost is a share of GPU time, so a version run on another
   machine shows "cost not comparable: different hardware" instead of a percentage.

### What stays off the site

Calibration (ECE), McNemar and the per-family Holm details go in the method note and the results file. They support the verdicts
but they do not help someone pick a guardrail. The page has one line of method with a link to `32-version-progress.md` on GitHub.

### Copy rules

- Never "improved" or "regressed" for a change with no clear verdict.
- Never a bare score delta without its interval.
- No rulings, editions or internal process on the page (PRODUCT.md).

The prototypes are the folded rows in `site/components/leaderboard.tsx` and `site/app/versions/page.tsx`, both reading
`site/data/versions.json` through `site/lib/versions.ts`.

## 2. Next run: Perplexity Decider v1.2

Planned in `31-edition-3-models-plan.md` as `pplx-decider-v1-2-27b`. That plan adds v1.2 to the board as a new system. This section
adds the version comparison against v1 and what it needs.

### What has to be decided first

Task 1 of plan 31 checks whether Perplexity's Decisions API serves v1.2. That decides the route:

| Route | Where the held-back slice goes | Ruling needed | Cost estimate |
|---|---|---|---|
| Hosted, Decisions API | Perplexity | Yes, new: ruling 21 covered v1 only | USD 0.60 to 1.00 |
| Self-hosted, open weights on one A100 80 GB | the project VM only | Spend only | USD 15 to 30 |

Hosted estimate: v1 cost USD 0.56 for all 9,975 checks at USD 0.04 per million input tokens. With the same prompts and price, v1.2
costs the same. Add the smoke run and one retry pass, and allow for a price change up to about 1.7 times. The price must be read
from Perplexity's pricing page and dated in `tariffs.json` before the forecast.

Self-hosted estimate: Strands Decider 26B-A4B took 4,756 seconds on a2-ultragpu-1g at USD 5.03 an hour, USD 6.68. That model
activates 4B parameters per token. A dense 27B is slower, roughly two to four times on the same card, so 3 to 6 hours with set-up
and the smoke run.

### Rulings the owner needs to make

1. **Held-back slice to Perplexity for v1.2.** Only if the route is hosted. The ruling should say the same terms as ruling 21 apply:
   the data-retention waiver and held-back rows allowed, for v1.2 only.
2. **Spend.** Hosted under USD 2, or self-hosted under USD 35, with a stop if the forecast exceeds it.
3. **How v1.2 shows on the board.** As a new row beside v1, matching Jev 1.13.0 and 1.14.0 and the Strands checkpoints. That is the
   current practice and needs no change. Confirm it.
4. **The version verdict rule.** The Holm families in `32-version-progress.md` and the three verdict words above. Make it a ruling
   before v1.2's numbers exist, so the rule cannot be fitted to the result.

### Steps

1. Plan 31 Task 1: one canned call, no dataset rows, under USD 0.01. Ask the owner first.
2. Owner rulings 1 to 4.
3. Freeze. `e2_versions.py` needs no freeze of its own: it reads the ledgers the new run writes. Its version verdict rule is fixed
   by ruling 4.
4. Run v1.2 under plan 31: smoke on dev rows, extension manifest committed, full pass, retry pass, report, score.
5. Add `pplx-decider-v1-2-27b` to `versions.LINEAGES["perplexity-decider"]["versions"]`, move it out of `planned`, and add the
   ledger folder to `e2_versions.SOURCES`. Run `uv run python benchmark/runs/e2_versions.py score`. Its board check must pass.
6. Write the findings into `32-version-progress.md` and rebuild the site data.

## 3. A repeatable recipe for the next Jev release

Jev 1.14.0 ran with its own script, `benchmark/runs/e2_jev114_run.py`, copied from the gpt-6-luna run. The next release should not
need a new script.

1. **Generalise the run script.** Turn `e2_jev114_run.py` into `e2_jev_release.py --version 1.15.0`. The system id, ledger folder,
   manifest name and tariff key all come from the version. Arms copy Jev 1.13.0's eight question sets, as now. The model is sent by
   its versioned id, never `jev-latest`, and the response's model field is checked on every row.
2. **Tariff.** A dated entry in `tariffs.json`, read from TypeSafe's models page on the run day.
3. **Smoke, freeze, run, report, score**, as for 1.14.0. Cost about USD 0.38 per release at today's price, plus a few cents for the
   smoke.
4. **Version analysis.** Append the version to `LINEAGES["jev"]`, run `e2_versions.py score`, and update the write-up and the site.
5. **A drift check, new.** Before the run, resend 1,000 public test rows to the previous version, about USD 0.04, and compare them
   with its board ledger. A hosted API can change behind a fixed version id. If more than 1% of judgments flip with no version
   change, the version comparison carries a note that part of the change may be serving drift. The same check fits Perplexity
   if v1.2 runs hosted.

Ruling for future Jev releases. Jev 1.14.0's held-back rows went to TypeSafe under ruling 21, as 1.13.0's did. A standing ruling
would save asking each time: a new version of a model already on the board, from the same vendor and endpoint, may receive the
held-back slice on the same terms as its predecessor, with its own freeze manifest and a spend cap of USD 2 per release. The owner
decides whether to grant it. Until then each release needs its own yes.

## 4. Costs at a glance

| Run | Estimate |
|---|---|
| This analysis (`e2_versions.py`) | free, offline |
| Perplexity v1.2, hosted | USD 0.60 to 1.00 |
| Perplexity v1.2, self-hosted on A100 | USD 15 to 30 |
| Each future Jev release | about USD 0.40, plus USD 0.04 for the drift check |
