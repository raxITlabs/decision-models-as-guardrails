# How content-safety guard models and safety classifiers are benchmarked

Scope: GuardBench, WildGuardTest/Mix, Aegis 1.0/2.0, HarmBench, JailbreakBench, OR-Bench, XSTest, BeaverTails, SORRY-Bench, and the evaluation sections of Llama Guard 3/4, ShieldGemma, WildGuard, Qwen3Guard, Granite Guardian, NemoGuard, gpt-oss-safeguard, DynaGuard, GuardReasoner, PolyGuard, plus "Policy Is Not Capability" (arXiv 2610.25060). Researched 2026-10-24. Figures come from the primary paper or model card unless marked **[unverified]**.

## Dataset construction, labels, and inter-annotator agreement

### Takeaway
The human-labelled test sets that guard papers keep reusing (WildGuardTest, Aegis, BeaverTails, XSTest) report only moderate agreement on harmfulness: Fleiss κ 0.50–0.55 for WildGuardTest's harm tasks, about 74% raw agreement for Aegis, and 81.7% for BeaverTails. That means a meaningful share of "errors" against gold labels are rows where trained humans also disagree. The over-refusal sets differ in kind. XSTest is small and hand-written with very high agreement (κ ≈ 0.9). OR-Bench is large and LLM-generated, and its "safe" labels come from an LLM-ensemble vote.

### Cited Findings
**GuardBench (Bassani & Sanchez, EMNLP 2024)**
- 40 datasets: 35 English datasets from prior work, a new UnsafeQA set (22,180 single-turn QA items, auto-labelled), and four machine-translated prompt sets (DE, FR, IT, ES) — [GuardBench paper, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.1022.pdf); [GitHub](https://github.com/AmenRa/GuardBench)
- Inclusion criteria: user–AI chat or prompt-shaped text; labels that fall within generally acknowledged harm categories; public data on GitHub or HF; permissive licence; English only at first — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- Exclusions: social-media moderation datasets, multiple-choice and completion sets, datasets labelled by automated tools (Perspective API, OpenAI Moderation API, e.g. RealToxicityPrompts, LMSYS-Chat-1M), and jailbreak/adversarial sets. Unsafe prompts *inside* jailbreak sets were kept without the jailbreak wrapper — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- Table 1 records per dataset whether labels are Manual or Auto, the unsafe share, and the source. Examples: BeaverTails 330k (11,088 test rows, 55% unsafe, manual); DICES 350 (50%); ConvAbuse (853 rows, 15%); HarmfulQA (16,459 rows, 45%, auto/LLM) — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- Translations: 31k prompts translated with MADLAD-400-3B-MT. Native speakers rated about 100 prompts per language on a 5-point Likert scale, and the average was above 4 — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)

