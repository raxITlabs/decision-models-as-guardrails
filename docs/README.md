# decision-models-as-guardrails docs

decision-models-as-guardrails compares configured guardrail detectors (decision models with written questions, and Amazon Bedrock Guardrails) across six task suites, on quality, cost and latency. Public version v0.0.1: dataset at https://huggingface.co/datasets/raxITLabs/decision-models-as-guardrails. Results: the second run in `benchmark/results/second-benchmark/`, which the results site shows, and the first run in `benchmark/results/first-benchmark/`.

Renamed on 5 October 2026: the benchmark was called jev-as-a-guardrails (and [gold]rails before that). Code identifiers keep the old names.

Before that, the benchmark was called [gold]rails, and before that Gold Rails, until 30 September 2026. Dated notes and records below keep the name they were written under, and code identifiers keep `goldrails`. The Hugging Face dataset moved from `raxITLabs/goldrails` to `raxITLabs/jev-as-a-guardrails` the same day.

## Layout

| Folder | What it holds |
|---|---|
| `teach/` | Material for learning how the benchmark works |
| `benchmark/` | Design, contract, audits, budget and release runbook for decision-models-as-guardrails (14 to 25) |
| `research/` | The early research notes (18 September 2026), raw research dumps, video transcripts, prior art and the data-quality review |
| `reference/` | Copies of the TypeSafe docs, the first API spec and the TypeScript spikes |
| `reports/`, `release/`, `archive/` | Published HTML reports, the v0.0.1 sign-off packet, and superseded pages |

Five files at the top of `docs/` and `docs/typesafe-reference/models.md` are one-line pointers to the new locations. They stay because signed or frozen records (the contracts, saved leaderboards and frozen review files) cite those paths.

## Start here

| File | What it holds |
|---|---|
| [teach/gold-rails-primer.html](teach/gold-rails-primer.html) | A one-page walkthrough for newcomers: who is compared, what gets tested (including the three bias parts), how one message is judged, tune-freeze-test, the score, paired intervals, cost and limits. Read it rendered at https://raxitlabs.github.io/goldrails/teach/gold-rails-primer.html |
| [teach/benchmark-pipeline.html](teach/benchmark-pipeline.html) | For engineers: one diagram of the whole run, from pinned sources to published results, with every artifact and evidence gate. Source: `teach/diagrams/benchmark-pipeline.dataflow.json` |
| [benchmark/18-benchmark-structure.md](benchmark/18-benchmark-structure.md) | The six suites and how the harness fits together |
| [benchmark/19-evaluation-contract-v1.md](benchmark/19-evaluation-contract-v1.md) | The rules a result must follow. Signed as v1.1 on 28 September 2026 (`benchmark/contracts/v1.1-signed.json`) |

## How bias is reported

Bias is reported as three parts, because each answers a different question.

| Part | Question | Where it sits |
|---|---|---|
| Hate and discrimination detection | Does the system catch content its source labelled hateful or discriminatory? | Inside the content suite, scored once as content rows |
| Guardrail fairness diagnostics | Do false blocks, missed violations or decisions on identity-swapped text differ across groups? | Beside the six-suite score, outside it (B1, B2) |
| Decision-model bias diagnostics | Does a decision model make unsupported stereotyped assumptions on these dataset tasks? | A separate supplementary test (BBQ, discrim-eval). Bedrock is not applicable |

The six-suite score covers the guardrail tasks. The fairness diagnostics say whether that performance holds across groups, and on this data every group is too small to say either way. The decision-model tests support conclusions about their own tasks and nothing wider. The content score is moderation accuracy, not a fairness percentage. The audit is [benchmark/25-bias-audit.md](benchmark/25-bias-audit.md). `benchmark/runs/bias_parts.py` writes the three-part view of the existing results to `benchmark/results/first-benchmark/bias-parts.json`, copying values from `bias.json` without recomputing them.

## Building the benchmark

| File | What it holds |
|---|---|
| [benchmark/14-gold-rails-v1-spec.md](benchmark/14-gold-rails-v1-spec.md) | decision-models-as-guardrails v1: 10k rows, composition per feature, HF layout, harness adapters, landing page, under $100 in API and GPU spend, eight weeks |
| [benchmark/16-evaluation-contract.md](benchmark/16-evaluation-contract.md) | After the pilot review: what a run may claim, claims withdrawn, fixes made, and the contract before the next run |
| [benchmark/17-guardrail-policy-v0.md](benchmark/17-guardrail-policy-v0.md) | Policy v0.1 for review: two comparisons kept apart, separate labels for topic, harmful assistance, actionable and harmful detail, unsafe replies and instruction overrides; request routing vs reply enforcement; twelve rows proposed with full text in dataset/frozen |
| [benchmark/18-benchmark-structure.md](benchmark/18-benchmark-structure.md) | Six suites (content, prompt attacks, denied topics, word filters, sensitive information, grounding), Automated Reasoning excluded; one harness, one results format, the leaderboard plot, sources per suite, current coverage, order of work |
| [benchmark/19-evaluation-contract-v1.md](benchmark/19-evaluation-contract-v1.md) | Evaluation contract v1, draft pending sign-off: six-suite scope, balanced-accuracy task score with tuning-only thresholds, equal weights, failure and coverage rules, group bootstrap, measured cost and p95 latency, freeze-before-test, size and budget, and the six review decisions. Supersedes the conflicting parts of 14, 16 and 18 |
| [benchmark/20-source-audit.md](benchmark/20-source-audit.md) | Every dataset loader: upstream revision, licence, what a positive meant at the source, and what still needs a person |
| [benchmark/21-bias-evaluation.md](benchmark/21-bias-evaluation.md) | History: bias sources, task mapping and open decisions as planned on 23 September. docs/25 replaces its framing |
| [benchmark/22-budget-forecast.md](benchmark/22-budget-forecast.md) | Spend so far against the GCP audit logs, and the forecast for the rest |
| [benchmark/23-release-runbook.md](benchmark/23-release-runbook.md) | From reviewed labels to the published benchmark: checks, sign-off and publication steps |
| [benchmark/24-bias-licence.md](benchmark/24-bias-licence.md) | Bias data sources, licences and what each release option ships |
| [benchmark/25-bias-audit.md](benchmark/25-bias-audit.md) | Every bias test and the hate rows in the content suite: source task, what defines a correct answer, adaptations, which systems compare, what the evidence supports, and which of the three parts each belongs to. Machine-readable copy in `benchmark/results/first-benchmark/bias-audit.json` |

