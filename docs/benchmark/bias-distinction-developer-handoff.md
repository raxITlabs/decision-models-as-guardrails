# Clarify bias testing in Gold Rails

## The fundamental problem

Our current presentation of “bias” is confusing because it groups together tests that answer different questions:

- Can the system detect discriminatory content?
- Does the guardrail itself treat comparable content differently across identity groups?
- Does a decision model make stereotyped assumptions on the dataset’s decision tasks?

These are related, but they are not interchangeable. A system can detect hateful content accurately while unfairly blocking harmless identity-related content. Neither result establishes how it performs on other decision-bias tasks.

We need to distinguish these questions throughout the dataset documentation, methodology and results. This is a clarification of what the experiments measure—not a reason to discard the work.

## Keep the benchmark objective unchanged

**Can a decision-model implementation perform these guardrail functions, at what quality, cost and latency?**

The dataset supplies the reference answers. Bedrock and Jev are systems under test; neither defines correctness.

## Organize the assessment into three parts

| Part | What it measures | Place in the assessment |
|---|---|---|
| Hate and discrimination detection | Whether the system detects content labelled as hateful or discriminatory. | Within the core content-moderation suite, where the source labels support that task. |
| Guardrail fairness diagnostics | Whether false blocks or missed violations differ across identity groups, and whether equivalent identity-swapped examples receive consistent decisions. | Alongside the core results, outside the overall quality score. |
| Decision-model bias diagnostics | Whether the model makes unsupported stereotyped assumptions in the existing dataset tasks. | A separate supplementary evaluation. Bedrock is not applicable where it cannot perform the same task. |

Do not add hiring questions or new scenarios for this clarification. Use the existing datasets.

## Developer actions

1. **Audit the existing bias tasks and their mappings.** For each, record the original source task, reference labels, adaptations, model input and expected output. Map it to the appropriate part above. A toxicity label or identity mention must not automatically become a discrimination label.
2. **Replace the generic “Bias” heading.** Use the specific names above. Add a short explanation distinguishing detection of discriminatory content from fairness of the detector.
3. **Preserve current results.** Keep historical runs, scores and denominators unchanged during this reporting correction. Do not silently move bias rows into the content suite or count the same examples twice. Any scoring change requires a separately documented analysis.
4. **Report fairness with the necessary context.** Show group sample sizes, false-positive and false-negative rates, and uncertainty. For matched pairs, show both decision consistency and correctness: a system that allows everything can be perfectly consistent while failing its task. Flag insufficient evidence where comparisons are too small or unmatched.
5. **Use all three parts in the overall assessment, without forcing them into one number.** The six-suite score summarizes the defined guardrail tasks. Fairness diagnostics qualify whether that performance is consistent across groups. Supplementary decision-model tests support only their own task-specific conclusions.

## Claims to avoid

- A moderation accuracy score is not a fairness percentage.
- Detecting hate does not establish that a system is free of bias.
- No observed group difference does not prove equal treatment.
- Bedrock’s hate filter is not a general-purpose bias detector.
- A demographic difference on unmatched scenarios does not isolate demographic bias.

AWS describes identity-based discrimination within its Hate category; it does not list a separate general-purpose bias content filter. See [AWS content-filter definitions](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-content-filters.html).

## Completion criteria

A reader should be able to identify **what was tested, what defines correctness, which systems are comparable, and what the evidence supports** for every result.

Keep the public version **v0.0.1**, the results site local, and historical results intact. Complete this clarification without dataset expansion or new model calls unless the audit identifies a specific invalidating defect.
