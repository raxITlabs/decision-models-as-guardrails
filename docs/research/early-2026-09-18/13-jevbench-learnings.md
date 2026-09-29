# What JevBench teaches us, and what we take

Source: github.com/fstandhartinger/jevbench (MIT), cloned 22 September 2026 at v1.3.0. Benchmark Heaven's benchmark for Jev-class decision models: 534 decisions, 48 ranked systems, four axes. Read in full: README, IMPLEMENTATION, RESULTS v1.0 to v1.3, HARD-TIER, all docs/v1.2-additions-*, and the code under jevbench/.

## How it is run

- **One record schema.** `Task(id, family, state, question{type, instructions, criteria}, labels, expected, split, group, provenance)`. `validate()` refuses an `expected` not in `labels` and a state carrying `expected`, `label`, `ground_truth`, or `answer_key`. `dataset_hash()` is order-independent; `manifest.json` pins one hash per split, frozen before any system ran.
- **One adapter contract.** `DecisionResult(probs over exact labels, probs_source native|verbalized, model, status, latency, usage, raw, label)`. Adapters "never retry, never fall back to another model, and never repair a bad answer". Native decision models get `{"decision": question}` on `/v1/systemone`; LLMs get a strict JSON schema asking for a probability map and are marked `verbalized`. The two are never pooled for calibration. Token logprobs are not used for anyone.
- **Scoring is pure and fails closed.** A distribution must cover exactly the label set, be finite, in [0,1], and sum to 1 within 1e-3 (pre-registered) or 2e-2 (headline, because several models round to three decimals). Outside that it is invalid and counts as wrong; probabilities are never synthesised. Argmax for classification; for Score questions argmax is accuracy and expected value is a separate MAE. Ties break lexicographically.
- **Serial runner with a money ledger.** `flock`-serialised append-only ledger: reserve worst-case cost before the request, settle the real cost after; the cap comes from the ledger's first row so a later run cannot raise it; a settlement above its reservation raises. Raw request and response written to an exclusively created file and fsynced before the next call. Raw dir and results must be outside the repo or the runner refuses. Stops on 401, 403, 429, or three consecutive infrastructure errors; unattempted tasks are never scored wrong. No retries.
- **Cost is never invented.** `cost_usd` is null unless tariff and usage are both known; the basis is recorded (`derived_usage_times_tariff`, `local_cpu_no_provider_tariff`, ...). Unit is dollars per 1,000 decisions, stated everywhere, after a v1.2.3 correction of three arithmetic mistakes that changed no rank.
- **Aggregation re-derives everything** from per-item records through an allowlist; a test proves private item text cannot leak into an export. Empty samples are null with n=0, not zero. Partial runs are marked and never share a rank with complete ones.

## How the score evolved, and why

| Version | Change | Defect it fixed |
|---|---|---|
| v1.0 | five axes, no combined score | "a single number would delete exactly the thing you came here to see" |
| v1.1 | easy tier added | a flat zero "would have ranked it level with a system that answers nothing at all" |
| v1.1.2 | Balanced 33:33:33, cost range widened | systems pinned at the 100 cap |
| v1.1.3 | GPU round | self-hosted rebuilds took the top on speed and cost, "not accuracy"; near-100% ceiling hid gaps |
| v1.2 | hard tier (220 items, half held out), calibration axis, geometric mean of four axes | ceiling effect; label-only systems needed a defined calibration outcome (0) |
| v1.2.4 | services that run another entrant's model listed but not ranked | classifier.dev's fast tier is Jev; ranking it "put the same model in the list twice" |
| v1.3.0 | intelligence above chance, `(acc - chance)/(1 - chance)`, and `(I/50)^2` multiplier below 50 | "cheap and fast but barely better than guessing could rank high" |

## Findings we should expect to reproduce

- Jev re-run 16 minutes later changed 3 of 242 answers: "read a gap of about a point between two rows as noise". Bootstrap intervals, not point rankings.
- Option order flipped a small model from 72% to 21% on yes/no items. Small models are "very sensitive to option order".
- Thinking modes: OpenJev `think=512` reached Intelligence 88 but scored 60 on cost; djev thinking exhausted an 8k output budget on 72 of 534 items, and those count as failures and are priced.
- Rerankers, GLiNER, and encoder classifiers can have excellent calibration and speed and still collapse under the near-chance penalty. Speed and cost without accuracy is not a decision model.
- No combination (cascade, committee, best-of-n) beat the best single system on the composite; a confidence cascade kept 99.6% of Jev's accuracy at a ninth of the cost but lost on the composite because cost is only one axis.
- Prompt limits change scores in both directions: Nimble 9B's hard-tier accuracy rose 22 points after an 8k limit and its score fell, because the long items were now answered, priced, and slow.

