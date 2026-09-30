"""Profanity rerun on Civil Comments' original obscene labels (dataset v1.3, subset first-benchmark-v1.3), every system.

    uv run python benchmark/runs/profanity_v13_run.py tune      # the 50 profanity tuning rows, every system
    uv run python benchmark/runs/profanity_v13_run.py freeze    # writes freeze-extension-4.json; commit it
    uv run python benchmark/runs/profanity_v13_run.py test      # the 160 profanity test rows, once, under the committed manifest
    uv run python benchmark/runs/profanity_v13_run.py latency   # serial latency pass, 50 rows per system

Every system answers ``v1-f4-obscenity``, the Civil Comments raters' own question; Bedrock answers it from its frozen
word-filter guardrail's managed PROFANITY list. Thresholds are fitted on the 50 tuning rows by the usual rule (maximise
tuning task score). The manifest names the primary manifest's sha256 and is committed before any test call; the runner
refuses test rows until then. Ledgers: ``prof-v13-tune.jsonl``, ``prof-v13-test.jsonl``, ``prof-v13-latency.jsonl``.
Earlier profanity results (the lexicon-selected set with single-AI labels) stay as they were.

Which run: ``GOLDRAILS_RUN`` and ``GOLDRAILS_FROZEN_RUN`` (run_context.py); ``--dry-run`` prints what a stage would run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import first_benchmark as FB  # noqa: E402
import run_context as RC  # noqa: E402

from goldrails_bench.runner import run_matrix  # noqa: E402
from goldrails_bench.subset import load_subset_rows  # noqa: E402

SUBSET = "first-benchmark-v1.3"
SUITE = "word_filters"
CTX = FB.CTX
EXT = CTX.frozen_subsets / "freeze-extension-4.json"
SELECTION = CTX.frozen_selections / "prof-v13-selection.json"
QUESTION_SET = "v1-f4-obscenity"   # the raters' own question, for every system (Bedrock reads its managed list)
CONTRACT = CTX.default_contract(FB.REPO / "benchmark" / "contracts" / "v1.1.json")


def rows(split: str) -> list:
    return [r for r in load_subset_rows(SUBSET, "F4", split) if r.subtask == "profanity"]


def systems(kinds: set) -> dict:
    return {k: v for k, v in FB.clients(kinds, SUITE).items() if k != "regex-baseline"}


def run(stage: str, kinds: set, split: str, serial=False, limit=None, manifest=None, rerun=False):
    FB.OUT.mkdir(parents=True, exist_ok=True)
    rs = rows(split)[: limit or None]
    ledger = FB.OUT / f"prof-v13-{stage}{'-rerun' if rerun else ''}.jsonl"   # a recorded row is never rerun in place
    for name, (client, gpu) in systems(kinds).items():
        q = QUESTION_SET
        out = run_matrix({name: client}, FB.qsets([q]), rs, workers={"jev-1.13.0": 8}, serial=serial,
                         gpu_of={name: gpu} if gpu is not None else {}, results_path=ledger, load=FB.LOAD,
                         freeze_manifest=manifest, progress=lambda *_: None)
        print(f"prof-v13 {stage:8s} {name:24s} {q:12s} {len(out):4d} rows, {sum(not r['ok'] for r in out)} failed", flush=True)


def freeze(kinds: set):
    from goldrails_bench import freeze as F
    from goldrails_bench.leaderboard import build
    from goldrails_bench.policy import DEFAULT_POLICY
    ledgers = [p for p in (FB.OUT / "prof-v13-tune.jsonl", FB.OUT / "prof-v13-tune-rerun.jsonl") if p.exists()]
    for tune in ledgers:
        splits = {json.loads(x)["dataset"]["split"] for x in tune.read_text().splitlines() if x.strip()}
        if splits != {"tune"}:
            raise SystemExit(f"{tune.name} holds splits {sorted(splits)}; only tuning rows may fit anything")
    args = [str(x) for p in ledgers for x in (p, p.with_suffix(".arms.jsonl")) if x.exists()]
    doc = build(args, contract_path=CONTRACT, mode="smoke")   # a successful re-attempt supersedes its failed original
    names = set(systems(kinds))
    EXT.parent.mkdir(parents=True, exist_ok=True)
    arms = [a for a in doc["arms"] if a["system"] in names and a["suite"] == SUITE and a["question_set"] == QUESTION_SET]
    primary_sha = hashlib.sha256(FB.MANIFEST.read_bytes()).hexdigest()
    test_sha = rows("test")[0].dataset["sha256"]
    m = F.write_manifest(doc, EXT, retry_policy=DEFAULT_POLICY, test_datasets={SUITE: test_sha},
                         arms=[a["arm_id"] for a in arms],
                         extends={"manifest_sha256": primary_sha, "subset": SUBSET, "systems": sorted(names),
                                  "reason": ("profanity subtask replaced by 'Profanity or obscenity — Civil Comments' (dataset v1.3): "
                                             "original obscene rater fractions, >= 0.5 yes, 0 no; every system answers "
                                             "the raters' question; thresholds fitted on the new tuning rows (contract v1.1)")})
    probs = F.validate(m)
    if probs:
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    if not CTX.is_first:
        m["run"] = {"id": CTX.run, "declaration": RC.rel(CTX.subsets / "run.json"), "subset": SUBSET,
                    "contract": RC.rel(CONTRACT)}
    EXT.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    SELECTION.write_text(json.dumps({
        "rule": "every system answers v1-f4-obscenity (the Civil Comments raters' question); threshold fitted on the v1.3 tuning rows",
        "chosen": [{"system": a["system"], "suite": SUITE, "question_set": a["question_set"],
                    "tune_task_score": (a.get("suite_score") or {}).get("value")} for a in sorted(arms, key=lambda a: a["system"])]},
        indent=1) + "\n")
    print(f"extension manifest: {len(m['arms'])} arms -> {EXT.relative_to(FB.REPO)}; commit it before the test stage")


def main(argv=None) -> int:
    global CONTRACT
    load_dotenv(find_dotenv(usecwd=True))
    RC.check_env_unchanged(CTX)
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("tune", "freeze", "test", "latency"))
    ap.add_argument("--systems", default="open,jev,bedrock")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--rerun", action="store_true", help="write to the -rerun ledger (re-attempts of failed rows)")
    ap.add_argument("--contract", help=f"contract the freeze fits under (default {RC.rel(CONTRACT)})")
    ap.add_argument("--dry-run", "--plan", dest="dry_run", action="store_true",
                    help="print paths, systems, rows and already-recorded rows; build no client, call nothing")
    ap.add_argument(RC.I_KNOW_FLAG, dest="i_know", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    kinds = set(a.systems.split(","))
    if a.contract:
        CONTRACT = Path(a.contract).resolve()
    if a.stage in ("tune", "freeze"):
        RC.require_same_run(CTX, a.stage)
    if a.dry_run:
        return dry_run(a, kinds)
    if a.stage == "freeze":
        RC.refuse_protected([EXT, SELECTION], a.i_know, "freeze")
        RC.refuse_existing([EXT, SELECTION], "freeze")
    else:
        RC.refuse_protected([FB.OUT], a.i_know, a.stage)
    if a.stage == "tune":
        run("tune", kinds, "tune", limit=a.limit, rerun=a.rerun)
    elif a.stage == "freeze":
        freeze(kinds)
    elif a.stage == "test":
        run("test", kinds, "test", manifest=EXT, rerun=a.rerun)
    else:
        run("latency", kinds, "tune", serial=True, limit=a.limit or 50, manifest=EXT)
    return 0


def plan(stage: str, kinds: set, split: str, limit=None, manifest=None, rerun=False) -> RC.Plan:
    """What ``run`` would run, from the implementations declaration: no clients, no calls."""
    p = RC.Plan(CTX, "profanity_v13_run.py", stage)
    p.path("results", FB.OUT)
    p.path("subset", FB.REPO / "benchmark" / "subsets" / SUBSET / "manifest.json")
    if manifest is not None:
        p.path("manifest (read)", manifest)
    rs = rows(split)[: limit or None]
    ledger = FB.OUT / f"prof-v13-{stage}{'-rerun' if rerun else ''}.jsonl"
    for name in (k for k in RC.declared_systems(FB.IMPL, kinds, SUITE) if k != "regex-baseline"):
        p.add(SUITE, name, [QUESTION_SET], rs, ledger)
    return p


def dry_run(a, kinds) -> int:
    import json as _json
    print(_json.dumps(CTX.describe()))
    if a.stage == "freeze":
        print(f"== profanity_v13_run.py freeze (run {CTX.run}) — DRY RUN\n   reads   {RC.rel(FB.OUT / 'prof-v13-tune.jsonl')}"
              f" (+ prof-v13-tune-rerun.jsonl if present)\n   reads   {RC.rel(FB.MANIFEST)} (primary manifest sha256 goes in extends)\n"
              f"   writes  {RC.rel(EXT)}{'  (EXISTS: freeze would refuse)' if EXT.exists() else ''}\n"
              f"   writes  {RC.rel(SELECTION)}\n   contract {RC.rel(CONTRACT)}\n"
              f"   protected first-benchmark location: {RC.is_protected(EXT)}")
        return 0
    split = "test" if a.stage == "test" else "tune"
    limit = (a.limit or 50) if a.stage == "latency" else a.limit
    plan(a.stage, kinds, split, limit, EXT if a.stage == "test" else None, a.rerun and a.stage != "latency").print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
