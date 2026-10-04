# Edition 2 content: sources, tags and proposals

First-labeller output for the content suite (docs/benchmark/26-edition-2-plan.md, row "Content"). Built by
`uv run python -m goldrails_dataset.sources.e2_content --v1-build <dir> ...` with seed 20261002 and tag version
`e2-content-tags-v1`. Nothing here is reviewed yet. A blind second labeller works from `review-packet/`, then the owner.

## Files

| File | What it holds |
|---|---|
| `candidates.jsonl` | 2,299 new dev and test rows. `private/candidates.jsonl` holds the 397 private-slice rows and must stay out of git, because the repository is public. Each row is a full `Record` plus `suite`, `label`, `source`, `licence`, `group`, `proposed_split` (dev, test or private; private rows have `visibility: heldout`), `harm_category`, `harm_categories`, `harm_subcategories`, `in_bedrock_five`, `vendor_owned`, `vendor`, `entity_types`, `upstream_split`, `upstream_train_split_flag`, `label_rationale` and `packet_id`. |
| `v1-content-tags.jsonl` | Tags for all 2,326 F1 rows in the v1.3 release build. Ids only, no text. Includes `in_subset` and `subset_split` so the v1 ledgers can be re-scored with and without Bedrock's coverage gap. |
| `v1-outside-five.jsonl` | The 32 v1 test positives that taxonomy.py files under PII (21) or TOPIC (11). Each was read and carries a proposal. |
| `review-packet/`, `private/review-packet/` | Blind packets in the `packet.py` format: `00-policy.md`, `01-rows.md`, `labels.template.jsonl`. Rows use opaque `packet_id`s in hash order, so the packet shows no source, label or rationale. |
| `counts.json` | Every count below, plus exclusions by reason and the per-cell pools left after exclusion. |

## Sources

| Source (loader) | Licence | Pinned at | Upstream split | Used for | Vendor-owned |
|---|---|---|---|---|---|
| Aegis 2.0 test (`aegis2`) | CC-BY-4.0 | HF d86bb8b | test | input yes/no | NVIDIA |
| Aegis 2.0 validation (`e2_content_aegis2_val`) | CC-BY-4.0 | HF d86bb8b | validation | removed 5 October (round 6) | NVIDIA |
| Aegis 2.0 test, rows v1 left (`e2_content_aegis2_test`, round 6) | CC-BY-4.0 | HF d86bb8b | test | input yes/no | NVIDIA |
| BeaverTails (`e2_content_beavertails`, round 6) | CC-BY-NC-4.0, ids only | HF 8401fe6 | 330k_test | output yes/no | no |
| OpenAI moderation eval (`openai_moderation`) | MIT | HF 84e5cf3 | train (only split; it is the eval set) | input yes/no | OpenAI |
| AILuminate demo (`ailuminate_demo`) | CC-BY-4.0 | git 769cc2b | demo set | input yes | no |
| OR-Bench hard-1k (`orbench`) | CC-BY-4.0 | HF e36d8b8 | train (only split) | over_refusal | no |
| OR-Bench 80k (`e2_content_orbench80k`, new) | CC-BY-4.0 | HF e36d8b8 | train (only split) | over_refusal; harmful_goal no | no |
| HarmBench text behaviours (`e2_content_harmbench`, new) | MIT | git 8e1604d | test | harmful_goal yes | no |
| HarmBench classifier val (`e2_content_harmbench_cls`, new) | MIT | git 8e1604d | classifier validation | output yes/no | no (completions come from several models; generator recorded per row) |
| XSTest v2 (`e2_content_xstest`, new) | CC-BY-4.0 | git d7bb5bd | test | harmful_goal yes/no | no |

Every source has a licence that allows redistribution with attribution. The four new upstreams are not yet in
`dataset/release/redistribution.json`, so the integration agent should add them (see REGISTER.md).

I added new sources only where v1 had used up the old ones. All 200 JailbreakBench behaviours are in v1, so
harmful_goal needed HarmBench and XSTest. v1 took 776 of the Aegis test split's 852 labelled replies, and every
reply left over shares a conversation or text with a v1 row, so output needed Aegis validation and HarmBench's
human-labelled completions. OR-Bench 80k contributes more benign prompts from the same upstream as hard-1k.

Rows flagged `upstream_train_split_flag: true` come from OpenAI moderation and OR-Bench (hard-1k and 80k). Both
publish a single split called "train", and that split is the benchmark itself. No source has a separate test split
that we passed over.

## Round 6, 5 October 2026

pplx-decider-v1-27b publishes its training recipe (`source/src/autojev/data.py` at 5117a6c). It trains on the Aegis
2.0 train split and tunes on the validation split, and it only evaluates on the test split. So the 400
`e2_content_aegis2_val` rows were not fair test rows for that model, and all of them left, dev rows included
(`uv run python -m goldrails_dataset.sources.e2_content --round6`).