**WildGuardMix / WildGuardTest (Han et al., 2024)**
- WildGuardMix has 92K labelled items. WildGuardTrain has 86,759 (48,783 prompt-only and 37,976 prompt+response). WildGuardTest has 5,299 human-annotated items built from a 1,725-pair test split — [WildGuard arXiv 2406.18495](https://arxiv.org/html/2406.18495)
- Sources: synthetic vanilla and adversarial prompts (WildTeaming, 2–7 in-the-wild tactics per prompt), in-the-wild LMSYS-Chat-1M and WildChat, and annotator-written HH-RLHF, Anthropic red-team, AegisSafetyTrain, and Safety-Tuned Llamas — [WildGuard](https://arxiv.org/html/2406.18495)
- Three annotators per item. Fleiss κ was 0.55 for prompt harm, 0.72 for refusal, and 0.50 for response harm. Gold is the majority vote; items without at least 2-way agreement were dropped, and an "unsure" option existed — [WildGuard](https://arxiv.org/html/2406.18495)
- GPT-4 training labels were audited on 500 items: 92% agreement for prompt harm, 82% for response harm, 95% for refusal — [WildGuard](https://arxiv.org/html/2406.18495)
- The paper also released XSTest-Resp: 446 response-harm items (368 harmful, 78 benign) and 449 refusal items — [WildGuard](https://arxiv.org/html/2406.18495)

**Aegis 1.0 (Ghosh et al., 2024)**
- About 26k interactions (26,541 collected) from HH-RLHF harmless prompts, with Mistral responses. About 12 annotators worked concurrently, each item got ≥3 annotations (86,736 total), and raw agreement was "approximately 74%" — [Aegis 1.0 arXiv 2404.05993](https://arxiv.org/html/2404.05993)
- The taxonomy has 13 core categories in the intro, but §8.6 says "14 explicit categories" plus "Other", so the count is inconsistent in the rendered paper — [Aegis 1.0](https://arxiv.org/html/2404.05993)
- A "Needs Caution" label (3,461 instances) is mapped to unsafe by the Defensive model and to safe by the Permissive model. Test set: 1,199 rows (639 unsafe, 412 safe, 148 Needs Caution) — [Aegis 1.0](https://arxiv.org/html/2404.05993)

**Aegis 2.0 (Ghosh et al., 2025)**
- 12 core categories and 9 fine-grained risks. 34,248 samples: 16,880 prompts and 17,368 prompt-response pairs, of which 5,200 are synthetic refusals from Gemma-2-27B. Prompts come from HH-RLHF, DAN, AART, and Do-Not-Answer; responses from Mistral-7B-v0.1 — [Aegis 2.0 arXiv 2501.09004](https://arxiv.org/html/2501.09004)
- 12 annotators, ≥3 annotations per item, raw agreement about 74%, and a 10–15% QA audit per chunk. An LLM jury (Mixtral-8x22B, Mistral-NeMo, Gemma-2-27B) labels responses only when the human conversation-level vote is unsafe. Test split: 1,984 rows, stratified — [Aegis 2.0](https://arxiv.org/html/2501.09004)

**BeaverTails (Ji et al., 2023)**
- 333,963 QA pairs (99,734 unique; 16,851 unique prompts) in the 330k set. The 30k set has 30,207 pairs and 7,774 prompts. There are 14 harm categories — [BeaverTails arXiv 2307.04657](https://arxiv.org/html/2307.04657)
- The label unit is the QA pair: a pair is harmless only if it is "risk-neutral across all 14 harm categories". This is a judgement of the interaction, not the toxicity of one utterance — [BeaverTails](https://arxiv.org/html/2307.04657)
- About 70 crowdworkers; 3.34 annotations per pair on average for 330k, one per pair for 30k. Safety meta-label agreement was 81.68%. The split is 9:1 train:test — [BeaverTails](https://arxiv.org/html/2307.04657)

**XSTest (Röttger et al., 2023/NAACL 2024)**
- 250 hand-written safe prompts (10 types × 25: homonyms, figurative language, safe targets, safe contexts, definitions, real discrimination/nonsense group, nonsense discrimination/real group, historical events, privacy-public, privacy-fictional), plus 200 unsafe contrast prompts that are minimal edits of safe ones. One passage in §4.3 says "200 safe prompts", which conflicts with 250 — [XSTest arXiv 2308.01263](https://arxiv.org/html/2308.01263)
- Responses are labelled full compliance, full refusal, or partial refusal. Agreement was 93.8–98.4% (Fleiss κ 0.89–0.97) across five models — [XSTest](https://arxiv.org/html/2308.01263)

**OR-Bench (Cui et al., 2024; ICML 2025 [venue unverified])**
- Pipeline: Mixtral-8x7B writes toxic seeds and rewrites each into 5 "seemingly toxic" prompts. An ensemble of GPT-4-turbo, Llama-3-70b, and Gemini-1.5-pro moderates them, and only prompts judged safe by majority vote are kept — [OR-Bench arXiv 2405.20947](https://arxiv.org/html/2405.20947)
- Sizes: OR-Bench-80K; OR-Bench-Hard-1K (prompts rejected by ≥3 large models, so selection is adversarial to LLM refusal); OR-Bench-Toxic (600); 10 categories — [OR-Bench](https://arxiv.org/html/2405.20947)
- Validation: on the paper's table, a human expert scored 94.0 and the ensemble moderator 93.0 — [OR-Bench](https://arxiv.org/html/2405.20947)

**HarmBench (Mazeika et al., 2024)**
- 510 behaviours (400 text, 110 multimodal). Functional types: standard 200, copyright 100, contextual 100, multimodal 110. Seven semantic categories — [HarmBench arXiv 2402.04249](https://arxiv.org/html/2402.04249)

**JailbreakBench (Chao et al., 2024)**
- JBB-Behaviors: 100 harmful behaviours in 10 categories aligned to OpenAI usage policies (18% AdvBench, 27% TDC/HarmBench, 55% original), plus 100 topic-matched benign behaviours for over-refusal — [JailbreakBench arXiv 2404.01318](https://arxiv.org/html/2404.01318)

**SORRY-Bench (Xie et al., 2024)**
- 44 fine-grained categories × 10 = 440 base unsafe instructions. 20 linguistic mutations add 8.8K more; five are languages (Malayalam, Tamil, Marathi, Chinese, French). 7,040 human judgements — [SORRY-Bench arXiv 2406.14598](https://arxiv.org/html/2406.14598)

**DynaBench (DynaGuard, 2025)**
- Train: 61.5k synthetic multi-turn dialogues with GPT-4o labels, using about 500 hand-written seed rules expanded to about 5,000 and combined into 40,000 policies. Test: 543 handcrafted examples, with a median of 10 rules per policy and 3 turns — [DynaGuard arXiv 2509.02563](https://arxiv.org/html/2509.02563)
- Audit: 743 training samples were reviewed by 3 annotators; Cohen's κ against the labels was 0.85 — [DynaGuard](https://arxiv.org/html/2509.02563)

**PolyGuard (2025)**
- PolyGuardPrompts test set: 29K items in 17 languages, all machine-translated from the WildGuardMix test split. Labels come from Llama-Guard-3-8B and GPT-4o, with Llama-3.1-405B resolving conflicts, and are propagated across languages. Human check: 50 items per language. Inter-annotator Krippendorff α on safety labels was **0.46** — [PolyGuard arXiv 2504.04377](https://arxiv.org/html/2504.04377)

### Inferences
- With κ around 0.5 on WildGuardTest's harm tasks and 74% raw agreement on Aegis, the noise ceiling on those rows is well below 100%. Rank differences of a point or two on those subsets are likely within label noise. This supports raxIT's use of bootstrap CIs and tiers rather than point ranks.
- OR-Bench's "benign" label is itself an LLM-majority judgement. When a guard "over-blocks" an OR-Bench-Hard row, it is partly disagreeing with GPT-4/Llama-3-70B/Gemini rather than with humans. XSTest is the cleaner human-labelled over-refusal anchor, but it is tiny (250 safe items).

### Gaps
- Agreement statistics for the ToxicChat and OpenAI Moderation datasets were not checked in this pass.
- The OR-Bench venue (ICML 2025) is from memory and unverified.

## Metrics, threshold choice, and calibration

### Takeaway
F1 with harmful as the positive class is close to universal, and most papers state no threshold, so the decoded "unsafe" token is the decision in practice. The exceptions differ. Llama Guard 3 and ShieldGemma add AUPRC. ShieldGemma reports "optimal F1", an oracle threshold. Qwen3Guard picks the best strict/loose mode per benchmark. Granite Guardian states 0.5 and adds recall at fixed FPR. GuardBench deliberately rejects AUPRC. None of the sources reviewed reports calibration (ECE or similar) or confidence intervals, except that gpt-oss-safeguard mentions a non-significant difference in passing.

### Cited Findings
- **GuardBench** uses F1, or Recall when a dataset has only unsafe rows. It explicitly does not use AUPRC because "it overemphasizes models' Precision at the expense of Recall in the case of binary classification", and because F1/Recall don't need probabilities, which makes closed-weight models comparable. Scores come from scikit-learn. No significance testing appears in the paper — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- The GuardBench library (as of an Oct 2025 update) supports precision, recall, F1, MCC, AUPRC, sensitivity, specificity, G-mean, FPR, and FNR. Default metrics are F1 and recall. `moderate()` returns unsafe probabilities — [GuardBench GitHub](https://github.com/AmenRa/GuardBench)
- **WildGuard** uses F1 for all three tasks, with no threshold stated — [WildGuard](https://arxiv.org/html/2406.18495)
- **GuardReasoner** uses F1 with harmful/refusal positive, and a *sample-weighted* average of F1 across 13 benchmarks (sizes 0.1K–3K). No threshold. Rows that closed APIs refuse to classify are counted as harmful/refused "for the fairness" (GPT-4o rejected 36.81%, Claude 3.5 Sonnet 45.92%) — [GuardReasoner arXiv 2501.18492](https://arxiv.org/html/2501.18492)
- **Llama Guard 3** reports F1, AUPRC, and FPR. The unsafe probability is the first-token probability, and "we can then apply score thresholding". No threshold value is published. English internal set: LG3 F1 0.939, AUPRC 0.985, FPR 0.040; LG2 0.877 / 0.927 / 0.081; GPT-4 0.805 / N/A / 0.152 — [Llama Guard 3 model card](https://huggingface.co/meta-llama/Llama-Guard-3-8B)
- **Llama Guard 4** reports Recall, FPR, and F1 (no AUPRC). English: R 69%, FPR 11%, F1 61%. Multilingual average over 7 languages: R 43%, FPR 3%, F1 51%. No threshold stated — [Llama Guard 4 model card](https://huggingface.co/meta-llama/Llama-Guard-4-12B)
- **ShieldGemma** reports "Optimal F1" and AU-PRC. The paper does not say how the optimal threshold is chosen or whether it is per dataset. Baseline numbers are copied from prior papers, not re-run. Example: SG-9B on OpenAI Mod gets 0.821/0.907 and on ToxicChat 0.694/0.782 — [ShieldGemma arXiv 2407.21772](https://arxiv.org/html/2407.21772)
- **Granite Guardian** reports AUC, AUPRC, F1, recall, and precision. P/R/F1 use **threshold 0.5**. The appendix gives recall and AUC at fixed FPR of 0.1, 0.01, and 0.001. Aggregate harm for 8B: AUC 0.871, AUPRC 0.846, F1 0.758 — [Granite Guardian arXiv 2412.07724](https://arxiv.org/html/2412.07724)
- **Qwen3Guard** uses F1. The tri-class output maps to binary in two ways: strict (controversial = unsafe) or loose (controversial = safe). Table averages use "the optimal mode per benchmark", which amounts to choosing the operating point per dataset after seeing results — [Qwen3Guard arXiv 2510.14276](https://arxiv.org/html/2510.14276)
- **gpt-oss-safeguard** uses an internal "multi-policy accuracy" in which an item counts only if all policies are labelled correctly: 120b 46.3%, 20b 43.6%, internal Safety Reasoner 52.2%, gpt-5-thinking 43.2%. It also reports F1 on OpenAI Mod 2022 (120b 82.9%) and ToxicChat (120b 79.3%). It notes one difference "is not statistically significant" without giving the method — [gpt-oss-safeguard technical report, 2025-10-29](https://cdn.openai.com/pdf/08b7dee4-8bc6-4955-a219-7793fb69090c/Technical_report__Research_Preview_of_gpt_oss_safeguard.pdf)
- **DynaGuard** uses F1, with no threshold stated — [DynaGuard](https://arxiv.org/html/2509.02563)
- **PolyGuard** uses F1 for binary tasks and Exact Match/Jaccard for categories — [PolyGuard](https://arxiv.org/html/2504.04377)
- **Aegis 1.0** uses AUPRC and F1. Aegis 2.0 uses harmfulness F1, the mean over 3 seeds — [Aegis 1.0](https://arxiv.org/html/2404.05993); [Aegis 2.0](https://arxiv.org/html/2501.09004)
- **OR-Bench** metrics: rejection rate on seemingly-toxic prompts and acceptance rate on toxic prompts. Refusal is judged by keyword matching on 80K and by GPT-4 on Hard-1K/Toxic. Across 32 models, the Spearman correlation between safe-prompt and toxic-prompt rejection is 0.89 — [OR-Bench](https://arxiv.org/html/2405.20947)
- **XSTest** reports full and partial refusal rates on safe vs unsafe prompts. String-match and GPT-4 classifiers recover the manual rankings but miss partial refusals — [XSTest](https://arxiv.org/html/2308.01263)
- **"Policy Is Not Capability"** reports catch rate (harmful flagged) and over-refusal rate (benign flagged) separately, plus a "seed floor" (spread across seeds) against the "label-supervision range" (spread across training arms). Its shipped model at deployment threshold has precision 0.968 and recall 0.496 — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)

### Inferences
- raxIT's fixed 0.5 threshold with balanced accuracy is closest to Granite Guardian's 0.5 convention, and stricter than ShieldGemma's optimal F1 or Qwen3Guard's per-benchmark mode choice. Both of those report oracle operating points, which inflates them relative to a fixed-threshold board. This is worth stating when comparing to vendor-reported numbers.
- Balanced accuracy (the mean of TPR and TNR) is uncommon in this literature. F1 ignores true negatives, so on harmful-heavy sets it hides over-blocking, which is exactly where raxIT finds headroom (OR-Bench/XSTest). Granite's recall at fixed FPR and Llama Guard's FPR column are the nearest precedents for exposing over-blocking.
- No source reviewed reports bootstrap CIs, paired tests, or multiple-comparison correction across a leaderboard. raxIT's paired bootstrap with Holm tiers appears to be unusual in this space (based on this sample, not an exhaustive survey).

### Gaps
- WildGuard's and Llama Guard's default decision rule is generation of the "unsafe"/"yes" token, which is equivalent to argmax, not an explicit 0.5. This was not verified line by line in either paper.
- No source found reported calibration metrics (ECE, reliability diagrams) for any guard model.
- How ShieldGemma picks the "optimal F1" threshold (per dataset or global) is not stated in the paper.

## Handling taxonomy mismatch between a guard's policy and the dataset's labels

### Takeaway
Most benchmarks collapse everything to binary safe/unsafe and accept that a guard trained on a different policy will be penalised. GuardBench says this outright, and WildGuard concedes that other-taxonomy models "might demonstrate lower performance". Model cards avoid the problem by evaluating on internal sets aligned with their own policy (Llama Guard 3/4) or by choosing a policy prompt or binary mode per dataset (ShieldGemma, Qwen3Guard, Granite). The 2025–26 work makes the mismatch the main finding. GuardBench shows that swapping the policy prompt alone lifts Mistral-7B to state of the art on several datasets. "Policy Is Not Capability" shows that 10 training arms of the same architecture spread 23× on one benchmark purely by labelling policy.

### Cited Findings
- **GuardBench** collapses labels to binary because there is "lack of a generally accepted taxonomy of unsafe content" and the authors "are unable to map the unsafe content categories of every dataset to a reference taxonomy". Some datasets are unsafe by construction — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- **GuardBench RQ4**: Mistral-7B-Instruct prompted with MD-Judge's moderation policy ("Mis+") shows "a very significant performance uplift, often outperforming MD-Judge and even reaching state-of-the-art results on multiple datasets". The authors conclude that moderation policies "significantly impact the effectiveness of guardrails models" — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- **WildGuard** says its harm definitions "may differ from the categories that others may prefer", and models built on other taxonomies "might demonstrate lower performance when evaluated on WildGuardTest" — [WildGuard](https://arxiv.org/html/2406.18495)
- **Llama Guard 3** says comparison is hard because "each model is built on its own policy". It aligned to MLCommons hazards to drive standard adoption and evaluated on internal MLCommons-labelled sets plus XSTest — [Llama Guard 3 card](https://huggingface.co/meta-llama/Llama-Guard-3-8B)
- **Llama Guard 4** omits competitor models because they are "typically not aligned with the specific safety policy" it was trained on — [Llama Guard 4 card](https://huggingface.co/meta-llama/Llama-Guard-4-12B)
- **ShieldGemma**: on OpenAI Mod it used OpenAI's own harm definitions as the policy and then aggregated to binary. On ToxicChat it took the max over its six harm predictions. It calls direct comparison "challenging" because of differing policies, and says its gap over GPT-4 is "expected" since it was trained on data similar to the test sets — [ShieldGemma](https://arxiv.org/html/2407.21772)
- **Granite Guardian**: any row unsafe under the source dataset's taxonomy gets the umbrella harm label. Baselines run as follows: Llama Guard with its default template, ShieldGemma with the "Dangerous Content" policy throughout, Granite with its umbrella harm definition — [Granite Guardian](https://arxiv.org/html/2412.07724)
- **Qwen3Guard** attributes cross-benchmark disagreement to differing risk tolerance: treating controversial as unsafe suits Aegis, and as safe suits OpenAIMod. It handles this through the per-benchmark mode — [Qwen3Guard](https://arxiv.org/html/2510.14276)
- **Aegis 1.0** mapped categories by hand for heatmap comparison (Sexual/minors → Sexual; hate and violence collapsed) because Llama Guard does not separate them — [Aegis 1.0](https://arxiv.org/html/2404.05993)
- **gpt-oss-safeguard**: on OpenAI Mod 2022 it used OpenAI internal policies (one adapted for later changes). On ToxicChat it used "a short hand-written prompt adapted from some of our internal policies". So the policy is written per dataset — [gpt-oss-safeguard report](https://cdn.openai.com/pdf/08b7dee4-8bc6-4955-a219-7793fb69090c/Technical_report__Research_Preview_of_gpt_oss_safeguard.pdf)
- **DynaGuard / DynaBench** make the policy an input; each test item comes with its own rules. On DynaBench, LlamaGuard3 scores 13.1 F1 and WildGuard 20.9, against DynaGuard-8B at 73.1. On the standard safety average they are close (WildGuard 80.0, DynaGuard 81.1). Fixed-taxonomy guards collapse on unseen policies but not on standard harm sets — [DynaGuard](https://arxiv.org/html/2509.02563)
- **NemoGuard 8B content safety** has 23 unsafe categories plus safe and "needs caution", and "Novel safety risk categories and policies can be provided in the instruction" — [NemoGuard model card](https://huggingface.co/nvidia/llama-3.1-nemoguard-8b-content-safety)
- **"Policy Is Not Capability"** (Jebraeeli et al., Lenovo; arXiv 2610.25060, 18 Oct 2026; header ties it to the NeurIPS 2026 "Trust-AI-Eval" (TAE) workshop, poster status per search snippet **[venue unverified beyond arXiv header]**):
  - About 53k prompts labelled under two policies. Policy A is a moderation-product rubric that blocks copyright reproduction, policy-refusal, and edgy-but-harmless prompts. Policy B is an LLM-jury request-intent rubric that treats those as safe. Binary agreement between them is 90.1% — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)
  - Ten ModernBERT training arms (149M and 395M). Across arms, HarmBench-copyright catch rate ranges 0.99 while WildGuard-benign ranges 0.043, which is the 23× spread — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)
  - Validation accuracy correlates ρ = +0.74 with "policy-loaded" benchmarks and ρ = +0.34 with "capability-loaded" ones. HarmBench-copyright vs OR-Bench-hard Spearman is −0.868 (149M) and −0.745 (395M) — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)
  - Cross-lab: Granite Guardian scores 0 and Qwen3Guard-4B scores 99 on the same 75 HarmBench-copyright prompts — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)
  - Mapping alone (counting boundary_safe as unsafe) swings over-refusal from 5.7% to 96.0% — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)
  - Recommendations: print train–test overlap ("Assume overlap until measured"), report a seed floor from three seeds of more than one recipe, and state the labelling policy and quoted split — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)

### Inferences
- raxIT's content-request headroom sits mostly in over-blocking on OR-Bench and XSTest rows. This is the "policy-loaded" region that 2610.25060 identifies: OR-Bench-hard is anti-correlated with HarmBench-copyright across policies. A guard that over-blocks OR-Bench may simply be trained on a broader policy, not be less capable. Reporting these rows as a separate over-refusal axis, as 2610.25060 and Llama Guard's FPR column do, would make this visible instead of folding it into one balanced-accuracy number.
- Category-level policy mismatches can be extreme (Granite 0 vs Qwen3Guard 99 on copyright). Per-source-dataset breakdowns are needed for honest headline ranks.

### Gaps
- No benchmark found that publishes a formal, per-dataset mapping from each guard's taxonomy to each dataset's label scheme, beyond Aegis 1.0's ad hoc heatmap mapping.

## Contamination, held-out/private sets, and training-set overlap

### Takeaway
Overlap disclosure is weak across the field. Several guard models train on the train splits of the very benchmarks they report: WildGuardTrain→WildGuardTest, Aegis train→Aegis test, BeaverTails train→BeaverTails test, ToxicChat. GuardBench marks such cases with an asterisk, and Granite notes it ignored baseline overlap. Only JailbreakBench and HarmBench have formal protocol-level guards (judge withheld from submissions; validation/test behaviour split). 2610.25060 measured exact-match overlap of 88% for JailbreakBench-benign and 82% for OR-Bench-hard in its training pools.

### Cited Findings
- GuardBench Table 3 marks with * the cases where "a model was trained on the training set of the corresponding dataset", e.g. MD-Judge on BeaverTails 330k (0.887*) and on ToxicChat — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- WildGuard has no explicit decontamination statement against evaluation benchmarks. The only dedup is MinHash on 3-grams at 0.5, applied to generated vanilla prompts. Its training data includes AegisSafetyTrain while it evaluates on AegisSafetyTest — [WildGuard](https://arxiv.org/html/2406.18495)
- GuardReasoner trains on WildGuardTrain (86,759), AegisTrain (10,798), BeaverTailsTrain (27,186), and ToxicChatTrain, and tests on the matching test sets, with no decontamination discussion — [GuardReasoner](https://arxiv.org/html/2501.18492)
- Qwen3Guard has no explicit overlap statement. BeaverTails prompts are both a benchmark and the source of its "Think" test set, and WildJailbreak is both RL training and RL evaluation — [Qwen3Guard](https://arxiv.org/html/2510.14276)
- Granite Guardian results "do not consider train-test overlap for baselines" — [Granite Guardian](https://arxiv.org/html/2412.07724)
- PolyGuard trains on translated WildGuardMix train and tests on translated WildGuardMix test (PolyGuardPrompts) — [PolyGuard](https://arxiv.org/html/2504.04377)
- ShieldGemma concedes it was "trained on datasets similar to the test datasets" — [ShieldGemma](https://arxiv.org/html/2407.21772)
- **JailbreakBench**: the leaderboard judge is Llama-3-70B, chosen from 6 candidates on 300 human-labelled items (3 experts, about 95% agreement). It scored 90.7% agreement, 11.6% FPR, 5.5% FNR; GPT-4 scored 90.3/10.0/9.1 and Llama Guard 72.0/9.0/60.9. Submissions "may not use this judge" to prevent overfitting. A Llama-3-8B refusal judge on the 100 benign behaviours flags models refusing more than 90%. The artifacts repo stores jailbreak strings (PAIR, GCG, JailbreakChat, prompt+RS), and the leaderboard is at jailbreakbench.github.io. No private held-out behaviours were found in the parts of the paper read — [JailbreakBench](https://arxiv.org/html/2404.01318)
- **HarmBench**: 100 validation and 410 test behaviours; attacks and defences must not tune on test or semantically identical behaviours. Classifier: fine-tuned Llama-2-13B (hashing classifier for copyright). Human agreement on validation: HarmBench cls 93.19, GPT-4 88.37, Llama Guard 66.94, AdvBench 69.93. Standardised ASR uses N=512 generated tokens because generation length moves substring ASR by up to 30% — [HarmBench](https://arxiv.org/html/2402.04249)
- **SORRY-Bench** judge selection compared 35 evaluator configs on human labels. It chose fine-tuned Mistral-7B-instruct-v0.2 (81.0% agreement, about 10 s per pass vs about $3 / 20 min for GPT-4o) — [SORRY-Bench](https://arxiv.org/html/2406.14598)
- **DynaBench** says train and test rules are "mutually exclusive" — [DynaGuard](https://arxiv.org/html/2509.02563)
- **OR-Bench** is "designed for ongoing updates to prevent over-fitting". It has no contamination analysis — [OR-Bench](https://arxiv.org/html/2405.20947)
- **2610.25060** exact-match lower bounds in its training pools: JailbreakBench-benign 88.0% (88/100), OR-Bench-hard 82.1% (1,083/1,319), HarmBench-copyright 25.0%, WildGuard-harmful 14.3%, StrongREJECT 12.1%, AdvBench about 2%, OR-Bench-toxic 0%. 69.3% of its own multilingual validation split was verbatim in training. After decontamination only two over-refusal benchmarks remained usable — [arXiv 2610.25060](https://arxiv.org/html/2610.25060)

### Inferences
- OR-Bench-hard and JBB-benign are highly exposed (82–88% overlap in one lab's pools). Guards scoring well on them in raxIT's board may have seen them in training. A training-overlap disclosure column, or a held-back slice (raxIT already keeps one), is the standard 2610.25060 asks for.
- Withholding the judge (JailbreakBench) is the closest analogue to raxIT's held-back slice: the protocol-level defence against benchmark overfitting.

### Gaps
- Llama Guard 3/4, ShieldGemma, and NemoGuard model cards make no training-data overlap statement against public benchmarks; this is absence of evidence in the cards, not a confirmed overlap.
- Whether HarmBench's 410-behaviour test set is still effectively private was not checked; it is public on GitHub [unverified].

## Multilingual, multi-turn, and response (output) moderation coverage

### Takeaway
Response moderation is standard: WildGuardTest, BeaverTails, SafeRLHF, HarmBench-response, XSTest-Resp, and Aegis 2.0 are the usual set. Multilingual evaluation is mostly machine-translated English (GuardBench, PolyGuard, Qwen3Guard's Chinese sets, SORRY-Bench mutations), with light human spot checks. Natively written multilingual sets are rare (RTP-LX is one). Multi-turn is thin: GuardBench's conversational sets (ProsocialDialog, DICES, BAD, ConvAbuse) and DynaBench are the main ones.

### Cited Findings
- GuardBench prompts translated to DE/FR/IT/ES. Llama Guard Defensive/Permissive degrade least: on PromptsEN, LG-D 0.850 F1 vs PromptsDE 0.819. MD-Judge drops more (0.861 → 0.683 DE) — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- GuardBench conversation sets include multi-turn (Bot-Adversarial Dialogue, ConvAbuse, DICES 350/990, HarmfulQA, ProsocialDialog) and single-turn (BeaverTails, UnsafeQA). MD-Judge was best on conversations. ToxiGen HateBERT came close to Llama Guard despite having 70× fewer parameters — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- Qwen3Guard: Chinese via Qwen3-MT translations of ToxicChat, WildGuardTest, XSTest, and BeaverTails, plus in-house PolST (1,412 prompts, 4,038 responses). Multilingual: RTP-LX (10 named languages plus a 30-language "Others" average) and PolyGuard-Prompt/Response. The claim of "119 languages" has no matching 119-language test set. Streaming evaluation includes sentence-level latency annotations (813 response-only, 569 with thinking traces) — [Qwen3Guard](https://arxiv.org/html/2510.14276)
- Llama Guard 3 multilingual internal set covers 7 languages (FR, DE, HI, IT, PT, ES, TH), with F1/FPR reported per language. Llama Guard 4 reports only the 7-language average plus single- and multi-image results — [LG3 card](https://huggingface.co/meta-llama/Llama-Guard-3-8B); [LG4 card](https://huggingface.co/meta-llama/Llama-Guard-4-12B)
- PolyGuard: 17 languages; prompt harm, response harm, and refusal. PG F1 on PGPrompts harmful request is 87.12 vs Llama Guard 3 at 67.98 — [PolyGuard](https://arxiv.org/html/2504.04377)
- gpt-oss-safeguard's only multilingual evidence is MMMLU (14 languages, chat setting). The report says this does "not directly assess performance during content classification with a provided policy" — [gpt-oss-safeguard report](https://cdn.openai.com/pdf/08b7dee4-8bc6-4955-a219-7793fb69090c/Technical_report__Research_Preview_of_gpt_oss_safeguard.pdf)
- Aegis 2.0 is single-turn prompts or prompt+response. Its 1,080 multi-turn dialogues belong to a separate topic-following dataset — [Aegis 2.0](https://arxiv.org/html/2501.09004)
- DynaBench is multi-turn throughout (test median 3 turns, max 13) — [DynaGuard](https://arxiv.org/html/2509.02563)
- Granite Guardian adds RAG groundedness (9 TRUE datasets), outside content safety. 8B average AUC is 0.854 — [Granite Guardian](https://arxiv.org/html/2412.07724)
- Llama Guard 3 also reports tool-use moderation: search-tool-call F1 0.856 and code-interpreter abuse F1 0.885 — [LG3 card](https://huggingface.co/meta-llama/Llama-Guard-3-8B)

### Inferences
- Translated benchmarks carry the English label unchanged into every language, so multilingual scores measure robustness to translation, not culturally situated harm. PolyGuard's α = 0.46 on safety labels hints at how much labels would shift if re-annotated natively.

### Gaps
- NemoGuard's evaluation numbers (the model card defers to the Aegis 2.0 paper and an OpenReview link) were not extracted beyond the Aegis 2.0 table.

## Presentation (leaderboards, per-category tables)

### Takeaway
Papers present large per-dataset tables (GuardBench: 40 rows × 13 models with improvement markers) or task-averaged F1 (WildGuard, GuardReasoner, Qwen3Guard). Model cards present internal-set tables with deltas against the previous version. Live leaderboards are rare and fragile: GuardBench's HF Space showed a runtime error on 2026-10-24, and JailbreakBench is the best-maintained public leaderboard. Per-category (hazard-level) tables are uncommon in public-benchmark sections.

### Cited Findings
- GuardBench Table 3 has one row per dataset (prompts, conversations, multilingual), one column per model, bold for best and underline for second best, * for train-set exposure, and ↑/‡ for improvement over Mistral and MD-Judge. There is no aggregate score — [GuardBench paper](https://aclanthology.org/2024.emnlp-main.1022.pdf)
- The GuardBench leaderboard is an HF Space (AmenRa/guardbench-leaderboard). On 2026-10-24 it showed "Runtime error", and submissions go by contacting the maintainers — [HF Space](https://huggingface.co/spaces/AmenRa/guardbench-leaderboard); [GitHub](https://github.com/AmenRa/GuardBench)
- JailbreakBench's leaderboard at jailbreakbench.github.io is built on RobustBench code, can be filtered by threat model (black_box/white_box/transfer), and links each entry to its artifacts — [JailbreakBench](https://arxiv.org/html/2404.01318)
- Llama Guard 4 card: absolute R/FPR/F1 with Δ against LG3 per subset (English, multilingual, single-image, multi-image) — [LG4 card](https://huggingface.co/meta-llama/Llama-Guard-4-12B)
- DynaGuard reports a table with a DynaBench column, a safety average, and an all-tasks average. Its ablation table shows the base model at 33.9 → label SFT 64.6 → CoT+GRPO 71.7 — [DynaGuard](https://arxiv.org/html/2509.02563)
- Qwen3Guard reports per-benchmark F1 tables for English, Chinese, and multilingual, split by prompt and response, with averages computed at the optimal mode per benchmark — [Qwen3Guard](https://arxiv.org/html/2510.14276)
- Granite Guardian aggregates harm across benchmarks (AUC/AUPRC/F1/R/P) and puts fixed-FPR operating points in the appendix — [Granite Guardian](https://arxiv.org/html/2412.07724)
- Aegis 2.0 reports out-of-domain (OpenAI Mod, WildGuardTest, XSTest), in-domain (Aegis2 test), and a separate table for categories added at inference (Financial, Legal, Medical, NSFW) — [Aegis 2.0](https://arxiv.org/html/2501.09004)

### Inferences
- No surveyed benchmark presents significance tiers or CIs on a leaderboard. raxIT's Holm-tier presentation is a differentiator, and the per-dataset table with exposure markers (GuardBench's *) is a cheap precedent worth borrowing for training-overlap disclosure.

### Gaps
- The GuardBench leaderboard's current contents (models, aggregation) could not be read because the Space was down.
- The WildGuard paper's appendix (past 100k characters) and the JailbreakBench appendix were not fully read; per-category tables there may exist.