## Early research (18 September 2026, before anything was built)

| File | What it holds |
|---|---|
| [research/early-2026-09-18/01-jev-primer.md](research/early-2026-09-18/01-jev-primer.md) | What Jev is, the three question types, pricing, limits, known weaknesses |
| [research/early-2026-09-18/02-community-research.md](research/early-2026-09-18/02-community-research.md) | What people said about Jev in its first 72 hours (HN, Reddit, X, YouTube) |
| [research/early-2026-09-18/03-cybersecurity-decision-map.md](research/early-2026-09-18/03-cybersecurity-decision-map.md) | Where in cybersecurity a decision model fits, rated |
| [research/early-2026-09-18/04-ir-showcase-ideas.md](research/early-2026-09-18/04-ir-showcase-ideas.md) | Incident response and raxIT showcase ideas, rated |
| [research/early-2026-09-18/05-bedrock-guardrails-mapping.md](research/early-2026-09-18/05-bedrock-guardrails-mapping.md) | Bedrock Guardrails policy by policy, rebuilt on Jev, with gaps and cost |
| [research/early-2026-09-18/06-product-design.md](research/early-2026-09-18/06-product-design.md) | The combined product: Bedrock-compatible API plus action guardrails |
| [research/early-2026-09-18/07-poc-plan.md](research/early-2026-09-18/07-poc-plan.md) | POC scope, go/no-go criteria, then the UI phase |
| [research/early-2026-09-18/08-sources.md](research/early-2026-09-18/08-sources.md) | Links to everything cited |
| [research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md](research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md) | Every Bedrock Guardrails policy, API, tier, limit, and price, verified 18 Sep 2026, plus what the June 2026 agentic additions do to our pitch |
| [research/early-2026-09-18/10-evaluation-datasets.md](research/early-2026-09-18/10-evaluation-datasets.md) | Hugging Face datasets per check type, with the POC sampling plan |
| [research/early-2026-09-18/11-defence-in-depth-and-prior-art.md](research/early-2026-09-18/11-defence-in-depth-and-prior-art.md) | Four-tier guardrail architecture, what three practitioner benchmarks and the community repos taught us, and the slop-detection showcase |
| [research/early-2026-09-18/12-jev-inside-the-runtime-engine.md](research/early-2026-09-18/12-jev-inside-the-runtime-engine.md) | The recommendation: Jev as the semantic uplift behind runtime-security-core's existing seams, skills as the wedge, mapped to the OWASP Agentic Skills Top 10 |
| [research/early-2026-09-18/13-jevbench-learnings.md](research/early-2026-09-18/13-jevbench-learnings.md) | How JevBench is built and scored, what it found, and which of its rules we adopt for the guardrail benchmark |
| [research/early-2026-09-18/15-grayzonebench-learnings.md](research/early-2026-09-18/15-grayzonebench-learnings.md) | How our 2025 GrayZoneBench was run and published, what to reuse (org, site, publish shape, moderation client) and what to change (labels not judges, hashes, ledger, no windows) |
| [research/early-2026-09-18/appendix-vault-script-survey.md](research/early-2026-09-18/appendix-vault-script-survey.md) | Earlier survey of the raxit-vault scripts for Jev opportunities |

Read 01, 05, 06, 07 in that order for the original research in ten minutes.

## Folders

| Folder | What it holds |
|---|---|
| [reports/](reports/) | Published pages: content-filter explainer, decision memo, benchmark plan, golden dataset plan, system design |
| [specs/](reference/specs/) | The original content-filter API design spec |
| [research-raw/](research/raw/README.md) | Raw last30days research dumps that 02 and 11 were distilled from |
| [ts-spikes/](reference/ts-spikes/README.md) | The first TypeScript calls to Jev, before the benchmark moved to Python |
| [transcripts/](research/transcripts/) | Verbatim transcripts of the three practitioner videos cited in 11 |
| [prior-art/](research/prior-art/README.md) | OWASP skills checklist and the community guardrail repos' questions and cases |
| [typesafe-reference/](reference/typesafe/README.md) | Local Markdown copies of the live TypeSafe docs: API, models, SDKs, guardrails cookbook, jaggedness |
| [release/](release/signoff-v0.0.1-2026-09-28.md) | The v0.0.1 sign-off packet: exact contract, analysis and dataset versions |
| [research/](research/data-quality-team-2026-09-24/README.md) | The 24 September data-quality review and its evidence scripts |
| [archive/](archive/2026-09-28-bedrock-feature-map/README.md) | Superseded pages kept as a record, with a note on what replaced each |

Terminology: a *question set* is the fixed set of typed questions sent to a decision model with each row (TypeSafe's cookbook calls this a battery; we do not).
