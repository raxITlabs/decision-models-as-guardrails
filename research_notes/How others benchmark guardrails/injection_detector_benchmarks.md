# How prompt-injection and jailbreak detectors are benchmarked

Scope: Lakera PINT, Meta Prompt Guard 1/2 + LlamaFirewall, Protect AI DeBERTa, deepset, InjecGuard/PIGuard + NotInject, BIPIA, AgentDojo, InjecAgent, LLMail-Inject, Tensor Trust, HackAPrompt, Hackett et al. 2025, Nasr/Carlini et al. "The Attacker Moves Second", Fomin "When Benchmarks Lie" (arXiv 2602.14161, which exists).
Research date: 2026-10-24. "UNVERIFIED" marks figures I recall but could not confirm in this session.

## 1. How datasets are built and labelled, and how benign or hard-negative rows are made

### Takeaway
Detector benchmarks fall into two families.
- **Classification sets** (PINT, NotInject, the Prompt Guard private set, the 18-dataset LODO pool) label single texts as attack or benign. Their benign side increasingly includes deliberate "hard negatives": benign text that contains injection trigger words or looks like an attack.
- **Task or agent environments** (BIPIA, AgentDojo, InjecAgent, LLMail-Inject) have no row labels. They measure whether an attack goal was reached inside a task.

Only PINT and NotInject build hard negatives on purpose, and both report that ordinary detectors fall apart on them. This is the same failure raxIT sees on its direct prompt-attack job.

### Cited findings

