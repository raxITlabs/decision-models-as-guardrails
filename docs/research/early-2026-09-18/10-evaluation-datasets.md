# Evaluation datasets on Hugging Face

Checked on 18 September 2026. "Gated" means a one-click licence acceptance with a Hugging Face account. Sizes are the Hub's own bucket.

## Content filtering (v1)

| Dataset | Size | Labels | Maps to | Gated |
|---|---|---|---|---|
| `nvidia/Aegis-AI-Content-Safety-Dataset-2.0` | 10k-100k | 13 categories, prompt label and response label | Hate, Insults (harassment), Sexual, Violence, Misconduct (criminal planning, weapons, fraud) | No |
| `allenai/wildguardmix` | 10k-100k | prompt harmful, response harmful, response is refusal; adversarial subset | All five plus the good-refusal case | Auto |
| `lmsys/toxic-chat` | 10k-100k | toxicity, jailbreak, on real Vicuna traffic | False-positive traps on real user messages | No |
| `PKU-Alignment/BeaverTails` | 100k-1M | 14 harm categories on responses | Per-category threshold tuning | No |
| `toxigen/toxigen-data` | 100k-1M | implicit hate, target group | Hate, hard implicit cases | No |
| `google/civil_comments` | 1M-10M | toxicity, insult, identity attack, threat scores (Jigsaw) | Insults, Hate, Violence | No |

## Prompt attack

| Dataset | Size | Notes | Gated |
|---|---|---|---|
| `TrustAIRLab/in-the-wild-jailbreak-prompts` | 10k-100k | The set TypeSafe's guardrails cookbook used; jailbreak plus regular prompts | No |
| `JailbreakBench/JBB-Behaviors` | <1k | 100 harmful behaviours plus benign twins; standard benchmark | No |
| `deepset/prompt-injections` | <1k | Injection-specific, small | No |
| `allenai/wildjailbreak` | 1k-10k on Hub bucket, 262k rows | Synthetic adversarial and benign pairs | Auto |

## Sensitive information

| Dataset | Size | Notes | Gated |
|---|---|---|---|
| `ai4privacy/pii-masking-300k` | 100k-1M | Span-level PII labels, many entity types, multilingual | No |

## Denied topics and grounding

No off-the-shelf denied-topics set. `OpenSafetyLab/Salad-Data` (6 domains, 16 tasks, 10k-100k, not gated) can stand in for topic definitions during the POC. For grounding, the canonical RAGTruth repo returned 401; HaluEval is the fallback. Neither is needed before those checks exist.

## POC plan

1. Primary: Aegis 2.0. Write the 13-to-5 category mapping table into `fixtures/aegis-mapping.json` and treat it as a design decision.
2. False positives: Toxic-Chat, real traffic.
3. Sample 500 to 1,000 rows per set, stratified by label. Run through Jev (our question set) and Bedrock `InvokeGuardrailChecks`. Report precision and recall per category at several thresholds, plus latency and cost.
4. Jailbreak sets go in the second round, when prompt attack is a check. Expect them to show Jev's adversarial weakness; that is what they are for.

This replaces the hand-written fixtures in 07 for content filtering. The PII trap fixtures in 07 stay, since none of the public sets have the order-number and test-key traps we care about.


## Addendum, 22 September 2026: datasets for parity across the six suites

Adding harmful-content examples does not build parity with managed guardrails; the gaps are the other suites.
Shortlist, first three first.

| Suite | Add | Why | Watch |
|---|---|---|---|
| Grounding | RAGTruth | Source passages, generated replies, hallucination spans: exactly "is this reply supported by the supplied evidence" | Query relevance needs separate labels |
| Sensitive information | AI4Privacy PII Masking 300k (English subset) | Text, spans, masked output: scores detection and the actual masking | Synthetic; custom licence, check before redistribution; map entity types explicitly |
| Prompt attacks | PINT (Check Point, was Lakera) | Attacks, benign documents, confusing-but-benign inputs; its published evaluation already includes Bedrock, Azure Prompt Shields, Model Armor | Confirm access to the actual cases; part is proprietary |
| Indirect prompt attacks | Microsoft LLMail-Inject | Attacks arriving inside emails with scenario context and benign email controls | Attack present and attack succeeded are different labels; keep the context |
| Content false positives | XSTest | Exaggerated safety on benign requests, beside OR-Bench | Its safe label does not say whether a sensitive category is present |
| Denied topics | BARRED, selectively | The health-advice task separates prohibited advice from permitted discussion | Import only tasks expressible as a topic rule |
| Word filters | A small published deterministic set, ours | Configured list, text, expected matches: case, punctuation, boundaries, lookalikes | Expected behaviour specified independently of any vendor |
| Later | ToxicChat (real conversations; non-commercial licence), HaluBench (more grounding domains; contains RAGTruth-derived rows, deduplicate) | | |

Correction made the same day: JailbreakBench behaviors are harmful and benign *goals* with no attack technique
applied, so they now feed F1 harmful-request classification (subtask harmful_goal), not F2 jailbreak. Real jailbreak
prompts (the JBB artifacts) are a separate loader still to write. Gandalf supplies leakage positives only; benign
controls for that subtask come from the injection set until a paired benign source is added.

For every import, record the original task and label (what "positive" meant there), the shared input every system
receives, each adaptation (mapping, wording, truncation; a substantive change sends the label back for review), and
coverage (which services and models can attempt it at all).
