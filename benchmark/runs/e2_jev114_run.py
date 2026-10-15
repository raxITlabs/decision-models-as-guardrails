"""Jev 1.14.0 (api.typesafe.ai, released 14 October 2026) as the thirteenth system: all six suites on the rows the
other twelve were scored on.

    uv run python benchmark/runs/e2_smoke.py run --systems jev-1.14 --source local   # dev rows first (smoke ledger)
    uv run python benchmark/runs/e2_jev114_run.py plan --source local       # rows per subtask, guard, cost forecast
    uv run python benchmark/runs/e2_jev114_run.py freeze --source local     # extension manifest; commit it first
    uv run python benchmark/runs/e2_jev114_run.py all --source local        # forecast, main pass, retry passes
    uv run python benchmark/runs/e2_jev114_run.py report --source local     # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_jev114_run.py score --source local   # benchmark/results/final/

The model is sent by its versioned id ``jev-1.14.0``, never ``jev-preview`` or ``jev-latest``: an alias moves with the
next release, and the response's model field is recorded per row either way.

The rows are exactly the other systems' rows: the five full-run suites (their test files hash as the primary freeze
recorded) and the r26 prompt-attack suite (hashes as the r26 extension recorded), test split plus the unpublished
slice, owner exclusions left out. ``e2_full.TestRows.guard`` refuses anything else, before any call and again before
each one.

The freeze is an extension manifest (``goldrails_bench.freeze``) that extends the primary
(``benchmark/subsets/edition2/freeze-manifest.json``) with one arm per Jev 1.14.0 question set: Jev 1.13.0's eight
arms (question set, score scale, fixed 0.5 rule) on the same dataset versions, with the config hash the smoke test's
serving gives. Nothing is fitted. ``run`` refuses to send until the manifest is committed, and every record carries
its sha256.

Data handling. The unpublished slice goes to TypeSafe, as it did for Jev 1.13.0 in the full run (ruling 21). TypeSafe
does not train on API requests; zero data retention is an enterprise term, so the default API retention applies.

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/jev-1.14.0/private/``;
``report`` and ``score`` write committed ledgers with public test rows only and run the privacy checks. ``score`` is
the full rescore: the eleven, gpt-6-luna's extension run and this one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_attacks_rerun as ar  # noqa: E402  (points e2_full's globals at the r26 rerun, which its score reads)
import e2_full as full  # noqa: E402
import e2_openai_run as luna  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_smoke as smoke  # noqa: E402

REPO = full.REPO
SYSTEM = smoke.JEV_114
KIND = "jev-1.14"
ENDPOINT = "https://api.typesafe.ai"
TEMPLATE = "jev-1.13.0"
OUT = full.FINAL / "ledgers" / SYSTEM
WORK = OUT / "private"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / f"freeze-manifest-{SYSTEM}.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
SMOKE = smoke.OUT / f"{SYSTEM}.jsonl"
LABEL = "jev-1.14.0 extension run: every edition 2 test row and the unpublished slice, contract v2.0 as amended"
APPROVAL = ("jev-1.14.0 added as the thirteenth system at the owner's request of 15 October 2026; spend under the "
            "USD 5 cap; unpublished slice sent to TypeSafe as for jev-1.13.0 (ruling 21)")
NOUL_ADAPTER = {"name": "noul-e2", "version": "1"}
WORKERS = 8                      # as jev-1.13.0 in the full run
RETRY_ROUNDS = 2
COST_CAP_USD = 5.0
DISCLOSURES = [
    "jev-1.14.0 was sent the same Noul question sets as jev-1.13.0, in TypeSafe's native question format (contract "
    "v2.0 discloses that the format favours Jev), by its versioned model id rather than the jev-preview alias.",
    "The unpublished slice was sent to TypeSafe, as it was for jev-1.13.0 in the full run (ruling 21). TypeSafe does "
    "not train on API requests; zero data retention is an enterprise term, so its default API retention applies.",
    "jev-1.14.0 ran after the other twelve systems, under its own freeze manifest committed before its first test "
    "call (benchmark/subsets/edition2/freeze-manifest-jev-1.14.0.json).",
    "jev-1.14.0 ran after the ruling 32 label review. It was sent the reviewed build's test rows, whose text is the "
    "frozen version's; the rows that review removed were not sent, and every system is scored without them.",
]
CAVEATS = ["jev-1.14.0 was a preview release when it ran (jev-preview pointed at it, jev-latest at jev-1.13.0); the "
           "response's model field is recorded per row"]


def use_paths() -> None:
    sample.OUT, sample.RUN_LOG = OUT, RUN_LOG


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_event(key: str, value) -> None:
    def go():
        d = sample._log()
        d.setdefault(key, []).append(value)
        sample._save_log(d)
    sample._locked(go)


def select(tr) -> dict:
    return ar._select_all_tasks(tr)


# --- forecast --------------------------------------------------------------------------------------------------

def forecast(sel: dict) -> dict:
    """USD from the smoke test's measured input tokens: per subtask a least-squares line of tokens on state
    characters (the question set is a fixed overhead per subtask), applied to every selected row. High = 1.5 x."""
    import numpy as np
    from goldrails_bench import leaderboard as lb
    if not SMOKE.exists():
        raise SystemExit(f"no smoke ledger at {full._rel(SMOKE)}: run e2_smoke.py run --systems {KIND} first")
    price = next(e for e in lb.load_tariffs()["entries"] if SYSTEM in e["match"].get("models", []))
    usd_m = price["prices"]["input_tokens"]["usd_per_million"]
    pts = defaultdict(list)
    for x in SMOKE.open(encoding="utf-8"):
        d = json.loads(x)
        if d["outcome"] == "decided" and (d.get("usage") or {}).get("input_tokens"):
            pts[(d["suite"], d["subtask"])].append((d["state_chars"], d["usage"]["input_tokens"]))
    by, total_tok = {}, 0
    for k, rows in sel.items():
        if not pts[k]:
            raise SystemExit(f"the smoke ledger has no decided {k[0]}/{k[1]} row to forecast from")
        xs, ys = zip(*pts[k])
        slope, icpt = np.polyfit(xs, ys, 1) if len(set(xs)) > 1 else (0.0, float(np.mean(ys)))
        tok = sum(max(icpt + slope * smoke.state_chars(r), 1.0) for r in rows)
        by[f"{k[0]}/{k[1]}"] = {"rows": len(rows), "tokens": round(tok), "tokens_per_char": round(float(slope), 4),
                                "overhead_tokens": round(float(icpt))}
        total_tok += tok
    usd = total_tok * usd_m / 1e6
    return {"rows": sum(len(v) for v in sel.values()), "input_tokens": round(total_tok), "usd_per_million": usd_m,
            "total_usd": round(usd, 3), "high_usd": round(1.5 * usd, 3), "cap_usd": COST_CAP_USD, "by_subtask": by,
            "basis": f"smoke ledger {full._rel(SMOKE)}: measured input tokens per subtask fitted on state "
                     "characters, applied to every selected row; high = 1.5 x"}


# --- freeze ----------------------------------------------------------------------------------------------------

def _cfg(qs: str) -> str:
    return hashlib.sha256(json.dumps({"adapter": NOUL_ADAPTER, "model": SYSTEM, "endpoint": ENDPOINT,
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16]


def _template_arms() -> list:
    """Jev 1.13.0's eight arms: the primary's for the five kept suites, the r26 extension's for prompt attacks."""
    from goldrails_bench import freeze as F
    pm, _ = F.load_committed(PRIMARY)
    xm, _ = F.load_committed(R26)
    arms = [a for a in pm["arms"] if a["system"] == TEMPLATE and a["suite"] != ar.SUITE]
    arms += [a for a in xm["arms"] if a["system"] == TEMPLATE]
    if len(arms) != 8:
        raise SystemExit(f"expected 8 {TEMPLATE} arms to copy, found {len(arms)}")
    return arms


