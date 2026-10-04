# Content suite: the human second-label sample

Owner ruling 7 (`29-owner-rulings-2026-10-03.md`) says a person second-labels a 400-row stratified sample of the
content suite, and we publish the agreement rate. This page covers how the sample is drawn, how to label it and how
the result is scored. It contains no row text, and nothing it describes puts row text into git.

## What is in git and what is not

| File | In git | Holds |
|---|---|---|
| `dataset/goldrails_dataset/content_sample.py` | yes | Draws the sample, builds the labelling page, scores the labels. |
| `dataset/goldrails_dataset/content_sample_label.html` | yes | The page template. It holds no rows. |
| `dataset/edition2/content/sample/` | no | `label.html` (the page with the 400 rows embedded) and `manifest.json` (sampled ids and strata). |
| `dataset/edition2/content/agreement.json` | yes | The sample design and, once labels exist, the agreement figures. Counts and rates only. |

The whole `sample/` folder is git-ignored. `label.html` carries the row text, much of it harmful, and some of it
comes from sources whose licence is not cleared for redistribution. Do not commit it, attach it to an issue or
publish it as a web page. Pass it to the labeller by hand.

## The sample

The population is every content row in the current edition 2 build's public tune and test files
(`dataset/edition2/build/F1.tune.jsonl` and `F1.test.jsonl`) whose id is in the tracked public
`dataset/edition2/content/candidates.jsonl`. That excludes the private slice, the rows the build dropped for overlap,
and the disputed rows still waiting for the owner. On 3 October 2026 the population was 2,261 rows.

Strata are subtask x first label x source, which gives 15 strata. Each stratum gets at least 10 rows, and the rest of
the 400 goes out in proportion to stratum size by largest remainder. Within a stratum the rows are drawn with Python's
`random.Random(20261003)` from the ids in sorted order, and the 400 are then shuffled with the same generator, so the
labeller sees strata mixed. The seed, the per-stratum counts and the sha256 of both build files are in
`agreement.json` under `design`.

| Stratum (subtask, first label, source) | Population | Sample |
|---|---:|---:|
| harmful_goal, no, e2_content_orbench80k | 141 | 25 |
| harmful_goal, no, e2_content_xstest | 190 | 32 |
| harmful_goal, yes, e2_content_harmbench | 188 | 32 |
| harmful_goal, yes, e2_content_xstest | 157 | 28 |
| input, no, aegis2 | 153 | 27 |
| input, no, openai_moderation | 152 | 26 |
| input, yes, aegis2 | 94 | 19 |
| input, yes, ailuminate_demo | 111 | 21 |
| input, yes, openai_moderation | 89 | 19 |
| output, no, e2_content_aegis2_val | 175 | 30 |
| output, no, e2_content_harmbench_cls | 147 | 26 |
| output, yes, e2_content_aegis2_val | 189 | 32 |
| output, yes, e2_content_harmbench_cls | 155 | 28 |
| over_refusal, no, e2_content_orbench80k | 92 | 19 |
| over_refusal, no, orbench | 228 | 36 |
| **Total** | **2,261** | **400** |

If the build changes before labelling starts, rerun `draw`. Same build, same seed, same 400 rows. A changed build gives
a new sample and a new `sample_key`, and the page keeps labels for each sample key apart.

## Build the page

    uv run python -m goldrails_dataset.content_sample draw

This needs the git-ignored `content/local/text.jsonl` (rows from uncleared sources) and a built edition 2
(`uv run python -m goldrails_dataset.edition2`). It writes `sample/label.html`, `sample/manifest.json` and a
pending `agreement.json`. The page reads the content policy (`benchmark/policies/content/request.md` and `reply.md`)
at build time, so rebuild it after a policy edit.

## Labelling

Open `label.html` in a browser. It is one file, works offline and makes no network requests. Enter your name; the
export records it.

Each row shows one message to judge. A **request** row is a user's message, judged against the request policy. A
**reply** row is an assistant's reply, judged against the reply policy, with the user's turn above it as context.
The matching policy opens beside the row. It includes clarifications C1 to C3, which ruling 8 approved: personal data
alone is not a content violation, narrating or discussing violence is not harmful without operational detail or
glorification, and name-calling aimed at a person is an insult while untargeted rudeness is not.

The page hides the first label, the source, the harm category and the split. Judge each row from the policy alone.

- **Yes** means the judged text breaks the policy.
- **No** means it does not.
- **Unsure** is for a row the policy does not settle. Say why in the note. Don't use it to skip a row that is
  unpleasant but clear.

Notes are optional. Write which policy line decided the row, or what made it hard. Do not paste row text into a note:
notes leave the machine in the export.

| Key | Does |
|---|---|
| `Y` / `N` / `U` | label yes, no or unsure, then move to the next row |
| `J` or right arrow, `K` or left arrow | next or previous row |
| `G` | next unlabelled row |
| `/` | write a note (`Esc` leaves it) |
| `Backspace` | clear this row's label |
| `P` | show or hide the policy |
| `E` | export |
| `?` | list the keys |

The page saves every change to the browser's local storage, so you can close it and come back. Local storage belongs
to one browser profile. A private window, or clearing site data, loses it. Export at the end of each session to be
safe. **Import** loads an export back in, keeping the newer label for each row.

**Export JSONL** downloads one line per labelled row:

    {"id": "...", "label": "yes|no|unsure", "note": "...", "labeller": "...", "timestamp": "ISO 8601"}

Send that file to the owner. It holds ids, labels and your notes, no row text.

## Scoring

    uv run python -m goldrails_dataset.content_sample score content-sample-labels-NAME-DATE.jsonl

The scorer takes one or more exports from one labeller and keeps the newest label for each id. It rejects an id that
is not in the sample and a label that is not yes, no or unsure. It compares the person's label with the label the
build holds and writes `agreement.json`. That is the first label in `candidates.jsonl`, except for the 14 content
disputes that ruling 8 resolved, where it is the final label in `content/resolutions.jsonl`. The draw stores it as
`reference` in the sample manifest.

- **overall**: agreement and Cohen's kappa on rows labelled yes or no, the unsure count, agreement with unsure counted
  as disagreement, the first-to-human confusion counts, agreement and kappa weighted back to the population (each row
  weighs stratum population over stratum sample), and a stratified bootstrap 95% interval (2,000 resamples, the
  sample seed) for agreement and kappa.
- **by_stratum**, **by_subtask**, **by_source**, **by_split**: the same counts and agreement per group.

The first label takes one value in every stratum, because it is one of the stratum keys. It also takes one value
across the whole `over_refusal` subtask. In those groups kappa is undefined, so `agreement.json` gives `null` and a
note, and the group is read by its agreement rate. Kappa is meaningful overall and in the mixed groups.

`status` reads `awaiting labels`, `partial` (fewer than 400 rows labelled) or `complete`. Only a complete result is
the published figure for ruling 7.

The edition 2 build audit (`uv run python -m goldrails_dataset.edition2`) reads `agreement.json`. A content row with
no blind second label counts as covered when the sample was drawn from the current build, meaning its F1 tune and test
digests match the build files. The audit then reports the sample as `pending human labels`. A sample drawn from an
earlier build fails the second-label gate until it is redrawn. Until `status` is `complete`, the audit's
`publication` block stays `ready: false`, and `--require-publishable` exits 1.
