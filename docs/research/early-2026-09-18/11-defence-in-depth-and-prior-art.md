# Defence in depth: a guardrail system, not a Jev call

Written 21 September 2026 from three practitioner videos, the community guardrail repos surveyed the same day, and our own runs. The question this answers: Jev is a System One classifier with a small window and no reasoning, and it only answers the questions it is asked. How do we build a guardrail that is robust when the question set is incomplete?

## What the three videos established

| Source | Finding | Consequence for us |
|---|---|---|
| Prompt Engineering, "OPEN JEVs are Here!" | One broad Noul "is this email phishing" scored ~60%. Eight concrete indicator Nouls fed to a lightweight classifier scored 94%. | Jev is a feature extractor. Code (or a small trained model) is the decider. Never ship a single "is this harmful" question. |
| Same | A frozen 22M encoder plus logistic regression beat Jev on Banking77 (93.2 vs 80.1), emotion, and phishing, at 8 ms on CPU. Jev won Yelp rating (67.2 vs 51.9) and every zero-shot or changed-policy case. | For fixed categories with labels, the honest baseline is a tiny local model. Jev's edge is custom categories, policy edits without retraining, and fan-out. Say so in the eval. |
| Same | Thirty questions cost the same latency as one. Classical zero-shot scales linearly per label. | Over-ask. Indicators, catch-alls, novelty, and self-consistency questions are near-free. |
| Same | Reported confidence 88% at 80% accuracy on Banking77. Temperature scaling cut calibration error by about two thirds. | Thresholds are tuned on our data, not the cookbook's. A calibration layer in code is cheap and expected. |
| Theo, "Jev is incredible" | Ten-second rule: if a human answers in under ten seconds after perceiving the input, Jev fits. Failed at "which threads are worth a video" after repeated prompt revisions. "Use it like an if statement." | Every question we write gets the ten-second test. Judgments that need reasoning go to the escalation tier. |
| Nate Herk, "12 Real Use Cases" | Slop labeller is one three-way Choice on tweet text, "not doing very well in the first hour". Advice: 100-case golden set, compare Jev against Opus and Sol on accuracy and cost before trusting. | Slop detection is unsolved in public and is the same architecture as the guardrail. Good showcase. Golden sets are mandatory. |

## What the community repos established

Octapull/jev-guardrail, 0xArx/jevegis, leepokai/jev-guard and their forks converged, independently and within six days, on: "treat the state as untrusted data" in every instruction; negative carve-outs in criteria ("refusals do not count", "discussing injection does not count"); three routing bands with thresholds near 0.3 and 0.7; a deterministic read-only allowlist that never calls the API; shadow mode as the default ship state; fail-closed on oversized input; and for tool calls, a Noul asking whether the user's own recent messages authorised this exact action. None measured accuracy beyond 30 to 42 hand-written cases. None covered denied topics, word filters, grounding, or PII beyond a leak Noul.

## The architecture

Four tiers. Each exists because a specific failure mode above needs it.

1. **Deterministic layer.** Word lists, regex candidates for PII and secrets, tool allowlists, schema validation, Cedar policy. Exact, free, first. Anything code can decide is never asked of Jev.
2. **Jev as evidence extractor.** Per check, many narrow indicator Nouls (not a verdict Noul), one severity Score independent of category, one catch-all Noul ("raises a safety or policy concern not covered above"), one novelty Noul ("unusual for this application's traffic"), and where useful a second phrasing of a key judgment for self-consistency. State is filtered and chunked: the message, its role, the prior turn, the relevant policy clauses. Never the whole thread.
3. **Decider.** Where labelled data exists (Bedrock's five categories via Aegis and Toxic-Chat, PII via pii-masking-300k, prompt attack via the in-the-wild set), a small classifier per check trained on Jev's indicator probabilities plus code features. Where it does not (custom categories, new denied topics), calibrated thresholds on the raw Nouls with wider review bands. Thresholds and weights live in a versioned policy object; changing them never re-runs inference.
4. **Escalation and learning.** Review band, catch-all fired, novelty high, or self-consistency disagreement routes a small slice to a System Two model with the full policy in context, or to a human. Every confirmed miss becomes a new indicator question or a Cedar rule in the next question set version. The autoresearch cookbook automates proposing candidate questions from errors.

Coverage of the seven Bedrock pillars under this design: content filters, prompt attacks, denied topics, PII, and grounding through tiers 1 to 3; word filters through tier 1 alone; Automated Reasoning is not replicated and is stated as out of scope, with typed fact extraction plus Cedar offered as the alternative mechanism.

## What this changes in the spec and the eval

- The `contentFilter` module's `plan()` returns indicator Nouls per category, not one Noul per category. Built-in indicator sets start from Bedrock's category definitions and the eight-indicator phishing decomposition as a pattern.
- A `calibration` step in code (temperature scaling per question, fitted on the labelled sets) sits between Jev answers and the decider.
- The eval adds a local baseline column: a frozen small encoder plus logistic regression trained on the same labelled rows. If it beats Jev on fixed categories, we report that and position Jev on the things it uniquely does.
- Golden set minimum: 100 labelled cases per check before any threshold is published. Nate's number, and the right one.

## Showcase

Slop detection for X and LinkedIn as the open-source demonstration: code features (em-dash density, emoji per line, hashtag count, length, link count) plus indicator Nouls (generic claim without specifics, engagement bait, listicle scaffolding, restates the headline, promotional intent, AI vocabulary), a value Score, a small classifier trained on a labelled set, and the same four tiers. Non-adversarial, public data, no privacy contradiction, and no measured version exists yet.

## Sources

- https://youtu.be/FVzI3QAxwNs (Prompt Engineering, "OPEN JEVs are Here!")
- https://youtu.be/F3YXg7AaKWE (Theo, "Jev is incredible")
- https://youtu.be/ymgH8jS6Wb8 (Nate Herk, "I Tested Jev on 12 Real Use Cases")
- https://github.com/Octapull/jev-guardrail, https://github.com/0xArx/jevegis, https://github.com/leepokai/jev-guard
- https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md, https://docs.typesafe.ai/cookbooks/sde_cascade.md, https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook.md
