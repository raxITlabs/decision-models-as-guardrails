# Edition 2 plan: fixed decision rule, bigger dataset, cheap onboarding

Status: draft for owner approval, 2 October 2026. Nothing here changes contract v1.1 or the published results until contract v2.0 is signed.

## Why

Per-model threshold tuning does not scale to 70-80 systems and is not what independent guardrail leaderboards do. GuardBench binarizes at `> 0.5` with no per-model fitting; the Jev Decision Index uses `noul >= 0.5`; AILuminate uses a fixed evaluator and a private official set. An independent expert review (2 October) agreed with the direction and added three corrections:

1. A fixed 0.5 rule measures calibration as much as ranking quality, and the question format is TypeSafe's, so it likely widens Jev's lead. Offline rescoring confirms it: Jev 90.9 → 88.4, Kev-9B 87.1 → 79.7. Name it "out-of-the-box decision" and disclose this.
2. The benchmark must define the task (policy text + labelled rows), not the questions. Question sets become the reference adapter for Noul models. OpenAI moderation, Llama Guard and Bedrock never read our questions.
3. The test set is too small to rank many systems. At 80/80 per class one suite's balanced accuracy is about ±5.5 points; 250/250 gives about ±3.1.

Verified in the v1 test ledgers:

- Prompt attacks: 240 harmful, 80 benign, all 80 benign rows from `deepset_injections`, so false blocks on jailbreak and leakage are never measured.
- Denied topics: 29 harmful, 44 benign.
- PII test positives: PASSWORD 4, SSN 4, IP_ADDRESS 4, USERNAME 7, against the repo's own floor `ENTITY_TEST_FLOOR = 30` (`dataset/goldrails_dataset/audit.py`).
- Jev content at 0.5: catch rate 0.81, false-block rate 0.36. Balanced accuracy alone hides this.
- AUROC ≥ 0.99 for Jev, Kev-4B and Kev-9B on attacks, topics, PII, words and profanity: those suites no longer separate the top systems.

## Decisions for contract v2.0

| Topic | Decision |
|---|---|
| Unit of the benchmark | Task = suite policy text + labelled rows. Adapters translate. |
| Headline rule | Out-of-the-box decision: probability outputs flag at ≥ 0.5 per question (max over category questions); verdict APIs use their own flag; configurable services (Bedrock) use a frozen, documented setting. Rule recorded with every score. |
| Headline metric | Balanced accuracy per subtask, with catch rate and false-block rate as required columns. Ties broken by false-block rate. F1@0.5 published for comparison with GuardBench. |
| Secondary, score-producing systems only | AUROC, recall at false-block rate ≤ 5%. Calibration (Brier, ECE) only for single-question subtasks or per question against its category label, since the max score is not a probability (`benchmark/goldrails_bench/score.py`). Never ranked across verdict and score systems. |
| Tuning | Appendix only. Later, a separately ranked "Calibrated" division where submitters fit one threshold per subtask on the public dev split, declared before test. |
| Question wording | One frozen question set per suite for all Noul models, chosen by rule, not by results. Content uses v1. Any revision is checked against at least three non-Jev models, with a revision budget and a log. |
| Coverage | "Capability not offered" = not evaluated, no overall rank. Runtime failure = wrong. Runs with more than 2% failures are invalid. Per-suite leaderboards are the primary view. |
| Statistics | Paired group bootstrap difference intervals, bootstrap rank intervals, tiers, Holm-adjusted paired tests. |
| Drift | Pinned dated model IDs, evaluation date on every score, a monthly ~300-row sentinel rerun; outside the interval = "stale". |
| Integrity | Automated overlap check by ID, text hash and group that fails the freeze. Private test slice from edition 2, zero-retention terms with API vendors where offered. |
| Disclosures | 48 previously run prompt-attack test rows, reused test rows across runs, Bedrock coverage gaps, Noul format native to Jev, the fixed rule widening Jev's lead, raxIT's relationship to TypeSafe, vendor-owned data sources. |
| Security | Hugging Face reproductions run sandboxed, no `trust_remote_code` without code review. |

## Two tracks

### Track 1: Tuesday release (no new data)

Uses the existing v1 test set, labelled "v1 test set, previously examined, re-scored under a rule fixed in advance".

1. Owner signs contract v2.0.
2. Rerun Kev-9B content on v1 (560 rows) so every Noul model shares one content wording. Needs the VM.
3. Re-score all v1 test ledgers under v2.0 rules: per suite catch rate, false-block rate, balanced accuracy, AUROC, paired intervals, tiers.
4. v1.1 tuned leaderboard published as a labelled appendix.
5. Results page and method page updated with the disclosures above.

