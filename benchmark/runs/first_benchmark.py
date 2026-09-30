"""Run the first Gold Rails benchmark on the frozen subset, in stages.

    uv run python benchmark/runs/first_benchmark.py tune --systems open,jev,regex
    uv run python benchmark/runs/first_benchmark.py tune --systems bedrock
    uv run python benchmark/runs/first_benchmark.py freeze          # writes the manifest; commit it before testing
    uv run python benchmark/runs/first_benchmark.py test --systems open,jev,regex,bedrock
    uv run python benchmark/runs/first_benchmark.py latency --systems open,jev,regex,bedrock

Stages never touch test rows before the freeze manifest is committed (the runner refuses). Core suites and bias write
separate ledgers so the leaderboard reads only core suites. Every open-model stage records allocated VM time in
``serving.jsonl`` for cost per 1,000.

Which run: ``GOLDRAILS_RUN`` (default ``first-benchmark``) and ``GOLDRAILS_FROZEN_RUN`` (run_context.py). Rows always
come from the ``first-benchmark`` data subset. A run other than the first skips the superseded F5 AI4Privacy suite by
default (``--suites`` overrides), freezes against the signed contract v1.1 (``--contract`` overrides) and keeps its
manifest and selection in ``benchmark/subsets/<RUN>/``. ``--dry-run`` prints what a stage would run and calls nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402

from goldrails_bench.question_sets import load as load_qs  # noqa: E402
from goldrails_bench.runner import run_matrix  # noqa: E402
from goldrails_bench.subset import load_subset_rows  # noqa: E402

SUBSET = RC.DATA_SUBSET                       # the data subset; the run id is CTX.run
REPO = RC.REPO
CTX = RC.current()
OUT = CTX.results
MANIFEST = CTX.frozen_subsets / "freeze-manifest.json"          # read by test, latency and the extension scripts
MANIFEST_OUT = CTX.subsets / "freeze-manifest.json"             # written by freeze (same file: freeze needs FROZEN == RUN)
SELECTION = CTX.frozen_selections / "selection.json"
SELECTION_OUT = CTX.selections / "selection.json"
IMPL = json.loads((RC.IMPL_DIR / "implementations.json").read_text())
CORE = {"content": "F1", "prompt_attacks": "F2", "word_filters": "F4", "sensitive_info": "F5", "grounding": "F6"}
ALL_SUITES = list(CORE) + ["bias_b1", "bias_b3"]
DEFAULT_SUITES = [s for s in ALL_SUITES if s not in CTX.skipped("core")]
HARDWARE = {"key": RC.DEFAULT_HARDWARE, "zone": None}      # set by --hardware / --vm-zone
LOAD = {"concurrency": {"api:jev-1.13.0": 8, "api:bedrock": 1, "gpu_lane": 2}, "batch_size": 1,
        "client_location": IMPL["declared_load"]["client_location"]}
BEDROCK_OF = IMPL["systems"]["managed_service"]["composite_of"]


def qsets(names):
    return {n: load_qs(*n.split("-", 1)) for n in names}


def clients(kinds: set, suite: str):
    """{system: (client, gpu or None)} applicable to this suite."""
    out = {}
    if "jev" in kinds:
        from goldrails_bench.systemone import SystemOneClient
        out["jev-1.13.0"] = (SystemOneClient("jev-1.13.0", model="jev-1.13.0", identity={"model": "jev-1.13.0", "provider": "api.typesafe.ai"}), None)
    if "open" in kinds:
        from goldrails_bench.endpoints import resolve_models
        from goldrails_bench.systemone import SystemOneClient
        for m in resolve_models(mode="tunnel"):
            out[m["name"]] = (SystemOneClient(m["name"], base_url=m["url"], model=m["model"], identity=m["identity"], timeout=300), m["gpu"])
    if "bedrock" in kinds and suite in BEDROCK_OF:
        name = BEDROCK_OF[suite]
        if name == "bedrock-checks":
            from goldrails_bench.bedrock import BedrockChecksClient
            out[name] = (BedrockChecksClient(), None)
        else:
            from goldrails_bench.bedrock_apply import BedrockApplyClient
            out[name] = (BedrockApplyClient(name.split("-")[-1]), None)
    if "regex" in kinds and suite == "word_filters":
        from goldrails_bench.regex_words import RegexWordClient
        out["regex-baseline"] = (RegexWordClient(), None)
    return out


def serving_note(stage: str, systems: dict, rows_by_system: dict, started: float, ended: float, windows: dict):
    """Allocated VM time per open model: the wall-clock window in which the VM served only that model's calls (systems
    run one after another), so each model is charged the whole VM for its own window (share 1.0)."""
    gpu_systems = [s for s, (_, g) in systems.items() if g is not None]
    if not gpu_systems:
        return
    with (OUT / "serving.jsonl").open("a") as f:
        for s in gpu_systems:
            rec = {"stage": stage, "system": s, "hardware": HARDWARE["key"],
                   "allocated_seconds": round(windows.get(s, 0.0), 1), "share": 1.0, "method": "per-system window",
                   "evaluations": rows_by_system.get(s, 0),
                   "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                   "ended": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ended))}
            rec.update(RC.zone_fields(HARDWARE["key"], HARDWARE["zone"]))
            f.write(json.dumps(rec) + "\n")



def suite_rows(suite: str, split: str, limit=None) -> list:
    feat = CORE.get(suite, "F7")
    rows = load_subset_rows(SUBSET, feat, split)
    if suite == "bias_b1":
        rows = [r for r in rows if r.subtask == "b1_disparate_fpr"]
    elif suite == "bias_b3":
        rows = [r for r in rows if r.subtask == "b3_decision"]
    return rows[:limit] if limit else rows


def question_groups(suite: str, name: str, rows: list, chosen: dict | None) -> dict:
    """{question set: rows} one system answers in this suite."""
    if suite == "bias_b3":
        return {"v1-f7-bbq": [r for r in rows if r.provenance.source == "bbq"],
                "v1-f7-discrim-eval": [r for r in rows if r.provenance.source == "discrim_eval"]}
    cand = IMPL["candidate_question_sets"]["content" if suite == "bias_b1" else suite]
    names = [chosen[(name, "content" if suite == "bias_b1" else suite)]] if chosen is not None else cand
    return {n: rows for n in names}


def ledger_of(stage: str, suite: str) -> Path:
    return OUT / (f"{stage}-bias.jsonl" if suite.startswith("bias") else f"{stage}.jsonl")


def run_stage(stage: str, kinds: set, split: str, chosen: dict | None = None, serial=False, limit=None, suites=None):
    OUT.mkdir(parents=True, exist_ok=True)
    workers = {"jev-1.13.0": 8}
    for suite in (suites or ALL_SUITES):
        rows = suite_rows(suite, split, limit)
        if not rows:
            continue
        systems = clients(kinds, "content" if suite == "bias_b1" else suite)
        if suite == "bias_b3":
            systems = {k: v for k, v in systems.items() if not k.startswith("bedrock") and k != "regex-baseline"}
        ledger = ledger_of(stage, suite)
        started = time.time(); counts = {}; windows = {}
        for name, (client, gpu) in systems.items():
            t_sys = time.time()
            groups = question_groups(suite, name, rows, chosen)
            for qname, grows in groups.items():
                if not grows:
                    continue
                out = run_matrix({name: client}, qsets([qname]), grows, workers=workers, serial=serial,
                                 gpu_of={name: gpu} if gpu is not None else {}, results_path=ledger, load=LOAD,
                                 freeze_manifest=MANIFEST if split == "test" else None, progress=lambda *_: None)
                counts[name] = counts.get(name, 0) + len(out)
                print(f"{stage} {suite:15s} {name:24s} {qname:22s} {len(out):4d} rows, {sum(not r['ok'] for r in out)} failed", flush=True)
            windows[name] = time.time() - t_sys
        serving_note(f"{stage}:{suite}", systems, counts, started, time.time(), windows)


def plan_stage(stage: str, kinds: set, split: str, chosen: dict | None = None, limit=None, suites=None) -> RC.Plan:
    """What ``run_stage`` would run, from the implementations declaration and the subset: no clients, no calls."""
    p = RC.Plan(CTX, "first_benchmark.py", stage)
    p.path("results", OUT)
    if stage in ("test", "latency"):
        p.path("selection (read)", SELECTION)
    if split == "test":
        p.path("manifest (read)", MANIFEST)
    skipped = [s for s in ALL_SUITES if s not in (suites or ALL_SUITES)]
    if skipped:
        p.notes.append("suites skipped: " + ", ".join(f"{s} ({CTX.skipped('core').get(s, 'not selected')})" for s in skipped))
    for suite in (suites or ALL_SUITES):
        rows = suite_rows(suite, split, limit)
        if not rows:
            continue
        systems = RC.declared_systems(IMPL, kinds, "content" if suite == "bias_b1" else suite)
        if suite == "bias_b3":
            systems = {k: v for k, v in systems.items() if not k.startswith("bedrock") and k != "regex-baseline"}
        for name in systems:
            if chosen is None and stage in ("test", "latency"):   # the selection is written at the freeze
                cand = IMPL["candidate_question_sets"]["content" if suite == "bias_b1" else suite]
                groups = question_groups(suite, name, rows, {(name, "content" if suite == "bias_b1" else suite): cand[0]})
                note = None if suite == "bias_b3" else f"one of {cand}, chosen at the freeze"
            else:
                groups, note = question_groups(suite, name, rows, chosen), None
            for qname, grows in groups.items():
                if grows:
                    p.add(suite, name, [qname], grows, ledger_of(stage, suite), note)
    return p

def rerun_failed():
    """Documented correction: re-attempt only the test rows whose original call failed on a transient connection error
    that the frozen retry policy should have retried (the retry matcher missed SDK-prefixed error names). Same frozen
    configuration and manifest; results go to test-rerun.jsonl and the original records stay untouched."""
    from collections import defaultdict
    from goldrails_bench.policy import TRANSIENT_3
    failed = defaultdict(set)
    for line in (OUT / "test.jsonl").read_text().splitlines():
        d = json.loads(line)
        if not d["ok"] and TRANSIENT_3.retryable(d.get("error")):
            failed[(d["system"], d["question_set"], d["dataset"]["feature"])].add(d["id"])
    suite_of = {v: k for k, v in CORE.items()}
    for (system, qname, feat), ids in sorted(failed.items()):
        suite = suite_of[feat]
        rows = [r for r in load_subset_rows(SUBSET, feat, "test") if r.id in ids]
        client, gpu = clients({RC.kind_of(system)}, suite)[system]   # Bedrock and regex rows too, not only open and Jev
        out = run_matrix({system: client}, qsets([qname]), rows, gpu_of={system: gpu} if gpu is not None else {},
                         results_path=OUT / "test-rerun.jsonl", load=LOAD, freeze_manifest=MANIFEST, progress=lambda *_: None)
        print(f"rerun {system} {qname} {feat}: {len(out)} rows, {sum(not r['ok'] for r in out)} failed", flush=True)


def load_chosen() -> dict:
    m = json.loads(SELECTION.read_text())
    return {(x["system"], x["suite"]): x["question_set"] for x in m["chosen"]}


def freeze_guard(i_know: bool, suites=None) -> None:
    """Before anything is read or built: same run, not the first run's records, nothing already frozen."""
    RC.require_same_run(CTX, "freeze")
    RC.refuse_protected([MANIFEST_OUT, SELECTION_OUT], i_know, "freeze")
    RC.refuse_existing([MANIFEST_OUT, SELECTION_OUT], "freeze")


