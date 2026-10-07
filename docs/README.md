# docs

| File | What it holds |
|---|---|
| [benchmark/26-edition-2-plan.md](benchmark/26-edition-2-plan.md) | The plan the benchmark follows: fixed decision rule, dataset build, integrity checks, onboarding a model |
| [benchmark/27-evaluation-contract-v2.md](benchmark/27-evaluation-contract-v2.md) | The evaluation contract in prose; `benchmark/contracts/v2.0.json` is the version the scorer reads |
| [benchmark/28-new-decision-models-research.md](benchmark/28-new-decision-models-research.md) | Research on the hosted decision models added to the roster, with the price pages the tariffs cite |
| [benchmark/29-owner-rulings-2026-10-03.md](benchmark/29-owner-rulings-2026-10-03.md) | The decisions that settled open questions in the contract and the dataset |
| [benchmark/30-content-sample-labelling.md](benchmark/30-content-sample-labelling.md) | How the content suite's second-label sample is drawn and labelled |
| [benchmark/RELEASE-HANDOVER-2026-10-07.md](benchmark/RELEASE-HANDOVER-2026-10-07.md) | Release-day steps and where the results are kept |

## Vendor docs

Copies of documentation published by the benchmarked vendors. `goldrails_dataset.vendor_overlap` scans them for
dataset rows a vendor printed (`dataset/edition2/VENDOR-OVERLAP.md`), and `benchmark/goldrails_bench/tariffs.json`
cites some of them as its price source. Their paths are part of those records, so they stay where they are.

- TypeSafe (Jev): `reference/typesafe/`, `typesafe-reference/models.md`, `research/early-2026-09-18/01-jev-primer.md`,
  `research/early-2026-09-18/08-sources.md`
- AWS (Bedrock Guardrails): `09-bedrock-guardrails-feature-inventory.md` (a pointer),
  `research/early-2026-09-18/05-bedrock-guardrails-mapping.md`,
  `research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md`, `archive/2026-09-28-bedrock-feature-map/`,
  and `../research_notes/Profanity and denied topic references/bedrock_equivalence.md`
- OpenAI (gpt-6-luna): `reference/openai/decisions-api.md`

Terminology: a *question set* is the fixed set of typed questions sent to a decision model with each row.