No new vendors on Tuesday. OpenAI moderation, if added, appears per suite only, with the 39 `openai_moderation` content rows flagged.

### Track 2: Edition 2 (new dataset, then full run, then new models)

Dataset targets: at least 250 harmful / 250 benign test rows per scored subtask, at least two sources per subtask, grouped by source. About 3,500 test rows per system.

| Suite | Change |
|---|---|
| Denied topics | 29/44 → ≥ 250/250, ≥ 8 topics. Authored rows reviewed independently. Most urgent. |
| PII | ≥ 30 positives per scored entity type, 50 preferred. Source DRIVER_ID or drop it from the score. |
| Prompt attacks | Hard benign rows for jailbreak and leakage (role-play, security Q&A, over-defence prompts). Less reliance on deepset's train split. |
| Grounding | ≥ 400 rows from at least two sources beyond RAGTruth. |
| Content | Move the 32 PII/topic positives to their suites or tag every row with its category, so results show with and without Bedrock's coverage gap. Tag vendor-owned sources (`openai_moderation`, `aegis2`). |
| Words | Shrink to a sanity check; it is saturated. |
| Profanity | Keep semantic labels; document that Bedrock's word list is a different policy. |

## Workflow: team of agents

Each phase ends with a gate. A gate failure stops the workflow and reports back.

| Phase | Agents (parallel within a phase) | Output | Gate |
|---|---|---|---|
| 0. Owner | none | Contract v2.0 signed, budget approved | Owner sign-off |
| 1. Build | **Scoring**: v2.0 headline rule, required columns, AUROC, recall at 5% false blocks, restricted calibration, coverage rule, failure cap, rank intervals and tiers, tuned appendix cohort. **Integrity**: overlap check in the freeze, the 48 IDs added to the examined list. **Adapters**: task-based adapter contract; Noul adapter with frozen question sets; verdict adapter (Bedrock, then OpenAI moderation); serving-config capture; sandbox rule. **Dataset** (one agent per suite: topics, PII, attacks, grounding, content tags): source research, loaders, rows at target sizes, labels, review packets. | Code with tests, dataset v2.0 candidate rows | `uv run pytest` passes; dataset audit passes per-class and per-entity floors; overlap check passes; each agent's work verified by a second agent |
| 2. Quick test | **Offline**: re-score v1 ledgers under v2.0 (no calls). **Smoke**: 20 rows per suite per system on the new dataset. | Smoke ledgers, offline v2.0 leaderboard | Zero adapter errors, failure rate under 2%, offline scores reproduce known v1 numbers |
| 3. Full test, current systems | Run Jev, Kev-0.8B/4B/9B, Open-Jev-2B, Laya, Bedrock and the regex baseline on the edition 2 test set | Ledgers, leaderboard, paired intervals, tiers | Publication checks pass; owner review |
| 4. New models | **Research**: access, pricing, terms, data retention for OpenAI and Perplexity decision APIs, Cloudflare's model, OpenAI moderation, selected HF reproductions. **Adapters**: one per new API. | Onboarding plan, adapters, compatibility checks | Each new system passes the compatibility check before a full run |

### Before the full run (status 5 October 2026)

- [ ] Owner reviews the 242 disputed rows (`dataset/edition2/build/needs-owner-review.jsonl`).
- [ ] Owner second-labels the 400-row content sample (ruling 7).
- [ ] Owner checks the custom-words row label.
- [ ] Licence review of the new edition 2 sources (ids-only until cleared, ruling 10).
- [ ] Perplexity confirms its data-retention terms.
- [x] (5 Oct, Hub commit bc1849e, version 1.0.0) Publish edition 2 to the Hugging Face dataset (`raxITLabs/decision-models-as-guardrails`) and point the runners at that copy, so published scores come from the same rows anyone can download. Withheld text and the unpublished slice stay local.
- [ ] Owner signs contract v2.0 and approves the run budget.

Owner-only steps, never automated: signing the contract, approving spend, reviewing authored labels, publishing.

## Cost and time

- Phases 1 and 2 (offline parts): agent time only.
- Kev-9B content rerun and smoke tests: VM up for about 1-2 hours (~$2/hour) plus Jev and Bedrock calls (cents).
- Full edition 2 run: about 3,500 rows × 8 systems. VM time is the main cost; forecast before starting, as the v1 contract requires.
- New models: per-vendor API cost, forecast per vendor.

## Open questions for the owner

1. Tuesday track first, edition 2 track in parallel, or edition 2 only?
2. Who reviews authored labels for the new denied-topics and prompt-attack rows?
3. Approve VM spend for the Kev-9B rerun and smoke tests?
4. Which new APIs do we already have access to?
