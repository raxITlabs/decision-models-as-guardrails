# Recommendation: Jev as the semantic uplift for runtime-security-core, with skills as the wedge

Written 21 September 2026. Inputs: the OWASP Agentic Skills Top 10 checklist, a read of runtime-security-core (ADR-0009, ADR-0011, ADR-0013, the classify / intent / inputscan / semantic / scanner / mcp packages), the seven 2026 surveys in doc 09's memo, and docs 01 to 11.

## Correction, same day: the runtime is local-only

ADR-0009 F10: no key or network call is ever a precondition for a verdict, and the engine's promise is deterministic, no ML, on a laptop. A hosted Jev call at output-recording time is permitted by ADR-0011's receipt mechanism but puts customer tool results on a third-party wire, which the engine's buyers reject. The `intent.Classifier` and `classify.Provider` rows below are therefore **opt-in cloud uplift only, off by default**, not the primary story. What holds without qualification: install-time and CI-time skill scanning, authoring-time policy checks, and Jev as an offline labelling teacher for a small local ONNX model shipped in the ADR-0013 signed sidecar, which is what runs in the live path. Retraining after a policy change becomes one cheap Jev pass over the corpus instead of a labelling project.

## The decision

Stop treating the Jev guardrail as a standalone product that competes with Bedrock. Put Jev behind the seams runtime-security-core already has for a non-deterministic classifier, and make skills the first thing it judges. The engine keeps its invariant (no LLM in the decision path, replayable from the DPR). Jev supplies the one thing the engine's own package docs say it lacks: "behavioral / semantic analysis (not just pattern matching)", which is OWASP AST08's first check and the reason 13.4% of critical skills got past Snyk's regexes.

Three reasons this beats the standalone guardrail:

1. **We already own the deterministic half.** Scanner, Cedar policy generation, MCP proxy with description scanning, taint tracking, kill switch, DPR receipts, warrant approvals, compliance report. That is tiers 1, 3, and most of 4 of the defence-in-depth design in doc 11. Only tier 2 is missing, and ADR-0011 already specifies exactly how a model may feed it.
2. **The buyer research points here.** 82% of mid-market agent builders rely on provider-native controls; 30% keep an agent inventory; 7.2% have a named owner. A skill inventory with risk tiers, install receipts, and per-invocation audit is OWASP AST09 verbatim and a CTO can adopt it without a security org.
3. **Skills are a named, fresh, measurable threat.** ClawHavoc: 1,184 malicious skills, five of the seven most-downloaded ClawHub skills confirmed malware. OWASP published a Top 10 and a checklist. NVIDIA's SkillSpector and Alice's Caterpillar exist but no one has a labelled benchmark that says how well semantic scanning of SKILL.md actually works. That benchmark is the research project.

## Where Jev plugs in, seam by seam

Every integration below respects ADR-0011: Jev never runs inside `Govern`; its output is recorded as a receipt before it becomes a fact; `Govern` reads the fact; replay reconstructs from the DPR and never re-invokes Jev.