The Aegis test split could not fill their place. v1 already holds every labelled test reply, so
`e2_content_aegis2_test` adds prompts to `input` only: 80 harmful and 25 benign, all to test (input's dev and
private cells were already at target). That leaves `output` short of a second source, so round 6 adds BeaverTails
replies from its 330k_test split. It is in neither Perplexity's nor Strands' recipe. Its licence is CC-BY-NC-4.0, so
the text stays local and the tracked file holds ids, labels and hashes.

Round 6 changes nothing about the rows that stay. Every kept row keeps its split. New rows pass the first build's
exclusions, and four more:

- anything already in edition 2, in any suite (id, text, group or near-duplicate);
- any text in a split a benchmarked model's published recipe trains or tunes on (`model_overlap.seen_by_model`; 36
  Aegis test prompts and 3,008 BeaverTails pairs failed this, most because BeaverTails and Aegis share Anthropic
  red-team prompts);
- an upstream positive with no category in Bedrock's five. Under ruling 8 (C1) personal data alone is not a content
  violation, and a privacy, politics or "unethical" tag alone does not settle the label, so those rows stay out
  rather than get a forced label;
- a BeaverTails pair that appears more than once with different `is_safe` labels.

At most two replies per BeaverTails question, and the question is the group, so its replies share a split. The
selection and split order are salted like the first build's. The new dev and private rows fill each cell to the
same targets (45 and 50); the rest is test.

| Subtask | Class | Source | Dev | Test | Private |
|---|---|---|---|---|---|
| input | yes | e2_content_aegis2_test | 0 | 80 | 0 |
| input | no | e2_content_aegis2_test | 0 | 25 | 0 |
| output | yes | e2_content_beavertails | 13 | 206 | 11 |
| output | no | e2_content_beavertails | 11 | 212 | 17 |

Labels are the upstream ones: Aegis `prompt_label`, BeaverTails `is_safe` (crowd annotators). The ruling 7 human
sample was drawn again from the round 6 build, so it covers the new rows.

The same day, every test or unpublished row in any suite whose text is in Perplexity's training or development data
left edition 2 (`EXCLUDED.jsonl`, reason "text in pplx-decider-v1-27b training or development data";
`dataset/edition2/MODEL-TRAINING-OVERLAP.json`). In content that is 14 public test `aegis2` input rows and one
XSTest row, plus 4 unpublished rows. One dev row stays and is listed in the overlap file. One new Aegis test prompt
shares text with TypeSafe's cookbook and left under ruling 18, so 79 of the 80 harmful prompts remain.

The tables below are the first build's and are kept as a record.

## Exclusions

A row is out if any of these hold. Counts are in `counts.json`.

- **Overlap with v1.** The row matches v1 by id, by normalised text (state or context, two normalisations), by group (Aegis conversation), or as a near-duplicate (token Jaccard ≥ 0.7 on prompts up to 400 characters). The reference set is the v1.0, v1.1-ai, v1.2 and v1.3 release builds (git-ignored, read from the main checkout), plus every row-id-shaped string in `dataset/samples`, `dataset/frozen` (including examined-ids), `benchmark/results`, `benchmark/runs` and `benchmark/subsets`. That comes to 308 files and 10,226 ids. If one row of a group overlaps, the whole group goes.
- **Source rules.** Aegis "Needs Caution" rows and synthetic refusal-augmentation replies, OpenAI rows with an unlabelled category, HarmBench completions without a unanimous 3/3 or 0/3 vote (114), and HarmBench copyright behaviours.
- **Topic handoff.** 124 positives whose only category is specialised advice (AILuminate `spc_*`, Aegis "Unauthorized Advice") are left out of content. Their ids are in `counts.json` → `topic_handoff_ids` for the denied-topics agent.
- **Duplicate text inside edition 2.** v1 sources win over new ones. OR-Bench hard-1k wins over 80k, which contains it.

Groups merge across sources when rows share a text or are near-duplicate prompts (18 merges). No group straddles
splits.

## Counts (rows: dev / test / private)

| Subtask | Class | Source | Dev | Test | Private |
|---|---|---|---|---|---|
| input | yes | ailuminate_demo | 18 | 103 | 24 |
| input | yes | aegis2 | 8 | 90 | 12 |
| input | yes | openai_moderation | 19 | 77 | 14 |
| input | no | aegis2 | 21 | 136 | 28 |
| input | no | openai_moderation | 24 | 134 | 22 |
| output | yes | e2_content_aegis2_val | 13 | 176 | 11 |
| output | yes | e2_content_harmbench_cls | 32 | 123 | 39 |
| output | no | e2_content_aegis2_val | 17 | 158 | 25 |
| output | no | e2_content_harmbench_cls | 34 | 113 | 33 |
| harmful_goal | yes | e2_content_harmbench | 40 | 148 | 42 |
| harmful_goal | yes | e2_content_xstest | 33 | 124 | 39 |
| harmful_goal | no | e2_content_xstest | 49 | 148 | 49 |
| harmful_goal | no | e2_content_orbench80k | 13 | 128 | 9 |
| over_refusal | no | orbench | 28 | 200 | 32 |
| over_refusal | no | e2_content_orbench80k | 17 | 75 | 18 |

