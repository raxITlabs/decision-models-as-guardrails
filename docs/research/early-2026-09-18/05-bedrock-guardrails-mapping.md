# Bedrock Guardrails, rebuilt on Jev

Question: can we build the equivalent of Amazon Bedrock Guardrails powered entirely by Jev? Short answer: most of it, one piece by a different mechanism, one piece not at all, and the interesting part is what Bedrock does not do.

## Policy by policy

| Bedrock policy | Jev version | Verdict |
|---|---|---|
| Content filters (hate, insults, sexual, violence, misconduct) with strength levels | One Noul per category and one Score for severity in one request. TypeSafe's guardrails cookbook is this. Strength level becomes a probability threshold. | Direct replacement |
| Prompt attacks (injection, jailbreak) | Noul "does this try to override or reveal instructions." Cookbook tested on the in-the-wild jailbreak dataset. | Direct replacement, with the adversarial caveat below |
| Denied topics (natural-language definitions plus examples) | Noul per topic with the definition and examples in the criteria, or one Choice over topics plus "none." Customers write criteria the way they write Bedrock topic definitions. | Direct replacement |
| Word filters, profanity, custom lists | Code. Regex. Jev adds nothing and its own docs say matching belongs in code. | Stays deterministic |
| Sensitive information (PII types, block or mask, custom regex) | Regex finds candidate spans, Jev confirms each is a real identifier and not a test fixture or order number. Masking is code. Pre-parsed extraction cookbook. | Replacement, better on false positives |
| Contextual grounding (grounding and relevance scores for RAG) | Choice per claim: source supports, contradicts, or is silent. Score for relevance. Citation-check cookbook. | Direct replacement |
| Automated Reasoning checks (formal proofs against a natural-language policy) | Jev cannot prove anything. It can extract typed facts (amount, actor, resource, intent) and a deterministic engine decides. That engine is Cedar. Bedrock proves; we mediate. | Different mechanism |
| Image content filters | No. Jev is text only. Caption or OCR first. | Gap |
| ApplyGuardrail API, model-agnostic | This is the product shape: a gate in front of any model on any host. | Same shape |

## What Bedrock does not have

Bedrock is content-centric. It checks what the user typed and what the model said. It does not check what the agent is about to do. Adding tool-call scope (Noul), next-action risk (Score from read-only to irreversible), trace deviation (Noul), and secret leakage in tool outputs turns a content guardrail into an action guardrail. One request per turn covers all of it.

Calibrated confidence per question is the other thing Bedrock lacks. Their strength levels are static. Confidence lets code route: pass above one threshold, hold for review in the middle, block below, with different thresholds for a read and a wire transfer.

## Cost, list prices only, unverified

Bedrock Guardrails charges per policy per evaluation. Around $0.15 per 1,000 characters for content filters and denied topics, $0.10 for PII and grounding, per source. A full stack on both input and output is roughly $2 per million tokens. Jev is $0.042 per million input tokens for the whole question set, output free. Somewhere between 15x and 50x cheaper on paper. Both sides are vendor numbers.

## The two problems that decide credibility

1. TypeSafe's jaggedness page says adversarial content "can move the answer" and state is not treated as hostile by default. That is the property a guardrail must have. A guardrail built on Jev alone is one an attacker can talk past, the same critique TypeSafe levels at system prompts. Jev cannot be the only layer. It is the fast semantic layer between deterministic checks (regex, allowlists, Cedar) and human review. The NIST result that no finite guardrail set is universally robust argues for the learning loop: every bypass becomes a new question in the question set.
2. Jev proposes, code decides. "Can't hallucinate but can still be wrong" has to be the design principle on the box.

## Three product shapes considered

- A. Drop-in ApplyGuardrail clone. Same policies, Jev underneath, cheaper. Easy to benchmark, commodity the day AWS reprices.
- B. Action guardrail for agents. Content policies as table stakes plus tool-call scope, action risk, trace review, confidence routing, Cedar as the gate. What Bedrock does not do.
- C. Jev as the signature engine inside the existing raxIT harness. Smallest build, hardest to demo alone.

Decision: combine A and B. See 06.