| Engine seam | Today | With Jev | OWASP items |
|---|---|---|---|
| **Opt-in cloud only.** `intent.Classifier` (async, observe-only, TTL fact in session, enforced only when Cedar has a `when intent ==` condition) | Keyword rules on tool id | Jev Choice over intent classes plus a risk Score, on `{tool, args, user's recent turns, invoking skill's declared purpose}`. Shadow mode is the package's default already. | 3.2, B4 audit |
| **Opt-in cloud only; default is the distilled local model.** `classify.Provider` (non-sealed, runs at `RecordOutput` / `ScanAndRecord`, labels enter `CAR.Taint` after a DPR receipt) | Regex taint labels PII / SECRET / FINANCIAL | Regex finds candidates, Jev confirms each with one Noul (real secret vs test fixture), and adds a new label `UNTRUSTED_INSTRUCTION` when a tool result carries text aimed at the agent. A tainted session then hits the existing trifecta `forbid` on egress. This is jev-guard's ingress scan, made replayable. | 5.1 to 5.6 at runtime, 3.8 |
| `inputscan` and `mcp` description_scan (deterministic, fail-closed) | Unicode smuggling, hidden-phrase list, 7-vector detector | Unchanged as tier 1. Jev runs second, only on what passes, with Nouls for tool poisoning, description-vs-schema mismatch, and instructions addressed to the model. | 4.1, 4.2, AST01 for MCP tools |
| `scanner` / `raxit init` (repo scan to capabilities to Cedar) | Tool and endpoint discovery, shell heuristics | New `raxit skill scan`: for each skill, deterministic checks first (hash, signature, manifest schema, yaml safe-load, secret scan, external-reference inventory, identity-file writes), then Jev over the natural-language layer: does the instruction file ask the agent to do anything beyond its stated purpose or hidden from the user; is the description consistent with the scripts; is the declared risk tier consistent with requested permissions; does it instruct fetching from unpinned URLs. Output: risk tier L0 to L3 and a receipt into the inventory. | 1.2, 1.4, 1.6, 4.1, 4.2, 4.5, 5.1, 5.5, 8.1, 8.2, 9.1, 9.2 |
| Cedar policy generation | From tool inventory | From skill manifests too: a skill's declared permissions (3.1 to 3.8) become the Cedar allow set for calls made while that skill is active; `skill_id` travels in `CAR.Context`. A call outside the manifest is denied deterministically; a call inside it but semantically off-purpose is flagged by the intent seam. | AST03, 6.2, 6.7, 9.4 |
| DPR and compliance report | Framework-mapped evidence | Every Jev receipt (provider id, model version, question ids, probabilities) is evidence. The report gains an "OWASP Agentic Skills Top 10" mapping alongside EU AI Act / NIST / ISO 42001. | AST09 |

What stays deterministic and never touches Jev: hash pinning, signatures, TUF verification, sandboxing, network allowlists, YAML loaders, the verdict itself.

## What this does to the guardrail work so far

- The content-filter question set, calibration step, and indicator-Noul design (docs 11, spec) become the `classify.Provider` implementation. Nothing is wasted.
- The `/v1/evaluate` API still exists, as the sidecar the engine calls at output-recording time, not as a customer-facing Bedrock alternative. It can be exposed later if a customer wants it standalone.
- The Bedrock comparison shrinks to one column in a broader eval and stops being the headline.

## Runtime path that keeps local-only

1. Define taint and intent classes as Jev questions (policy as text).
2. Run Jev offline over a labelled or synthetic corpus per class; record receipts.
3. Train a frozen small encoder plus a linear head on Jev's labels and code features; validate against human labels.
4. Package as an ADR-0013 signed model bundle for the classifier sidecar; the engine loads it locally, no network.
5. When the policy changes, repeat steps 2 to 4. Jev's cost makes this a nightly job.

## The research project, restated

Question: how much does a System One model add to deterministic scanning of agent skills and tool results, at what cost, and where does it fail?

Corpus: the toxicskills-goof samples, the ClawHavoc skill set where obtainable, SkillSpector's test fixtures, plus a benign set drawn from popular skill registries and our own skills. Label each against the checklist items that need judgment (1.2, 1.4, 4.1, 4.5, 8.1). Add the in-the-wild jailbreak set and Aegis for the tool-result taint labels.

Arms: regex-only (`inputscan` as is), Jev semantic layer, SkillSpector's optional LLM mode, and a frozen small encoder trained on the labelled skills. Report precision, recall, cost, and latency per checklist item. Publish the corpus, the questions, and the receipts.

Go/no-go, written before the run: Jev must raise recall on the semantic checklist items by a margin that matters over regex alone, at a false-positive rate a developer will tolerate on install, and the receipts must replay bit-for-bit through the engine.

## First four weeks

1. Week 1: `raxit skill scan` deterministic half, wired to the existing scanner and inventory. Corpus collection starts.
2. Week 2: Jev `classify.Provider` and `intent.Classifier` implementations behind ADR-0011 receipts, shadow mode only. Reuse the question set code.
3. Week 3: Jev semantic layer in `skill scan`; eval harness over the corpus with all four arms.
4. Week 4: results, go/no-go, and a writeup mapped to the OWASP checklist. If go, the MCP description-scan uplift and Cedar-from-manifest follow.

## Sources

- OWASP Agentic Skills Top 10 checklist: https://github.com/OWASP/www-project-agentic-skills-top-10/blob/main/checklist.md
- runtime-security-core: README, ADR-0009, ADR-0011, ADR-0013, `internal/classify`, `internal/intent`, `internal/inputscan`, `internal/semantic`, `internal/scanner`, `internal/mcp`
- docs 09, 10, 11 in this folder; the decision memo artifact
