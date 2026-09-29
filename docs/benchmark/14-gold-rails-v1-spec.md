# Gold Rails v1: what the dataset is, where it lives, what runs on it

> Superseded in part: [doc 19](19-evaluation-contract-v1.md) (draft, pending sign-off) replaces this doc's row targets, composition scope, cost table, metrics and publication gate.

Written 22 September 2026. Supersedes the row targets in the golden-dataset plan; the feature definitions, freshness rules, and record schema there still apply.

## Size and cost, fixed first

10,200 rows total: 8,700 test, 1,500 tune. About 1,300 of the test rows (15%) are private.

| Cost line | v1 estimate | Basis |
|---|---|---|
| Bedrock InvokeGuardrailChecks | about $8 | 10k rows × up to 3 checks × $0.07 to $0.10 per 1k text units |
| OpenAI omni-moderation | $0 | free |
| GPT-5 mini as classifier | about $20 | 10k rows × ~1.2k tokens in, short JSON out |
| Jev, 15-question question set, run twice for test-retest | under $2 | 20k requests × ~1.3k tokens × $0.042 per M |
| Kev 0.8B / 4B / 9B and one more open model | about $30 | ~10 rented H100 hours; 0.8B runs on CPU |
| Google Model Armor, Azure AI Content Safety | deferred to v1.1 | same rows, about $10 each when added |
| Annotation | in-house | ~1,200 crafted rows written with rationale, 5% audit (~500 rows) re-labelled by a second person |
| **Total v1 spend** | **under $100 API and GPU** | plus one engineer, eight weeks |

## Composition

| Feature | Test rows | Sources, headline | Sources, anchor (reported separately) | Crafted (private half) |
|---|---|---|---|---|
| F1 content, input | 1,500 | AILuminate v1.1 practice (CC-BY), SORRY-Bench 2025 | ToxicChat, HarmBench sample: 300 | 0 |
| F1 content, output | 800 | Aegis 2.0 response rows with their prompts | BeaverTails sample: 150 | 0 |
| F1 over-refusal | 500 | OR-Bench hard subset | XSTest: 100 | 100 benign-but-scary in our domains |
| F2 direct attacks + leakage | 1,000 | Lakera PINT public, gandalf_ignore_instructions | WildJailbreak, JBB sample: 200 | 200 PINT-style, private |
| F2 indirect attacks | 700 | LivePI, MCPTox | AgentDojo sample: 100 | 150 tool results and MCP descriptions, private |
| F3 policy adherence | 1,200 | DynaBench test split (written policies + dialogues) | none exists | 12 Bedrock-format topics × ~40 rows; 20 written policies in Bedrock and gpt-oss-safeguard format × ~20 rows |
| F4 word filters | 300 | LDNOOBW + generated obfuscations, deterministic labels | none | all generated, reviewed |
| F5 PII and secrets | 1,000 | PII Arena English cuts (secrets included) | pii-masking-400k sample: 200 | 150 traps: order numbers, test keys, public addresses |
| F6 grounding | 600 | FACTS Grounding public set, FaithBench sample | RAGTruth sample: 100 | 0 |
| F7 bias B1 disparate FPR | 400 | civil_comments identity slice, benign only | none | 100 fresh benign identity mentions |
| F7 bias B2 counterfactual | 400 pairs | generated from HolisticBias descriptors over F1 headline rows, human reviewed | none | half the templates private |
| F7 bias B3 decision bias | 300 | AgentFairBench | discrim-eval sample: 100 | 0 |
| F8 actions | 300 | LivePI goals, MCP-SafetyBench | none | 100 kill-the-god-agent scenarios, private |

Deferred to v1.1: multilingual slice, Model Armor and Azure baselines, NeMo Colang policy format, image anything.

## Where it lives

**Hugging Face**: `raxitlabs/gold-rails` (public) and `raxitlabs/gold-rails-private` (private, never released).

```
gold-rails/
  README.md              datasheet: features, sources, licences, label_basis, contamination flags, what is private and why
  manifest.json          sha256 per feature × split, frozen before any run
  data/{feature}/tune.jsonl
  data/{feature}/test.jsonl          public test rows only
  mappings/categories.json          source category → AILuminate + Bedrock
  question_sets/v1/{feature}.json       the exact questions sent to decision models, versioned
  question_sets/v1/llm-classifier.json  the prompt sent to LLM baselines
  scripts/rebuild.py                re-fetches licence-restricted rows (ND, NC) by id from their sources
```

Configs: one per feature, splits `tune` and `test`. Licence-restricted rows ship as ids plus the rebuild script. Record schema as in the golden-dataset plan (JevBench's, extended).

## The benchmark

**Repo**: `raxitlabs/gold-rails-bench`, Python, `uv`, Apache-2.0. Borrowed from JevBench: record validator and hash, adapter contract, ledger runner, fail-closed scoring, aggregation through an allowlist, raw files outside the repo, pre-registration by commit.

Adapters in v1:

| Adapter | Systems | Needs |
|---|---|---|
| `systemone` | Jev 1.13.0, Kev 0.8B/4B/9B, OpenJev (all speak `POST /v1/systemone`) | TypeSafe key (have); a GPU box or RunPod for the open models |
| `bedrock` | InvokeGuardrailChecks for F1, F2 direct, F5; ApplyGuardrail with a denied-topics guardrail for F3 topics | AWS account, us-east-1 |
| `openai_moderation` | omni-moderation-latest for F1 | OpenAI key |
| `openai_compat` | GPT-5 mini with the same category text, strict JSON schema, marked verbalized | OpenAI key |
| `regex` | F4, F5 candidates, floor | none |

Outputs: `results/{system}/{run_id}.parquet` per item, `results/summary.json` with per-feature F1, recall at 5% FPR, AUPRC, ECE and Brier where probabilistic, over-refusal rate, B1 FPR gap, B2 flip rate and mean delta, B3 discrimination score, p50/p95 latency at concurrency 1 and 16, dollars per 1,000 evaluations with basis, anchor-vs-headline gap, and bootstrap intervals.

## The landing page

A static page that reads `summary.json`: one table per feature with the systems as rows, a calibration plot per probabilistic system, a cost-versus-recall scatter, the anchor-versus-headline gap column, and links to the dataset, the repo, every question set, and every raw receipt for public rows. No claims the JSON does not contain.

## Eight weeks

1. Weeks 1 to 2: schema, loaders for the headline sources, mapping file, first freeze of tune split. Access requests sent (BELLS, "IPI in the Wild" authors).
2. Weeks 3 to 4: crafted rows written and reviewed, counterfactual generator, audit, full freeze, HF release of the public slice.
3. Weeks 5 to 6: harness and five adapters; tune-split run fills the capability matrix; thresholds fixed and committed.
4. Week 7: full test run, all systems, test-retest for bias; Bedrock comparison measured.
5. Week 8: summary.json, landing page, writeup. v1.1 planning with Model Armor and Azure.

## Pre-registered go/no-go for publishing

Publish if: anchor-slice numbers for OpenAI moderation and one open model fall within 3 F1 points of published figures; every headline number has a bootstrap interval; every private row has a receipt; test-retest agreement is reported. Publish regardless of whether Jev wins.