def freeze(contract=None, suites=None):
    from goldrails_bench import freeze as F
    from goldrails_bench.leaderboard import build
    from goldrails_bench.policy import DEFAULT_POLICY
    suites = suites or ALL_SUITES
    doc = build([str(OUT / "tune.jsonl"), str(OUT / "tune.arms.jsonl")], contract_path=contract and str(contract), mode="smoke")
    best = {}
    for a in doc["arms"]:
        v = (a.get("suite_score") or {}).get("value")
        key = (a["system"], a["suite"])
        if v is None or a["suite"] not in suites:
            continue
        if key not in best or v > best[key][0] or (v == best[key][0] and a["question_set"] < best[key][1]["question_set"]):
            best[key] = (v, a)
    chosen = [a for _, a in best.values()]
    test_sha = {su: load_subset_rows(SUBSET, feat, "test")[0].dataset["sha256"] for su, feat in CORE.items() if su in suites}
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    m = F.write_manifest(doc, MANIFEST_OUT, retry_policy=DEFAULT_POLICY, test_datasets=test_sha, arms=[a["arm_id"] for a in chosen])
    sel = {"rule": "per system and suite, the candidate question set with the highest tuning task score; ties to the lower name",
           "chosen": [{"system": a["system"], "suite": a["suite"], "question_set": a["question_set"], "tune_task_score": v}
                      for v, a in sorted(best.values(), key=lambda t: (t[1]["suite"], t[1]["system"]))]}
    if not CTX.is_first:   # the first run's files keep their historical shape
        m["run"] = sel["run"] = run_block(contract, suites)
    SELECTION_OUT.parent.mkdir(parents=True, exist_ok=True)
    SELECTION_OUT.write_text(json.dumps(sel, indent=1) + "\n")
    add_bias_arms(m, suites)
    print(f"manifest: {len(m['arms'])} core arms + bias arms -> {MANIFEST_OUT}; commit it before the test stage")
    arm_summary(m)