Test totals per class: input 270/270, output 299/271, harmful_goal 272/276, over_refusal 275 (negatives only).
Every scored cell clears 250, and every subtask has at least two sources. Split targets were 45 dev and 50 private
per cell. XSTest pairs and HarmBench behaviours couple rows across classes, so harmful_goal dev and private run a
little over target.

Test positives by harm category:

| Subtask | hate | insults | sexual | violence | misconduct | pii | other |
|---|---|---|---|---|---|---|---|
| input | 53 | 12 | 65 | 39 | 72 | 16 | 13 |
| output | 23 | 40 | 12 | 22 | 168 | 11 | 23 |
| harmful_goal | 19 | 10 | 1 | 78 | 121 | 12 | 31 |

106 of 841 test positives (12.6%) fall outside Bedrock's five. 151 positives carry more than one category.
`entity_types` holds PII that a regex found verbatim in the text (EMAIL, PHONE, IP_ADDRESS). These are routing
hints, not labels: 7 harmful_goal and 13 output rows.

## Tagging rule

`harm_tags` keeps every category a row's source lists. v1 kept only the first mapped one. `harm_category` is the
first category among Bedrock's five, or the first outside category when none of the five applies. Benign rows get
`none`. The mappings live in `sources/e2_content.py`.

Where my mappings differ from taxonomy.py:
- Aegis Harassment and Profanity, and OpenAI HR, go to insults, not hate.
- Misinformation and intellectual property go to other. v1 put them inside the five via defamation→INSULTS and ipv→MISCONDUCT.
- Self-harm goes to violence, which is a boundary call, and the subcategory says so.

I read and filed by hand the 18 HarmBench "harmful" catch-all behaviours, about 80 of the 200 XSTest unsafe
prompts (the rest follow their type's default), the 20 JailbreakBench disinformation and government rows, and the
32 rows below.

Under these tags the v1.3 subset has 24 test positives outside the five (13 other, 7 pii, 4 topic), not 32. The 24
include 13 that v1's taxonomy filed inside the five: misinformation as INSULTS and intellectual property as MISCONDUCT.

## Proposal: the 32 v1 positives outside the five

| Proposal | Rows | Examples |
|---|---|---|
| retag into the five | 21 | Phishing, blackmail, card cloning, record theft (misconduct). Racial face recognition (hate). |
| keep in content, tagged pii | 7 | Doxxing: home addresses, "who lives at this address". No PII entity in the text, so these are not PII-suite rows. |
| move to denied topics | 4 | Investment bot (InvestmentAdvice), AIDS and schizophrenia treatment plans (MedicalDiagnosis), DUI defence (LegalAdvice). |
| label query (overlaps the above) | 3 | Aegis replies labelled unsafe that refuse or disclose nothing: `5a8744861f`, `e363adf5c6`, `3ef40d6f5a`. |

The privacy positives should stay in content as tagged rows. The PII suite scores entity detection, and these rows
are requests to find someone. Moving them would change what they measure. Content gets two published views: all
positives, and positives with `in_bedrock_five` true (all negatives in both). Moves only apply in edition 2. The
four topic rows are v1 test rows, so they cannot enter an edition 2 suite.

## Proposal: shrink the words suite to a sanity check

The `word` subtask is deterministic, built from four phrases × templates, and AUROC is at least 0.99 for every top
system. I propose:
- Keep 24 test rows: one per template variant per phrase on a 2-phrase rotation, with 12 match and 12 non-match.
- Report it as a pass/fail gate ("all variants correct" or the list of failures), not a ranked score.
- Leave it out of any overall rank.
- Keep profanity as the scored subtask, with the note that Bedrock's managed word list is a different policy.

That frees about 130 test rows of run budget per system.

## Open issues

- Every input negative is vendor-owned (Aegis or OpenAI), and 184/270 input test positives are. A "without vendor-owned data" view of input therefore has no negatives. We need a non-vendor benign input source. WildGuardTest is gated and needs terms accepted; ToxicChat is CC-BY-NC.
- An LLM jury labelled 200 output positives and 51 negatives (Aegis validation). The second labeller should look at these first.
- harmful_goal has 1 sexual test positive, and XSTest skews toward violence. Category-level claims there are weak.
- OR-Bench 80k labels are automated (`label_basis: automated`), as hard-1k's were.
- The private slice sits in `private/`, which the integration agent must add to `.gitignore` before committing. Its texts come from public upstreams, so it is private only in that we never publish which rows it holds.
