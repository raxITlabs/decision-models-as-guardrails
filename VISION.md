# [gold]rails: vision

## Why

Our core question is: Can this new class of decision models—Jev, Kev, Open-Jev and similar systems—provide guardrails that are competitive with managed services such as Amazon Bedrock Guardrails?

We want to understand:

* Effectiveness: Do they detect harmful requests and unsafe responses while allowing legitimate use?
* Flexibility: Can they follow an application's written policy, including exceptions and context?
* Operational value: How do latency, cost, reliability and implementation effort compare?
* How they work as guardrails: What questions, thresholds and application logic are required to turn their outputs into useful decisions?

The comparison is between configured guardrail detectors across selected task suites: a decision model with its questions and decision rules, and a managed service with the policies configured for each suite. It does not cover every capability of either, so untested capabilities are listed with the results. Both should be evaluated against the same independently defined policy and held-out examples, with comparable tuning effort.

Separate capability tests will help explain the results—for example, whether a failure comes from the model, question wording, threshold or unsupported functionality.

The benchmark should establish where decision models are a credible alternative or complement to managed guardrails, where they fall short, and what adopting them requires.

## The question, sharpened

Across Bedrock Guardrails' six comparable capabilities (content filtering, prompt attacks, denied topics, word
filters, sensitive information detection and masking, contextual grounding and relevance), how competitive are
decision-model implementations on quality, cost and latency, and with what limitations? Automated Reasoning is an
explicit exclusion: formal verification is a different capability from the models under test.

## How that shapes the work

- The selected dataset's task definition and expected outcomes define correctness. Bedrock and decision-model implementations receive equivalent test cases and are scored against that same reference. A published label is ground truth for its original task, not for every task we might assign it, so each import records what "positive" meant at the source and every adaptation made.
- The raxIT custom-policy study (docs/17) is separate and optional. It does not block the core benchmark.
- Everything a result depends on is recorded: dataset hash, question wording, model checkpoint, threshold, and the raw responses. A number without those is not a result.
- The dataset lives on Hugging Face under raxITLabs; the results live on raxit.ai; anyone can rerun the whole thing in their own cloud project from this repository.

See [docs/18](docs/benchmark/18-benchmark-structure.md) for the six suites and the results format, [docs/14](docs/benchmark/14-gold-rails-v1-spec.md) for the v1 plan and [docs/16](docs/benchmark/16-evaluation-contract.md) for what a run may claim and what must exist before the next one.