**Lakera PINT**
- 4,314 inputs: 3,016 English and 1,298 non-English, from a mix of public and proprietary data — [lakeraai/pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- Category mix:
  - prompt injections 5.2%
  - jailbreaks 0.9%
  - hard negatives 20.9%
  - user-agent chats 36.5%
  - benign public documents 36.5%

  Some injections are embedded inside long documents. Languages: 12 Indo-European, 8 Asian and 4 others. — [pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- So roughly 94% of PINT rows are benign. The score depends heavily on false-positive behaviour. (Computed from the shares above.)
- Rows are YAML records with `text`, `category` and a boolean `label`. The system under test supplies a function that takes a string and returns a boolean. — [pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- The repository is now archived (read-only) — [pint-benchmark](https://github.com/lakeraai/pint-benchmark)

**NotInject (InjecGuard / PIGuard paper, ACL 2025)**
- Trigger words were mined by comparing word-frequency ranks in malicious and benign corpora (Δr(w) = Rb(w) − Rm(w)). GPT-4o-mini screened the candidates, and three human raters scored them; words with a mean score above 3 were kept. That left 113 trigger words. — [arXiv 2410.22770 HTML](https://arxiv.org/html/2410.22770v3)
- GPT-4o-mini then wrote benign sentences containing 1, 2 or 3 trigger words: 113 per subset, 339 in total. A safety re-check and manual review followed. — [arXiv 2410.22770 HTML](https://arxiv.org/html/2410.22770v3)
- Topics: Common Queries, Technique Queries, Virtual Creation, Multilingual Queries — [leolee99/PIGuard](https://github.com/leolee99/PIGuard)
- The model was renamed from InjecGuard to PIGuard because of licensing issues — [leolee99/PIGuard](https://github.com/leolee99/PIGuard)
- The paper's benign evaluation uses the benign data from PINT and WildGuard. Its malicious evaluation uses PINT and BIPIA attacks. — [arXiv 2410.22770 HTML](https://arxiv.org/html/2410.22770v3)

**Meta Prompt Guard 2**
- Evaluated on a *private* in-house benchmark "built from datasets distinct from the training data", meant to test generalisation to unseen attacks and benign distributions. The datasets are not named. — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M); [LlamaFirewall paper](https://arxiv.org/html/2505.03574v1)
- The multilingual set is the same prompts machine-translated into 8 more languages — [LlamaFirewall paper](https://arxiv.org/html/2505.03574v1)
- Training mix: open benign web data, user prompts and LLM instructions, plus malicious datasets, synthetic injections and red-team data from earlier Prompt Guard versions — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- An energy-based loss penalises confident wrong predictions on benign prompts "to improve precision on out-of-distribution data" — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)

**Protect AI deberta-v3-base-prompt-injection-v2**
- Trained on about 22 open datasets (counted from the licence tally on the model card), including open-instruct, jackhhao/jailbreak-classification and Salad-Data. Some injections were hand-written from papers and competitions. — [HF model card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)
- Post-training evaluation used 20,000 prompts from datasets not used in training — [HF model card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)

**deepset deberta-v3-base-injection**
- Fine-tuned on `deepset/prompt-injections`, which the card does not size. The training log suggests about 550 training rows; that is an inference, not a stated figure. — [HF model card](https://huggingface.co/deepset/deberta-v3-base-injection)
- The card treats legitimate inputs as "questions or keyword searches" and warns the model can be "trigger-happy" — [HF model card](https://huggingface.co/deepset/deberta-v3-base-injection)

**"When Benchmarks Lie" (Fomin, arXiv 2602.14161, ICLR 2026)**
- Pools 18 datasets: about 105K samples, 47% malicious — [arXiv 2602.14161](https://arxiv.org/html/2602.14161)
- The datasets: AdvBench, HarmBench, WildJailbreak, Yanismiraoui, BIPIA, InjecAgent, LLMail, Mosscap+Gandalf, Jayavibhav, Qualifire, SafeGuard, Deepset, Enron, OpenOrca, Dolly-15k, 10k Prompts, SoftAge — [arXiv 2602.14161](https://arxiv.org/html/2602.14161); also [ICLR 2026 listing](https://www.iclr.cc/virtual/2026/10016274)
- Warns that single-class datasets let dataset identity act as a shortcut for the label — [arXiv 2602.14161](https://arxiv.org/html/2602.14161)

**BIPIA (Yi et al., Microsoft)**
- Indirect injection benchmark built on three factors: task, attack type and attack position in the external content — [arXiv 2312.14197](https://arxiv.org/html/2312.14197v4)
- Five scenarios: email QA (100 emails), web QA (1,000 NewsQA), table QA (1,000 WikiTableQuestions), summarisation (1,000 XSum) and code QA (100 Stack Overflow) — [arXiv 2312.14197](https://arxiv.org/html/2312.14197v4)
- 626,250 training prompts and 86,250 test prompts — [arXiv 2312.14197](https://arxiv.org/html/2312.14197v4)

**AgentDojo (Debenedetti et al., NeurIPS 2024 D&B)**
- 97 user tasks, 27 injection tasks (Workspace 6, Slack 5, Travel 7, Banking 9) and 629 security cases, formed as user × injection task pairs within each environment — [arXiv 2406.13352 HTML](https://arxiv.org/html/2406.13352v3)

**InjecAgent**
- 1,054 test cases spanning 17 user tools and 62 attacker tools — [uiuc-kang-lab/InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent)
- Two attack types, Direct Harm and Data Stealing, each in a "base" and an "enhanced" setting (the enhanced setting adds a hacking prompt) — [InjecAgent repo](https://github.com/uiuc-kang-lab/InjecAgent)

**LLMail-Inject (Microsoft et al., SaTML 2025 challenge)**
- 839 participants made 461,640 submissions, which reduce to 208,095 unique human-written attack prompts — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)
- Four retrieval levels, 40 sub-levels in Phase 1 and 24 in Phase 2. Level 4 also requires exfiltrating data through the email. — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)
- Released on Hugging Face under MIT: raw submissions, unique prompts, LLM annotations, and the synthetic emails and system prompts. The Microsoft text classifier itself is not released, only its outputs. — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)

**Tensor Trust (Toyer et al., ICLR 2024)**
- More than 563,000 attacks and 118,000 prompt-based defences, collected from an online game (126k and 46k in the 2023 preprint). Spawns two benchmarks: prompt extraction and prompt hijacking. — [ICLR 2024 proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/519c51529c3544b3430bd8b17d400365-Abstract-Conference.html); [arXiv 2311.01011v1](https://arxiv.org/abs/2311.01011v1)

**HackAPrompt (Schulhoff et al., EMNLP 2023)**
- About 600K adversarial prompts from a global competition with about 2.8K participants — UNVERIFIED (search returned nothing; from memory of [arXiv 2311.16119](https://arxiv.org/abs/2311.16119))

### Inferences
- PINT (about 21% hard negatives, about 73% benign chats and documents) and NotInject (339 trigger-word benign rows) are the closest public analogues to raxIT's "benign rows that look like attacks". Both show this class decides rankings.
- Agentic benchmarks (AgentDojo, InjecAgent, BIPIA) do not give per-row detector labels. A detector is scored only through the agent's ASR and utility. They are a different job from row classification.

### Gaps
- PINT's exact hard-negative construction, and the size of its public vs proprietary split, are only in DETAILS.md, which I did not fetch.
- Meta's private benchmark composition is undisclosed.
- I could not confirm the deepset dataset size.

## 2. Metrics, thresholds and calibration (fixed vs tuned per model)

### Takeaway
There is no common metric.
- PINT gives one "PINT score" with vendors "optimally configured".
- Meta reports AUROC and recall at 1% FPR.
- NotInject-style papers report three accuracies (benign, malicious, over-defense) and their mean.
- Agent benchmarks report ASR and utility, with detector thresholds tuned to a utility budget.
- Model cards report accuracy, precision, recall and F1 on their own held-out sets.

Fixed-0.5 evaluation is rare; Fomin's LODO paper is the main example. Most vendor evals tune the operating point, which hides the over-blocking that a fixed threshold exposes.

### Cited findings

**PINT**
- Leaderboard (PINT score, test date) — [pint-benchmark](https://github.com/lakeraai/pint-benchmark):

  | System | PINT score | Tested |
  |---|---|---|
  | Lakera Guard | 95.22% | 2025-05-02 |
  | AWS Bedrock Guardrails | 89.24% | 2025-05-02 |
  | Azure AI Prompt Shield (Documents + User Prompts) | 89.12% | 2025-05-02 |
  | protectai deberta-v3-base-prompt-injection-v2 | 79.14% | 2025-05-02 |
  | Llama Prompt Guard 2 86M | 78.76% | 2025-05-05 |
  | Google Model Armor | 70.07% | 2025-08-27 |
  | Aporia | 66.44% | 2025-05-02 |
  | Llama Prompt Guard 1 | 61.82% | 2025-05-02 |

- Solutions were "optimally configured" for comparability; the README does not give the formula — [pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- PINT score is a balanced accuracy (mean of per-label accuracy) — UNVERIFIED; I believe this is stated in the repo's DETAILS.md / notebook but did not confirm it.

**Prompt Guard 1 and 2 (direct jailbreak detection)**

| Model | AUC (EN) | Recall @ 1% FPR (EN) | AUC (multilingual) | Latency (A100, 512 tokens) |
|---|---|---|---|---|
| Prompt Guard 1 | .987 | 21.2% | .983 | 92.4 ms |
| Prompt Guard 2 86M | .998 | 97.5% | .995 | 92.4 ms |
| Prompt Guard 2 22M | .995 | 88.7% | .942 | 19.3 ms |

Sources: [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M); the [LlamaFirewall HTML](https://arxiv.org/html/2505.03574v1) extraction gave .98 for the 86M English AUC, probably a rendering or typo difference.

- The AUC barely moves (.987 → .998) while recall at 1% FPR jumps from 21% to 97.5%. AUC hides the operating-point problem; tail-FPR recall exposes it.
- The model card gives no threshold guidance, only that fine-tuning on application data reduces false positives — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)

**Prompt Guard and other detectors on AgentDojo (model card)**
- The card reports "APR @ 3% utility reduction" (attack prevention rate): PG1 67.6%, PG2-86M 81.2%, PG2-22M 78.4%, ProtectAI 22.2%, deepset 13.5%, LLM Warden 12.9% — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- Each detector's threshold is set per model to reach a fixed utility loss — [LlamaFirewall paper](https://arxiv.org/html/2505.03574v1)

**LlamaFirewall on AgentDojo**

| Setup | ASR | Utility |
|---|---|---|
| No guardrail | 17.6% | 47.7% |
| PG2-86M | 7.5% | 47.0% |
| AlignmentCheck (Llama 4 Maverick) | 2.89% | 43.1% |
| PG2 + AlignmentCheck | 1.75% | 42.7% |

- PG2-22M cuts ASR by 41% with no utility loss — [LlamaFirewall paper](https://arxiv.org/html/2505.03574v1)
- The paper is inconsistent on the utility budget: 3% in Sec. 4.1 and about 1.5% in the appendix — [LlamaFirewall paper](https://arxiv.org/html/2505.03574v1)

**NotInject / PIGuard metrics**
- Benign accuracy, malicious accuracy and over-defense accuracy (accuracy on NotInject), with "Average" as their unweighted mean. 50% on over-defense is random. No threshold is stated. — [arXiv 2410.22770 HTML](https://arxiv.org/html/2410.22770v3)
- Table 1 (%):

  | Model | Over-defense | Benign | Malicious | Average |
  |---|---|---|---|---|
  | fmops | 5.60 | 34.63 | 93.50 | 44.58 |
  | deepset | 5.31 | 34.06 | 91.50 | 43.62 |
  | PromptGuard (v1) | 0.88 | 26.82 | 97.10 | 41.60 |
  | ProtectAI v2 | 56.64 | 86.20 | 48.60 | 63.81 |
  | Lakera Guard | 87.61 | 90.89 | 53.19 | 77.23 |
  | GPT-4o | 86.73 | 90.78 | 79.10 | 85.53 |
  | InjecGuard | 87.32 | 85.74 | 77.39 | 83.48 |

  Source: [arXiv 2410.22770 HTML](https://arxiv.org/html/2410.22770v3)
- The headline "+30.8%" is a *relative* gain over ProtectAI v2 (83.48 / 63.81); the absolute gain is about 19.7 points. Computed from the [paper's table](https://arxiv.org/html/2410.22770v3).

**Protect AI v2 model card**
- Own evaluation set: accuracy 99.93%, F1 99.93%.
- 20k unseen prompts: accuracy 95.25%, precision 91.59%, recall 99.74%, F1 95.49%.
- Previous version on the same 20k: accuracy 94.8%, F1 95%.
- Stated limits: does not detect jailbreaks, English only, false positives on system prompts. No threshold is stated (binary output).

Source: [HF model card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)

**deepset model card**
- Evaluation accuracy 0.9914, loss 0.0673 — [HF model card](https://huggingface.co/deepset/deberta-v3-base-injection)

**AgentDojo metrics**
- Benign utility, utility under attack and targeted ASR — [arXiv 2406.13352 HTML](https://arxiv.org/html/2406.13352v3)
- GPT-4o results:

  | Defense | Benign utility | Utility under attack | Targeted ASR |
  |---|---|---|---|
  | No defense | 69.0% | 50.01% | 57.69% |
  | ProtectAI "PI detector" | 41.49% | 21.14% | 7.95% |
  | Tool filter | 73.13% | 56.28% | 6.84% |

  The authors say the detector "has too many false positives" — [arXiv 2406.13352 HTML](https://arxiv.org/html/2406.13352v3)

**LLMail-Inject**
- Defences were calibrated to under 5% FPR on synthetic emails — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)
- FPR on 1,000 Enron emails: text classifier (Prompt Shield) 0%, TaskTracker 4.0–5.7%, LLM judge 5.0%, stacked 10%. The authors call the stacked rate too high to deploy without recalibration. — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)
- Phase 1 recall: text classifier about 60–68%, TaskTracker 76–95%, LLM judge 99.4%, all stacked 99.8% — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)

**InjecAgent and BIPIA**
- Both report ASR per category or setting. BIPIA reports ASR per task and attack type — [arXiv 2312.14197](https://arxiv.org/html/2312.14197v4); [InjecAgent repo](https://github.com/uiuc-kang-lab/InjecAgent)

**When Benchmarks Lie**
- Metrics: pooled ROC AUC with DeLong CIs, per-dataset accuracy, recall on malicious-only sets, and benign FPR. Probes use *fixed* thresholds of 0.5 (default) and 0.9 (conservative). The paper notes per-fold optimal thresholds vary widely and gives a matched-FPR comparison in its Appendix P. — [arXiv 2602.14161](https://arxiv.org/html/2602.14161)
- Production baselines (benign FPR; detection rates):

  | System | Benign FPR | Harmful | Jailbreak | Indirect | Other |
  |---|---|---|---|---|---|
  | PromptGuard 2 | 0.4% | 36.7% | 48.5% | 37.3% | extraction 100% |
  | LlamaGuard | 3.0% | 97.4% | 28.9% | 27.4% | — |
  | Llama-as-judge | 4.4% | — | — | 7.1% | agentic 21.5% |
  | ProtectAI v2 | 4.2% | 0% | — | 8% | — |
  | deepset v2 | 82.4% | — | — | — | TPR 99.8% |
  | Probe @0.5 | 6.8% | — | 71.2% | 66.7% | — |

  "—" means the extract did not give a figure for that cell. Source: [arXiv 2602.14161](https://arxiv.org/html/2602.14161)

### Inferences
- raxIT's fixed-0.5 balanced accuracy is closest to the per-class accuracy averaging in NotInject/PIGuard and to Fomin's fixed-threshold probes. It is unlike PINT's "optimally configured" vendors and Meta's recall at 1% FPR.
- Worth reporting alongside the fixed-0.5 headline:
  - a tuned or matched-FPR secondary view (Meta, LLMail-Inject and Fomin all calibrate to an FPR budget)
  - recall at a low FPR, such as 1%
- deepset's 82% benign FPR and PG1's 0.88% over-defense accuracy show what over-blocking does to a detector. raxIT's 74.4 ceiling, driven by benign false blocks, is consistent with every external eval that includes hard negatives.

### Gaps
- I did not see PINT's exact scoring formula or vendor threshold settings.
- PIGuard's own updated table is only in an image ([repo](https://github.com/leolee99/PIGuard)).

## 3. Held-out or private test data, contamination handling and cross-dataset generalisation

### Takeaway
- PINT and Meta keep their test data private.
- PINT says no evaluated system, Lakera Guard included, was trained on its inputs.
- LLMail-Inject keeps the defending classifier private but releases the attacks.

The strongest evidence on generalisation is Fomin's LODO study: same-source splits inflate AUC by 8–16.5 points, and 28% of top features are dataset shortcuts. Vendor-reported in-distribution numbers (99%+ on model cards) do not transfer.

### Cited findings
- **PINT:**
  - Evaluated systems, Lakera Guard included, are not trained directly on PINT inputs, nor on inputs submitted organically to Guard. So the score "doesn't reflect training optimization for this benchmark".
  - Part of the data is proprietary. Only an example dataset is public.

  Source: [pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- **Prompt Guard 2:** private benchmark "distinct from training data" — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- **Protect AI v2:** a 20k-prompt eval from unseen datasets gives 95.25% accuracy, against 99.93% in-distribution — [HF model card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2)
- **LODO (Fomin):**
  - Each of 17 dataset groups is held out in turn and the classifier trained on the rest.
  - Llama-3.1-8B probe: AUC 0.996 under 5-fold CV vs 0.912 under LODO. Qwen-3.5-2B: 0.998 vs 0.829. The gap is 8–16.5 points across four models.
  - Per-dataset accuracy gaps: mosscap +20.1, jayavibhav +25.4, qualifire +18.0, enron +16.6, deepset +2.5, safeguard +1.2.
  - 28% of top SAE features act as dataset-specific shortcuts.

  Source: [arXiv 2602.14161](https://arxiv.org/html/2602.14161)
- **Fomin's recommendations:**
  - Report LODO alongside CV.
  - Pick datasets spanning distinct attack surfaces and formats.
  - Run a dataset-identity classifier as a sanity check.
  - Be wary of single-class datasets.
  - Pair LODO with adversarial red-teaming, because LODO measures distribution shift, not robustness.

  Source: [arXiv 2602.14161](https://arxiv.org/html/2602.14161)
- **Gate AI** (arXiv 2606.02959) also uses LODO diagnostics. Not examined. — [search result](https://www.emergentmind.com/papers/2606.02959)
- **NotInject** shows the cost of trigger-word bias: PG1 0.88%, deepset 5.31% and fmops 5.60% over-defense accuracy — [arXiv 2410.22770 HTML](https://arxiv.org/html/2410.22770v3)
- **BIPIA's applicability to current models** has been questioned (from a search snippet; source not opened) — [search context, arXiv 2510.08829](https://arxiv.org/pdf/2510.08829)

### Inferences
- raxIT scores on public-dataset rows. Detectors trained on those same public sets (ProtectAI's ~22 sources, deepset, PromptGuard's open data) may be contaminated.
- A per-source breakdown, or a LODO-style "trained-on-this-source?" flag per system, would answer the strongest critique. Fomin's dataset-identity classifier check is cheap to copy.
- PINT's private-test model and LLMail's private-classifier model are the two disclosed anti-contamination patterns.

### Gaps
- PINT gives no detail on how it verifies the no-training claim for third-party vendors. It appears to be a statement, not an audit.

## 4. Adaptive attacks and how robustness is reported

### Takeaway
Static benchmark numbers greatly overstate detector robustness.
- Adaptive search or RL beats Protect AI, PromptGuard and Model Armor more than 90% of the time; PIGuard holds best at 71% ASR.
- Character-injection and AML evasion reach up to 100% evasion on commercial guardrails.
- Competitions (LLMail-Inject, Tensor Trust, HackAPrompt) supply human adaptive attacks as data.

Robustness is reported as ASR under a named attack budget, never as a certified number.

### Cited findings
**"The Attacker Moves Second" (Nasr, Carlini et al., arXiv 2510.09023, USENIX Security 2026)**
- Bypassed 12 defences; most had originally reported near-zero ASR — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1); [USENIX](https://www.usenix.org/conference/usenixsecurity26/presentation/nasr)
- Detectors attacked: Protect AI, PromptGuard, PIGuard, Model Armor. Also attacked: Spotlighting, Prompt Sandwiching, RPO, Circuit Breakers, StruQ, MetaSecAlign, Data Sentinel, MELON. — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1)
- Attack methods — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1):
  - GCG gradient attack
  - RL with GRPO
  - MAP-Elites / OpenEvolve search with a Gemini-2.5-Pro mutator
  - human red-teaming: more than 500 participants, 40 challenges, $20k in prizes
- Detector results — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1):
  - more than 90% adaptive ASR against Protect AI, PromptGuard and Model Armor
  - PIGuard 71%
  - 123 successful human injections against detectors under the strictest setting
  - "many successful triggers weren't obviously malicious", so detectors couldn't flag them without more false positives
  - stacking detectors did not help
- Other defences: MetaSecAlign goes from 2% static to 96% adaptive on AgentDojo (80-sample subset), and Circuit Breakers reaches 100% on HarmBench under RL — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1)
- Recommendations — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1):
  - evaluate against adaptive, compute-scaled attackers
  - include human red-teamers who know the defence
  - treat automated judges as attackable
  - "empirical evaluations cannot prove that a defense is robust"
- Commentary: [Simon Willison](https://simonw.substack.com/p/new-prompt-injection-papers-agents)

**Hackett et al. (arXiv 2504.11168, LLMSec 2025)**
- Title: "Bypassing LLM Guardrails: An Empirical Analysis of Evasion Attacks against Prompt Injection and Jailbreak Detection Systems" — [arXiv 2504.11168](https://arxiv.org/abs/2504.11168)
- Tests six systems, including Azure Prompt Shield and Meta Prompt Guard — [arXiv 2504.11168](https://arxiv.org/abs/2504.11168)
- The other four are ProtectAI v1/v2, NVIDIA NeMo Guard Jailbreak Detect and Vijil — UNVERIFIED; the abstract does not name them
- Attacks: character injection (e.g. homoglyphs, zero-width and diacritic characters) and algorithmic AML evasion — [arXiv 2504.11168](https://arxiv.org/abs/2504.11168)
- Reaches "up to 100% evasion success". Word-importance rankings from offline white-box models raise ASR against black-box targets. — [arXiv 2504.11168](https://arxiv.org/abs/2504.11168)

**Other adaptive and human-attack evidence**
- **Prompt Guard 2** uses a modified tokenizer against adversarial tokenization (fragmented tokens, inserted whitespace). Its limitations section concedes that adaptive attacks may bypass it. — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- **LlamaFirewall** reports no adaptive attack on PG2 and notes that AgentDojo mostly uses the "important instructions" attack — [LlamaFirewall paper](https://arxiv.org/html/2505.03574v1)
- **AgentDojo** is framed as extensible ("not a static test suite"). Its "Max" attack (best of four prompts) adds about 10% ASR. The authors expect repeat-prompt defences to fail under adaptive attack. — [arXiv 2406.13352 HTML](https://arxiv.org/html/2406.13352v3)
- **LLMail-Inject:**
  - Teams needed about 506 attempts for a first success against the LLM judge, against about 89 for the text classifier.
  - Level-4 team success with GPT-4o-mini: text classifier 0.60, TaskTracker 0.44, Spotlight 0.53, LLM judge 0.32, all combined 0.17.
  - In Phase 2, no submission beat all stacked defences.
  - Detected attacks triggered the tool more often, which suggests evading detection trades off against reaching the attack goal.

  Source: [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)
- **LLMail-Inject transfer:** Meta SecAlign 32% ASR, GPT-4o 58% and GPT-5 mini 47% on the curated subsets; attacks transfer to coding (37%) and file tasks (28–45%) — [arXiv 2506.09956](https://arxiv.org/abs/2506.09956)
- **DataSentinel** (IEEE S&P 2025) trains a detector by minimax against adaptive attacks — [arXiv 2504.11358](https://arxiv.org/abs/2504.11358). Nasr et al. still reach above 80% on redirected tasks — [arXiv 2510.09023](https://arxiv.org/html/2510.09023v1)
- **Tensor Trust** finds many models vulnerable to the game's attack strategies, and some strategies generalise to deployed apps — [ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/519c51529c3544b3430bd8b17d400365-Abstract-Conference.html)

### Inferences
- A static-dataset board like raxIT's measures the false-block / static-detection trade-off, not adversarial robustness. That limit should be stated explicitly, citing Nasr et al.
- Nasr et al. found that successful adaptive triggers often look benign. So pushing detectors to block more "attack-looking" benign rows would not buy robustness; it would only raise false blocks. This supports raxIT's choice to penalise false blocks.

### Gaps
- Per-detector *static* baseline ASRs in Nasr et al. were not in the extracted text.
- Hackett's per-system ASR breakdown is not in the abstract.

## 5. How results are presented

### Takeaway
- PINT uses a single-number leaderboard table with test dates.
- Meta uses model-card tables (AUC, recall at 1% FPR, latency) and a bar-style AgentDojo comparison.
- Academic benchmarks use multi-column tables: benign, malicious and over-defense accuracy, or utility, utility under attack and ASR.
- Fomin adds CIs (DeLong) and per-dataset gap tables.

None of the boards found reports paired bootstrap CIs or significance tiers the way raxIT does.

### Cited findings
- **PINT:**
  - one score per system with a test date
  - vendors listed by product name, including AWS Bedrock, Azure Prompt Shield and Google Model Armor
  - a notebook for self-evaluation, with example evaluators in `examples/`

  Source: [pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- **Prompt Guard 2:** a table of AUC (EN and multilingual), recall at 1% FPR, latency and parameter count, plus a separate AgentDojo comparison against ProtectAI, deepset and LLM Warden — [HF model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M)
- **PIGuard:** a three-axis table plus an average; the README results live in an image — [arXiv 2410.22770](https://arxiv.org/html/2410.22770v3); [PIGuard repo](https://github.com/leolee99/PIGuard)
- **AgentDojo:** a utility vs ASR table per defence. The framework's site hosts a results table across models (site not fetched this session). — [arXiv 2406.13352 HTML](https://arxiv.org/html/2406.13352v3)
- **LLMail-Inject:** recall per defence and phase, FPR on Enron, team success rates per defence, and attempts-to-first-success — [arXiv 2506.09956 HTML](https://arxiv.org/html/2506.09956v2)
- **When Benchmarks Lie:** pooled AUC with DeLong CIs, a CV vs LODO gap table, and a per-category detection plus benign-FPR table for production guardrails — [arXiv 2602.14161](https://arxiv.org/html/2602.14161)

### Inferences
- raxIT's uncertainty reporting (paired bootstrap CIs, Holm tiers) goes further than the comparison boards here. Fomin's DeLong CIs are the only comparable practice found.
- raxIT could add two panels to match the field:
  - an over-defense column separate from benign and attack accuracy (the NotInject style)
  - recall at 1% FPR or an ROC panel (the Meta style)

  Either would show why the direct prompt-attack job tops out at 74.4.

### Gaps
- I did not check whether PINT shows per-category or per-language breakdowns on the leaderboard.
- I did not fetch the AgentDojo website leaderboard.
- HackAPrompt's presentation was not verified.
