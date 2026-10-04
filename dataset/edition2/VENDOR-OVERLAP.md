# Edition 2 rows whose text a benchmarked vendor published

Scanned 4 October 2026 with `uv run python -m goldrails_dataset.vendor_overlap` (run from `dataset/`). This file
gives ids and file paths only. It never quotes row text.

## Why

A row that a vendor printed in its own docs may have been used to tune or check that vendor's model. It cannot be a
fair test row for that vendor. TypeSafe makes Jev, and its LLM guardrails cookbook prints two of our public prompt
attack test rows in full.

## How the scan works

The scanner reads every edition 2 row: dev, test and the unpublished slice, with licence-withheld text restored from
`local/`. It compares each text field (text, source passage, query, context turns) with every vendor file tracked in
the repository. Text is normalised first: NFKC, lower case, apostrophes dropped, HTML tags and entities and JSON escapes
read as spaces. A row matches a file when

- the two share a run of 8 consecutive words, or
- a row text of 4 to 7 words equals a whole line, table cell, quoted string or JSON string in the file.

Texts under 4 words ("yes", "ok", "hi") appear in nearly every file, so the scanner ignores them.

A row that matches in test or the unpublished slice is excluded with the reason
`text published by a benchmarked vendor (<vendor>)`. Public ids go to `EXCLUDED.jsonl` in this folder. Unpublished ids
go to the git-ignored `<suite>/private/EXCLUDED.jsonl`. A dev row stays in dev and is listed here as flagged.

### Vendor files scanned (51)

| Vendor | Files |
|---|---|
| TypeSafe (Jev) | `docs/reference/typesafe/**` (45 files), `docs/typesafe-reference/models.md`, `docs/research/early-2026-09-18/01-jev-primer.md`, `docs/research/early-2026-09-18/08-sources.md` |
| AWS (Bedrock Guardrails) | `docs/09-bedrock-guardrails-feature-inventory.md`, `docs/research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md`, `docs/research/early-2026-09-18/05-bedrock-guardrails-mapping.md`, `docs/archive/2026-09-28-bedrock-feature-map/` (2 files), `research_notes/Profanity and denied topic references/bedrock_equivalence.md` |

The repository holds no docs from the other benchmarked systems (Kev, Open-Jev, Laya). As a cross-check, `--others`
scanned the other 273 tracked text files outside `dataset/` and the run outputs: community guardrail projects in
`docs/research/prior-art/`, video transcripts, social-media research, the benchmark code and our own docs. None holds
the text of an edition 2 row.

## Matches

All 13 matches are prompt attack rows, all against one file:
`docs/reference/typesafe/cookbooks_llm_guardrails.md` (TypeSafe). No Bedrock file matched, and no row from content,
denied topics, word filters, PII or grounding matched.

"Windows" is the number of shared 8-word runs. "Coverage" is the share of the row's own runs that the file holds, so
1.0 means the cookbook prints the whole row.

| Id | Split | Windows | Coverage | Action |
|---|---|---|---|---|
| `f2-jackhhao_jailbreak-b4602e1803` | test | 110 | 1.000 | excluded |
| `f2-itw_jailbreak_prompts-61d18a8461` | test | 102 | 0.927 | excluded |
| `f2-itw_jailbreak_prompts-c961fe042a` | test | 10 | 0.062 | excluded |
| `f2-jackhhao_jailbreak-af3a05e95b` | test | 10 | 0.056 | excluded |
| `f2-jackhhao_jailbreak-6088aa6956` | test | 10 | 0.048 | excluded |
| `f2-itw_jailbreak_prompts-e858d0e131` | test | 10 | 0.039 | excluded |
| `f2-itw_jailbreak_prompts-aef517c5d9` | test | 2 | 0.012 | excluded |
| `f2-itw_jailbreak_prompts-c1174a7b53` | test | 2 | 0.010 | excluded |
| `f2-itw_jailbreak_prompts-06a8272ed0` | test | 1 | 0.003 | excluded |
| `f2-jackhhao_jailbreak-b095395987` | test | 1 | 0.003 | excluded |
| `f2-jackhhao_jailbreak-709080e3d1` | test | 1 | 0.002 | excluded |
| `f2-jackhhao_jailbreak-ada5d8b10c` | dev | 2 | 0.008 | kept in dev, flagged |
| one unpublished row | unpublished | 2 | 0.022 | excluded (id in the git-ignored file) |

## What the owner should know

There are two kinds of match. The first two rows are the cookbook's own examples, copied whole (coverage 0.93 and
1.0). The other eleven are different jailbreaks from the "DAN" family. Each shares one stock opening sentence with the
cookbook's DAN example and has its own body. The owner kept the strict 8-word rule on 4 October 2026 (ruling 18 in
`docs/benchmark/29-owner-rulings-2026-10-03.md`): all eleven test rows and the unpublished row stay excluded, the nine
that share only the DAN opening included. The excluded ids are gone from every candidate, second-label, resolution
and text-cache file, tracked and git-ignored, and live only in the exclusion lists.

The cookbook names its source. It says its jailbreaks come verbatim from the TrustAIRLab in-the-wild jailbreak prompts
collection on Hugging Face. That collection is our `itw_jailbreak_prompts` source. Rows from it that the cookbook does
not print are not excluded, but TypeSafe has worked with the collection. This is the same exposure as any public
benchmark source, and the prompt attack disclosure should name it.

The scan covers vendor files in this repository only. A vendor may print a row elsewhere, in a model card, a blog post
or a live docs page changed after we copied it. Rerun the scanner after refreshing `docs/reference/typesafe/`.

Excluding these rows changes the prompt attack test split. The edition 2 build, the counts and the shortcut gate need
a rerun before any score uses them.
