#!/usr/bin/env python3
"""Serve a Laya checkpoint (convaiinnovations/laya) behind TypeSafe's /v1/systemone request and response shape.

Laya is an in-process Python API with no HTTP server of its own. This wrapper is standard library only, so the
same file runs on the VM (as goldrails-run-laya) and on a laptop for a check. The checkpoint is pinned by
revision through huggingface_hub and loaded with the author's package; questions pass through unchanged because
Laya takes Jev's typed questions as they are and answers in Jev's shape (noul, choice with probabilities, score
with legend and probabilities).

    python laya_server.py --ref convaiinnovations/laya --revision <sha> --port 8012 --device cuda:0
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 4 * 1024 * 1024
UNCUT = 10 ** 9   # a max_len no sequence reaches, to measure a question's prefix uncut


def limits(agent) -> dict:
    """The context the server runs at and where each number comes from."""
    enc = getattr(getattr(getattr(agent, "model", None), "encoder", None), "config", None)
    return {"max_len": int(agent.cfg.get("max_len", 512)), "head_max_len": int(agent.cfg.get("head_max_len", 192)),
            "encoder_max_positions": getattr(enc, "max_position_embeddings", None)}


def truncation_report(agent, state, questions: dict) -> dict:
    """Tokens before and after Laya's cut, per question, built with the package's own sequence builder.

    ``input_tokens_before`` is the uncut sequence: question, every option in full and the whole state, with the four
    special tokens. ``input_tokens_after`` is what ``build_sequence`` hands the model. ``state_tokens_kept`` shows how
    much of the state survived the ``max_len`` cut; ``head_cut`` is true when ``head_max_len`` shortened the question
    or an option."""
    from laya.common import build_sequence, render_options, serialize_state

    tok, lim = agent.tok, limits(agent)
    mask = tok.mask_token
    n_state = len(tok(serialize_state(state).replace(mask, " "), add_special_tokens=False)["input_ids"])
    per_q, before_sum, after_sum = {}, 0, 0
    for qid, qdef in questions.items():
        q = agent._to_internal(qdef)
        ins = str(q["ins"]).replace(mask, " ")
        head_full = len(tok("%s question: %s" % (q["t"], ins), add_special_tokens=False)["input_ids"])
        opts_full = sum(1 + len(tok(" " + o.replace(mask, " "), add_special_tokens=False)["input_ids"])
                        for o in render_options(q))
        prefix_full = 3 + head_full + opts_full                     # [CLS] head [SEP] options [SEP]
        before = prefix_full + n_state + 1                          # ... state [SEP]
        after = len(build_sequence(tok, state, q, lim["max_len"], lim["head_max_len"])[0])
        prefix_kept = len(build_sequence(tok, "", q, UNCUT, lim["head_max_len"])[0]) - 1
        kept = max(0, min(n_state, after - prefix_kept - 1))
        per_q[qid] = {"input_tokens_before": before, "input_tokens_after": after, "state_tokens_kept": kept,
                      "head_cut": prefix_kept < prefix_full, "truncated": after < before}
        before_sum, after_sum = before_sum + before, after_sum + after
    return {**lim, "truncated": any(v["truncated"] for v in per_q.values()),
            "state_truncated": any(v["state_tokens_kept"] < n_state for v in per_q.values()),
            "state_tokens": n_state, "input_tokens_before": before_sum, "input_tokens_after": after_sum,
            "questions": per_q}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="convaiinnovations/laya")
    ap.add_argument("--revision", required=True, help="40-hex commit of the Hugging Face repo")
    ap.add_argument("--subfolder", default=None, help="checkpoint inside the repo, e.g. multilingual")
    ap.add_argument("--model-name", default="laya", help="what /v1/models reports and requests may name")
    ap.add_argument("--device", default=None)
    ap.add_argument("--max-len", type=int, default=None,
                    help="override the checkpoint's max_len (default: keep it; 512 for the English checkpoint)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8012)
    a = ap.parse_args()

    from huggingface_hub import snapshot_download
    import laya

    path = snapshot_download(a.ref, revision=a.revision)
    t0 = time.perf_counter()
    agent = laya.load(path, device=a.device, subfolder=a.subfolder)
    checkpoint_max_len = int(agent.cfg.get("max_len", 512))
    if a.max_len is not None:
        enc_max = limits(agent)["encoder_max_positions"]
        if a.max_len < 1 or (enc_max and a.max_len > enc_max):
            raise SystemExit(f"--max-len {a.max_len} is outside 1..{enc_max} (encoder positions)")
        agent.cfg["max_len"] = a.max_len
    context = {**limits(agent), "checkpoint_max_len": checkpoint_max_len,
               "max_len_source": "--max-len override" if a.max_len is not None else "checkpoint rl_agent_config.json"}
    print(json.dumps({"loaded": a.ref, "revision": a.revision, "device": str(agent.device),
                      "laya": getattr(laya, "__version__", None), "load_s": round(time.perf_counter() - t0, 1),
                      **context}), flush=True)
    lock = threading.Lock()
    accepted = {None, a.model_name, a.ref, "laya"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # one line per request, like the other servers
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
                return self.send(200, {"models": [{"id": a.model_name, "name": a.model_name, "ref": a.ref, "revision": a.revision,
                                                   **context}]})
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
                with lock:  # the cut is measured with the same tokenizer and limits the model is about to use
                    trunc = truncation_report(agent, req["state"], req["questions"])
                    t = time.perf_counter()
                    out = agent.predict(req["state"], req["questions"])
            except (ValueError, KeyError, TypeError) as e:
                return self.send(422, {"error": str(e)})
            except Exception as e:  # never substitute an answer when inference fails
                import traceback; traceback.print_exc()
                return self.send(500, {"error": "model inference failed", "error_type": type(e).__name__})
            out["model"] = a.model_name
            out["metadata"] = {"ref": a.ref, "revision": a.revision, "device": str(agent.device),
                               "inference_seconds": round(time.perf_counter() - t, 4),
                               "max_len_source": context["max_len_source"], "checkpoint_max_len": checkpoint_max_len,
                               "truncation": {**trunc, "matches_usage": trunc["input_tokens_after"]
                                              == (out.get("usage") or {}).get("input_tokens")}}
            self.send(200, out)

    print(json.dumps({"url": f"http://{a.host}:{a.port}", "model": a.model_name}), flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
