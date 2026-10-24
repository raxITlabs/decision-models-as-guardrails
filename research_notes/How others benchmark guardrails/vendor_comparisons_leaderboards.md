# Vendor and independent comparisons and leaderboards of managed LLM guardrail products

Scope note: about 20 tool calls. Some named vendors (Lasso, Protect AI/Prisma AIRS, Mindgard, HiddenLayer, CalypsoAI, Haize Labs, Arthur, Pangea efficacy, General Analysis) produced no fetchable head-to-head benchmark. Those are listed under Gaps rather than filled in from memory.

## Who has published head-to-head guardrail comparisons and leaderboards?

### Takeaway
Most published head-to-heads that include managed products (Bedrock Guardrails, Azure Content Safety and Prompt Shields, Google Model Armor, OpenAI Moderation) come from vendors selling a competing guardrail. Each one ranks the publisher first. The independent material is either academic (attack and evasion papers, "No Free Lunch") or covers open-weight guard models only (Artificial Analysis, GuardBench), not the managed APIs.

### Cited Findings
**Vendor-run head-to-heads that include managed products**
- **Lakera PINT benchmark** (prompt injection). Lakera Guard 95.22%, AWS Bedrock Guardrails 89.24%, Azure AI Prompt Shield (Documents + User Prompts) 89.12%, protectai/deberta-v3-base-prompt-injection-v2 79.14%, Llama Prompt Guard 2 (86M) 78.76%, Google Model Armor 70.07% (tested 2025-08-27), Aporia 66.44%, Llama Prompt Guard 61.82%. Most systems were tested 2025-05-02. — [lakeraai/pint-benchmark](https://github.com/lakeraai/pint-benchmark)
- **Fiddler 2025 Guardrails Benchmarks Report** (April 2025). Compares Fiddler "Centor" models with Amazon Bedrock and Azure AI Content Safety on jailbreak, toxicity and faithfulness, plus OpenAI Moderation (toxicity) and a Ragas GPT-4o judge (faithfulness). Best F1:
  - Jailbreak: Fiddler 0.94, Bedrock 0.92, Azure 0.87.
  - Toxicity: Fiddler 0.91, Bedrock 0.88, OpenAI Moderation 0.88, Azure 0.77.
  - Faithfulness: Fiddler 0.84, Bedrock 0.80, Azure 0.74, Ragas GPT-4o 0.74.

  — [Fiddler report](https://www.fiddler.ai/guardrails-benchmarks/access)
- **Guardrails AI "AI Guardrails Index"** (Feb 12, 2025). Claims "20+ leading guardrail solutions" across 6 domains: jailbreak prevention, PII detection, content moderation, hallucination detection, competitor presence and restricted topics. The announcement names no competitor products and says Guardrails AI "emerged as a top performer across multiple benchmarks." — [Guardrails AI blog](https://guardrailsai.com/blog/introducing-the-ai-guardrails-index); [Index: Jailbreaking](https://guardrailsai.com/index/ai-guardrails-index-jailbreaking)
  - Guardrails AI's own jailbreak figures as summarised by search (I could not read the live table because it renders with JS): its validator F1 0.815, Anthropic's model 0.810, Llama Prompt Guard 0.666. Its PII validator F1 0.652 vs Microsoft Presidio 0.370 (UNVERIFIED, search summary) — [Guardrails AI blog: advanced PII and jailbreak](https://guardrailsai.com/blog/advanced-pii-and-jailbreak)
- **"A Comparative Evaluation of AI Agent Security Guardrails"** (arXiv 2604.24826, 2026). Compares DKnownAI Guard, AWS Bedrock Guardrails, Azure Content Safety and Lakera Guard. DKnownAI Guard comes first: recall 96.5%, TNR 90.4%. Ground truth is human annotation, and decisions are binary BLOCKED/ALLOWED. The abstract page lists no affiliations, so I could not confirm a vendor tie from it. A paper evaluating a little-known product that comes out best should be treated as likely vendor-authored until checked. — [arXiv 2604.24826](https://arxiv.org/abs/2604.24826)
- **Guardion.ai leaderboard**. Has head-to-head pages such as "AWS Bedrock Guardrails vs Lakera Guard" (Prompt Attack Risk Benchmark). A search summary reported an F1 shown as NaN on the comparison page, so it looks unreliable (UNVERIFIED, not fetched). — [Guardion compare page](https://guardion.ai/leaderboard/compare/aws-bedrock-guardrails-vs-lakera-guard)

**Independent or academic comparisons**
- **"No Free Lunch with Guardrails"** (arXiv 2504.00441). Benchmarks Llama Guard, Bedrock Guardrails and Guardrails AI together on F1 and latency. Per a search summary (UNVERIFIED, PDF not fetched): on WildJailbreak, Bedrock F1 0.785 at 0.203 s, Llama Guard 0.636 at 0.959 s, Guardrails AI 0.619 at 0.348 s. On the usability or over-refusal set (PHTest), Bedrock 0.938 and Llama Guard 0.971. — [arXiv 2504.00441](https://arxiv.org/pdf/2504.00441)
- **"Bypassing LLM Guardrails: An Empirical Analysis of Evasion Attacks against Prompt Injection and Jailbreak Detection Systems"** (arXiv 2504.11168). Six detectors including Azure Prompt Shield and Meta Prompt Guard. Character-injection evasion reached up to 100% in some cases. Average ASR against Azure Prompt Shield was 71.98% on prompt injection and 60.15% on jailbreaks. Every detector except Azure was tested white-box. The baseline (un-attacked) Azure Prompt Shield accuracy was about 90% on jailbreaks and about 59% on prompt injections. — [arXiv 2504.11168v3](https://arxiv.org/html/2504.11168v3)
- **Artificial Analysis × NVIDIA, "Benchmarking guardrail models for safety, refusal, and latency"** (June 11, 2026). Covers open-weight guard models (Qwen3Guard, Llama Guard 3/4, Nemotron safety variants, WildGuard, gpt-oss-safeguard 20B/120B, Granite Guardian 4.1, ShieldGemma) plus OpenAI omni-moderation, with prompted gpt-oss as an "exploratory" baseline. Datasets: WildGuardTest (1,699), ToxicChat (5,083), XSTest (450), 7,232 prompts in total, prompt harm only. Headline metric is the equal-weighted average F1, alongside recall and specificity. Latency is measured end-to-end, one request at a time, over 450 prompts with 20 warm-up requests discarded, self-hosted on B200-class GPUs. omni-moderation was timed on OpenAI's hosted API and is flagged as not comparable. No cost figures. The text describes itself as an "exploratory comparison" and says there is "no common standard" yet. NVIDIA was the partner and NVIDIA's own Nemotron models were among those tested. — [Artificial Analysis](https://artificialanalysis.ai/de/articles/guardrail-safety-benchmark)
- **GuardBench** (EMNLP 2024). 40 safety datasets, F1, with a public Hugging Face leaderboard for guard models. — [ACL Anthology](https://preview.aclanthology.org/setup/2024.emnlp-main.1022); [HF space AmenRa/guardbench-leaderboard](https://huggingface.co/spaces/AmenRa/guardbench-leaderboard/blob/b95ba7012ed2d113d6ce574e17d7767e4c3f2c11/src/about.py)
- **InjecGuard paper.** A search summary reports Lakera Guard catching 53.19% of malicious prompt injections in its tests (UNVERIFIED, aggregator summary; primary paper not fetched). — [Giskard comparison page citing it](https://www.giskard.ai/knowledge/ai-guardrails-comparison-2026)

**Attack research against a single vendor's guardrail**
- **Robust Intelligence (now Cisco), "Bypassing Meta's LLaMA Classifier: A Simple Jailbreak"** (July 29, 2024). Spacing out characters and stripping punctuation made Prompt-Guard-86M misclassify malicious prompts as benign. Press coverage reports a 99.8% success rate, which other outlets describe as detection falling from 100% to 0.2%. The bypass was found by comparing embedding weights of Prompt-Guard-86M against its base model, microsoft/mdeberta-v3-base. — [Cisco blog](https://blogs.cisco.com/security/bypassing-metas-llama-classifier-a-simple-jailbreak); [The Register](https://www.theregister.com/2024/07/29/meta_ai_safety/); [SC Media](https://scmagazine.com/news/metas-promptguard-model-bypassed-by-simple-jailbreak-researchers-say)

**Crowdsourced red-team arenas (they rank models, not guardrail products)**
- **Gray Swan × UK AISI Agent Red-Teaming Challenge** (Mar 8 – Apr 6, 2025): 1.8M attempts, 62,000 successful breaks, 22 anonymised LLMs, 44 target behaviours, $171,800 in prizes. Per-model ASR = breaks ÷ chats, ranging from 1.47% (Claude 3.7 Sonnet Thinking) to 6.49% (Llama-3.3-70B). Over-refusal was also measured. Judging was automated and calibrated with UK AISI, which also reviewed appeals by hand. The full attack dataset went only to co-sponsoring labs. The snapshot gives no indication that standalone guardrails or classifiers were scored. — [Gray Swan snapshot](https://www.grayswan.ai/news/uk-aisi-x-gray-swan-agent-red-teaming-challenge-results-snapshot); [NIST CAISI blog](https://www.nist.gov/blogs/caisi-research-blog/insights-ai-agent-security-large-scale-red-teaming-competition)
- **Pangea $10,000 prompt-injection challenge.** About 330,000 prompts and 300M+ tokens. The output is an attack-data report, not a detector comparison. Pangea's ">99% efficacy" claim for Prompt Guard comes with no dataset or baseline. — [Pangea report](https://info.pangea.cloud/prompt-injection-research-report-2025); [Pangea launch blog](https://pangea.cloud/blog/introducing-pangea-prompt-guard-and-ai-guard-to-secure-ai-applications/)

### Inferences
- Bedrock Guardrails appears in nearly every vendor head-to-head as the incumbent baseline (PINT, Fiddler, DKnownAI, No Free Lunch) and usually comes second. That makes Bedrock the reference point the market already uses, which supports raxIT's choice of comparator.
- Google Model Armor shows up in only one public comparison (PINT, 70.07%, Lakera-run). There is room for an independent Model Armor result.

### Gaps
- I found no fetchable head-to-head benchmarks from Lasso Security, Protect AI / Palo Alto Prisma AIRS, Mindgard, HiddenLayer, CalypsoAI (I could not confirm a "CalypsoAI leaderboard" exists in this pass), Haize Labs, Arthur (Arthur Shield) or General Analysis. The search for a General Analysis guardrail leaderboard returned only a company profile.
- Galileo Protect: only a vendor claim of "<200 ms" via Luna-2 SLMs ([parse.gl profile](https://www.parse.gl/brands/galileo-ai-2)). I found no head-to-head against Bedrock or others.
- "SoK: Evaluating Jailbreak Guardrails for LLMs": I found only third-party reviews ([themoonlight review](https://www.themoonlight.io/en/review/sok-evaluating-jailbreak-guardrails-for-large-language-models)) and did not fetch the paper. I can't say whether it includes commercial APIs.
- No crowdsourced "guardrail arena" that ranks guardrail products by votes or attacks was confirmed. The Lighthouz "Guardrails Arena" on HF returned nothing.

## Datasets, metrics, thresholds, and whether vendors tuned their own product

### Takeaway
Vendor benchmarks mix public and proprietary data. They report one headline number (PINT Score or best F1) and rarely state thresholds. They also say "optimally configured" without showing the competitors' configs. Only the academic work and Artificial Analysis name their datasets and protocol fully.

### Cited Findings
- **PINT:**
  - Data: 4,314 inputs (3,016 English, 1,298 non-English), a "blend of public and proprietary data." Mix: prompt injections 5.2%, jailbreaks 0.9%, hard negatives 20.9%, chats 36.5%, benign documents 36.5%. Some injections are embedded in long documents.
  - Contamination: Lakera says evaluated solutions, Lakera Guard included, are not trained on the inputs and won't be. The dataset itself is held back, and the public repo ships only an example YAML.
  - Metric: a single "PINT Score" %. The README does not give the formula.
  - Configuration: competitors were "optimally configured," with details in DETAILS.md (not read).

  — [PINT repo](https://github.com/lakeraai/pint-benchmark)
- **Fiddler:**
  - Data: "publicly available" jailbreak, toxicity and Q&A datasets, unnamed, using class-balanced randomised subsets. Fiddler says no examples were in its training data.
  - Metric: "Best F1", which implies the threshold was picked post hoc to maximise F1.
  - Bedrock and Azure: they return only low/medium/high categories, so no AUC was reported. The report doesn't say how those categories were mapped to a binary F1.

  — [Fiddler report](https://www.fiddler.ai/guardrails-benchmarks/access)
- **Artificial Analysis:** public datasets (WildGuardTest, ToxicChat, XSTest), equal-weighted F1. Each model used its own documented prompt format, so results depend on those prompts. — [Artificial Analysis](https://artificialanalysis.ai/de/articles/guardrail-safety-benchmark)
- **Gray Swan:** the attack data is private and goes to sponsor labs only. The metric is ASR per model. — [Gray Swan](https://www.grayswan.ai/news/uk-aisi-x-gray-swan-agent-red-teaming-challenge-results-snapshot)
- **DKnownAI comparison:** recall and TNR against human-annotated ground truth. Dataset and thresholds are not described on the abstract page. — [arXiv 2604.24826](https://arxiv.org/abs/2604.24826)
- **Fiddler faithfulness guardrail:** a 0–1 score flagged at a 0.5 default threshold. This is an example of a vendor documenting a fixed default threshold. — [Fiddler docs](https://docs.fiddler.ai/protection/guardrails)

### Inferences
- "Best F1" (Fiddler) and "optimally configured" (PINT) both let the publisher pick operating points after seeing the data. A fixed, pre-declared threshold such as raxIT's 0.5 is stricter and makes a defensible point of difference.
- Category-only outputs (Bedrock and Azure low/medium/high) stop vendors from reporting AUC for those products. A benchmark should say which strength level it maps to block/allow.

### Gaps
- PINT's DETAILS.md, which holds the per-vendor configuration such as which Bedrock filter strength was used, was not read.
- I found no public evidence of any managed vendor (AWS, Azure, Google) tuning their own product for these third-party benchmarks or responding to them.

## Were latency and cost reported, and how?

### Takeaway
Fiddler is the only source found with per-system latency and $ cost tables that include Bedrock and Azure. Artificial Analysis reports latency carefully but no cost. PINT reports neither.

### Cited Findings
- **Fiddler** (April 2025):
  - Latency per call: Fiddler 105–120 ms, Bedrock 260 ms, Azure 165 ms, OpenAI Moderation 200 ms, Ragas GPT-4o 8,200 ms.
  - Cost per 1K text units (1 text unit = 1,000 chars ≈ 250 tokens): jailbreak and toxicity at Fiddler $0.014–0.021, Bedrock $0.15, Azure $0.38, OpenAI Moderation $0.042. Faithfulness at Bedrock $0.10 and Ragas $0.04.
  - Scenario of 1B text units/year: Fiddler $18,200, Bedrock $130,000, Azure $380,000.
  - Setup: calls were co-located with each evaluator (for example, the same Azure availability zone) for "best case" latency.
  - Internal inconsistencies: Bedrock latency is given as 260 ms in the tables but 250/273 ms elsewhere, and the "2x cheaper" claim is really 3x at the listed prices.

  — [Fiddler report](https://www.fiddler.ai/guardrails-benchmarks/access)
- **Fiddler marketing:** "<100 ms" and "up to 18x lower cost" (vendor claim, unverified). — [Fiddler resources](https://www.fiddler.ai/resources/secure-llm-applications-with-fiddler-free-guardrails)
- **Artificial Analysis:** end-to-end latency, sequential requests, warm-up discarded. It flags hosted-API latency (omni-moderation) as not comparable with self-hosted GPU latency. No cost figures. — [Artificial Analysis](https://artificialanalysis.ai/de/articles/guardrail-safety-benchmark)
- **No Free Lunch:** reports latency in seconds per system alongside F1, for example Bedrock 0.203 s vs Llama Guard 0.959 s (UNVERIFIED search summary). — [arXiv 2504.00441](https://arxiv.org/pdf/2504.00441)
- **Guardrails AI:** quotes GPU vs CPU latency for its own validators (0.054 s GPU / 0.283 s CPU for jailbreak, per search summary, UNVERIFIED) and says it is "significantly faster" than "industry giants" without figures. — [Guardrails AI blog](https://guardrailsai.com/blog/introducing-the-ai-guardrails-index)

### Inferences
- Cost is the least-covered dimension. Where it does appear, it comes from a vendor using list prices and a self-chosen volume scenario. An independent, reproducible cost-per-1k-requests comparison against Bedrock would be close to unique.

### Gaps
- No source reported tail latency (p95/p99) or throughput limits for managed APIs.

## Conflicts of interest and reproducibility

### Takeaway
Every vendor-authored comparison found ranks the author first: Lakera (PINT), Fiddler, Guardrails AI and probably DKnownAI. None releases the full evaluation data. PINT releases harness code but keeps the dataset private, and Guardrails AI says it open-sourced code and data, which I could not verify.

### Cited Findings
- Lakera maintains PINT and comes first on it, with 95.22%. The harness notebook is public, the dataset is not. — [PINT repo](https://github.com/lakeraai/pint-benchmark)
- Fiddler comes first in all three categories of its own report. It omits dataset names, sizes, model versions, judge prompts, thresholds and category-to-score mappings, and gives no CIs. — [Fiddler report](https://www.fiddler.ai/guardrails-benchmarks/access)
- Guardrails AI publishes the Index and ranks itself top. It says it "open-sourced our dataset and codebase" (claim from search snippet, not verified). — [Guardrails AI blog](https://guardrailsai.com/blog/introducing-the-ai-guardrails-index)
- Artificial Analysis says the work was "conducted independently" but was done in partnership with NVIDIA, whose Nemotron models are included. — [Artificial Analysis](https://artificialanalysis.ai/de/articles/guardrail-safety-benchmark)
- Pangea's ">99% efficacy" has no dataset or baseline. — [Pangea](https://pangea.cloud/blog/introducing-pangea-prompt-guard-and-ai-guard-to-secure-ai-applications/)
- The arXiv evaluation of DKnownAI Guard reports its own subject product as best, and the abstract page shows no affiliations or code/data link. — [arXiv 2604.24826](https://arxiv.org/abs/2604.24826)
- In the independent "No Free Lunch" paper, the ranking differs from Guardrails AI's own index: Bedrock beats Guardrails AI on WildJailbreak F1 (UNVERIFIED summary). — [arXiv 2504.00441](https://arxiv.org/pdf/2504.00441)

### Inferences
- The pattern of "publisher ranks first, data withheld" is consistent across vendors. A benchmark that releases code and most data, holds back a slice only to prevent contamination, and states its own interest in the results would stand out.

### Gaps
- I did not verify whether Guardrails AI's dataset and code are actually downloadable, or whether Lakera ever released PINT data beyond the example file.

## Grounding and hallucination guardrail comparisons

### Takeaway
Published head-to-heads that include Bedrock's contextual grounding check are rare. The only one found is Fiddler's vendor report (Bedrock faithfulness F1 0.80 vs Fiddler 0.84). Galileo's Hallucination Index ranks LLMs, not guardrails.

### Cited Findings
- Fiddler faithfulness, best F1: Fiddler 0.84, Bedrock 0.80, Azure 0.74, Ragas GPT-4o 0.74. Bedrock cost $0.10 per 1K text units, latency about 260–273 ms. Datasets are unnamed public Q&A sets. — [Fiddler report](https://www.fiddler.ai/guardrails-benchmarks/access)
- Classmethod (Japanese AWS partner) blog posts evaluate Bedrock's contextual grounding check with Bedrock Evaluations (faithfulness, correctness, completeness, helpfulness). They test a single product, not a comparison, and the results were not fetched. — [Classmethod eval](https://dev.classmethod.jp/articles/amazon-bedrock-guardrails-grounding-eval/); [Classmethod trial](https://dev.classmethod.jp/articles/guardrails-for-amazon-bedrock-contextual-grounding-check/)
- Galileo Hallucination Index:
  - Ranks LLMs, not guardrail products, and is updated about every two quarters.
  - The RAG edition covers 22 models over short (<5k), medium (5k–25k) and long (40k–100k token) contexts, with context adherence scored by Galileo's proprietary ChainPoll method.
  - Claude 3.5 Sonnet came first. Gemini 1.5 Flash was best on cost.

  — [Galileo methodology](https://galileo.ai/hallucinationindex/methodology); [Galileo RAG special](https://galileo.ai/blog/llm-hallucination-index-rag-special)
- Guardrails AI Index lists "Hallucination Detection" as one of its 6 domains, but I did not retrieve its results. — [Guardrails AI blog](https://guardrailsai.com/blog/introducing-the-ai-guardrails-index)

### Inferences
- An independent grounding comparison (Bedrock contextual grounding vs decision models or LLM judges) with named datasets would fill a visible gap.

### Gaps
- I did not retrieve Arthur's hallucination benchmarks, Galileo Protect vs Bedrock, or Guardrails AI's hallucination-domain numbers.

## How results were presented

### Takeaway
Presentation runs from a single ranked table (PINT), to vendor PDF/landing pages behind a form (Fiddler, Guardrails AI report download), to interactive JS leaderboards whose numbers are not in the page text (Guardrails Index, Artificial Analysis), to arena leaderboards ranked by ASR (Gray Swan).

### Cited Findings
- **PINT:** one Markdown table in the GitHub README with system, PINT Score and test date per row, so readers can see results are dated. — [PINT repo](https://github.com/lakeraai/pint-benchmark)
- **Fiddler:** a gated report page with per-metric tables (F1/AUC, latency, cost), an annual cost scenario and "x times cheaper/faster" callouts. — [Fiddler report](https://www.fiddler.ai/guardrails-benchmarks/access)
- **Guardrails AI:** a per-domain index page (e.g. /index/ai-guardrails-index-jailbreaking) that renders its table client-side, plus a downloadable report. — [Index: Jailbreaking](https://guardrailsai.com/index/ai-guardrails-index-jailbreaking); [download page](https://guardrailsai.com/download-page)
- **Artificial Analysis:** an article with interactive charts. The numbers are not in the text and the findings are framed as recall vs over-refusal trade-offs. — [Artificial Analysis](https://artificialanalysis.ai/de/articles/guardrail-safety-benchmark)
- **Gray Swan:** a top-10 participant leaderboard (unique breaks, speed tie-break) and a model table with total breaks, total chats and ASR. Some models are anonymised at lab request. — [Gray Swan](https://www.grayswan.ai/news/uk-aisi-x-gray-swan-agent-red-teaming-challenge-results-snapshot)
- **Guardion:** pairwise "X vs Y" comparison pages generated from a leaderboard. — [Guardion](https://guardion.ai/leaderboard/compare/aws-bedrock-guardrails-vs-lakera-guard)

### Inferences
- Dated rows (PINT) and recall vs over-refusal framing (Artificial Analysis) are presentation patterns worth copying. Gated PDFs and JS-only tables make results hard to cite or verify.

### Gaps
- I could not see the Artificial Analysis or Guardrails Index chart values because the pages render them client-side.
