# AGENTS.md

Instructions for coding agents working in this repository.

## What this is

A benchmark that scores guardrail systems on accuracy and cost.

- `dataset/` builds the dataset.
- `benchmark/` runs every system and scores it.
- `infra/` holds Terraform for the GPU VM (Google Cloud) and the Bedrock guardrails (AWS).
- `site/` is the results website (Next.js). It has its own `site/AGENTS.md`.

## If you were asked to reproduce the benchmark

Follow `REPRODUCE.md` step by step. It lists the accounts, infrastructure, cost and time for each step. Steps 1 and 2
are free. Before any step that sends rows to a paid API or starts the GPU VM, ask the person and wait for a yes.

## Rules

- Python: use `uv` for everything (`uv sync --extra dev`, `uv run ...`). Never `pip install`.
- Tests: `uv run --with scikit-learn python -m pytest -q` (or `make test`). The tests need no API keys.
- Put keys in `.env`. Copy `.env.example` to make it. Never print, log or commit a key.
- Do not edit `benchmark/contracts/` (the scoring rules) or `benchmark/subsets/` (freeze manifests) to make a run
  pass. If a run needs a change there, that is a new release, not a fix.
- The held-back slice and the raw run ledgers are not in this repository. Code that reads them fails on purpose on
  any machine other than the maintainers'.
- Site: `cd site && pnpm install && pnpm dev`. Use `pnpm`, not `npx`.
