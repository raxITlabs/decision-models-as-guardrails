# Developer handoff: dataset first, benchmark on a frozen subset

Reviewed with the project owner, 23 September 2026. Proceed with preparation and implementation on this basis. This replaces the earlier assumption that the complete dataset must be evaluated, or every candidate reviewed, before v1 can move forward.

## Direction

The dataset and benchmark are separate deliverables:

1. Assemble a versioned Gold Rails dataset in our common format and prepare its Hugging Face release.
2. Select a smaller, representative, eligible subset for the first benchmark; run the implementations on that subset and publish the category cost–performance charts and overall comparison.

Do not wait for a massive dataset, an arbitrary row count, or exhaustive feature coverage. Preserve clear scope and correct comparisons. Use reasonable documented defaults for routine choices; raise only blockers affecting correctness, rights to publish, required human input, or the spending ceiling.

## Dataset deliverable

- Use the rebuilt, pinned sources and passing integrity/leakage audit as the foundation. Preserve source labels, mappings, provenance, group IDs, review status and stable identities.
- Keep reviewed authored cases, established source-labelled cases, and proposed/unreviewed cases distinguishable. Established source labels do not all need new human review; adaptations that change their meaning do.
- Unreviewed authored cases may remain in a clearly marked candidate configuration or partition. They must not silently enter the scored benchmark subset.
- Keep previously examined rows tuning-only and preserve conversation/document/attack-family/counterfactual grouping.
- Prepare the dataset card, real counts, coverage exclusions, licenses and rebuild instructions. Publish permitted text only. For restricted or unresolved sources, include IDs and acquisition instructions only where those are permitted.
- Give the release a version and checksum. Later additions create a new version; they do not change the dataset beneath an existing result.

## First benchmark subset

- Choose the smallest useful stratified subset supported by the budget and existing eligible labels. A planning range of approximately 1,000–2,000 core cases plus a modest bias subset is reasonable; it is not a mandatory target or a statistical guarantee.
- Select cases before viewing model outcomes. Record selection seed, source dataset version, exact IDs, groups and counts by suite/subtask/class. Include both violations and benign controls; do not use easy cases merely to fill quotas.
- Separate tuning from untouched test within the selection while respecting existing dataset splits. Do not promote examined tuning cases into test. Reuse existing tuning results only when input and implementation equivalence is verified.
- The 300-benign-case floor is a precision aspiration for a larger release, not a v1 blocker. Existing prompt-attack negatives can be used with disclosed sample sizes and confidence intervals.
- Denied topics still needs fresh eligible test positives and negatives. Build a modest diverse set for the first subset, rather than insisting on 300 cases immediately. AI-assisted drafting is acceptable; document it and have a human validate those authored labels independently of model predictions.
- One human can review ordinary authored cases; use a second review for ambiguous cases and all bias pairs. If reviewers are unavailable, keep these cases outside the scored subset and state the resulting missing coverage rather than claim independent review.

## Scope and scoring defaults

- Six English detection suites; direct-only prompt attacks for v1. Defer indirect attacks and query relevance with explicit coverage labels. Keep masking separately scored and outside the detection release's critical path. Automated Reasoning remains excluded.
- Bias is required work. Complete the small bias smoke, then include eligible source-backed bias tasks in the first evaluation. Counterfactual pairs enter scored results after review. Distinguish guardrail fairness from decision-model bias; Bedrock is not applicable to unsupported decision/QA tasks.
- Use the proposed balanced-accuracy headline, equal subtask weights within suites, equal weights across the six core suites, and the secondary recall-at-5%-tuning-FPR view. Show actual test false-positive rates and uncertainty.
- Publish category results even if one suite is not yet eligible. Publish the six-suite overall score only once all required suites are evaluated; do not silently average away missing coverage. Bias is reported separately.
- Keep the regex word-filter baseline visible. Record any supporting rules or extraction used by a model implementation.

## Freeze and execute

- Update doc 19 and the readiness packet to reflect this dataset/subset distinction and these defaults; do not reopen settled routine choices.
- Fit questions/configurations/thresholds on tuning only. Commit the subset and configuration manifest before test calls; final scoring loads the frozen thresholds. Keep all attempts and follow the transient-only retry policy.
- Record measured API usage, allocated serving time, declared load, latency and failures. Produce cost per 1,000 evaluations and category charts, followed by the complete-core aggregate. Do not present forecasts as measured costs.
- Corrections preserve the original run. Performance-driven changes require a fresh untouched holdout for a new final claim.
- Recompute the forecast for the smaller subset. Retain the existing $100 total project ceiling; the earlier $70 figure is an upper-bound proposal, not a spend target or newly granted approval. Do not incur a new unapproved charge on the strength of this handoff.

## Next return

Continue offline work without another broad decision questionnaire. Return a concise release/run packet: dataset version and counts, subset manifest, remaining human-review assignments, declared exclusions, frozen configuration status, and forecast spend. Identify publication or spending approval still required, if any. Once authorized, execute and publish rather than starting another open-ended planning cycle.

Definition of success: a usable versioned dataset plus an honestly scoped first benchmark with category quality-versus-cost charts, clear uncertainty and coverage, and an overall score when the six-suite comparison is complete.
