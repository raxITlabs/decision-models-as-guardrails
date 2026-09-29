# What GrayZoneBench teaches us, and what carries into Gold Rails

Source: github.com/raxITlabs/GrayZoneBench (Apache-2.0), cloned 22 September 2026. Last commit 20 August 2025, squashed to one commit. Dataset `raxITLabs/GrayZone` on Hugging Face (9 downloads, last updated 15 August 2025). Dashboard at bench.raxit.ai is still live.

## What it did

A safety-versus-helpfulness benchmark of chat models on "gray zone" prompts, following OpenAI's safe-completion framing. An enhanced HarmBench copy: 211 standard prompts, 1,230 contextual, with cybercrime subsets. Each target model answers; three tiers score the answer: deterministic rules (10% weight), OpenAI moderation (penalty factor), and a LangGraph multi-agent LLM judge (90% weight, 95% when confident). Effectiveness = safety × helpfulness. Results per model land in `out/`, upload to GCS, and a Next.js dashboard reads them.

## How it was run, precisely

- **Providers.** LangChain clients: OpenAI direct, Anthropic and gpt-oss via Bedrock (`ChatBedrockConverse`, AWS profile), Gemini via Google GenAI. Provider detected from the model name. OpenRouter does not appear anywhere in the code; the recollection that it was used may be from a different run or a local branch. Reasoning-effort is ignored by the unified client.
- **Judge.** Separate judge model, prompts in `utils/judge.py`, rubrics in `scoring_rubrics.py`, agent workflow in `agentic_evaluator.py`. Judge output parsed best-effort from JSON with a plain-text fallback.
- **Runs.** `--num-prompts`, `--start-index`, `--shuffle --seed` windows; per-sample raw response and judge response written as JSON next to a markdown summary; a live Rich display; a timestamped `results_*.json`.
- **Publishing.** `gcs_uploader.py` writes `latest/metadata.json` (~5 KB) plus `latest/models/{model}.json` (~200 KB each) to sidestep a 1 MB payload limit; the site's `cached-data.ts` fetches those with Next's `use cache` and cache tags; deployed on Vercel with a service-account JSON in env. Charts with Nivo, tables with TanStack.
- **Dataset.** CSV with `prompt, category`, pushed to the Hub under the `raxITLabs` org with `standard` and `contextual` configs.

## What to reuse

1. **The org and the surfaces.** `raxITLabs` on Hugging Face exists; `bench.raxit.ai` exists with a GCS bucket and a Vercel deploy. Gold Rails publishes to the same org and can live at a path on the same site, so there is one place where raxIT benchmarks appear.
2. **The publish shape.** Small `metadata.json` plus one file per system is exactly what a static results page needs. Keep it; rename to `summary.json` plus `systems/{system}.json`.
3. **The site skeleton.** Next.js, Nivo, TanStack, dark and light themes, and the `SampleDetailsModal` that shows one row's raw evaluation. Gold Rails needs the same modal to show a receipt. Fork the site, delete the gray-zone components, keep the data layer.
4. **`openai_moderation.py`.** A working moderation client with category scores and timing; it becomes the OpenAI baseline adapter after switching to `omni-moderation-latest`.
5. **Python with uv, Rich progress, per-sample raw files.** All consistent with the Gold Rails harness.
6. **Bedrock and Google credentials handling.** The env layout and the AWS-profile path are what the Bedrock Guardrails adapter needs; nothing new to set up on the account side.

## What to change, and why

| GrayZoneBench | Gold Rails | Reason |
|---|---|---|
| Truth comes from an LLM judge with 90% weight | Truth comes from human or deterministic labels frozen before any run; LLM classifiers are systems under test, never judges | The one public critique of Jev's numbers was LLM answer keys; JevBench and every serious 2026 paper avoid them |
| Scores blend three tiers with hand-set weights and confidence boosts | Raw per-item scores are stored; every metric is recomputed from them by a pure function; no blending | Weights chosen by the authors are indistinguishable from tuning to a preferred outcome |
| No dataset hash, no manifest, no held-out split | sha256 per feature and split, manifest committed before the run, private slice | Reproducibility and contamination defence |
| No cost ledger; tokens shown in the live table | Reserve-then-settle ledger, dollars per 1,000 evaluations with an explicit basis | Cost is a headline axis, not a display column |
| Retries and best-effort JSON parsing inside the judge | No retries, no repair; invalid output is invalid and counted | Invalid output is a finding about the system |
| Windows via `--num-prompts N` | Every system runs every row; partial runs are marked and unranked | A window is a way to cherry-pick without meaning to |
| 211 to 1,230 prompts, one source | ~10k rows, twelve sources, freshness-first, anchor slice separate | The dataset was the weak part; 9 downloads says the market agreed |
| Squashed history, single commit | Pre-registration by commit, addition notes per system, superseded rows kept | The history is the audit trail |
| Results only in GCS | Results in GCS for the site, and in the repo as parquet with receipts for public rows | A reader must be able to check a number without our bucket |
| Provider detection by model-name substring | Explicit adapter per system, version pinned in the run manifest | "gpt" matching "gpt-oss" was already a special case in the old code |

## One correction to the shared memory

The code calls OpenAI, Bedrock, and Google directly through LangChain. If OpenRouter was used, it was outside this repository. For Gold Rails, OpenRouter is a reasonable way to reach the LLM-classifier baselines and any hosted open decision models with one key, but Bedrock Guardrails, Model Armor, and Azure Content Safety are not on OpenRouter and need their own accounts regardless.

## Concretely, for week 5 of the Gold Rails plan

- Fork `site/` into the new repo, strip to layout, theme, data layer, table, scatter, and the details modal.
- Port `gcs_uploader.py` to write `summary.json` and `systems/*.json`; keep the bucket.
- Port `openai_moderation.py` as the first baseline adapter.
- Do not port `judge.py`, `agentic_evaluator.py`, `scoring_rubrics.py`, or `deterministic_analyzer.py`. Their job does not exist in a labelled benchmark.
