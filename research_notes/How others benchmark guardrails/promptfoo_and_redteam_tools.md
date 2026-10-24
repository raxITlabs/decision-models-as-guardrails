# How promptfoo and open red-teaming tools (garak, PyRIT, Giskard, DeepTeam) evaluate guardrails

Research date: 2026-10-24. All docs pages were fetched on this date; "last updated" dates are given where the page stated one.

## 1. promptfoo: guardrail-evaluation methodology, test generation, grading, reporting, published numbers

### Takeaway
promptfoo treats a guardrail as a binary `flagged` signal that the target returns. Its guidance is to test both sides: attacks should be flagged (`not-guardrails`) and benign prompts should pass (`guardrails`). It names four metrics: attack block rate, false-positive rate, indeterminate rate, and latency/cost. It warns repeatedly that a missing signal or an error must not count as a pass. Its red-team side generates attacks from plugins and strategies and grades them with LLM judges, reporting ASR plus a CVSS-style risk score. It has published no head-to-head numbers comparing guardrail products. Its strongest methodological contribution is a Dec 2025 post arguing that ASR is not portable across setups.

### Cited Findings
**Guardrail assertion semantics**
- The `guardrails` assertion "does not run a guardrail or inspect the text". It reads a normalized top-level `guardrails.flagged` field from the provider response. `flagged: true` fails `guardrails` and passes `not-guardrails`. — [promptfoo docs: guardrails assertion](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)
- Pass/fail table: if `flagged` is omitted, or the whole `guardrails` object is missing, `guardrails` **passes** and `not-guardrails` fails. The docs warn: "A pass means Promptfoo did not receive `flagged: true`; it does not prove that a guardrail ran." — [same](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)
- There is no dedicated false-positive assertion. False positives show up when `guardrails` is applied to benign traffic, and false negatives when `not-guardrails` is applied to attacks. The docs warn against setting `guardrails` as a suite-wide default in mixed suites, because it would also attach to the attack cases. — [same](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)
- `flagged` alone decides the verdict. `flaggedInput` and `flaggedOutput` only refine the reason. — [same](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)
- Provider errors skip assertions entirely, so an expected block must come back as scorable output. For custom HTTP targets, map native allow/block into `{flagged, flaggedInput, flaggedOutput, reason}` and **throw** on unknown or failed decisions: "Mapping any of those states to `flagged: false` creates a false pass." — [same](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)
- `purpose: redteam` override: when `flagged: true`, the test is force-passed ("Content failed guardrail safety checks") and the vulnerability grader is skipped. Enable it "only" when `flagged` means the request was actually blocked, not for detect-only or logging-only guardrails. — [same](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)
- Built-in normalization is specific to endpoint and mode. Azure OpenAI covers Chat/Completions/Assistants content-filter results (Responses is not normalized the same way). Bedrock covers InvokeModel and non-streaming Converse via `guardrail_intervened`, with direction "often unknown" and streaming/cached responses possibly differing. Google AI Studio exposes safety ratings, and hard blocks become errors. Vertex AI covers prompt block reasons including Model Armor. OpenAI Chat covers refusals and content-filter finish reasons. Anthropic covers structured classifier refusals only. Other OpenAI-compatible providers are not normalized. — [same](https://www.promptfoo.dev/docs/configuration/expected-outputs/guardrails/)

**"Testing guardrails" guide: the methodology**
- Core principle: a useful eval "measures both sides of the policy". Attacks should be flagged and legitimate requests should stay usable. "A high block rate is not useful if legitimate requests are routinely rejected." — [promptfoo guide: Testing guardrails](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- Two levels. **Integrated** tests the full app with guardrails on, including prompt construction, streaming and app filters. **Direct** calls the guardrail service alone, which is cheaper and suited to threshold tuning and vendor comparison. The guide warns that "Direct guardrail testing does not exercise the LLM or your production application", so keep at least one integrated eval. — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- Four recommended metrics:
  1. Attack block rate: flagged attacks ÷ attacks.
  2. False-positive rate: flagged benign ÷ benign.
  3. **Indeterminate rate**: timeouts, partial runs, skipped filters, filter errors.
  4. Latency and cost: integrated vs standalone overhead.
  — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- Execution failures should "surface as errors and be tracked as indeterminate". "Missing guardrail metadata currently behaves like `flagged: false`", and "a green test with no `guardrails` object proves nothing about enforcement." — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- Test-set advice: use fixed cases for regression and generated attacks for discovery. Cover multilingual prompts, encodings, misspellings, multi-turn attacks, streaming output, and policy boundaries. — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- Vendor specifics:
  - Azure Prompt Shields: read `userPromptAnalysis.attackDetected` and `documentsAnalysis[].attackDetected`, and fail on non-2xx.
  - Azure Content Safety severity is ordinal (0/2/4/6), so pick a documented threshold such as `severity >= 4`.
  - Bedrock: map `GUARDRAIL_INTERVENED` → flagged, and note that "detection-only findings are not interventions". Because the built-in provider adds metadata mainly on intervention, a benign pass may just be the fallback.
  - OpenAI: moderation results, structured refusals and `content_filter` are separate signals.
  - Lakera and Llama Guard are not covered on this page.
  — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- `guardrails-eval` is described as a collection of vulnerability plugins for adversarial coverage, "not a provider integration or an assertion". — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)

**Test-case generation (red team)**
- Plugins generate base test cases per vulnerability (OWASP / MLCommons / HarmBench-mapped). Dataset-backed plugins include `xstest`, `harmbench`, `beavertails`, `donotanswer`, `aegis`, `toxic-chat`, `pliny`, `cyberseceval` and `unsafebench`. `xstest` (ambiguous words with harmful and benign readings) is the only plugin aimed at over-refusal. — [promptfoo: LLM vulnerability types](https://www.promptfoo.dev/docs/red-team/llm-vulnerability-types/)
- Strategies wrap the plugin cases. `basic` runs the unmodified cases. Each strategy is listed with a cost and an "ASR increase", measured relative to the same run with no strategy:
  - Static encodings (Base64, Hex, ROT13, leetspeak, homoglyph, Morse, Pig Latin, emoji smuggling, camelCase, audio/image/video): low cost, roughly 0–30%.
  - Jailbreak templates (DAN etc.): 20–30%.
  - Iterative jailbreak and tree: high cost, 60–80%. Meta-agent: 70–90%. `jailbreak:composite`: medium cost, 60–80%. Best-of-N: 40–60%. Citation/Likert/authoritative markup/math prompt: 40–60%. GCG: 0–10%.
  - Multi-turn Crescendo, GOAT, Hydra and Goblin: high cost, 70–90%. Mischievous User: 10–20%.
  - Retry (re-runs previously failed cases): 50–70%.
  - Layer (chains strategies). Custom strategies.
  - Dynamic strategies stop when the budget is exhausted or early on success. Recommended defaults are `jailbreak:meta` (single-turn) and `jailbreak:hydra` (multi-turn). Multi-turn scans track target, attacker and grader tokens separately.
  — [promptfoo: Strategies](https://www.promptfoo.dev/docs/red-team/strategies/)
- Note: the ASR-increase bands are promptfoo's own ranges, with no stated source dataset or target. Treat them as **unverified vendor estimates**.

**Grading and reporting**
- Each plugin uses an LLM-as-judge grader that produces pass/fail. The strategies page mentions grading requests but does not name the judge model per strategy. **Not verified on the fetched pages**: the per-plugin rubric text and the default grader model. — [Strategies](https://www.promptfoo.dev/docs/red-team/strategies/)
- Risk score (0–10, "follows CVSS v3.x/v4.0 levels") = Impact + Exploitability + Human Factor + Complexity Penalty:
  - Impact: Critical 4, High 3, Medium 2, Low 1.
  - Exploitability: 0 if ASR = 0, else 1.5 + 2.5×ASR.
  - Human factor: base 1.5/1.0/0.5/0 by exploitability class, × (0.8 + 0.2×ASR).
  - Complexity penalty: 0.1 + 0.4×ASR, capped at 0.5, applied to low-complexity cases only.
  - Bands: 9–10 Critical, 7–8.9 High, 4–6.9 Medium, 0.1–3.9 Low.
  - System score = max individual score, +0.5 per additional critical and +0.25 per additional high.
  - The page's own Scenario 3 computes to 5.65 but is labelled "High", which is internally inconsistent. Page last updated 2026-10-23.
  — [promptfoo: Risk scoring](https://www.promptfoo.dev/docs/red-team/risk-scoring/)

**Methodology critique by promptfoo itself (Dec 12 2025, Michael D'Angelo, CTO)**
- Reported ASR "can shift... by 50 percentage points or more" with the same attack, depending on attempt budget, prompt set and judge. — [promptfoo blog: ASR not portable](https://www.promptfoo.dev/blog/asr-not-portable-metric/)
- Attempt budget: a 1% per-attempt attack reaches about 9.6% at K=10, 39.5% at K=50 and 98% at K=392, via 1−(1−p)^K. — [same](https://www.promptfoo.dev/blog/asr-not-portable-metric/)
- Prompt-set label noise: in an audit of 10 "Political Activities" prompts from JailbreakRadar, the author labelled 1 a clear violation, 7 borderline and 2 clearly fine, yet the source paper reported over 80% ASR on that category. — [same](https://www.promptfoo.dev/blog/asr-not-portable-metric/)
- Judge choice: at a true 50% rate, Judge A (TPR 0.76, FPR 0.16) gives 0.46 observed ASR and Judge B (TPR 0.90, FPR 0.30) gives 0.60. Both are 80% accurate, yet they differ by 14 points. — [same](https://www.promptfoo.dev/blog/asr-not-portable-metric/)
- Recommendations:
  - State K.
  - Report median and p95 attempts-to-success and cost per success.
  - Report a no-attack baseline.
  - Disclose the prompt set, its labelling and the policy date.
  - Disclose the judge model, its TPR/FPR and the rubric.
  - Disclose decoding settings and micro vs macro aggregation.
  - Define the threat model.
  The post does not explicitly call for confidence intervals. — [same](https://www.promptfoo.dev/blog/asr-not-portable-metric/)

**Published product comparisons**
- No promptfoo-authored blog post or doc on the fetched pages publishes numbers comparing Bedrock, Azure, Lakera, Llama Guard or OpenAI moderation. The first page of the blog index had no such post. — [promptfoo blog index](https://www.promptfoo.dev/blog/)
- Third party: a Wavestone RiskInsight benchmark reportedly compared Bedrock Guardrails, Azure Content Safety, GCP Model Armor and Lakera Guard in default configs. It used F1 as the primary metric and promptfoo red-teaming as a second stage. The search snippet said Azure "never incorrectly categorized legitimate prompts" and Bedrock was best at blocking malicious prompts. **Unverified**: the article URL returned 404 when fetched, so these come only from the search snippet. — [Wavestone RiskInsight (search result; 404 on fetch)](https://www.riskinsight-wavestone.com/en/?p=28319)

**Ownership context**
- OpenAI announced on 2026-03-09 that it would acquire Promptfoo and integrate it into OpenAI Frontier. Promptfoo is to stay open source and multi-provider. — [OpenAI announcement](https://openai.com/blog/openai-to-acquire-promptfoo); [Security Boulevard](https://securityboulevard.com/2026/03/openai-acquires-security-startup-promptfoo-to-fortify-ai-agents)
- Whether the deal closed was not confirmed from the sources fetched.

### Inferences
- promptfoo's four metrics (block rate, FPR, indeterminate rate, latency/cost) line up with raxIT's balanced accuracy plus cost axis. raxIT could adopt the explicit **indeterminate rate** as a reported column, so that errors and timeouts are never silently scored as "allow".
- promptfoo's warning that missing metadata behaves like `flagged: false` is exactly the failure mode a Bedrock benchmark must guard against. Bedrock detect-only findings vs `GUARDRAIL_INTERVENED` must be mapped deliberately.
- The "direct vs integrated" split justifies raxIT's choice to benchmark guardrails directly. raxIT should state that it measures direct classification, not end-to-end app blocking.
- The ASR-portability post reads as a checklist raxIT already mostly meets (fixed prompt set, fixed threshold, one attempt per row, public datasets, CIs). The judge item does not apply because raxIT uses dataset labels, not an LLM judge. This is a point of contrast worth stating.
- Conflict-of-interest note: promptfoo is now OpenAI-owned, and raxIT benchmarks an OpenAI Decisions API. Any promptfoo-derived comparison should be read with that in mind.

### Gaps
- Default grader model and rubric text per plugin were not fetched.
- The Wavestone numbers could not be verified (404).
- No promptfoo-published guardrail-vs-guardrail leaderboard was found. Blog page 2 onward was not checked.
- How `xstest` results are graded (over-refusal counted as failure?) was not confirmed.

## 2. garak: probe/detector architecture, scoring, calibration, reporting

### Takeaway
garak (NVIDIA; arXiv June 2024) is a scanner built from generators, probes, detectors and buffs, wired together by a harness. Each probe/detector pair yields a pass rate. Reports give an absolute pass rate plus a **relative Z-score** against a calibration "bag" of models, and both are binned into DEFCON-style grades 1–5. Aggregation uses the minimum, so one weak area pulls down the whole grade. Its detectors are mostly string or classifier based. An independent study found them the least reliable of the scanners tested.

### Cited Findings
- Paper: Derczynski, Galinkin, Martin, Majumdar, Inie, "garak: A Framework for Security Probing Large Language Models", arXiv:2406.11036, submitted 16 Jun 2024. — [arXiv](https://arxiv.org/abs/2406.11036)
- Components and roles — [arXiv HTML](https://arxiv.org/html/2406.11036v1):
  - **Generators** wrap the target. Any Python function or API can be one.
  - **Probes** each target one vulnerability type.
  - **Detectors** score outputs with keyword/signature matching and ML classifiers.
  - **Buffs** perturb prompts (lowercasing, paraphrase, base64).
  - A **harness** chooses which probes to run and routes their outputs to detectors.
- Reporting artifacts — [arXiv HTML](https://arxiv.org/html/2406.11036v1):
  - JSONL report: one record per prompt, with probe and parameters, outputs, and detector results.
  - **Hitlog** of prompt/response pairs that indicated failure.
  - HTML summary grouped by taxonomy (OWASP LLM Top 10, AVID), with probes sorted by highest failure rate.
  - Optional upload to the AI Vulnerability Database.
- The paper's only explicit threshold is in the atkgen evaluation: a toxicity score ">0.5" counts as toxic. — [arXiv HTML](https://arxiv.org/html/2406.11036v1)
- Limitations the authors state — [arXiv HTML](https://arxiv.org/html/2406.11036v1):
  - Signature detectors "detect only a single known issue and do not generalize".
  - "It is also difficult to automatically detect model failures."
  - Detector performance is "fragile, and may even require per-model data annotation".
  - Probes are English-only.
  - No quantitative FP/FN analysis.
  - NeMo Guardrails is only cited, not evaluated.
- Scoring — [garak reporting docs](https://reference.garak.ai/en/latest/reporting.html):
  - The digest's `absolute_score` is a pass rate. `hit_at_k` values are hit rates.
  - Unscoreable outputs (`nones`) are excluded from `total_evaluated`.
  - Relative scores are "a Z-score computed against a set of recently tested other models and systems".
  - Absolute and relative scores are each binned into grades 1 (worst) to 5 (best), DEFCON-style. Multi-part results are "aggregated using a minimum, to avoid obscuring important failures".
  - Relative bands assume "the middle 10% is average, the bottom 15% is terrible, and the top 15% is great".
- Calibration — [garak calibration docs](https://reference.garak.ai/en/latest/reporting.calibration.html):
  - The bag is chosen on quantity, recency, size (1–10B, 11–99B, 100B+), provider (no more than 2 per provider) and openness (open weights preferred).
  - For each probe/detector pair, the mean and SD of pass rate are computed across the bag, and a Shapiro-Wilk p-value is reported to check normality.
  - Bands: about ±0.125 is "competitive" (the middle 10%); above +1 is much better; below −1 is much worse.
  - SDs are "artificially bound... at a non-zero minimum" (value not stated).
  - Caveat: "It's possible to get a great Z-score and a low absolute score."
  - Refreshing the bag improves recency but hurts comparability across runs.
  - The bag list lives in `bag.md` on GitHub (not fetched). No calibration date is given.

### Inferences
- garak's Z-score-vs-bag is a relative ranking idea, comparable to raxIT's Holm-adjusted tiers but cruder: there are no pairwise tests, and the bands come from distribution quantiles. raxIT's paired bootstrap plus Holm is the more rigorous version of "is system A distinguishable from the field".
- Min-aggregation of grades is a design choice worth noting. raxIT reports balanced accuracy, a mean of TPR and TNR, which can hide a weak category. A per-category floor or worst-category column would echo garak.
- garak scores **only attack failure**. It has no benign/over-refusal axis, so it does not measure false positives.

### Gaps
- Exact Z-score formula and SD floor value were not found.
- Current bag membership and calibration date are unknown (bag.md not fetched).
- No garak-native guardrail-product evaluation was found. garak can target NeMo Guardrails, but that was not verified in the fetched pages.

## 3. PyRIT, Giskard, DeepTeam: scoring, multi-turn, guardrails vs models

### Takeaway
All three use LLM-as-judge scoring. PyRIT is the only one that publishes **meta-evaluation numbers for its own judges** against human labels; its best refusal-judge accuracy is about 89.6%. Giskard has moved to a judge-regression CI approach, giskard-checks, but publishes no accuracy numbers. DeepTeam ships its own LLM-judged "guards" (default gpt-4.1) and a CVSS-like score, with no published guard accuracy. None of them benchmarks third-party guardrail products head to head.

### Cited Findings
**PyRIT (Microsoft)**
- Early scoring relied on string matching (e.g. "Sorry"), which "didn't scale". LLM judges then produced false positives on benign text and passed harmful content that carried disclaimers. That led to a human-labelled evaluation set of "several hundred examples" graded against PyRIT rubrics by the Microsoft AI Red Team and vendors. — [PyRIT blog "Scoring scorers", 2026-04-14](https://microsoft.github.io/PyRIT/latest/blog/2026-04-14-scoring-scorers)
- Metrics — [same](https://microsoft.github.io/PyRIT/latest/blog/2026-04-14-scoring-scorers):
  - Objective (true/false) scorers: accuracy, precision, recall, F1.
  - Harm (Likert 1–5, normalized) scorers: MAE, a one-sample t-test, Krippendorff's α.
  - Improving judges is called "an important yet difficult research problem".
- Published scorer metrics. Objective scorer: SelfAskRefusalScorer, inverted. — [PyRIT scorer metrics](https://microsoft.github.io/PyRIT/latest/code/scoring/scorer-metrics)

  | Judge model | Accuracy | F1 | Avg time |
  |---|---|---|---|
  | gpt-5.4 + JSON schema | 89.62% (±1.53) | 0.894 | 1.18 s |
  | gpt-4o, no schema | 89.37% | 0.892 | 0.59 s |
  | gpt-4o + schema | 88.35% | 0.875 | 0.69 s |

  Across 31 configs, scoring time ranged from 0.043 s to 10.4 s.
- Violence harm scorers — [same](https://microsoft.github.io/PyRIT/latest/code/scoring/scorer-metrics):
  - SelfAskLikert gpt-4o: MAE 0.177–0.190, combined α 0.81–0.84.
  - AzureContentFilterScorer: MAE 0.244, α 0.775.
  - The docs recommend `num_scorer_trials` ≥ 3 in production to measure variance.
  - They also compute a constant-guess baseline MAE and split unanimous vs contested human rows.
- Earlier versions (per the Fujitsu study) had binary, 1–5 and 0–1 LLM scorers with explanations, plus a strategy for evaluating the evaluator. — [arXiv 2410.16527](https://arxiv.org/html/2410.16527v2)
- Not fetched: details of the multi-turn attacks (Crescendo, PAIR, TAP, RedTeaming) and the converters. **Unverified here**: they are known PyRIT components, but no docs page was fetched to confirm current names.

**Giskard**
- Giskard Hub 2.0.0 (2025-09-25) added autonomous red-teaming agents that run dynamic multi-turn attacks across more than 40 probes, mapped to OWASP LLM categories. — [Giskard Hub release notes 2.0.0](https://docs.giskard.ai/hub/ui/release_notes/2_0_0.html) (via search snippet; page not fetched)
- 2026-05-12 meta-evaluation post (Messiaen, Berenstein) — [Giskard blog](https://www.giskard.ai/knowledge/who-judges-the-llm-as-a-judge-meta-evaluation-of-an-llm-vulnerability-scanner):
  - The scanner's LLM judge decides attack success, and it is itself tested.
  - Method: snapshot real attack traces, freeze human-annotated expected verdicts, replay them through the judge with a deterministic equality check in CI (pytest over JSONL), and use a fixed synthetic target answer to isolate the judge.
  - Example: `PIILeakScorer`.
  - The post reports **no** dataset size, accuracy or FPR. It frames itself as regression detection: "someone still has to certify the adjudicators."
  - The open-source library was rebuilt as **giskard-checks**.
- Giskard v2 (2024) used a mix of static and LLM evaluators. The LLM evaluator was conditioned on a model description and generated safety requirements. — [arXiv 2410.16527](https://arxiv.org/html/2410.16527v2)

**DeepTeam (Confident AI)**
- Each vulnerability ships an LLM-as-judge metric that outputs only 0 or 1. Attacks are single-turn or multi-turn (multi-turn adapts to replies). — [DeepTeam intro](https://www.trydeepteam.com/docs/red-teaming-introduction)
- CVSS-style per-case score — [same](https://www.trydeepteam.com/docs/red-teaming-introduction):
  - `(impact×0.6 + exploitability×0.3 + exposure×0.1)×10`.
  - Impact is fixed at MEDIUM. Exploitability is declared per attack. Exposure is 0.3, 0.6 or 0.9.
  - A passed case scores 0. Errored cases are excluded from the average.
  - Bands match CVSS. Frameworks such as OWASP and MITRE ATLAS are configurable.
- DeepTeam Guardrails — [DeepTeam guardrails intro](https://trydeepteam.com/docs/guardrails-introduction); [deploy guide](https://trydeepteam.com/guides/guide-deploying-guardrails):
  - Input and output guards, e.g. PromptInjectionGuard, ToxicityGuard, Privacy, Illegal, Topical, Cybersecurity, Hallucination. The deploy guide lists 7.
  - Verdicts are `safe` / `uncertain` / `unsafe`. A breach occurs if any guard returns unsafe **or uncertain**.
  - `evaluation_model` defaults to gpt-4.1. `sample_rate` defaults to 1.0.
  - The docs say the guardrails focus "on speed and reliability" but publish no latency figures and no accuracy metrics.
  - No FP handling is described beyond user-defined retry logic.

### Inferences
- PyRIT's scorer-metrics page is the closest analogue to raxIT's method: human-labelled ground truth, accuracy/F1 with standard errors, timing per call. Its own judges reach about 89–90% accuracy on refusal detection. Any red-team ASR built on such judges inherits roughly 10% label error. raxIT avoids this by scoring against dataset labels, and should say so explicitly.
- DeepTeam's "uncertain counts as breach" is effectively a conservative threshold choice built into the product. It is relevant when comparing raxIT's fixed 0.5 threshold with three-way-verdict systems.
- DeepTeam's guards (and Giskard's judges) are LLM decision systems in their own right. They are candidates for inclusion as benchmarked systems, not only as evaluators.

### Gaps
- PyRIT's current multi-turn attack/executor names and its Azure Prompt Shield target/scorer were not verified.
- No published accuracy numbers were found for DeepTeam guards or Giskard judges.
- None of the three publishes a benchmark of third-party guardrails (Bedrock, Azure, Lakera, etc.).

## 4. False positives / over-blocking, thresholds, latency and cost

### Takeaway
Only promptfoo gives first-class guidance on false positives (an FPR metric with benign cases asserted via `guardrails`) and on indeterminate results, latency and cost. garak and DeepTeam's red-team mode measure attack success only. Thresholds are mostly left to the user: Azure severity ≥ 4 is suggested, garak's toxicity cutoff is > 0.5, and DeepTeam treats uncertain as unsafe. Latency is reported as per-scorer timing (PyRIT) or as token accounting (promptfoo multi-turn), never as a guardrail product comparison.

### Cited Findings
- promptfoo FPR metric, "optimize for both safety and usability", indeterminate rate, integrated vs standalone latency and cost. — [promptfoo Testing guardrails](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- promptfoo: Azure Content Safety severity is ordinal, so choose a documented threshold (e.g. `severity >= 4`). Do not label failed requests `flagged: false`. — [same](https://www.promptfoo.dev/docs/guides/testing-guardrails/)
- promptfoo strategy pages give relative cost tiers (Low/Medium/High) and say multi-turn scans account target, attacker and grader tokens separately. — [promptfoo Strategies](https://www.promptfoo.dev/docs/red-team/strategies/)
- promptfoo: only `xstest` targets over-refusal among its dataset plugins. — [promptfoo vulnerability types](https://www.promptfoo.dev/docs/red-team/llm-vulnerability-types/)
- garak: the toxicity cutoff is > 0.5 (atkgen), and there is no benign axis. — [arXiv 2406.11036](https://arxiv.org/html/2406.11036v1)
- PyRIT reports average scoring time per scorer config (0.043–10.4 s). — [PyRIT scorer metrics](https://microsoft.github.io/PyRIT/latest/code/scoring/scorer-metrics)
- DeepTeam: `uncertain` counts as a breach, and there is a `sample_rate` for cost control. — [DeepTeam guardrails](https://trydeepteam.com/docs/guardrails-introduction)
- PyRIT notes LLM judges flag benign replies as harmful, a judge-side false positive. — [PyRIT blog](https://microsoft.github.io/PyRIT/latest/blog/2026-04-14-scoring-scorers)

### Inferences
- raxIT's fixed 0.5 threshold plus balanced accuracy (which weights benign TNR equally) is stricter about over-blocking than any of these tools' defaults. That is a differentiator worth stating.
- No tool reports cost per correct decision or per 1k rows for guardrail products. raxIT's cost axis fills a real gap.

### Gaps
- No tool publishes cross-vendor latency or cost numbers for guardrail products.
- No threshold-sweep or ROC guidance was found in any of the tools' docs.

## 5. Weaknesses critics point out (judge reliability, attack quality, reproducibility)

### Takeaway
The main independent critique is a Fujitsu study (Nov 2024). It found scanner evaluators misclassify attack outcomes by up to about 37% (garak worst; PyRIT's LLM judges best) and called for evaluator-accuracy minimums and a shared benchmarking platform. The vendors themselves concede the core problems: promptfoo on ASR non-portability and judge TPR/FPR, PyRIT and Giskard on judge reliability, garak on fragile detectors.

### Cited Findings
- Brokman et al. (Fujitsu Research), arXiv:2410.16527v2, 13 Nov 2024 — [arXiv](https://arxiv.org/html/2410.16527v2):
  - Compared garak v0.9.0.14.post1, Giskard v2.14.4, PyRIT v0.2.2.dev0 and CyberSecEval.
  - Used about 5K prompts across LLaMA-3-8B, Command R, Mistral Small and GPT-4o, with 1,045 manually annotated responses.
  - Misclassification "can reach 37%" (garak, max margin of error 26%). Giskard and PyRIT LLM evaluators were most reliable, and PyRIT had the lowest MOE.
  - Examples: garak Jailbreak on Command R gave ASR 73.0% with MOE 17.2%; Giskard Context & Continuation gave 40.0% / 9.1%; CyberSecEval code gen on GPT-4o gave 19.5% / 19.8%.
  - Failure modes:
    - Static evaluators lack context (e.g. "unethical" read as a refusal; a missing colon in "ANTI-DAN:" flagged as a failure).
    - LLM evaluators misread instructions, and generated requirements invalidated correct refusals.
    - Little or no explanation of verdicts.
  - Reproducibility: the authors had to construct some Giskard and PyRIT attacks themselves, and PyRIT had no formal report at the time. Ambiguous responses were excluded.
  - Internal inconsistency: the text says code-gen ASR is "nearly 70%" while the table shows 74.3% and 82.4%.
  - Recommendations: regulators should set evaluator-accuracy thresholds per category, and the field needs a shared, continuously updated benchmarking platform.
- promptfoo's own critique: ASR depends on K, prompt set and judge. Documented judge artifacts include misclassified safe preambles, length sensitivity, self-preference bias and hallucinated outputs. Framework defaults dominate leaderboards ("mostly measures those defaults"). — [promptfoo blog](https://www.promptfoo.dev/blog/asr-not-portable-metric/)
- garak authors: detectors are fragile and may need per-model annotation. — [arXiv 2406.11036](https://arxiv.org/html/2406.11036v1)
- PyRIT: judges are non-deterministic, have training biases and struggle with social nuance, so it recommends multiple trials. — [PyRIT blog](https://microsoft.github.io/PyRIT/latest/blog/2026-04-14-scoring-scorers)
- Giskard: judge drift and false positives motivated freezing verdicts in CI. — [Giskard blog](https://www.giskard.ai/knowledge/who-judges-the-llm-as-a-judge-meta-evaluation-of-an-llm-vulnerability-scanner)
- promptfoo's strategy ASR-uplift ranges (e.g. 70–90% for Crescendo/GOAT) are unsourced vendor bands and depend on the attacker LLM. — [promptfoo Strategies](https://www.promptfoo.dev/docs/red-team/strategies/)

### Inferences
- The recurring weaknesses all apply to red-team scanners:
  - judge error of about 10–37%
  - generated attacks that vary run to run
  - framework defaults driving the numbers
  - no benign axis
  raxIT's design (fixed public labelled rows, frozen manifests, a deterministic threshold, paired CIs, Holm tiers) addresses each one directly. That framing is a strong "why this benchmark" argument.
- raxIT's own label-noise risk is the analogue of promptfoo's JailbreakRadar audit, since public datasets contain borderline "harmful" rows. A small human relabel audit of a sample, reporting the borderline share, would pre-empt the same criticism.
- The Fujitsu call for a "shared benchmarking platform" is a direct opening for raxIT's leaderboard positioning.

### Gaps
- No independent 2025–2026 replication of the Fujitsu scanner-reliability study was found, so post-2024 versions (Giskard Hub 2.0, PyRIT 1.x, garak current) are unevaluated.
- No critique specific to DeepTeam was found.
