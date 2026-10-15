#!/usr/bin/env python3
"""Serve Amazon Strands Decider checkpoints (StrandsAgents/strands-decider-*) on POST /v1/systemone.

The ``strands-decider`` package (PyPI 0.1.0, or a pinned commit of its repository for Gemma 4) ships the System One server itself; ``strands-decider serve`` binds
127.0.0.1, which an IAP tunnel cannot reach. This launcher builds the same app with the package's ``create_app`` and
runs it under uvicorn on the host it is given (0.0.0.0 on the VM; the firewall limits who connects). It loads the
checkpoint from a local directory that startup.sh downloaded at a pinned revision, with HF_HUB_OFFLINE set by the
runner, so nothing else is fetched at serve time. ``trust_remote_code`` is never passed.

The package is experimental and its ``create_app`` signature is not documented, so the launcher maps its arguments
by name and stops with the signature in the error when it cannot. Check the journal on first boot.

    python strands_server.py --checkpoint /opt/goldrails/checkpoints/strands-decider-2b --port 8013 --device cuda:0

A checkpoint larger than one card (strands-decider-26B-A4B, about 51 GB in bf16, on 40 GB A100s) is split with
``--split-gpus N``: the package's engine moves the whole model to one device, so the launcher loads the torso with a
balanced device map over the N visible GPUs instead, keeps the readout head on cuda:0, brings the torso's hidden states
back to cuda:0, and stops the engine's ``.to(device)`` from undoing the split. The weights and the arithmetic are the
package's; only where layers sit changes.
"""
from __future__ import annotations

import argparse
import importlib
import inspect

CONTEXT_TOKENS = 4096   # the model's window (model card and package README); the server cuts silently beyond it
APP_MODULES = ("strands_decider.server", "strands_decider.serve", "strands_decider.app", "strands_decider")
PATH_ARGS = ("checkpoint", "checkpoint_path", "model_path", "model_dir", "path", "model", "model_id", "model_name_or_path")
DEVICE_ARGS = ("device",)
NAME_ARGS = ("served_model_name", "model_alias", "name")


def find_create_app():
    for mod in APP_MODULES:
        try:
            m = importlib.import_module(mod)
        except ImportError:
            continue
        if callable(getattr(m, "create_app", None)):
            return m.create_app
    raise SystemExit(f"strands-decider: no create_app in any of {APP_MODULES}")


def app_kwargs(create_app, checkpoint: str, device: str, model_name: str | None) -> dict:
    """create_app keyword arguments by parameter name. Raises when no parameter takes the checkpoint path."""
    params = inspect.signature(create_app).parameters
    kw = {}
    path = next((p for p in PATH_ARGS if p in params), None)
    if path is None:
        raise SystemExit(f"strands-decider: cannot tell which create_app argument takes the checkpoint: "
                         f"create_app{inspect.signature(create_app)}")
    kw[path] = checkpoint
    for p in DEVICE_ARGS:
        if p in params:
            kw[p] = device
    for p in NAME_ARGS:
        if p in params and model_name:
            kw[p] = model_name
    if "trust_remote_code" in params:
        kw["trust_remote_code"] = False
    return kw


def split_over_gpus(n: int) -> None:
    """Make the package load the checkpoint split over ``n`` GPUs. Replaces ``StrandsDeciderModel`` where the server
    module looks it up, before ``create_app`` runs."""
    import torch
    import strands_decider.server as srv
    from strands_decider.modeling import StrandsDeciderModel

    if torch.cuda.device_count() < n:
        raise SystemExit(f"--split-gpus {n}: only {torch.cuda.device_count()} GPUs visible")

    def split_load(path, *, device_map=None, attn_implementation=None):
        model = StrandsDeciderModel.load(path, device_map="balanced", attn_implementation=attn_implementation)
        for name, child in model.named_children():
            if name != "torso":
                child.to("cuda:0")

        def to_first(_module, _args, out):
            if getattr(out, "last_hidden_state", None) is not None:
                out.last_hidden_state = out.last_hidden_state.to("cuda:0")
            return out
        model.torso.register_forward_hook(to_first)
        model.to = lambda *a, **k: model          # the engine's model.to(device) would gather every layer on cuda:0
        print(f"strands: split over {n} GPUs: {sorted({str(p.device) for p in model.parameters()})}", flush=True)
        return model

    srv.StrandsDeciderModel = type("SplitStrandsDeciderModel", (), {"load": staticmethod(split_load)})


def share_card(app, serialize: bool = False) -> None:
    """Several servers share one card: give back the caching allocator's reserve after every request, or each process
    keeps its own peak and the card fills up (as the Kev and Open-Jev runners do).

    ``serialize`` (a model split over several GPUs) runs one request at a time, so only one forward pass crosses the
    cards at once. A CUDA error poisons the process for good, so the server then exits and systemd starts a clean one;
    the run's retry passes resend what failed meanwhile."""
    import asyncio
    import os
    import torch
    if not torch.cuda.is_available():
        return
    lock = asyncio.Lock() if serialize else None

    @app.middleware("http")
    async def release(request, call_next):
        try:
            if lock is None:
                return await call_next(request)
            async with lock:
                return await call_next(request)
        except Exception as e:
            if "CUDA error" in str(e):
                print(f"strands: {e!s:.300}; exiting for a clean restart", flush=True)
                os._exit(3)
            # The server is reachable only through the IAP tunnel, and the run's clients record no error body; the
            # traceback in the 500 is the one way to read a failure when the journal is out of reach.
            import traceback
            from fastapi.responses import PlainTextResponse
            tb = traceback.format_exc()
            print(tb, flush=True)
            return PlainTextResponse(tb[-4000:], status_code=500)
        finally:
            try:
                torch.cuda.empty_cache()
            except Exception as e:  # a CUDA error raised late, at the release
                print(f"strands: {e!s:.300}; exiting for a clean restart", flush=True)
                os._exit(3)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="local directory holding the pinned revision")
    ap.add_argument("--model-name", default=None)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8013)
    ap.add_argument("--split-gpus", type=int, default=1, help="split the model over this many visible GPUs")
    a = ap.parse_args(argv)
    if a.split_gpus > 1:
        split_over_gpus(a.split_gpus)
    create_app = find_create_app()
    kw = app_kwargs(create_app, a.checkpoint, a.device, a.model_name)
    if a.split_gpus > 1 and "use_prefix_cache" in inspect.signature(create_app).parameters:
        # A split model forwards each question with the whole prompt instead of reusing one KV cache across cards: the
        # shared-prefix path hit "CUDA error: an illegal memory access" after about ten requests on four L4 cards, even
        # one request at a time (15 October 2026). The other path is the package's own fallback, which truncates alike.
        kw["use_prefix_cache"] = False
    app = create_app(**kw)
    share_card(app, serialize=a.split_gpus > 1)
    import uvicorn
    uvicorn.run(app, host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