def run_block(contract, suites) -> dict:
    return {"id": CTX.run, "declaration": RC.rel(CTX.subsets / "run.json"),
            "contract": RC.rel(contract) if contract else "goldrails_bench.leaderboard.DEFAULT_CONTRACT",
            "suites": list(suites),
            "skipped_superseded": {s: r for s, r in CTX.skipped("core").items() if s not in suites}}


def arm_summary(m: dict) -> None:
    from collections import Counter
    c = Counter(a["suite"] for a in m["arms"])
    print("arms per suite: " + ", ".join(f"{k} {v}" for k, v in sorted(c.items())))
    for su in sorted(c):
        print(f"  {su:15s} " + ", ".join(sorted(a["system"] for a in m["arms"] if a["suite"] == su)))


def add_bias_arms(m: dict, suites=None):
    """Bias rows are test rows too, so their arms must be frozen: B1 reuses each system's chosen content question set
    and its request threshold; B3 uses the fixed bias question sets with no threshold (source-defined metrics)."""
    from goldrails_bench import freeze as F
    from goldrails_bench.runner import config_hash
    suites = suites or ALL_SUITES
    rows = load_subset_rows(SUBSET, "F7", "test")
    sha = rows[0].dataset["sha256"]
    extra = []
    for kinds in ({"jev"}, {"open"}, {"bedrock"}):
        try:
            cl = clients(kinds, "content")
        except Exception as e:  # noqa: BLE001
            print(f"bias arms for {kinds}: {e}"); continue
        for name, (client, _) in cl.items():
            content_arm = next((a for a in m["arms"] if a["system"] == name and a["suite"] == "content"), None)
            if content_arm is None:
                continue
            q = content_arm["question_set"]
            if "bias_b1" in suites:
                extra.append({"system": name, "question_set": q, "config_hash": config_hash(client, qsets([q])[q]), "dataset_sha256": sha,
                              "suite": "bias_b1", "thresholds": content_arm["thresholds"], "tuned_on": content_arm["tuned_on"]})
            if not name.startswith("bedrock") and "bias_b3" in suites:
                for q3 in ("v1-f7-bbq", "v1-f7-discrim-eval"):
                    extra.append({"system": name, "question_set": q3, "config_hash": config_hash(client, qsets([q3])[q3]),
                                  "dataset_sha256": sha, "suite": "bias_b3", "thresholds": None, "tuned_on": None})
    m["arms"] += extra
    probs = F.validate(m)
    if probs:
        raise SystemExit("manifest invalid: " + "; ".join(probs))
    MANIFEST_OUT.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")


