# decision-models-as-guardrails. `make help` lists these.
NB ?= benchmark/notebooks/04_cloud_pass_pilot.ipynb
LEDGER ?= benchmark/results/pilot-cloud-pass.jsonl

.PHONY: help test build up run pause down status report tunnel tunnel-down infra-init infra-plan
help:  ## this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*##' '{printf "  make %-12s %s\n", $$1, $$2}'

test:  ## unit tests
	uv run pytest -q
build:  ## rebuild the pilot sample from the public sources
	uv run python -m goldrails_dataset.build --out dataset/samples/pilot --per-cell 25 --seed 7

up:  ## VM up (create or resume), tunnels open, wait until every model answers
	infra/ctl.sh up
run:  ## execute a notebook against the VM (NB=path, default notebook 04)
	uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=7200 $(NB)
pause:  ## tunnels down, VM stopped, disk kept (cheap; resume with make up)
	infra/ctl.sh pause
down:  ## destroy the VM and everything Terraform made
	infra/ctl.sh down
status:  ## VM state, served models, tunnels
	infra/ctl.sh status
report:  ## scores table, charts and a README next to a results ledger (LEDGER=path)
	uv run python -m goldrails_bench.report $(LEDGER)

tunnel:  ## (re)open tunnels only
	infra/tunnels.sh up
tunnel-down:  ## close tunnels only
	infra/tunnels.sh down
infra-init:  ## terraform init (first time in a fresh clone)
	cd infra/gcp && terraform init
infra-plan:  ## terraform plan
	cd infra/gcp && terraform plan
