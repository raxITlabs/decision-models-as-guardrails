#!/usr/bin/env bash
# Runs on every boot. Installs a pinned, checksum-verified uv, checks out the two model
# repos at pinned commits, downloads pinned model revisions, and starts one systemd
# service per model. Model parameters travel through a systemd EnvironmentFile written
# with jq's @sh quoting; nothing from metadata is interpolated into a shell string.
set -euo pipefail
MD=http://metadata.google.internal/computeMetadata/v1/instance/attributes
H="Metadata-Flavor: Google"
md() { curl -sf -H "$H" "$MD/$1"; }
MODELS_JSON=$(md models-json)
IDLE_MIN=$(md idle-shutdown-minutes || echo 0)
KEV_SHA=$(md kev-repo-sha); OPENJEV_SHA=$(md openjev-repo-sha)
UV_VERSION=$(md uv-version); UV_SHA=$(md uv-installer-sha256)
export HOME=/root
apt-get install -y -q jq git >/dev/null 2>&1 || true
id goldrails >/dev/null 2>&1 || useradd -r -m -d /opt/goldrails -s /usr/sbin/nologin goldrails
mkdir -p /opt/goldrails/checkpoints /etc/goldrails && cd /opt/goldrails

# uv: pinned release, verified installer.
if ! command -v /usr/local/bin/uv >/dev/null; then
  curl -sSfL "https://astral.sh/uv/${UV_VERSION}/install.sh" -o /tmp/uv-install.sh
  echo "${UV_SHA}  /tmp/uv-install.sh" | sha256sum -c -
  UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh /tmp/uv-install.sh >/dev/null
fi

# Server code at pinned commits.
clone_at() { # url dir sha -- idempotent and self-healing: an interrupted boot leaves no trap
  if [ -d "$2" ] && [ "$(git -C "$2" rev-parse HEAD 2>/dev/null || true)" = "$3" ]; then return 0; fi
  rm -rf "$2"
  git init -q "$2"
  git -C "$2" remote add origin "$1"
  git -C "$2" fetch -q --depth 1 origin "$3"
  git -C "$2" -c advice.detachedHead=false checkout -q FETCH_HEAD
  [ "$(git -C "$2" rev-parse HEAD)" = "$3" ] || { echo "checkout of $1 did not land on $3"; exit 1; }
}
clone_at https://github.com/jaredpalmer/kev kev "$KEV_SHA"
clone_at https://github.com/Zefan-Cai/Open-Jev Open-Jev "$OPENJEV_SHA"
chown -R goldrails:goldrails /opt/goldrails
sudo -u goldrails -H bash -c 'cd /opt/goldrails/kev && /usr/local/bin/uv sync --extra serve' >/dev/null 2>&1
sudo -u goldrails -H bash -c "cd /opt/goldrails/Open-Jev && /usr/local/bin/uv venv -q .venv && /usr/local/bin/uv pip install -q -e '.[train]' huggingface_hub" >/dev/null 2>&1