def parse_suites(s: str | None) -> list:
    if not s:
        return DEFAULT_SUITES
    out = [x.strip() for x in s.split(",") if x.strip()]
    bad = [x for x in out if x not in ALL_SUITES]
    if bad:
        raise SystemExit(f"unknown suites {bad}; choose from {ALL_SUITES}")
    return [x for x in ALL_SUITES if x in out]


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    RC.check_env_unchanged(CTX)
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("tune", "freeze", "bias-arms", "test", "rerun-failed", "latency"))
    ap.add_argument("--systems", default="open,jev,regex,bedrock")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--suites", help=f"comma list from {ALL_SUITES}; default {DEFAULT_SUITES}")
    ap.add_argument("--contract", help="contract the freeze fits under (default: the leaderboard's built-in v1.0-draft "
                                       "for the first run, contracts/v1.1-signed.json for any other run)")
    ap.add_argument("--hardware", default=RC.DEFAULT_HARDWARE, help="tariff hardware key on serving records")
    ap.add_argument("--vm-zone", default=None, help="zone the VM runs in (default GOLDRAILS_VM_ZONE or <results>/vm-zone.txt)")
    ap.add_argument("--dry-run", "--plan", dest="dry_run", action="store_true",
                    help="print paths, suites, systems, rows and already-recorded rows; build no client, call nothing")
    ap.add_argument(RC.I_KNOW_FLAG, dest="i_know", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    kinds = set(a.systems.split(","))
    suites = parse_suites(a.suites)
    HARDWARE.update(key=a.hardware, zone=a.vm_zone or CTX.vm_zone())
    contract = Path(a.contract) if a.contract else CTX.default_contract(None)
    if a.stage in ("tune", "freeze", "bias-arms"):
        RC.require_same_run(CTX, a.stage)
    if a.dry_run:
        return dry_run(a.stage, kinds, suites, a.limit, contract)
    writes = {"tune": [OUT], "test": [OUT], "rerun-failed": [OUT], "latency": [OUT],
              "freeze": [MANIFEST_OUT, SELECTION_OUT], "bias-arms": [MANIFEST_OUT]}[a.stage]
    RC.refuse_protected(writes, a.i_know, a.stage)
    if a.stage == "tune":
        run_stage("tune", kinds, "tune", suites=suites)
    elif a.stage == "freeze":
        freeze_guard(a.i_know, suites)
        freeze(contract, suites)
    elif a.stage == "bias-arms":
        if RC.git_tracked(MANIFEST_OUT):
            raise SystemExit(f"{RC.rel(MANIFEST_OUT)} is committed; bias-arms would rewrite a frozen manifest")
        add_bias_arms(json.loads(MANIFEST_OUT.read_text()), suites)
    elif a.stage == "test":
        run_stage("test", kinds, "test", chosen=load_chosen(), suites=suites)
    elif a.stage == "rerun-failed":
        rerun_failed()
    elif a.stage == "latency":
        run_stage("latency", kinds, "tune", chosen=load_chosen(), serial=True, limit=a.limit or 100, suites=suites)
    return 0


def dry_run(stage: str, kinds: set, suites: list, limit, contract) -> int:
    print(json.dumps(CTX.describe()))
    if stage == "freeze":
        from goldrails_bench.leaderboard import _stable_hash
        c = json.loads(Path(contract).read_text()) if contract else None
        print(f"== first_benchmark.py freeze (run {CTX.run}) — DRY RUN\n   reads   {RC.rel(OUT / 'tune.jsonl')}"
              f"{'' if (OUT / 'tune.jsonl').exists() else '  (absent: run tune first)'}\n"
              f"   writes  {RC.rel(MANIFEST_OUT)}{'  (EXISTS: freeze would refuse)' if MANIFEST_OUT.exists() else ''}\n"
              f"   writes  {RC.rel(SELECTION_OUT)}{'  (EXISTS: freeze would refuse)' if SELECTION_OUT.exists() else ''}\n"
              f"   protected first-benchmark location: {RC.is_protected(MANIFEST_OUT)}\n"
              f"   contract {RC.rel(contract) if contract else 'built-in v1.0-draft'}"
              f"{'  hash ' + _stable_hash(c) if c else ''}\n   suites  {suites}\n"
              "   needs live clients (config hashes for the bias arms): run between make up and make down")
        return 0
    if stage == "bias-arms":
        print("bias-arms: rewrites an uncommitted manifest with bias arms; needs live clients")
        return 0
    if stage == "rerun-failed":
        from goldrails_bench.policy import TRANSIENT_3
        n = 0
        if (OUT / "test.jsonl").exists():
            for line in (OUT / "test.jsonl").read_text().splitlines():
                d = json.loads(line)
                n += (not d["ok"]) and TRANSIENT_3.retryable(d.get("error"))
        print(f"== first_benchmark.py rerun-failed (run {CTX.run}) — DRY RUN\n   {n} test rows failed on a retryable "
              f"error in {RC.rel(OUT / 'test.jsonl')}; they would be re-attempted into {RC.rel(OUT / 'test-rerun.jsonl')}")
        return 0
    split = "tune" if stage in ("tune", "latency") else "test"
    chosen = load_chosen() if stage in ("test", "latency") and SELECTION.exists() else None
    p = plan_stage(stage, kinds, split, chosen, (limit or 100) if stage == "latency" else limit, suites)
    p.print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
