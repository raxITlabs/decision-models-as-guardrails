#!/usr/bin/env bash
# Lifecycle of the model-serving VM in one place. Usage: infra/ctl.sh up|pause|down|status
#   up      create the VM if it does not exist, start it if it is stopped, then open tunnels and wait for every model
#   pause   close tunnels and stop the VM (disk and downloaded weights kept; the disk still bills at list price)
#   down    close tunnels and destroy everything Terraform made
#   status  VM state, served models, which tunnels are listening locally
set -euo pipefail
cd "$(dirname "$0")/.."
INSTANCE=${GOLDRAILS_INSTANCE:-gold-rails-serve}
PROJECT=${GOLDRAILS_PROJECT:-$(cd infra/gcp && terraform output -raw project 2>/dev/null || gcloud config get-value project 2>/dev/null)}

vm() { gcloud compute instances list --project "$PROJECT" --filter="name=$INSTANCE" --format="value(status,zone.basename())" 2>/dev/null; }

case "${1:-status}" in
  up)
    read -r state zone <<<"$(vm || true)"
    case "${state:-}" in
      "")
        # GPU capacity moves between zones; try the configured zone first, then the others, and pin the winner in tfvars.
        # The pinned zone comes from tfvars; a Terraform output can be stale after a destroy.
        PINNED=$(sed -n 's/^zone *= *"\(.*\)"/\1/p' infra/gcp/terraform.tfvars 2>/dev/null)
        ZONES=${GOLDRAILS_ZONES:-"${PINNED:-us-east4-a} us-east4-a us-east4-c us-central1-a us-central1-b us-central1-c us-west1-a us-west1-b us-west4-a"}
        ok=""
        for z in $ZONES; do
          echo "no VM in $PROJECT: creating with Terraform in $z"
          if (cd infra/gcp && terraform apply -input=false -auto-approve -var "zone=$z" >/tmp/gold-rails-apply.log 2>&1); then ok=$z; break; fi
          if grep -q STOCKOUT /tmp/gold-rails-apply.log; then echo "  stockout in $z"
          elif grep -q "does not exist in zone" /tmp/gold-rails-apply.log; then echo "  no such machine type in $z"
          else tail -5 /tmp/gold-rails-apply.log; exit 1; fi
        done
        [ -n "$ok" ] || { echo "no zone had capacity; try again later"; exit 1; }
        sed -i '' "s/^zone *=.*/zone         = \"$ok\"/" infra/gcp/terraform.tfvars 2>/dev/null || true ;;
      TERMINATED)
        # A stopped VM is pinned to its zone and resuming needs GPU capacity there; stockouts come and go in minutes.
        echo "starting $INSTANCE in $zone"
        ERR=$(mktemp -t gold-rails-start.XXXXXX); trap 'rm -f "$ERR"' EXIT
        for attempt in 1 2 3 4 5 6; do
          if gcloud compute instances start "$INSTANCE" --zone "$zone" --project "$PROJECT" --quiet >/dev/null 2>"$ERR"; then break; fi
          if grep -q STOCKOUT "$ERR" && [ "$attempt" -lt 6 ]; then echo "  GPU stockout in $zone (attempt $attempt/6); retrying in 90s"; sleep 90; else tail -3 "$ERR"; echo "could not start $INSTANCE; try later, or 'make down' and 'make up' to recreate it where capacity exists (weights re-download, ~10 min)"; exit 1; fi
        done ;;
      RUNNING)    echo "$INSTANCE already running in $zone" ;;
      *)          echo "$INSTANCE is $state; wait and retry"; exit 1 ;;
    esac
    infra/tunnels.sh down >/dev/null 2>&1 || true
    infra/tunnels.sh up >/dev/null
    ports=$(uv run python -c "from goldrails_bench.endpoints import describe; print(' '.join(str(m['port']) for m in describe()['models']))")
    want=$(wc -w <<<"$ports" | tr -d ' ')
    echo "waiting for $want model servers (first boot downloads weights; a restart takes ~4 min)"
    for i in $(seq 1 90); do
      have=$(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -c -E "127.0.0.1:($(tr ' ' '|' <<<"$ports"))" || true)
      [ "$have" -ge "$want" ] && break; sleep 10
    done
    [ "$have" -ge "$want" ] || { echo "only $have/$want servers up after 15 min; check: gcloud compute instances get-serial-port-output $INSTANCE"; exit 1; }
    echo "ready: $want servers reachable through tunnels"; "$0" status ;;
  pause)
    infra/tunnels.sh down >/dev/null 2>&1 || true
    read -r state zone <<<"$(vm || true)"
    # A machine with a bundled local SSD (a2-ultragpu-1g) refuses to stop until told what to do with it; it holds nothing.
    ssd=()
    if [ "${state:-}" = RUNNING ] && gcloud compute instances describe "$INSTANCE" --zone "$zone" --project "$PROJECT" \
         --format="value(disks[].type)" 2>/dev/null | grep -q SCRATCH; then ssd=(--discard-local-ssd=true); fi
    [ "${state:-}" = RUNNING ] && gcloud compute instances stop "$INSTANCE" --zone "$zone" --project "$PROJECT" ${ssd[@]+"${ssd[@]}"} --quiet >/dev/null
    echo "paused: VM stopped, disk kept (~\$20/month at list for 200 GB); 'make up' resumes in ~4 min" ;;
  down)
    infra/tunnels.sh down >/dev/null 2>&1 || true
    (cd infra/gcp && terraform destroy -input=false -auto-approve)
    echo "down: nothing left billing" ;;
  status)
    read -r state zone <<<"$(vm || true)"
    echo "vm: ${state:-none} ${zone:-} (project $PROJECT)"
    if [ "${state:-}" = RUNNING ]; then
      uv run python - <<'PY'
from goldrails_bench.endpoints import describe
import subprocess
d = describe()
up = subprocess.run("lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk '{print $9}'", shell=True, capture_output=True, text=True).stdout
for m in d["models"]:
    print(f"  {m['name']:14s} gpu {m['gpu']}  port {m['port']}  tunnel {'listening' if f'127.0.0.1:{m['port']}' in up else 'not open'}")
PY
    fi ;;
  *) echo "usage: infra/ctl.sh up|pause|down|status"; exit 2 ;;
esac
