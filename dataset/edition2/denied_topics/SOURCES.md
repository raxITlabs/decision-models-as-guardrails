# Denied topics, edition 2: sources

Built by `uv run python -m goldrails_dataset.sources.e2_denied_topics` on 2 October 2026. The command rewrites `candidates.jsonl`, `counts.json`, `review-packet/` and `_lead/`. Add `--offline` to build the authored rows alone.

Topic set: `topics-e2.json`. It has eight topics. The three v1 topics and the four v2 candidates are copied verbatim, and TaxAdvice is new. A row is `yes` when it falls within at least one definition and `no` otherwise. All eight definitions fit Bedrock Classic limits.

## Sources

| source | licence | revision | rows (yes / no) | what it adds |
|---|---|---|---|---|
| `e2_denied_topics` | CC-BY-4.0, authored by raxIT with AI-assisted drafting | loader files in `dataset/goldrails_dataset/sources/e2_denied_topics_cases_v1.py` and `_v2.py` | 360 / 400 | 45 matched pairs per topic: an in-topic request and a hard negative on the same subject that falls outside every definition. Also 40 confusers that borrow topic vocabulary or have none. |
| `e2_oasst2` | Apache-2.0 ([OpenAssistant/oasst2](https://huggingface.co/datasets/OpenAssistant/oasst2)) | `179dd21fc55192153d94adb0e0ce8f69e222bf75` | 18 / 71 | Real first user turns. Most are natural negatives that mention a topic area without asking for what it denies. |

Both licences allow redistribution with attribution, so text can ship (mode `text` in `dataset/release/redistribution.json`, entries proposed in `REGISTER.md`).

**OASST2 train split.** OASST2 publishes train and validation and has no test split. Three rows come from validation and 86 from train. Each train row carries `upstream_split: "train"` and a note in provenance. Any model trained on OASST2 may have seen these prompts. Only our labels are new.

**How OASST2 rows were picked.** I took English root prompts that were not deleted, not rejected in OASST review and 15 to 900 characters long. A keyword search per topic narrowed them, and I read each match. A prompt stayed only when its label was clear, or I flagged it as ambiguous.

## Labels

Claude drafted every label on 2 October 2026 as the first labeller. Each row has `label_basis: llm`, `review_status: candidate` and a one-line `label_rationale`. No row is reviewed yet. A blind second labeller (AI, then the owner, per `docs/benchmark/26-edition-2-plan.md`) labels `review-packet/` without seeing ours. The key that maps packet ids to record ids and proposed labels is in `_lead/`. Do not send `_lead/` or `candidates.jsonl` to the second labeller.

29 rows are flagged ambiguous, with the reason in the key: 18 authored, 11 from OASST2. Three in-topic rows also fall within a second topic (`ALSO_IN`). They stay `yes`.

Written in Spanish, German or French: 34 authored rows, in matched pairs.

## Splits

Splits are proposed per group and stratified by source and topic: about 70% test, 15% tune, 15% private. Private rows are test rows with `visibility: heldout`. A pair shares one group, so it never straddles splits. Each OASST2 conversation tree is one group.

| split | yes | no |
|---|---|---|
| test | 269 | 332 |
| tune | 57 | 74 |
| private | 52 | 65 |

Per topic (test yes / no): InvestmentAdvice 35/42, MedicalDiagnosis 36/41, LegalAdvice 35/39, ElectionPersuasion 32/33, GamblingTips 32/33, EmploymentDecisions 32/41, AcademicDishonesty 34/39, TaxAdvice 33/36, confusers 0/28. The full breakdown is in `counts.json`.

The 23 ambiguous rows in test (15 yes, 8 no) are the ones most likely to change. If the second labeller drops all 15 test positives, test still has 254 positives.

## Overlap check

The build stops if any row matches v1 by id or normalised text. It checks the v1 F3 loaders (`f3_controls`, `f3_controls_v2`, `f3_test_candidates`), the example questions in both topic files, `dataset/samples`, `dataset/frozen` (packets, reviews, `examined-ids.txt`), `benchmark/subsets` and the ids in every `benchmark/results` ledger. The last build found 0 id hits, 0 text hits and 0 duplicates inside edition 2. A test also checks for near duplicates against the v1 denied-topic texts, defined as 50% or more shared 5-word sequences, and found none.

## Known limits

- Positives are 95% authored. OASST2 has few real users asking for denied advice. A second published source of positives, such as BARRED's health-advice task or CantTalkAboutThis distractor turns, would reduce dependence on one writer's style.
- TaxAdvice and the four v2 topics are still candidates. The owner approves the topic set before any row counts.
- The authored rows share one writer. Hard negatives follow the pattern "general explanation, history, fiction or template". A system that learns that pattern could score well without reading the definitions.
