# decision-models-as-guardrails

A benchmark that asks one question: can a decision model replace a managed guardrail service? It sends the same
labelled rows to decision models (Jev, Kev, Open-Jev, Laya, Clef, pplx-decider, Strands Decider, gpt-6-luna) and to
Amazon Bedrock Guardrails, and compares them on accuracy and cost. Built by raxIT Labs.

The dataset is on Hugging Face as
[`raxITLabs/decision-models-as-guardrails`](https://huggingface.co/datasets/raxITLabs/decision-models-as-guardrails).
This repository holds the code that builds it, the code that runs every system against it, and the rules the scorer
follows.

## What is tested

Six suites, weighted equally in the overall score:

| Suite | A row asks |
|---|---|
| Content | Is this request or reply harmful under the content policy? |
| Prompt attacks | Is this message (direct) or this retrieved document (indirect) trying to change the assistant's instructions, jailbreak it or pull out its configuration? |
| Denied topics | Does this request fall under one of eight topics the application refuses? |
| Profanity | Does this text contain profanity? |
| Sensitive information | Which personal data types does this text contain? |
| Grounding | Does this reply make a claim its source does not support? |

A custom-words check runs beside the score as a pass or fail sanity test. Each suite's written policy is in
[`benchmark/policies/`](benchmark/policies/).

Every system is scored the same way. A decision model answers yes/no questions with a probability, and 0.5 or more
counts as yes. Nothing is tuned per model. The score is balanced accuracy on the test split, with paired bootstrap
intervals and tiers from Holm-adjusted tests. Part of the test split is held back as an unpublished slice. Every row
in it comes from public upstream data, so it is a contamination check, not a secret test. The scorer's rules are in
[`benchmark/contracts/v2.0.json`](benchmark/contracts/v2.0.json).

## Layout

```
dataset/      goldrails_dataset/ builds the dataset from the candidate rows and labels in dataset/edition2/
benchmark/    goldrails_bench/ (adapters, hosted clients, freeze and overlap checks, scorer), runs/ (run scripts),
              question_sets/, policies/, contracts/, subsets/ (freeze manifests)
infra/        Terraform for the GPU VM that serves the open models, and for the Bedrock guardrails
docs/         the evaluation contract and plan, and copies of vendor docs that the overlap scan reads
```

Python packages and folders keep the project's working names (`goldrails_dataset`, `goldrails_bench`).

## Reproduce it

[`REPRODUCE.md`](REPRODUCE.md) is the full guide. It lists each account, the GPU machine, and the cost and time for each
step. A coding agent can follow it. Point your agent at that file or at
https://decision-models-as-guardrails.vercel.app/reproduce.md. The agent runs the free steps and asks before any paid step.

The short version:

| To run | You need | Our cost (Oct 2026) |
|---|---|---|
| Tests, dataset, cost forecast | Python 3.12+, `uv`, git | Free |
| Jev 1.13 | TypeSafe API key | USD 0.38 |
| pplx-decider v1 27B | Perplexity API key | USD 0.56 |
| GPT-6 Luna | OpenAI key with Decisions API access (public beta) | USD 1.10 |
| Clef, Clef Flash | Cloudflare Workers AI. In practice you need the Workers Paid plan (USD 5 a month) | USD 2.76 |
| Amazon Bedrock Guardrails | AWS account with Bedrock, a CLI profile, Terraform (`infra/aws/`) | USD 1.12 |
| Kev 0.8B/4B/9B, Open-Jev 2B, Strands Decider 2B, Laya | Google Cloud project with quota for 2 NVIDIA L4 GPUs, `gcloud`, Terraform (`infra/gcp/`); one `g2-standard-24` VM, about USD 2 an hour on demand | USD 10.44 |

We do not publish the held-back slice (2,269 of the 9,975 checks). A rerun from a fresh clone covers the 7,706 public
rows only. Its scores are close to the board, but not identical.

```bash
uv sync --extra dev
uv run --with scikit-learn python -m pytest
cp .env.example .env    # API keys for the hosted systems you want to run
```

Each run script in [`benchmark/runs/`](benchmark/runs/) writes a freeze manifest first. It sends no row until you commit
that manifest. The commit proves that the configuration came before the results. `make up` starts the model VM and
`make pause` stops it (see [`infra/gcp/README.md`](infra/gcp/README.md)).

## Licences

The code is Apache-2.0. Each dataset row keeps its source's licence, listed per source in the dataset's `SOURCES.md`.
The record schema (`dataset/goldrails_dataset/records.py`) is adapted from
[JevBench](https://github.com/fstandhartinger/jevbench) (MIT).
