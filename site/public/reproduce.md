# Reproduce decision-models-as-guardrails 1.0.0

This file shows how to rerun the benchmark. A person can follow it, or a coding agent can follow it for a person.
It lists each account, each piece of infrastructure and each cost. Read it, then decide how far to go before you
spend money.

Site: https://decision-models-as-guardrails.raxitlabs.com ·
Code: https://github.com/raxITlabs/decision-models-as-guardrails ·
Dataset: https://huggingface.co/datasets/raxITLabs/decision-models-as-guardrails (pinned at commit `13beb711`)

## If you are an AI agent

- Read this whole file before you run a command. After you clone the repository, read `AGENTS.md` too.
- Use `uv` for every Python command. Do not use `pip`. Do not make a virtual environment by hand.
- Steps 1 and 2 are free and need no accounts. Do them first. Then report the result.
- Every step from 3 on sends rows to paid APIs or starts a paid GPU machine. Before you start step 3 or a later
  step, tell the person which accounts and keys the step needs, what it costs and how long it takes. Then wait for
  a yes.
- Never print, log or commit an API key. Put keys in `.env`. Git ignores that file.
- If a command fails, stop. Show the error to the person.
- Do not edit the scoring rules (`benchmark/contracts/`) or the freeze manifests (`benchmark/subsets/`) to make a
  run pass.

## What you can and cannot reproduce

- Each system answers 9,975 checks. 7,706 are public test rows. The other 2,269 are a held-back slice. We
  do not publish that slice, so nobody outside raxIT Labs can send those rows.
- A rerun from a fresh clone covers the 7,706 public rows only. Expect scores that are close to the board but not
  identical, because the board also includes the held-back slice. On that slice, overall scores are within 2.6
  points of the public rows.
- We already publish every system's answer to the 7,606 public rows in the eight scored use cases. Find them on the Data
  page of the site, or in `site/data/rows-index.json` in this repository. You can check any number without calling a
  model. The other 100 public rows are a custom-words sanity check. It is pass or fail, outside the score, and not on
  the Data page.
- The hosted APIs do not pin a model version. For that reason alone, a rerun months later can differ.

## What you need

| To run | Account and access | Environment variables | Our cost (Oct 2026) |
|---|---|---|---|
| Steps 1 and 2 (tests, dataset) | None | None | Free |
| Jev 1.13.0 | TypeSafe API key | `TYPESAFE_API_KEY` | USD 0.38 |
| Perplexity Decisions API (pplx-decider-v1-27b) | Perplexity API key (Decisions API) | `PERPLEXITY_API_KEY` | USD 0.56 |
| OpenAI Decisions API (gpt-6-luna) | OpenAI API key with access to the Decisions API (public beta). A 403 or 404 means you do not have access yet | `OPENAI_API_KEY` | USD 1.10 |
| Clef, Clef Flash | Cloudflare account with Workers AI. In practice you need the Workers Paid plan (USD 5 a month). The free allowance of 10,000 neurons a day ran out partway through our run. Use a token scoped to Workers AI read and run | `CLOUDFLARE_ACCOUNT_ID` (the 32-character id), `CLOUDFLARE_API_TOKEN` | USD 2.76 for both, plus the plan |
| Amazon Bedrock Guardrails | AWS account with Bedrock in your region, an AWS CLI profile (we used AWS SSO) and Terraform. Your role must be able to create guardrails and guardrail versions, and to call ApplyGuardrail | `AWS_PROFILE`, `AWS_REGION` (default `us-east-1`) | USD 1.12 |
| Kev 0.8B, 4B, 9B, Open-Jev 2B, Strands Decider 2B, Laya | Google Cloud project with billing, quota for at least 2 NVIDIA L4 GPUs in your zone, the `gcloud` CLI and Terraform | Optional: `GOLDRAILS_PROJECT`, `GOLDRAILS_ZONE`, `GOLDRAILS_INSTANCE` | USD 10.44 of VM time |
| Rebuilding withheld text (optional) | Hugging Face account that has accepted the terms of the gated sources (for example `allenai/wildjailbreak`) | `HF_TOKEN` | Free |

At list prices, our three runs cost about USD 16.40 in total. The managed APIs cost USD 5.93 and the GPU machine
cost USD 10.44. Your cost depends on your region, the prices on the day, and retries. `e2_full.py all` makes a high
cost forecast first. If that forecast is above USD 30, the script stops before any call.

### The GPU machine

Terraform in `infra/gcp/` creates one Google Cloud VM for the self-hosted models:

- The machine is a `g2-standard-24` with 2 NVIDIA L4 GPUs (24 GB each) and a 200 GB disk. We ran it on demand in
  `us-east4-a` at about USD 2.00 an hour. A spot VM in `us-central1` costs about USD 0.60 an hour, but it can stop
  mid-run.
