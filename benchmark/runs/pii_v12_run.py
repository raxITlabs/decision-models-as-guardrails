"""PII rerun on NVIDIA Nemotron-PII (dataset v1.2, subset first-benchmark-v1.2) for every system.

    uv run python benchmark/runs/pii_v12_run.py tune      # the 50 PII tuning rows, every system
    uv run python benchmark/runs/pii_v12_run.py freeze    # writes freeze-extension-3.json; commit it
    uv run python benchmark/runs/pii_v12_run.py test      # the 160 PII test rows, once, under the committed manifest
    uv run python benchmark/runs/pii_v12_run.py latency   # serial latency pass, 50 rows per system

Each system keeps the question set frozen for PII in the first benchmark (v2-f5-pii for all seven); only the threshold
is fitted again, on the new tuning rows, by the same rule (maximise tuning task score). The manifest names the primary
manifest's sha256 and is committed before any test call; the runner refuses test rows until then. Ledgers:
``pii-v12-tune.jsonl``, ``pii-v12-test.jsonl``, ``pii-v12-latency.jsonl``. The first benchmark's PII results stay as
they were.

Which run: ``GOLDRAILS_RUN`` and ``GOLDRAILS_FROZEN_RUN`` (run_context.py). A run that skipped the core F5 arm has no
PII entry in its core selection; each system then answers the sole PII candidate the implementations declaration names
(``v2-f5-pii``), and the selection file records that rule. ``--dry-run`` prints what a stage would run.
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

SUBSET = "first-benchmark-v1.2"
SUITE = "sensitive_info"
CTX = FB.CTX
EXT = CTX.frozen_subsets / "freeze-extension-3.json"
SELECTION = CTX.frozen_selections / "pii-v12-selection.json"
CONTRACT = CTX.default_contract(FB.REPO / "benchmark" / "contracts" / "v1.1.json")
RULE_FROZEN = "each system's PII question set frozen in the first benchmark (selection.json); threshold refitted on v1.2 tuning rows"


def sole_candidate(impl: dict = None) -> str:
    cands = (impl or FB.IMPL)["candidate_question_sets"][SUITE]
    if len(cands) != 1:
        raise SystemExit(f"no PII question set in the core selection and {len(cands)} declared candidates {cands}: "
                         "the fallback needs exactly one; freeze a core F5 arm or decide the set first")
    return cands[0]


def question_set_rule(selection_path=None, impl: dict = None) -> tuple[dict, str]:
    """({system: question set}, rule). The core selection's PII choice when it has one (the first run); otherwise
    the sole declared candidate for every system, because the superseded core F5 arm was never run."""
    path = Path(selection_path or FB.SELECTION)
    if path.exists():
        sel = json.loads(path.read_text())
        chosen = {c["system"]: c["question_set"] for c in sel["chosen"] if c["suite"] == SUITE}
        if chosen:
            return chosen, RULE_FROZEN
    q = sole_candidate(impl)
    names = [n for n in (impl or FB.IMPL)["systems"]["decision_models"]]
    names.append((impl or FB.IMPL)["systems"]["managed_service"]["composite_of"][SUITE])
    return ({n: q for n in names},
            f"core F5 (AI4Privacy) was skipped as superseded, so {RC.rel(path)} has no PII choice; every system "
            f"answers {q}, the sole sensitive_info candidate declared in {RC.rel(RC.IMPL_DIR / 'implementations.json')}; "
            "threshold fitted on v1.2 tuning rows")


def frozen_question_sets() -> dict:
    return question_set_rule()[0]


def rows(split: str) -> list:
    return [r for r in load_subset_rows(SUBSET, "F5", split) if r.subtask == "pii"]


def systems(kinds: set) -> dict:
    return {k: v for k, v in FB.clients(kinds, SUITE).items() if k != "regex-baseline"}


def run(stage: str, kinds: set, split: str, serial=False, limit=None, manifest=None, rerun=False):
    FB.OUT.mkdir(parents=True, exist_ok=True)
    rs = rows(split)[: limit or None]
    qs = frozen_question_sets()
    ledger = FB.OUT / f"pii-v12-{stage}{'-rerun' if rerun else ''}.jsonl"   # a recorded row is never rerun in place
    for name, (client, gpu) in systems(kinds).items():
        q = qs[name]
        out = run_matrix({name: client}, FB.qsets([q]), rs, workers={"jev-1.13.0": 8}, serial=serial,
                         gpu_of={name: gpu} if gpu is not None else {}, results_path=ledger, load=FB.LOAD,
                         freeze_manifest=manifest, progress=lambda *_: None)
        print(f"pii-v12 {stage:8s} {name:24s} {q:12s} {len(out):4d} rows, {sum(not r['ok'] for r in out)} failed", flush=True)


def freeze(kinds: set):
    from goldrails_bench import freeze as F
    from goldrails_bench.leaderboard import build
    from goldrails_bench.policy import DEFAULT_POLICY
    ledgers = [p for p in (FB.OUT / "pii-v12-tune.jsonl", FB.OUT / "pii-v12-tune-rerun.jsonl") if p.exists()]
    for tune in ledgers:
        splits = {json.loads(x)["dataset"]["split"] for x in tune.read_text().splitlines() if x.strip()}
        if splits != {"tune"}:
            raise SystemExit(f"{tune.name} holds splits {sorted(splits)}; only tuning rows may fit anything")
    args = [str(x) for p in ledgers for x in (p, p.with_suffix(".arms.jsonl")) if x.exists()]
    doc = build(args, contract_path=CONTRACT, mode="smoke")   # a successful re-attempt supersedes its failed original
    names = set(systems(kinds))
    EXT.parent.mkdir(parents=True, exist_ok=True)
    arms = [a for a in doc["arms"] if a["system"] in names and a["suite"] == SUITE]
    primary_sha = hashlib.sha256(FB.MANIFEST.read_bytes()).hexdigest()
    test_sha = rows("test")[0].dataset["sha256"]
    m = F.write_manifest(doc, EXT, retry_policy=DEFAULT_POLICY, test_datasets={SUITE: test_sha},
                         arms=[a["arm_id"] for a in arms],
                         extends={"manifest_sha256": primary_sha, "subset": SUBSET, "systems": sorted(names),
                                  "reason": ("PII source replaced by NVIDIA Nemotron-PII (dataset v1.2) after its audit; "
                                             "each system keeps its frozen PII question set and refits its threshold "
                                             "on the new tuning rows (contract v1.1)")})
    probs = F.validate(m)
    if probs:
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    if not CTX.is_first:
        m["run"] = {"id": CTX.run, "declaration": RC.rel(CTX.subsets / "run.json"), "subset": SUBSET,
                    "contract": RC.rel(CONTRACT), "question_set_rule": question_set_rule()[1]}
    EXT.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    sel_rule = question_set_rule()[1]
    SELECTION.parent.mkdir(parents=True, exist_ok=True)
    SELECTION.write_text(json.dumps({
        "rule": sel_rule,
        **({} if CTX.is_first else {"run": {"id": CTX.run, "contract": RC.rel(CONTRACT),
                                            "question_set_source": "core selection" if sel_rule == RULE_FROZEN
                                            else "sole declared candidate (core F5 skipped as superseded)"}}),
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
    p = RC.Plan(CTX, "pii_v12_run.py", stage)
    p.path("results", FB.OUT)
    p.path("subset", FB.REPO / "benchmark" / "subsets" / SUBSET / "manifest.json")
    if manifest is not None:
        p.path("manifest (read)", manifest)
    rs = rows(split)[: limit or None]
    ledger = FB.OUT / f"pii-v12-{stage}{'-rerun' if rerun else ''}.jsonl"
    for name in (k for k in RC.declared_systems(FB.IMPL, kinds, SUITE) if k != "regex-baseline"):
        p.add(SUITE, name, [frozen_question_sets()[name]], rs, ledger)
    return p


def dry_run(a, kinds) -> int:
    import json as _json
    print(_json.dumps(CTX.describe()))
    if a.stage == "freeze":
        print(f"== pii_v12_run.py freeze (run {CTX.run}) — DRY RUN\n   reads   {RC.rel(FB.OUT / 'pii-v12-tune.jsonl')}"
              f" (+ pii-v12-tune-rerun.jsonl if present)\n   reads   {RC.rel(FB.MANIFEST)} (primary manifest sha256 goes in extends)\n"
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
