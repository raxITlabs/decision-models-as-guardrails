# Methodology best practice for safety/guardrail classifier benchmarks

Context: raxIT "decision-models-as-guardrails" runs 20 systems on 9,975 public rows. Every system gets a fixed 0.5 threshold. The board reports balanced accuracy, paired bootstrap 95% CIs with groups resampled, and Holm-adjusted tiers. Edition 3 is planned as a hard set of 1,200 hand-written attack/benign twin pairs, with 60% held back, a canary GUID, rotation after each release, two blind labellers, and Krippendorff's alpha. Notes compiled 2026-10-24. Items marked UNVERIFIED come from background knowledge, not from a source fetched in this session.

## Threshold policy: fixed vs tuned vs threshold-free; fair comparison across calibrations; operating points

### Takeaway
The guardrail literature has no common threshold standard. Papers mix AUPRC (threshold-free, which needs a continuous score), vendor-default binary flags, and low-FPR operating points such as recall at 1% FPR. A fixed 0.5 is defensible as a "default deployment" view. Fair comparison also needs at least one threshold-free or fixed-FPR view, because many API systems return only a flag and calibration differs between systems.

### Cited Findings
- Llama Guard (Meta) reports AUPRC throughout. Azure's API returns no probability, so the authors swept candidate thresholds and kept the best average precision. GPT-4 and Azure are reported with threshold-based precision/recall/F1 in an appendix, because average precision could not be computed for them. — [Llama Guard paper](https://arxiv.org/pdf/2312.06674)
- RigorLLM sets the default probability threshold for the OpenAI and Perspective APIs at 0.5 for F1. It uses the probability of the "unsafe" token as Llama Guard's score for AUPRC. — [RigorLLM](https://arxiv.org/pdf/2403.13031)
- TWGuard notes that LLM guardrails emit discrete tokens with a fixed decision threshold. It uses the first-token log-probability of "unsafe"/"safe" as a continuous score so it can compute threshold-independent AUPRC. — [TWGuard](https://arxiv.org/pdf/2604.16542)
- The GuardBench leaderboard drops AUPRC, arguing that it overemphasises precision at the expense of recall, and reports F1 instead. — [GuardBench leaderboard](https://amenra-guardbench-leaderboard.hf.space)
- OpenAI Moderation is usually consumed as a boolean `flagged`. Without category scores a threshold sweep is impossible. — [summary via search of TWGuard/RigorLLM-style evaluations](https://arxiv.org/pdf/2403.13031) (UNVERIFIED in detail: the moderation endpoint does also return per-category scores, which some papers use)
- Artificial Analysis (with NVIDIA, 2026-06-11) parses each model's native output into a binary safe/unsafe label, with no score threshold. It runs at temperature 0 and non-streaming. The headline is average F1 across WildGuardTest, ToxicChat and XSTest, equally weighted, and it also reports recall and specificity. It says there is no common standard for evaluating these models. — [Artificial Analysis guardrail benchmark](https://artificialanalysis.ai/articles/guardrail-safety-benchmark)
- Prompt-injection detectors are often reported at a fixed low FPR. LlamaFirewall defines "recall at 1% FPR" as the share of attacks caught while FPR on benign prompts is held at 1%. Prompt Guard 2 86M reports AUC .998 and 97.5% recall at 1% FPR, against Prompt Guard 1 at AUC .987 and only 21.2% recall at 1% FPR. A near-identical AUC can therefore hide a large gap at a deployable operating point. — [LlamaFirewall](https://arxiv.org/pdf/2505.03574); [Prompt Guard 2 model card](https://huggingface.co/project-free-llama/Llama-Prompt-Guard-2-86M)
- The sources disagree on Prompt Guard 2 86M's AUC: .998 on the model card versus .98 in the LlamaFirewall paper table. — [model card](https://huggingface.co/project-free-llama/Llama-Prompt-Guard-2-86M); [LlamaFirewall](https://arxiv.org/pdf/2505.03574)
- PromptShield argues that AUC alone hides differences in the low-FPR regime. It reports that PromptGuard reaches AUC 0.874 on its benchmark. — [PromptShield](https://arxiv.org/pdf/2501.15145)

### Inferences
- The fixed 0.5 policy answers "what happens if you deploy with defaults". That question is legitimate, but it mixes classifier quality with calibration. Report alongside it: (a) AUROC/AUPRC for every system that exposes a score, (b) TPR at a fixed FPR (1% and/or 5%) on the benign set, and (c) the oracle-best threshold on a separate tuning split, labelled as an upper bound. Systems that only return a flag get a single ROC point, and the board should say so.
- A twin-pair hard set is well suited to a fixed-FPR view, because the benign twins give a matched estimate of the false-positive rate.
- Balanced accuracy at a fixed threshold is equivalent to (TPR + TNR)/2 at one ROC point. Plotting every system's operating point on a shared ROC/PR plane shows both calibration and discrimination in one figure.

### Gaps
- I found no guardrail benchmark that formally justifies a fixed 0.5 across heterogeneous systems. Most use vendor defaults or report AUPRC.
- I did not verify how HELM handles thresholds or calibration for classifier-style scenarios (HELM does report calibration metrics such as ECE; UNVERIFIED).

## Statistical reporting: CIs, paired tests, multiple comparisons, rank uncertainty, sample sizes

### Takeaway
Current best practice is per-item scores, clustered/grouped standard errors, paired differences, power analysis before building a set, and rank intervals or "set of plausible winners" in place of a single rank. raxIT's paired bootstrap with group resampling and Holm tiers matches this. The remaining gaps are small-n intervals per category and a family-wise "who could be best" set.

### Cited Findings
- Miller, "Adding Error Bars to Evals" (Anthropic, arXiv 2411.00640) treats eval questions as draws from a super-population and gives formulas for single-model and two-model analysis and for planning experiments. — [arXiv](https://arxiv.org/abs/2411.00640)
- Anthropic's five recommendations: (1) report SEM and a 95% CI; (2) cluster standard errors on the unit of randomisation, since clustered SEs on popular evals were over 3x the naive ones; (3) reduce within-question variance by resampling or by using next-token probabilities; (4) analyse paired differences, since frontier models' question-level scores correlate at 0.3–0.7, which shrinks the SE of the difference, and report the mean difference, SE, CI and correlation; (5) run a power analysis, with 3 percentage points as the example effect size. — [Anthropic research post](https://www.anthropic.com/research/statistical-approach-to-model-evals)
- Worked example: at 50% accuracy on 164 HumanEval items, an unpaired comparison needs a gap of about 11 points for p<0.05, versus about 8 points when paired. — [search summary citing Miller-style analysis; arXiv 2512.21326 "Measuring all the noises of LLM Evals"](https://arxiv.org/pdf/2512.21326) (attribution of the exact numbers to that paper is UNVERIFIED)
- Bowyer, Aitchison & Ivanova (ICML 2025 position paper): CLT-based error bars "usually dramatically underestimat[e] uncertainty" with fewer than a few hundred datapoints. They collapse to zero width at accuracy 0 or 1 and can leave [0,1]. The authors compare Wilson score, Clopper-Pearson and Bayesian alternatives. — [arXiv 2503.01747](https://arxiv.org/pdf/2503.01747); [PMLR](https://proceedings.mlr.press/v267/bowyer25a.html)
- Chatbot Arena estimates Bradley-Terry coefficients with CIs from a pivot bootstrap and from sandwich robust SEs. — [Chiang et al. 2024](https://arxiv.org/pdf/2403.04132)
- LMArena reports a "rank spread". The worst rank is 1 + the number of models whose upper CI endpoint exceeds this model's lower CI endpoint, and the best rank uses the mirror comparison. — [LMArena ranking method](https://news.lmarena.ai/ranking-method)
- "The Leaderboard Lottery" (ICML 2026, S. V. Jain): on data calibrated to Open LLM Leaderboard v2, the reported winner is the true best only 0–58% of the time under prompt resampling, and 95% sets of plausible winners contain 8–35 models. The paper proposes a paired-bootstrap Multiple Comparisons with the Best (MCB) that returns a confidence set of plausible winners with family-wise error control, needs only per-prompt scores, and restores ≥95% coverage. — [ICML 2026](https://icml.cc/virtual/2026/80012)
- Dropping a handful of preferences can change the top LLM rankings on Arena-style boards, and bootstrap ranks should be read as sets of statistically inseparable models. — [arXiv 2508.11847](https://arxiv.org/pdf/2508.11847)
- tinyBenchmarks (IRT): 100 curated examples per scenario estimate LLM performance within about 2% average error. That is evidence about the n needed for an aggregate score, not for a pairwise difference. — [tinyBenchmarks](https://arxiv.org/html/2402.14992v2)
- The Artificial Analysis guardrail benchmark reports no CIs, significance tests or repeated runs. — [Artificial Analysis](https://artificialanalysis.ai/articles/guardrail-safety-benchmark)

### Inferences
- For edition 3, cluster on the pair: resample twin pairs, not rows, because the attack and benign twin are not independent. This mirrors Miller's "cluster on the unit of randomisation".
- Per-category cells will often have n<200 on 1,200 pairs. Use Wilson or Clopper-Pearson (or Beta-posterior) intervals there, not normal-approximation intervals. Before release, run a power analysis on the smallest category to report the minimum detectable difference.
- Holm-adjusted tiers control FWER for pairwise claims. Consider adding an LMArena-style rank spread or an MCB "plausible best" set, which answer the reader's question ("who's best?") more directly.

### Gaps
- I did not fetch HELM's statistical reporting, or a paper titled "Benchmarks are not leaderboards". I could not confirm that such a paper exists under that exact title (UNVERIFIED).
- I did not fetch Bowyer et al.'s exact recommended method list.

## Contamination: canaries, private held-out sets, detection, API exposure

### Takeaway
Canaries help, but the evidence shows they leak: models reproduce the BIG-bench canary, and GPT-4's report admitted BIG-bench contamination. Serious boards add private or semi-private splits and rotation, and they acknowledge that sending held-out rows to hosted APIs is itself a leakage channel. ARC Prize names a "semi-private" tier explicitly for that reason. Scale SEAL restricts entries from developers who may have seen prompts via API logging.

### Cited Findings
- The GPT-4 report disclosed that BIG-bench had contaminated its training data and excluded it as an evaluation. — [LessWrong post](https://www.lesswrong.com/posts/kSmHMoaLKGcGgyWzs/big-bench-canary-contamination-in-gpt-4)
- The non-public GPT-4-base model reproduced the BIG-bench canary string and had memorised several tasks. Claude 3.5 Sonnet was also reported to reproduce it. A commenter could not replicate on GPT-4o or Llama-3 70B. These are informal forum reports, not peer-reviewed. — [Alignment Forum](https://alignmentforum.org/posts/kSmHMoaLKGcGgyWzs/big-bench-canary-contamination-in-gpt-4)
- A canary also lets you probe for training exposure by checking whether a model assigns anomalous probability to the string. — [Can we trust the evaluation on ChatGPT?](https://arxiv.org/pdf/2303.12767)
- ARC Prize 2024 verified submissions on a 100-task "semi-private" set rather than the private set, "due to the risk of data leakage". It flagged overfitting when the semi-private and public scores differed by more than 10 points, and it reports SOTA only on semi-private and private sets. — [ARC Prize 2024 Technical Report](https://arxiv.org/pdf/2412.04604)
- ARC-AGI-2 describes its semi-private tasks as not publicly released but "exposed to commercial APIs and thus carry some risk of leakage". ARC-AGI-3 describes its semi-private set as a holdout "used to test models behind an external API". — [ARC-AGI-2](https://arxiv.org/pdf/2505.11831); [ARC-AGI-3](https://arxiv.org/pdf/2603.24621)
- The ARC Kaggle competitions run with no internet access, to prevent leakage. Public standings use the semi-private set and winners are decided on the private set. — [ARC Prize 2025 report](https://arxiv.org/pdf/2601.10904); [ARC-AGI-2 2026 competition](https://newhotness.arcprize.org/competitions/2026/arc-agi-2)
- Scale SEAL: datasets "will remain private and unpublished". Scale limits entries from developers "who may have seen the specific prompt sets via API logging" and aims to refresh "multiple times a year". — [Scale blog](https://scale.com/blog/leaderboard); [methodology](https://scale.com/leaderboard/methodology)
- Critique: private evaluation by data curators carries a conflict of interest, since the same companies sell training data. Private benchmarks also lack transparency. — [Peeking Behind Closed Doors, arXiv 2503.04756](https://arxiv.org/pdf/2503.04756); [DeepLearning.AI](https://charonhub.deeplearning.ai/private-benchmarks-for-fairer-tests/)
- Scale's GSM1k showed several models overfitting to GSM8k, an example of detecting contamination with a fresh parallel set. — [DeepLearning.AI](https://charonhub.deeplearning.ai/private-benchmarks-for-fairer-tests/)
- LiveBench adds and updates questions monthly from recent sources such as competitions, arXiv, news and IMDb synopses, and scores automatically. A secondary summary says about one-sixth of questions are replaced each month and new questions are withheld for a month (UNVERIFIED against primary). — [LiveBench arXiv](https://arxiv.org/abs/2406.19314v1); [AlphaXiv overview](https://alphaxiv.org/overview/2406.19314v2)
- Kaggle splits its leaderboard into public and private parts, with final ranking on the private part, to prevent overfitting to the public LB (UNVERIFIED; standard Kaggle practice, not fetched).

### Inferences
- raxIT's held-back 60% will be exposed to every hosted API system on every run. In ARC's terms that makes it "semi-private", not private. Options: (a) label it semi-private publicly; (b) keep a small truly-private slice that runs only on open-weight models on raxIT's own GPU VM; (c) use provider zero-data-retention or no-training settings where available, and document which ones; (d) track the gap between the public split and the held-back split per system as a leakage and overfitting signal, as ARC does with its 10-point check.
- The canary GUID is worth keeping for transparency. Given the BIG-bench evidence, though, rotation is the real defence, so don't treat the canary as one.

### Gaps
- I found no published guardrail-specific benchmark policy on API exposure of held-out rows.
- I did not verify whether OpenAI, Anthropic or Google moderation endpoints log or train on inputs by default.

## Benchmark saturation and lifecycle

### Takeaway
Benchmarks now reach human-level within a few years. Responses include dynamic adversarial collection (Dynabench), periodic rotation (LiveBench, SEAL), IRT to find non-discriminating items, and harder successor sets.

### Cited Findings
- Dynabench: benchmarks once took decades to surpass human estimates, and newer ones do so "within just a few years". Its Figure 1 normalises baseline = −1 and human = 0. The proposed remedy is dynamic human-and-model-in-the-loop adversarial data collection. — [Dynabench](https://arxiv.org/pdf/2104.14337)
- Contextual AI later called that saturation plot "hopelessly outdated" and HellaSwag "basically solved". — [Contextual AI](https://contextual.ai/blog/plotting-progress-in-ai)
- IRT has been used to study saturation (un-discriminability) of benchmarks. tinyBenchmarks uses IRT to choose informative items. — [tinyBenchmarks](https://arxiv.org/html/2402.14992v2)
- ARC Prize uses public/semi-private/private tiers plus new versions (ARC-AGI-2, ARC-AGI-3) as its lifecycle. — [ARC-AGI-2](https://arxiv.org/pdf/2505.11831); [ARC-AGI-3](https://arxiv.org/pdf/2603.24621)

### Inferences
- raxIT's edition 3 pilot finding ("harmless attacks too easy, benign twins carry the signal") is a saturation diagnosis. Fitting a 2-parameter IRT model on the 20 systems' per-row outcomes would flag items with low discrimination for retirement at each rotation.
- Twenty systems is few for stable IRT fits. Use discrimination as a screening signal, not a hard rule.

### Gaps
- I did not fetch AdvGLUE or a source for the "benchmark half-life" term, and found no citable definition of it.

## Label quality: agreement norms, adjudication, contested items, label-error studies

### Takeaway
Test-set label error is common (≥3.3% on average in 10 major benchmarks) and can flip rankings. Safety datasets report only moderate agreement (WildGuardMix Fleiss κ 0.50–0.72). Krippendorff's conventional bar is α ≥ 0.80, with 0.667 as the floor for tentative conclusions.

### Cited Findings
- Northcutt, Athalye & Mueller (NeurIPS 2021 D&B): test sets of 10 common CV/NLP/audio datasets average at least 3.3% label errors, and ImageNet val has at least 6%. Confident learning flagged candidates, and humans confirmed about 51% of them (54% in the NeurIPS version). ResNet-18 outranks ResNet-50 if mislabeled-example prevalence rises by just 6%. — [arXiv 2103.14749](https://arxiv.org/pdf/2103.14749); [NeurIPS](https://neurips.cc/virtual/2021/22763)
- WildGuardMix: three annotators per item, with 92% / 82% / 95% item agreement on prompt harm, response harm and refusal. Fleiss κ was 0.55, 0.72 and 0.50 (the mapping of κ values to tasks is inferred, UNVERIFIED). 500 items were re-annotated as an audit. — [WildGuardMix README](https://huggingface.co/datasets/allenai/wildguardmix/blob/main/README.md)
- Aegis 2.0 annotators worked in Label Studio without seeing peers' work (blind), and volunteered based on skill and willingness to view toxic content. Agreement figures were not found in the search results. — [Aegis 2.0](https://arxiv.org/pdf/2501.09004)
- Krippendorff's α: rely on data with α ≥ 0.800, treat 0.667–0.800 as tentative conclusions only, and set the bar higher when errors are costly. — [Wikipedia](https://en.wikipedia.org/wiki/Krippendorff%27s_alpha) (secondary; the original source is Krippendorff's *Content Analysis*)

### Inferences
- Two blind labellers plus α is in line with practice. Pre-register an α target (≥0.80 overall, reported per category). Use a third adjudicator for disagreements, and either drop contested pairs from the scored set or publish them as a separate "contested" slice rather than forcing a label.
- Run confident-learning style flagging (cleanlab) using the 20 systems' outputs as the "model" signal. Rows that most systems "get wrong" with high confidence are candidates for label review before release.

### Gaps
- I found no published Krippendorff's α for a guardrail benchmark. Aegis agreement figures were not retrieved.

## Paired / minimal-pair evaluation designs

### Takeaway
Contrast sets (Gardner et al. 2020) and XSTest's minimally edited safe/unsafe contrasts are the direct precedent for twin pairs. Both show that minimal edits expose decision-boundary failures that standard test sets miss.

### Cited Findings
- Gardner et al. 2020: experts make small edits to test instances, usually changing the gold label, to probe local decision boundaries. Across 10 NLP datasets, performance fell by up to 25% versus the original test sets. — [arXiv 2004.02709](https://arxiv.org/abs/2004.02709)
- The "contrast consistency" metric (a model must get every element of a contrast set right) was not confirmed from the fetched abstract (UNVERIFIED; recalled from the paper body).
- XSTest has 250 safe prompts across 10 types and 200 unsafe contrasts built by minimal edits ("kill a Python process" vs "kill a person"), explicitly citing Gardner et al. Without the contrasts, a model that complies with everything would score perfectly on the safe prompts. — [XSTest](https://arxiv.org/pdf/2308.01263)

### Inferences
- Pair-level metrics to report: pair accuracy (both twins right), "flip rate" (attack blocked and benign twin also blocked, which measures over-blocking of surface features), and the reverse (both allowed). Bootstrap over pairs.

### Gaps
- No guardrail paper I found reports a pair-level metric with CIs.

## Cost and latency reporting norms

### Takeaway
Reporting norms are thin. Artificial Analysis gives the most explicit latency protocol (sequential requests, warmup discarded, mean and p95, named hardware) but no cost method. Model cards give single-number latency with hardware and sequence length.

### Cited Findings
- Artificial Analysis: end-to-end time per request, measured one at a time, with 20 warmup requests discarded. 450 measured requests per model (150 per dataset), stratified by label and prompt length. It reports average and p95 latency plus output tokens, but not p50. Self-hosted models run on vLLM/SGLang on B200-class nodes, while omni-moderation is measured on OpenAI's hosted endpoint. No cost methodology is given. — [Artificial Analysis](https://artificialanalysis.ai/articles/guardrail-safety-benchmark)
- Prompt Guard 2 states latency with hardware and input length: 92.4 ms (86M) and 19.3 ms (22M) on an A100 at 512 tokens. — [model card](https://huggingface.co/project-free-llama/Llama-Prompt-Guard-2-86M); [LlamaFirewall](https://arxiv.org/pdf/2505.03574)

### Inferences
- A defensible norm for raxIT: cost per 1k requests at a stated token-length distribution, with list price and date. Report p50/p95/p99 latency, concurrency, region, hardware (GPU type, serving stack) and warmup policy. Separate network RTT for hosted APIs where possible.

### Gaps
- I found no standards body or NeurIPS D&B guidance specific to cost/latency reporting for classifiers. I did not fetch the NeurIPS D&B checklist.