def extension_arms(tr) -> list:
    from goldrails_bench import freeze as F
    pm, _ = F.load_committed(PRIMARY)
    xm, _ = F.load_committed(R26)
    want = {su: d["sha256"] for su, d in pm["integrity"]["datasets"].items() if su != ar.SUITE}
    want[ar.SUITE] = xm["integrity"]["datasets"][ar.SUITE]["sha256"]
    have = {full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES}
    if want != have:
        raise SystemExit(f"test rows differ from the frozen ones: {sorted(k for k in want if want[k] != have.get(k))}")
    # the smoke test's serving must give the same config hash the scorer will compute from the run's records
    srv = {}
    for x in SMOKE.open(encoding="utf-8"):
        d = json.loads(x)
        srv.setdefault(d["serving"]["question_set"], d["serving"])
    out = []
    for a in _template_arms():
        qs, su = a["question_set"], a["suite"]
        s = srv.get(qs)
        if s is None or s["adapter"] != NOUL_ADAPTER or s["model_id"] != SYSTEM:
            raise SystemExit(f"the smoke ledger has no matching {SYSTEM} record for {qs}")
        cfg = _cfg(qs)
        if hashlib.sha256(json.dumps({"adapter": s["adapter"], "model": s["model_id"], "endpoint": s["endpoint"],
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16] != cfg:
            raise SystemExit(f"{qs}: the smoke record's serving does not reproduce the config hash")
        sha = have[su]
        out.append({"arm_id": f"{SYSTEM}|{qs}|{cfg}|{sha[:12]}", "system": SYSTEM, "question_set": qs,
                    "config_hash": cfg, "suite": su, "score_scale": a["score_scale"],
                    "decision_rule": a["decision_rule"], "dataset": {"sha256": sha},
                    "_template": f"{TEMPLATE}|{qs}|{a['config_hash']}|{a['dataset_sha256'][:12]}"})
    return out


def write_freeze(tr) -> dict:
    from goldrails_bench import freeze as F
    from goldrails_bench import leaderboard_v2 as lv2
    from goldrails_bench.leaderboard import _stable_hash
    from goldrails_bench.policy import DEFAULT_POLICY
    if MANIFEST.exists():
        raise SystemExit(f"{full._rel(MANIFEST)} exists; a freeze is written once")
    pm, pident = F.load_committed(PRIMARY)
    xm, xident = F.load_committed(R26)
    contract = lv2.load_contract()
    if _stable_hash(contract) != xm["contract"]["hash"]:
        raise SystemExit("the contract changed since the r26 extension; this run would need a contract amendment")
    arms = extension_arms(tr)
    doc = {"schema": F.EDITION2_SCHEMA, "arms": [{k: v for k, v in a.items() if not k.startswith("_")} for a in arms]}
    extends = {"manifest_sha256": pident["manifest_sha256"], "manifest_path": pident["path"],
               "reason": "a thirteenth system (jev-1.14.0, api.typesafe.ai, released 14 October 2026) on every "
                         "suite's frozen test rows: the five suites of the primary freeze and the r26 prompt-attack "
                         "suite; no arm of the primary, the r26 extension or the gpt-6-luna extension changes",
               "after_extension": {"manifest_sha256": xident["manifest_sha256"], "manifest_path": xident["path"],
                                   "note": "the prompt-attack arms use the r26 dataset version that extension froze; "
                                           "the contract is the one it amended to, unchanged since"}}
    # owner ruling 32: the dataset version every arm records is the frozen copy the other systems answered, so the
    # manifest is written from that copy and names its files by the repository paths the copy mirrors
    integ = full.frozen_integrity(tr)
    files = {full.FEATURE_SUITE[f]: [full.FROZEN / q.relative_to(REPO) if integ else q for q in tr.files[f]]
             for f in full.FEATURES}
    t0 = time.time()
    m = F.write_manifest(doc, MANIFEST, retry_policy=DEFAULT_POLICY,
                         test_datasets={full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES},
                         test_files=files, references=integ["references"] if integ else F.default_references(),
                         edition=2, extends=extends, contract=contract)
    if integ:
        prefix = full._rel(full.FROZEN) + "/"
        for d in m["integrity"]["datasets"].values():
            for x in d["files"]:
                x["path"] = x["path"].removeprefix(prefix)
    probs = F.validate(m) + F.integrity_problems(m, **(integ or {}))
    if probs:
        MANIFEST.unlink()
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    for out_arm, a in zip(m["arms"], arms):
        out_arm["checked_on"] = {"template_arm": a["_template"],
                                 "note": f"the same question set, score scale and fixed rule as {TEMPLATE}'s arm; "
                                         f"config hash from the {SYSTEM} smoke test's serving"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": [SYSTEM],
                "smoke": full._rel(SMOKE), "data_handling": DISCLOSURES[1]}
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"extension manifest: {len(m['arms'])} arms, integrity pass over {m['integrity']['test_rows']} test rows "
          f"({time.time() - t0:.0f}s) -> {full._rel(MANIFEST)}; commit it before any call")
    return m


# --- run -------------------------------------------------------------------------------------------------------

_build_systems = smoke.build_systems     # the real builder; run() swaps smoke's hook for build() below


def build():
    systems, skipped = _build_systems({KIND}, os.environ)
    if SYSTEM not in systems:
        raise SystemExit(skipped.get(KIND, f"{KIND} not configured"))
    adapter, _ = systems[SYSTEM]
    return {SYSTEM: (adapter, WORKERS)}, {}


def run(retry_failed: bool) -> dict:
    from goldrails_bench import freeze as F
    try:
        _, ident = F.load_committed(MANIFEST)
    except F.FreezeError as e:
        raise SystemExit(f"refusing to run: {e}") from None
    tr = full.TestRows()
    smoke.build_systems = lambda kinds, env=None: build()
    try:
        t = smoke.run_selection({KIND}, select(tr), WORK, None, reruns=False, guard=tr.guard,
                                retry_failed=retry_failed, stamp={"freeze": F.record_stamp(ident)})
    finally:
        smoke.build_systems = _build_systems
    for v in t.values():
        v["retry_failed_only"] = retry_failed
    sample.log_timing(t)
    return t


def failed_latest() -> int:
    p = WORK / f"{SYSTEM}.jsonl"
    last = {}
    for x in p.open(encoding="utf-8") if p.exists() else []:
        d = json.loads(x)
        last[(d["suite"], d["subtask"], d["row_id"])] = d["outcome"]
    return sum(v == "failed" for v in last.values())


def run_all() -> int:
    from goldrails_bench import freeze as F
    tr = full.TestRows()
    sel = select(tr)
    fc = forecast(sel)
    print("forecast:", json.dumps({k: v for k, v in fc.items() if k != "by_subtask"}), flush=True)
    log_event("forecasts", {"at": _now(), **fc})
    if fc["high_usd"] > COST_CAP_USD:
        print(f"forecast high {fc['high_usd']} USD is above the {COST_CAP_USD} USD cap: stopping before any call")
        return 2
    try:
        m, _ = F.load_committed(MANIFEST)
    except F.FreezeError as e:
        print(f"refusing to run: {e}")
        return 2
    probs = F.integrity_problems(m, **(full.frozen_integrity(tr) or {}))
    if probs:
        print("freeze manifest cannot back a test run: " + "; ".join(probs))
        return 2
    t0 = time.time()
    main = run(False)
    log_event("runs", {"pass": "main", "at": _now(), **main.get(SYSTEM, {})})
    rounds = []
    for i in range(1, RETRY_ROUNDS + 1):
        n = failed_latest()
        if not n:
            break
        print(f"retry pass {i}: {n} rows", flush=True)
        t = run(True)
        rounds.append({"pass": i, "sent": n, "still_failed": failed_latest(), **t.get(SYSTEM, {})})
    log_event("retry_passes", {"at": _now(), "rounds": rounds,
                               "note": "no row failed after the main pass" if not rounds else None})
    log_event("all_runs", {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "finished": _now(),
                           "seconds": round(time.time() - t0, 1), "failed_after_retries": failed_latest()})
    print(f"done in {(time.time() - t0) / 60:.1f} min; failed after retries: {failed_latest()}", flush=True)
    return 0


# --- report, public ledgers, privacy ---------------------------------------------------------------------------

def write_public(tr) -> list[Path]:
    return full.write_public_ledgers(WORK, OUT, tr)


def committed_files() -> list[Path]:
    return sorted(p for p in OUT.rglob("*") if p.is_file() and WORK not in p.parents and p.name != ".run-log.lock")


def report() -> int:
    tr = full.TestRows()
    recs = sample.load_ledgers(WORK)
    s = sample.run_summary(recs, select(tr))
    for sy, x in s.items():
        print(f"{sy:20s} rows {x['rows']:5d} failed {x['failed']:3d} (first pass {x['first_pass_failed']}) "
              f"not_offered {x['not_offered']:3d} never_logged {x['never_logged']:3d} wall {x['wall_seconds']} "
              f"failure kinds {x['failure_kinds']}")
    write_public(tr)
    pc = full.privacy_check(tr, committed_files() + [MANIFEST])
    print("privacy:", json.dumps(pc))
    return 0 if pc["pass"] else 1


def run_date() -> str:
    log = json.loads(RUN_LOG.read_text(encoding="utf-8")) if RUN_LOG.exists() else {}
    done = log.get("all_runs") or []
    if not done:
        raise SystemExit(f"{full._rel(RUN_LOG)} records no finished run; run `all` before `score`")
    return done[-1]["finished"][:10]


def extra_run() -> dict:
    run_entry = {"key": "jev_1_14_extension_run", "date": run_date(), "folder": full._rel(OUT), "suites": "all six",
                 "systems": [SYSTEM], "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    return {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
            "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files()}


def score(replicates: int | None = None) -> Path:
    """The full rescore: the eleven, gpt-6-luna's extension run and this one."""
    tr = full.TestRows()
    luna.write_public(tr)
    write_public(tr)
    return ar.score(replicates, extra_runs=[luna.extra_run(), extra_run()])


def plan() -> None:
    tr = full.TestRows()
    sel = select(tr)
    n = 0
    for (su, st), rows in sel.items():
        for r in rows:
            tr.guard(r)
        n += len(rows)
        u = sum(r["id"] in tr.unpublished for r in rows)
        print(f"{su}/{st}: {len(rows)} rows ({u} unpublished) {dict(Counter((r['subtask'], r['expected']) for r in rows))}")
    print(f"total {n} rows; guard passed")
    print("forecast:", json.dumps(forecast(sel), indent=1))


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "freeze", "all", "run", "report", "score"])
    ap.add_argument("--source")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--replicates", type=int, default=None)
    a = ap.parse_args(argv)
    smoke.use_source(a.source)
    WORK.mkdir(parents=True, exist_ok=True)
    if a.stage == "score":
        print(score(a.replicates))   # ar.score reads the r26 run's log through e2_sample's globals
        return 0
    use_paths()
    if a.stage == "plan":
        plan()
    elif a.stage == "freeze":
        write_freeze(full.TestRows())
    elif a.stage == "all":
        return run_all()
    elif a.stage == "run":
        print(run(a.retry_failed))
    else:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