## Fairness rules worth copying verbatim

- Mappings, endpoint conditions, and cost bases are pushed to the repo before the run. One 45-second exception is documented as such.
- Held-out items go only to the benchmark's own machines or a production API, never to an endpoint a submitter operates; a submitter-hosted run is shown as partial and unranked.
- "Every exclusion is an availability fact about our hardware and access, never a quality verdict." Refusals to accept gated terms, subscriptions, or bypass bot blocks on the author's behalf are stated.
- Contributor code runs only in a disposable container with no network, no host home, no Docker socket, empty environment.
- Authors get a re-run on request; superseded rows are kept in the artifact.
- Conflicts disclosed: the author's own router experiment supplies 146 decisions; benchmark-directed training is allowed and disclosed (smalljev calls its recipe "a JevBench hill-climb").
- "Held-out means not publicly released, not guaranteed unseen." Never claim a contamination proof.

## Stated limits

534 decisions is "a pilot, not a census", English only; the ×2 +0.15 s self-hosted latency adjustment is an assumption with a load measurement "planned"; one origin, one time of day; estimated costs are what a large provider would charge, not what the author pays.

## What we adopt

1. The record schema, validator, banned keys, order-independent hash, and per-split manifest. Extended with `feature`, `subtask`, `category` (AILuminate + Bedrock), `attribute` for bias rows, `visibility` public/heldout, and `label_basis` in provenance.
2. The adapter contract and the native vs verbalized split, and the rule that a label-only system gets accuracy and no calibration.
3. The ledger, the serial runner, the fsync-before-next-call, the outside-the-repo guard, the stop rule, and no retries.
4. Cost as dollars per 1,000 evaluations with an explicit basis, never invented. We add measured latency under load at concurrency 1 and 16 instead of a multiplier.
5. Pre-registration by commit before any run; addition notes per system; superseded rows kept.
6. Held-out slices for counterfactual templates, crafted topics, and action scenarios, with the JevBench wording about what held-out does and does not mean.
7. Thresholds fitted on public tune rows only, published and hashed, then the private rows run once. This is exactly how JevBench handled reranker temperature grids.
8. Chance-corrected accuracy per feature, so a two-way Noul slice and a five-way Choice slice are comparable.

## What we do differently, on purpose

- Guardrail tasks, not general decisions; human or deterministic labels only in the headline; bias as a scored feature.
- Managed services as baselines. JevBench has none because they do not speak the System One contract; our baseline adapters map their outputs onto our label sets and publish the map.
- Question sets are versioned files separate from records, because the same row is asked differently by a decision model, a service, and an LLM classifier.
- Load-tested latency instead of an adjustment factor.
- We will offer the guardrail tasks to Benchmark Heaven as a track before publishing, so the two benchmarks reinforce rather than compete.

## Addendum, 22 September: gold distributions from annotator disagreement

JevBench scores 20 hard-tier items against an exact gold probability distribution, not just a label, using total-variation distance. The guardrail equivalent is annotator disagreement. Where three annotators split on a row, the split is the gold distribution and a calibrated decision model should reproduce it; a service that returns a severity bucket cannot. Gold Rails therefore audits a 600-row subset with three annotators, keeps the vote split as `expected_distribution` beside `expected`, and reports TVD against it for every probabilistic system. Two further rules carried over: a composite, if published at all, is a geometric mean with components shown beside it; and a guardrail product that runs another entrant's model (classifier.dev's fast tier is Jev) is listed but not ranked.

## Addendum, 22 September 2026: throughput

JevBench's runner is a plain loop, one request at a time, for every system (`runner.py: for t in tasks`). That is deliberate: its Speed pillar is serial latency including the network, and its self-hosted endpoints ran with batch size 1 and prefix caching off so the number is comparable across hosts. It is not a fast way to run an accuracy pass; the Open-Jev rows took an H100 per model and still ran serially.

Gold Rails separates the two. Accuracy passes run every system concurrently with a few in-flight requests per hosted API (`goldrails_bench.runner.run_matrix`), because the answer to a row does not depend on when it was asked and nothing is retried. Latency is a separate small serial pass (`serial=True`) reported as p50 and p95 at concurrency 1, and later at 16, as the spec says, never derived from the throughput pass.
