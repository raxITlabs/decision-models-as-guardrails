"""Resolve model endpoints from GCP at run time instead of saving URLs.

The Terraform module writes the served model list (name, port, gpu) into the
instance's metadata, and the Compute API knows the instance's current external
IP. This module reads both through gcloud, so nothing about the VM is stored in
the repo or in .env. Requires `gcloud` to be authenticated for the project.

    from goldrails_bench.endpoints import resolve
    urls = resolve(mode="tunnel")   # {"kev-4b": "http://localhost:8010", ...}
    urls = resolve(mode="direct")   # {"kev-4b": "http://<external-ip>:8010", ...}

`tunnel` assumes `scripts/tunnels.sh up` is running. `direct` needs the
Terraform variable `direct_access_cidrs` to include your address.
"""
from __future__ import annotations

import json
import os
import subprocess

DEFAULTS = {"instance": "gold-rails-serve"}


def _gcloud(args: list[str]) -> str:
    return subprocess.run(["gcloud", *args], check=True, capture_output=True, text=True).stdout.strip()


def describe(instance: str | None = None, zone: str | None = None, project: str | None = None) -> dict:
    instance = instance or os.environ.get("GOLDRAILS_INSTANCE", DEFAULTS["instance"])
    project = project or os.environ.get("GOLDRAILS_PROJECT") or _gcloud(["config", "get-value", "project"])
    zone = zone or os.environ.get("GOLDRAILS_ZONE")
    if zone:
        raw = _gcloud(["compute", "instances", "describe", instance, "--zone", zone, "--project", project, "--format", "json"])
        d = json.loads(raw)
    else:  # zone is wherever Terraform found capacity; look the instance up by name across zones
        found = json.loads(_gcloud(["compute", "instances", "list", "--project", project, "--filter", f"name={instance}", "--format", "json"]))
        if not found:
            raise RuntimeError(f"no instance named {instance} in {project}; run terraform apply")
        d = found[0]
        zone = d["zone"].rsplit("/", 1)[-1]
    items = {i["key"]: i["value"] for i in d.get("metadata", {}).get("items", [])}
    models = json.loads(items.get("models-json", "[]"))
    ip = None
    for nic in d.get("networkInterfaces", []):
        for ac in nic.get("accessConfigs", []):
            ip = ac.get("natIP") or ip
    return {"instance": instance, "zone": zone, "project": project, "status": d.get("status"),
            "external_ip": ip, "machine_type": d.get("machineType", "").rsplit("/", 1)[-1], "models": models}


def resolve(mode: str = "tunnel", **kw) -> dict:
    info = describe(**kw)
    if info["status"] != "RUNNING":
        raise RuntimeError(f"{info['instance']} is {info['status']}; run terraform apply or start it")
    if mode == "tunnel":
        return {m["name"]: f"http://localhost:{m['port']}" for m in info["models"]}
    if mode == "direct":
        if not info["external_ip"]:
            raise RuntimeError("instance has no external IP")
        return {m["name"]: f"http://{info['external_ip']}:{m['port']}" for m in info["models"]}
    raise ValueError("mode must be tunnel or direct")


def model_alias(m: dict) -> str:
    """The model name a served System One endpoint accepts. Open-Jev only answers to its wire alias."""
    return "open-jev" if m.get("kind") == "openjev" else m["name"]


# Context windows that a kind's server documents and enforces, in tokens. Added to the identity, so the Noul adapter
# records them as serving.max_length. Strands Decider: 4,096 tokens, question cut from the front and state from the
# right, with no truncation flag (strands-decider 0.1.0 README). Other kinds keep the identity they had, so the config
# hash of runs already made does not move.
KIND_MAX_LENGTH = {"strands": 4096}


def identity_of(m: dict) -> dict:
    ident = {"ref": m.get("ref"), "revision": m.get("revision"), "kind": m["kind"]}
    if m["kind"] in KIND_MAX_LENGTH:
        ident["max_length"] = KIND_MAX_LENGTH[m["kind"]]
    return ident


def resolve_models(mode: str = "tunnel", **kw) -> list[dict]:
    """[{name, url, model, kind, gpu}] for every served model, ready for SystemOneClient(name, base_url=url, model=model)."""
    info = describe(**kw)
    urls = resolve(mode, **kw)
    return [{"name": m["name"], "url": urls[m["name"]], "model": model_alias(m), "kind": m["kind"], "gpu": m.get("gpu"),
             "identity": identity_of(m)} for m in info["models"]]


def tunnel_commands(**kw) -> list[str]:
    info = describe(**kw)
    return [f"gcloud compute start-iap-tunnel {info['instance']} {m['port']} --local-host-port=localhost:{m['port']} "
            f"--zone {info['zone']} --project {info['project']}" for m in info["models"]]
