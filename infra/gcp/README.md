# Serving open decision models on your own Google Cloud

One spot VM with L4 GPUs runs Kev-9B and Open-Jev-9B behind `POST /v1/systemone`, reachable only through IAP tunnels. The VM has an ephemeral external IP for outbound internet (installs, weight downloads); the firewall admits only IAP's range on port 22 and never opens the model ports, so nothing is reachable from outside. This is cheaper than a NAT gateway for a VM that exists for hours and is destroyed after.

SSH into the VM uses OS Login, so on an organisation-owned project the account must belong to the organisation (an outside Google account needs `roles/compute.osLoginExternalUser` at the org). The model-port tunnels do not need SSH. `terraform destroy` removes everything.

```bash
gcloud auth login && gcloud auth application-default login
cd infra/gcp && cp terraform.tfvars.example terraform.tfvars   # set project_id
terraform init && terraform apply
# wait ~10 minutes for drivers, weights, and servers (check: gcloud compute ssh ... -- journalctl -u 'goldrails-*' -f)
terraform output tunnel_commands   # run each in its own terminal
export KEV_URL=http://localhost:8009 OPENJEV_URL=http://localhost:8791
terraform destroy                  # when done
```

Rule for published numbers: every open model is served from this VM so all self-hosted latency is measured on the same hardware class. Local runs (`vendor/kev` on a laptop) are smoke tests only and never enter `results/`.

For the full roster use `terraform.tfvars.full-roster.example` (g2-standard-48, four L4s, about $1.20/hr spot).

Strands Decider 2B is `kind = "strands"`. When a strands model is listed, startup.sh installs `strands-decider` at
`strands_decider_version` (0.1.0) in its own uv venv under `/opt/goldrails/strands`, downloads the checkpoint at its
pinned revision before the unit starts, and runs `strands_server.py` (the package's `create_app` under uvicorn on
0.0.0.0) with the Hub offline. It is about 5 GB in bf16, so it fits beside a small model on one L4. Its window is
4,096 tokens and it cuts longer input without saying so; `endpoints.resolve_models` records that as
`identity.max_length`. To add it to a running VM, add the entry from the full-roster example to `terraform.tfvars` and
run `terraform apply` (owner step). The `create_app` signature is not documented: on first boot check
`journalctl -u goldrails-strands-decider-2b` for the launcher's message if the unit does not come up.

Costs, us-central1 list prices, approximate: g2-standard-24 (2× L4) about $1.90/hr on-demand, about $0.60/hr spot; g2-standard-8 (1× L4) about $0.85/hr on-demand, about $0.28/hr spot; 200 GB boot disk about $0.02/hr. The idle-shutdown cron powers the VM off after 60 minutes without GPU activity; a spot VM can also be preempted at any time, which is fine for a benchmark that writes receipts per row.

Quota: you need `NVIDIA_L4_GPUS` (or the `PREEMPTIBLE_` variant for spot) of at least 2 in the region. Check with `gcloud compute regions describe us-central1 --format='value(quotas)'`.

Supply chain: the VM checks out both model servers at pinned commits, downloads pinned model revisions, installs a checksum-verified pinned uv, and runs with a service account that can only write logs and metrics. Bump the pins deliberately, in a reviewed commit.

Latency measured against these servers is self-hosted latency and is reported as such, with the hardware named, never as a production API's.

## Known failure: "Request project/<id>/services timed out after 10m0s"

Seen on 23 September 2026 during `make down` and a later `make up`. The Google provider reads the project's enabled
APIs (Service Usage API) on every plan, and that call sometimes hangs for the full ten minutes on this project.
It is not the VM and not our configuration (`disable_on_destroy = false` has always been set, so destroy never
tries to disable APIs). Retry later. `make pause` does not use Terraform and keeps working, so the VM can always be
stopped even when Terraform cannot plan.
