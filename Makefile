# decision-models-as-guardrails. `make help` lists these.

.PHONY: help test build up pause down status tunnel tunnel-down infra-init infra-plan
help:  ## this list
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*##' '{printf "  make %-12s %s\n", $$1, $$2}'

test:  ## unit tests
	uv run --with scikit-learn python -m pytest -q
build:  ## rebuild the dataset build (dataset/edition2/build) from the committed candidates
	GOLDRAILS_GATE_WORKERS=8 uv run --with scikit-learn python -m goldrails_dataset.edition2

up:  ## VM up (create or resume), tunnels open, wait until every model answers
	infra/ctl.sh up
pause:  ## tunnels down, VM stopped, disk kept (cheap; resume with make up)
	infra/ctl.sh pause
down:  ## destroy the VM and everything Terraform made
	infra/ctl.sh down
status:  ## VM state, served models, tunnels
	infra/ctl.sh status

tunnel:  ## (re)open tunnels only
	infra/tunnels.sh up
tunnel-down:  ## close tunnels only
	infra/tunnels.sh down
infra-init:  ## terraform init (first time in a fresh clone)
	cd infra/gcp && terraform init
infra-plan:  ## terraform plan
	cd infra/gcp && terraform plan
