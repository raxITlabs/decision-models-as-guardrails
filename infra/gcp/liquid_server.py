#!/usr/bin/env python3
"""Serve a Liquid AI open d1 checkpoint (LiquidAI/d1-2B, LiquidAI/d1-3B) behind TypeSafe's /v1/systemone shape.

The open d1 models are in-process Transformers models with their own model code (``trust_remote_code``) and a
``system_one(state, questions)`` method; Liquid ships no HTTP server. This wrapper is standard library plus that
model, so the same file runs on the VM (as goldrails-run-liquid) and on a laptop for a check. The checkpoint is a
local directory downloaded at a pinned revision (startup.sh, or ``--ref``/``--revision`` here), and the model code
that ``trust_remote_code`` runs is the code in that directory, at that revision: nothing is fetched at serve time.

Questions pass through unchanged: d1 takes the Decision Index question schema (``type``, ``instructions``,
``criteria``), which is Jev's, and answers in Jev's shape (noul: P(yes); choice with probabilities; score with a
legend). The state is passed as the JSON object every System One model receives; d1's default state style writes it
as that object. No threshold, calibration or set size is changed: the call is the model card's.

    python liquid_server.py --checkpoint /opt/goldrails/checkpoints/liquid-d1-2b --model-name liquid-d1-2b --port 8031
    python liquid_server.py --ref LiquidAI/d1-2B --revision <sha> --model-name liquid-d1-2b --device mps   # laptop
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 4 * 1024 * 1024


def load(path: str, device: str):
    import torch
    from transformers import AutoModel

    dtype = torch.float32 if device == "cpu" else torch.bfloat16
    model = AutoModel.from_pretrained(path, trust_remote_code=True, dtype=dtype).to(device)
    model.eval()
    return model


def context_tokens(model) -> int | None:
    cfg = getattr(model, "config", None)
    text = getattr(cfg, "text_config", None)
    return getattr(text, "max_position_embeddings", None) or getattr(cfg, "max_position_embeddings", None)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=None, help="local directory holding the pinned revision")
    ap.add_argument("--ref", default=None, help="Hugging Face repo, downloaded at --revision (laptop use)")
    ap.add_argument("--revision", default=None, help="40-hex commit of the Hugging Face repo")
    ap.add_argument("--model-name", required=True, help="what /v1/models reports and requests may name")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8031)
    a = ap.parse_args(argv)

    path, ref, revision = a.checkpoint, a.ref, a.revision
    if path:
        marker = f"{path}/.goldrails-revision"
        try:
            on_disk = open(marker).read().strip()
        except OSError:
            on_disk = None
        if revision and on_disk != revision:
            raise SystemExit(f"checkpoint {path} is at {on_disk}, not {revision}")
        revision = revision or on_disk
    elif ref and revision:
        from huggingface_hub import snapshot_download
        path = snapshot_download(ref, revision=revision)
    else:
        raise SystemExit("give --checkpoint, or --ref with --revision")

    t0 = time.perf_counter()
    model = load(path, a.device)
    import torch
    import transformers
    info = {"ref": ref, "revision": revision, "device": a.device, "dtype": "float32" if a.device == "cpu" else "bfloat16",
            "context_tokens": context_tokens(model), "transformers": transformers.__version__, "torch": torch.__version__}
    print(json.dumps({"loaded": path, "load_s": round(time.perf_counter() - t0, 1), **info}), flush=True)
    lock = threading.Lock()   # one forward pass at a time on the card
    accepted = {None, a.model_name, ref}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"{self.address_string()} - {fmt % args}", flush=True)

        def send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/v1/models":
                return self.send(200, {"models": [{"id": a.model_name, "name": a.model_name, **info}]})
            if self.path == "/health":
                return self.send(200, {"ok": True})
            self.send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/systemone":
                return self.send(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n < 1 or n > MAX_BODY:
                    return self.send(413, {"error": "body size outside limits"})
                req = json.loads(self.rfile.read(n))
                if not isinstance(req, dict) or "state" not in req or not isinstance(req.get("questions"), dict):
                    return self.send(422, {"error": "request requires state and questions"})
                if req.get("model") not in accepted:
                    return self.send(422, {"error": "requested model is not loaded; see /v1/models"})
            except (ValueError, TypeError) as e:
                return self.send(422, {"error": str(e)})
            try:
                with lock:
                    t = time.perf_counter()
                    with torch.inference_mode():
                        out = model.system_one(req["state"], req["questions"])
                    dt = time.perf_counter() - t
                    if a.device.startswith("cuda"):
                        torch.cuda.empty_cache()   # shared card: give back the allocator's reserve
            except (ValueError, KeyError, TypeError) as e:
                return self.send(422, {"error": str(e)})
            except Exception as e:  # never substitute an answer when inference fails
                import traceback
                traceback.print_exc()
                return self.send(500, {"error": "model inference failed", "error_type": type(e).__name__})
            body = {"model": a.model_name, "answers": out.get("answers"), "usage": out.get("usage"),
                    "metadata": {**info, "inference_seconds": round(dt, 4)}}
            self.send(200, body)

    print(json.dumps({"url": f"http://{a.host}:{a.port}", "model": a.model_name}), flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
