# Incident response and showcase ideas

Context: raxIT's thesis is a self-improving security harness. Incidents become threat signatures, signatures become protection. The kill-the-god-agent demo repo already has Cedar policies and agent scenarios. No IR playbook material existed in the vault before this session.

Rated 1 to 5 on thesis fit, five-minute demo-ability, defensibility against "why not just an LLM", effort (5 is least), and business outcome clarity.

| # | Use case | Thesis | Demo | vs LLM | Effort | Outcome |
|---|---|---|---|---|---|---|
| 1 | Playbook-as-code triage gate. Every harness event goes through one Jev call: incident class (Choice), severity (Score), containment action (Choice), needs-human (Noul). Code executes the playbook step. Confidence decides auto-contain, ask analyst, or page. | 5 | 5 | 5 | 3 | 4 |
| 2 | Post-run review that mints signatures. Jev screens each completed agent trace: acted on injected text, touched secrets, drifted from task. Positives become candidate signatures, which become Cedar rules. | 5 | 4 | 4 | 3 | 4 |
| 3 | Regulatory notification clock. Reportable under CPS 234, SOCI, or the NDB scheme, which clock, what evidence is missing. Human confirms. | 3 | 4 | 3 | 2 | 5 |
| 4 | Playbook coverage lint. Does an existing playbook cover each incident class this month. | 3 | 3 | 3 | 2 | 3 |
| 5 | Classic SOC alert triage. Every vendor already demos this. | 2 | 4 | 2 | 2 | 3 |
| 6 | Voting triad (the MAGI idea from X). Three independent question sets vote. Fun, thin. | 2 | 5 | 2 | 2 | 1 |

## Recommendation

Ideas 1 and 2 as one loop: detect in the harness, triage with Jev, contain in code, review the trace after the run, mint a signature, push it into the Cedar gate so the next run is blocked deterministically. Closes the flywheel live and reuses existing scenarios. Idea 3 is the best follow-on for regulated-middle sales conversations but needs regime rules encoded carefully.

This thinking fed directly into the Bedrock Guardrails design in 05 and 06.