- The models are Kev 0.8B (port 8009), Kev 4B (8010), Kev 9B (8011), Laya (8012), Strands Decider 2B (8013) and
  Open-Jev 2B (8791). `infra/gcp/terraform.tfvars.full-roster.example` pins each repository and revision.
- The firewall lets in only Google's IAP range. `make up` opens IAP tunnels, and the runners reach the models
  through them.
- The first boot takes about 10 minutes for drivers and weights. A restart takes about 4 minutes. The VM shuts
  itself down after 60 idle minutes. It always shuts down after 8 hours.
- Our runs used about 6.6 hours of VM time in total. `make pause` stops the VM and keeps the disk (about USD 20 a
  month). `make down` deletes everything.
- If your zone has no L4 capacity, `make up` tries the zones in `GOLDRAILS_ZONES`.

## Steps

### 1. Install and test (free, no accounts)

You need Python 3.12 or later, `uv` and git.

```bash
git clone https://github.com/raxITlabs/decision-models-as-guardrails
cd decision-models-as-guardrails
uv sync --extra dev
uv run --with scikit-learn python -m pytest -q
```

### 2. Look at the dataset and the plan (free, no accounts)

The run scripts download the dataset from Hugging Face at the pinned commit. The `plan` commands work offline. They
list the rows per use case and forecast the cost.

```bash
uv run python benchmark/runs/e2_full.py plan
uv run python benchmark/runs/e2_smoke.py plan
```

### 3. Check one system on 20 rows per use case (small cost)

Copy `.env.example` to `.env`. Fill in only the keys for the systems you want. The compatibility check sends 20
public development rows per use case to each system that you name. It skips a system that has no key.

```bash
cp .env.example .env
uv run python benchmark/runs/e2_smoke.py run --systems jev
uv run python benchmark/runs/e2_smoke.py report
```

### 4. Set up AWS and Google Cloud (only for those systems)

```bash
aws sso login --profile "$AWS_PROFILE"
cd infra/aws && terraform init && terraform apply && cd ../..   # creates the five Bedrock guardrails

gcloud auth login
gcloud auth application-default login
make infra-init
make up        # creates or resumes the GPU VM and opens the tunnels
make status
```

### 5. Run the full benchmark (paid)

Each run writes a freeze manifest first. It sends nothing until you commit that manifest. This fixes the
configuration before any result exists.

```bash
uv run python benchmark/runs/e2_full.py preflight      # checks keys, VM and AWS session; no model call
uv run python benchmark/runs/e2_full.py freeze         # then: git add benchmark/subsets && git commit
uv run python benchmark/runs/e2_full.py all            # content, topics, profanity, personal data, grounding
uv run python benchmark/runs/e2_attacks_rerun.py freeze
uv run python benchmark/runs/e2_attacks_rerun.py all    # direct and indirect prompt attacks
uv run python benchmark/runs/e2_openai_run.py freeze
uv run python benchmark/runs/e2_openai_run.py all       # OpenAI Decisions API
make pause                                              # stop paying for the VM
```

To run only some systems, use `uv run python benchmark/runs/e2_full.py run --systems jev,clef`. To send again only
the rows that failed, for example after a rate limit, add `--retry-failed`.

Times on our run: Jev about 4 minutes, the OpenAI Decisions API about 17 minutes, the Perplexity Decisions API about 27 minutes, Bedrock about
67 minutes, and each self-hosted model about 1.5 hours per pass. The hosted runs and the VM runs go in parallel.

### 6. Score

```bash
uv run python benchmark/runs/e2_full.py report
uv run --with scikit-learn python benchmark/runs/e2_openai_run.py score
```

`score` reads the ledgers that your runs wrote. It writes `benchmark/results/final/leaderboard.json`. Compare your
public-row scores with the board. Expect small differences (see "What you can and cannot reproduce").

We have not yet tested `score` from a fresh clone that has no held-back rows. If it fails, open an issue with the
error. We will fix it.

### 7. Rebuild the withheld text (optional)

Some sources do not let us republish their text. For those rows, the dataset ships only the row id, the label and
the pinned source revision. This command gets the text from the original publishers:

```bash
uv run python -m goldrails_dataset.e2_local rehydrate
```

## Add your own system

Write an adapter (see `benchmark/goldrails_bench/adapters/README.md`). Run the step 3 compatibility check on it.
Then open an issue with the system's name, how to call it, the use cases it covers and the output of the check:
https://github.com/raxITlabs/decision-models-as-guardrails/issues

## Where the details are

- Scoring rules: `benchmark/contracts/v2.0.json`
- Written policies per use case: `benchmark/policies/`
- Infrastructure: `infra/gcp/README.md`, `infra/aws/README.md`
- Adapters: `benchmark/goldrails_bench/adapters/README.md`
