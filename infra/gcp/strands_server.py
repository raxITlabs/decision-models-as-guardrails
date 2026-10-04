#!/usr/bin/env python3
"""Serve Amazon Strands Decider (StrandsAgents/strands-decider-2B-hobson-v19) on POST /v1/systemone.

The ``strands-decider`` package (PyPI 0.1.0) ships the System One server itself; ``strands-decider serve`` binds
127.0.0.1, which an IAP tunnel cannot reach. This launcher builds the same app with the package's ``create_app`` and
runs it under uvicorn on the host it is given (0.0.0.0 on the VM; the firewall limits who connects). It loads the
checkpoint from a local directory that startup.sh downloaded at a pinned revision, with HF_HUB_OFFLINE set by the
runner, so nothing else is fetched at serve time. ``trust_remote_code`` is never passed.

The package is experimental and its ``create_app`` signature is not documented, so the launcher maps its arguments
by name and stops with the signature in the error when it cannot. Check the journal on first boot.

    python strands_server.py --checkpoint /opt/goldrails/checkpoints/strands-decider-2b --port 8013 --device cuda:0
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="local directory holding the pinned revision")
    ap.add_argument("--model-name", default=None)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8013)
    a = ap.parse_args(argv)
    create_app = find_create_app()
    app = create_app(**app_kwargs(create_app, a.checkpoint, a.device, a.model_name))
    import uvicorn
    uvicorn.run(app, host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
