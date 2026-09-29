# Gold Rails

A guardrail benchmark for decision models, built by raxIT Labs. Two deliverables, two folders: [`dataset/`](dataset/) builds the Gold Rails dataset that will live on Hugging Face under `raxITLabs`, and [`benchmark/`](benchmark/) runs decision models and managed guardrail services against it. [`infra/`](infra/gcp/README.md) provisions the model-serving VM in your own GCP project. [`docs/`](docs/README.md) is everything to read. New to the benchmark? Start with [`docs/teach/gold-rails-primer.html`](docs/teach/gold-rails-primer.html), a one-page walkthrough of how it works (download it and open it in a browser). Notebooks are the reference for every step and run from a clean checkout.

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

`dataset/samples/` is checked in only until the Hugging Face push exists; after that `benchmark/` pulls from `raxITLabs/goldrails` and `samples/` becomes a local cache. `benchmark/results/` holds per-run JSONL and receipts, which is what the raxit.ai results section reads.

The Python side is a uv workspace: `goldrails-bench` depends on `goldrails-dataset`, one lockfile at the root.

The record schema (`dataset/goldrails_dataset/records.py`) is adapted from [JevBench](https://github.com/fstandhartinger/jevbench) (MIT). Sources keep their own licences; see each loader's docstring.

Status: pilot. Nothing here is a result.