# Laya: the author's package at a pinned release, behind our stdlib System One wrapper (shipped via metadata).
LAYA_VERSION=$(md laya-version); [[ "$LAYA_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "refusing laya version: $LAYA_VERSION"; exit 1; }
mkdir -p /opt/goldrails/laya && md laya-server-py > /opt/goldrails/laya/laya_server.py && chown -R goldrails:goldrails /opt/goldrails/laya
# Idempotent and loud: keep an existing venv that already has the pinned laya; otherwise build it and say so. A silent
# failure here once left the service restarting in a loop with no venv (22 September 2026).
if ! sudo -u goldrails -H bash -c "cd /opt/goldrails/laya && [ -x .venv/bin/python ] && .venv/bin/python -c 'import laya, sys; sys.exit(0 if laya.__version__ == \"$LAYA_VERSION\" else 1)'" 2>/dev/null; then
  sudo -u goldrails -H bash -c "cd /opt/goldrails/laya && rm -rf .venv && /usr/local/bin/uv venv -q .venv && /usr/local/bin/uv pip install -q 'laya==$LAYA_VERSION' 'huggingface_hub>=0.20'" \
    && echo "laya $LAYA_VERSION venv ready" || echo "laya venv build FAILED (service will not start)"
else
  echo "laya $LAYA_VERSION venv present"
fi

# Strands Decider: the vendor's package at a pinned release in its own venv, launched by our create_app + uvicorn
# wrapper (shipped via metadata) so it binds 0.0.0.0. Built only when a strands model is listed. The checkpoint is
# downloaded here at its pinned revision, before the unit starts; the server then runs with HF_HUB_OFFLINE=1.
STRANDS_VERSION=$(md strands-version || echo "")
if echo "$MODELS_JSON" | jq -e 'any(.[]; .kind == "strands")' >/dev/null; then
  [[ "$STRANDS_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "refusing strands-decider version: $STRANDS_VERSION"; exit 1; }
  mkdir -p /opt/goldrails/strands && md strands-server-py > /opt/goldrails/strands/strands_server.py && chown -R goldrails:goldrails /opt/goldrails/strands
  if ! sudo -u goldrails -H bash -c "cd /opt/goldrails/strands && [ -x .venv/bin/python ] && .venv/bin/python -c 'import sys; from importlib.metadata import version; sys.exit(0 if version(\"strands-decider\") == \"$STRANDS_VERSION\" else 1)'" 2>/dev/null; then
    sudo -u goldrails -H bash -c "cd /opt/goldrails/strands && rm -rf .venv && /usr/local/bin/uv venv -q .venv && /usr/local/bin/uv pip install -q 'strands-decider==$STRANDS_VERSION' 'huggingface_hub>=0.34' 'uvicorn>=0.30'" \
      && echo "strands-decider $STRANDS_VERSION venv ready" || echo "strands-decider venv build FAILED (service will not start)"
  else
    echo "strands-decider $STRANDS_VERSION venv present"
  fi
  echo "$MODELS_JSON" | jq -c '.[] | select(.kind == "strands")' | while read -r m; do
    sname=$(echo "$m" | jq -r '.name'); sref=$(echo "$m" | jq -r '.ref'); srev=$(echo "$m" | jq -r '.revision')
    [[ "$sname" =~ ^[a-z0-9][a-z0-9-]{0,40}$ && "$sref" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && "$srev" =~ ^[0-9a-f]{40}$ ]] \
      || { echo "refusing strands model entry: $sname"; exit 1; }
    sudo -u goldrails -H env HF_HOME=/opt/goldrails/.cache/huggingface /opt/goldrails/strands/.venv/bin/python - "$sref" "$srev" "/opt/goldrails/checkpoints/$sname" <<'PY' \
      && echo "strands checkpoint $sname at $srev ready" || echo "strands checkpoint download FAILED for $sname"
import pathlib, sys
from huggingface_hub import snapshot_download
ref, rev, out = sys.argv[1:4]
marker = pathlib.Path(out) / ".goldrails-revision"
if not (marker.exists() and marker.read_text().strip() == rev):
    snapshot_download(ref, revision=rev, local_dir=out)
    marker.write_text(rev + "\n")
PY
  done
fi

# Triton builds its CUDA driver shim with gcc on first use. Do that here, outside the service sandbox, into the cache
# the units share, and let any compiler error reach the serial console instead of a bare 500 from the server.
dpkg -s python3-dev >/dev/null 2>&1 || { apt-get update -q >/dev/null; apt-get install -y -q python3-dev build-essential >/dev/null; }
mkdir -p /opt/goldrails/.cache/triton && chown -R goldrails:goldrails /opt/goldrails/.cache
sudo -u goldrails -H env TRITON_CACHE_DIR=/opt/goldrails/.cache/triton /opt/goldrails/Open-Jev/.venv/bin/python -c \
  'from triton.runtime import driver; print("triton driver ready:", driver.active.get_current_target())' \
  || echo "triton prewarm failed (see gcc output above)"

# Runner scripts read their parameters from the environment only.
cat > /usr/local/bin/goldrails-run-kev <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/goldrails/kev
# kev.serve binds 127.0.0.1, which IAP forwarding cannot reach; bind all interfaces (the firewall limits who can connect).
exec env CUDA_VISIBLE_DEVICES="$MODEL_GPU" KEV_DTYPE=bf16 KEV_MERGE=0 /usr/local/bin/uv run --extra serve \
  python -c '
import sys, torch, uvicorn, kev.serve as s
sys.argv = ["kev.serve", "--run", sys.argv[1], "--port", sys.argv[2]]
_run = uvicorn.run
uvicorn.run = lambda app, host="127.0.0.1", port=8008, **kw: _run(app, host="0.0.0.0", port=port, **kw)
# Several servers share one card: give back the caching allocator'"'"'s reserve after every request, or each process
# keeps its own peak and the card fills up.
_answer = s.Server.answer
def answer(self, req):
    try: return _answer(self, req)
    finally: torch.cuda.empty_cache()
s.Server.answer = answer
s.main()
' "${MODEL_REF}@${MODEL_REVISION}" "$MODEL_PORT"
RUN
cat > /usr/local/bin/goldrails-run-openjev <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/goldrails/Open-Jev
ckpt="/opt/goldrails/checkpoints/${MODEL_NAME}"
[ -d "$ckpt/package" ] || .venv/bin/hf download "$MODEL_REF" --revision "$MODEL_REVISION" --local-dir "$ckpt"
# jev.server swallows inference exceptions into a bare 500; log the traceback to the journal so failures are diagnosable.
exec env CUDA_VISIBLE_DEVICES="$MODEL_GPU" .venv/bin/python -c '
import sys, runpy, traceback, torch, jev.serving as sv
_predict = sv.Predictor.predict
def predict(self, request):
    try: return _predict(self, request)
    except Exception: traceback.print_exc(); sys.stderr.flush(); raise
    finally: torch.cuda.empty_cache()   # shared card: release the allocator reserve after every request
sv.Predictor.predict = predict
sys.argv = ["jev.server"] + sys.argv[1:]
runpy.run_module("jev.server", run_name="__main__")
' --checkpoint "$ckpt/package/checkpoint" \
  --device cuda:0 --max-length 4096 --batch-size 32 --no-prefix-cache --host 0.0.0.0 --port "$MODEL_PORT"
RUN
cat > /usr/local/bin/goldrails-run-laya <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/goldrails/laya
exec env CUDA_VISIBLE_DEVICES="$MODEL_GPU" .venv/bin/python laya_server.py --ref "$MODEL_REF" --revision "$MODEL_REVISION" \
  --model-name "$MODEL_NAME" --device cuda:0 --host 0.0.0.0 --port "$MODEL_PORT"
RUN
cat > /usr/local/bin/goldrails-run-strands <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
cd /opt/goldrails/strands
ckpt="/opt/goldrails/checkpoints/${MODEL_NAME}"
# Serve only the pinned revision that startup.sh downloaded; never fetch at serve time.
[ "$(cat "$ckpt/.goldrails-revision" 2>/dev/null || true)" = "$MODEL_REVISION" ] || { echo "checkpoint $ckpt is not at $MODEL_REVISION"; exit 1; }
exec env CUDA_VISIBLE_DEVICES="$MODEL_GPU" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python strands_server.py \
  --checkpoint "$ckpt" --model-name "$MODEL_NAME" --device cuda:0 --host 0.0.0.0 --port "$MODEL_PORT"
RUN
chmod +x /usr/local/bin/goldrails-run-kev /usr/local/bin/goldrails-run-openjev /usr/local/bin/goldrails-run-laya /usr/local/bin/goldrails-run-strands

# One unit per model. Values are shell-quoted by jq @sh before they touch a file.
echo "$MODELS_JSON" | jq -c '.[]' | while read -r m; do
  name=$(echo "$m" | jq -r '.name'); kind=$(echo "$m" | jq -r '.kind')
  # Allowlist: lowercase alnum and hyphen only, no dots, so the name is safe as a path component.
  [[ "$name" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || { echo "refusing model name: $name"; exit 1; }
  [[ "$kind" =~ ^(kev|openjev|laya|strands)$ ]] || { echo "refusing model kind: $kind"; exit 1; }
  echo "$m" | jq -r '@sh "MODEL_NAME=\(.name)\nMODEL_REF=\(.ref)\nMODEL_REVISION=\(.revision)\nMODEL_PORT=\(.port|tostring)\nMODEL_GPU=\(.gpu|tostring)"' > "/tmp/${name}.env"
  install -m 0640 -o root -g goldrails -T "/tmp/${name}.env" "/etc/goldrails/${name}.env"
  cat > "/tmp/goldrails-${name}.service" <<UNIT
[Unit]
Description=Gold Rails model server ${name}
After=network-online.target
[Service]
Type=simple
User=goldrails
Group=goldrails
Environment=HOME=/opt/goldrails
Environment=HF_HOME=/opt/goldrails/.cache/huggingface
Environment=TRITON_CACHE_DIR=/opt/goldrails/.cache/triton
Environment=PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
EnvironmentFile=/etc/goldrails/${name}.env
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/opt/goldrails
PrivateTmp=yes
ExecStart=/usr/local/bin/goldrails-run-${kind}
Restart=on-failure
RestartSec=10
[Install]
WantedBy=multi-user.target
UNIT
  install -m 0644 -T "/tmp/goldrails-${name}.service" "/etc/systemd/system/goldrails-${name}.service"
  systemctl daemon-reload
  systemctl enable --now "goldrails-${name}.service"
done

# Idle shutdown: no GPU utilisation for IDLE_MIN minutes -> power off.
if [ "${IDLE_MIN:-0}" -gt 0 ]; then
  cat > /usr/local/bin/goldrails-idle-check <<'CHK'
#!/usr/bin/env bash
STAMP=/var/run/goldrails-last-active
LIMIT_MIN=$(curl -sf -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/idle-shutdown-minutes || echo 0)
util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | sort -n | tail -1)
if [ "${util:-0}" -gt 5 ] || [ ! -f "$STAMP" ]; then date +%s > "$STAMP"; exit 0; fi
last=$(cat "$STAMP"); now=$(date +%s)
if [ $(( (now - last) / 60 )) -ge "$LIMIT_MIN" ]; then logger "goldrails: idle for $LIMIT_MIN min, shutting down"; shutdown -h now; fi
CHK
  chmod +x /usr/local/bin/goldrails-idle-check
  echo "*/5 * * * * root /usr/local/bin/goldrails-idle-check" > /etc/cron.d/goldrails-idle
fi
echo "goldrails startup complete"
