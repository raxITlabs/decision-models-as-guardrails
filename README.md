# jev-as-a-guardrails

A guardrail benchmark for decision models, built by raxIT Labs. Two deliverables, two folders: [`dataset/`](dataset/) builds the jev-as-a-guardrails dataset, published on Hugging Face as [`raxITLabs/jev-as-a-guardrails`](https://huggingface.co/datasets/raxITLabs/jev-as-a-guardrails), and [`benchmark/`](benchmark/) runs decision models and managed guardrail services against it. [`infra/`](infra/gcp/README.md) provisions the model-serving VM in your own GCP project. [`docs/`](docs/README.md) is everything to read. New to the benchmark? Start with the [jev-as-a-guardrails primer](https://raxitlabs.github.io/jev-as-a-guardrails/teach/gold-rails-primer.html), a one-page walkthrough of how it works (source: [`docs/teach/gold-rails-primer.html`](docs/teach/gold-rails-primer.html)). Notebooks are the reference for every step and run from a clean checkout.

## Run it

```bash
uv sync --extra notebooks --extra dev
uv run pytest
uv run python -m goldrails_dataset.build --out dataset/samples/pilot --per-cell 25 --seed 7
cp .env.example .env   # add TYPESAFE_API_KEY
uv run jupyter lab
```

The VM lifecycle is four verbs (`make help` lists everything):

```bash
make up      # create or resume the model VM, open tunnels, wait until every model answers (~4 min resume, ~10 min first boot)
make run     # execute notebook 04 against it (NB=path for another notebook)
make pause   # stop the VM, keep the disk and weights; ~$2/h stops, ~$20/month of disk continues
make down    # destroy everything; nothing left billing
```

Notebooks, in order:

- `dataset/notebooks/01_build_pilot_sample.ipynb` assembles a 250-row pilot from seven ungated public sources and shows what is in it.
- `benchmark/notebooks/02_smoke_jev.ipynb` sends ten rows to Jev with a six-question question set and prints the raw answers next to the labels.
- `benchmark/notebooks/03_jev_vs_kev_two_question_sets.ipynb` runs Jev and a local Kev-0.8B over the pilot with the v1 and v2 question sets.
- `benchmark/notebooks/04_cloud_pass_pilot.ipynb` runs Jev plus the open models served from the GCP VM: Kev 0.8B/4B/9B, Open-Jev-2B and Laya (`make up` first).

## Layout

```
dataset/     goldrails_dataset/ (schema, taxonomy, loaders, build), notebooks/, samples/, tests/
benchmark/   goldrails_bench/ (System One client, endpoint discovery), question_sets/, notebooks/, results/, tests/
infra/       gcp/ Terraform for the model VM, ctl.sh (up/pause/down/status), tunnels.sh
docs/        numbered research notes, reports/, specs/, prior-art/, transcripts/, typesafe-reference/, research-raw/, ts-spikes/
```

`dataset/samples/` holds the 250-row pilot and the older 1k sample that the notebooks and early smoke runs used. Its manifest lists two PII files, `F5.test.jsonl` and `F5.tune.jsonl`, that are not here: their rows came from AI4Privacy, whose licence needs written permission to redistribute. `load_rows` reads the pilot unless `GOLDRAILS_DATA` names another sample or the Hugging Face dataset. The benchmark runs pick their rows through the frozen subsets in `benchmark/subsets/`. `benchmark/results/` holds per-run JSONL and receipts, which is what the raxit.ai results section reads.

The Python side is a uv workspace: `goldrails-bench` depends on `goldrails-dataset`, one lockfile at the root.

The record schema (`dataset/goldrails_dataset/records.py`) is adapted from [JevBench](https://github.com/fstandhartinger/jevbench) (MIT). Sources keep their own licences; see each loader's docstring.

Status: two benchmark runs. The results site (`site/leaderboard/`) shows the second run, whose leaderboard the evaluator marks valid for publication. The first run's results stay on file beside it.

Renamed on 30 September 2026: the benchmark was called [gold]rails. Code identifiers keep the old name (the `goldrails_bench` and `goldrails_dataset` packages, `GOLDRAILS_*` variables, file names), and so do dated records written before the rename. The Hugging Face dataset moved from `raxITLabs/goldrails` to `raxITLabs/jev-as-a-guardrails` the same day.

## History

Until 2026-10-02 this repository was an export of a private working repo; that history is archived offline. Since then this is the only working repository. Commits land here directly, and `scripts/export_public.py` is no longer how a release gets built.

The export history matters in one place. The page checks (`benchmark/runs/check_page.py`) confirm that each run's freeze manifests were committed before its test ledgers, and here those files arrived together in export commits. So the checks read the dates from `benchmark/history/private-history.json`, a record of the private `git log` for every frozen file and ledger, and only for files whose bytes still match it. `scripts/record_private_history.py --check` rebuilds that record from the archive bundle and compares the two. [EXPORT.md](EXPORT.md) lists what the export left out, and why.
