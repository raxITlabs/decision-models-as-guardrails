"""Perplexity Decider v1.2 as the twenty-first and twenty-second systems: pplx-decider-v1.2 (27B) and
pplx-decider-flash-v1.2 (4B) on the Decisions API, all six suites on the rows the other twenty were scored on.

    uv run python benchmark/runs/e2_smoke.py run --systems perplexity-v1.2,perplexity-flash-v1.2 --source local
    uv run python benchmark/runs/e2_pplx12_run.py plan --source local       # rows per subtask, guard, cost forecast
    uv run python benchmark/runs/e2_pplx12_run.py freeze --source local     # extension manifest; commit it first
    uv run python benchmark/runs/e2_pplx12_run.py all --source local        # forecast, main pass, retry passes
    uv run python benchmark/runs/e2_pplx12_run.py report --source local     # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_pplx12_run.py score --source local   # benchmark/results/final/

Each model is sent under its versioned id and every response must report that id or the call fails
(``hosted.PerplexityDecisionsClient``, ``PPLX_PINNED``). The open weights are recorded for provenance: the reported
name echoes the request, so it guards against misrouting but does not prove which weights served.

Rows: every edition 2 test row and the unpublished slice of the five full-run suites and the r26 prompt-attack suite,
owner exclusions left out, the same rows as every other system. ``e2_full.TestRows.guard`` refuses anything else,
before any call and again before each one. Owner ruling 37 (27 October 2026) approves sending the unpublished slice
to Perplexity for these two models.

The freeze is one extension manifest that extends the primary with one arm per model and question set, copied from
Clef's arms (the same eight Noul question sets, fixed 0.5 rule and retry policy), with the config hash each model's
smoke test serving gives. ``run`` refuses to send until it is committed. The two models run one after the other,
under one 5/s throttle (Perplexity's 10/s limit is per organisation).

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/pplx-decider-v1-2/private/``;
``report`` and ``score`` write committed ledgers with public test rows only and run the privacy checks. ``score`` is the
full rescore: the eleven, then the extension runs of gpt-6-luna, Jev 1.14.0, the Strands checkpoints,
Microsoft-Decision-1 and this one.
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
import e2_msd1_run as msd1  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_smoke as smoke  # noqa: E402

REPO = full.REPO
from goldrails_bench import hosted  # noqa: E402

# system -> (model id sent and recorded, smoke kind). The config hash uses the model id.
SYSTEMS = {hosted.PPLX_V12_SYSTEM: (hosted.PPLX_V12_MODEL, "perplexity-v1.2"),
           hosted.PPLX_FLASH_SYSTEM: (hosted.PPLX_FLASH_MODEL, "perplexity-flash-v1.2")}
KINDS = {kind for _, kind in SYSTEMS.values()}
ENDPOINT = hosted.PERPLEXITY_URL
TEMPLATE = "clef"               # a hosted Noul model's arms; every Noul model has the same eight
RUN_NAME = "pplx-decider-v1-2"
OUT = full.FINAL / "ledgers" / RUN_NAME
WORK = OUT / "private"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / f"freeze-manifest-{RUN_NAME}.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
LABEL = ("pplx-decider-v1.2 extension run (27B and flash 4B): every edition 2 test row and the unpublished slice, "
         "contract v2.0 as amended")
APPROVAL = ("pplx-decider-v1.2 and pplx-decider-flash-v1.2 added at the owner's request of 27 October 2026 (Perplexity, "
            "released 15 October 2026, Decisions API); spend under the USD 5 cap; unpublished slice sent to Perplexity "
            "under ruling 37")
ROW_SCOPE = "every test row and the unpublished slice, as every other system (ruling 37)"
NOUL_ADAPTER = {"name": "noul-e2", "version": "1"}
WORKERS = 4                      # the client throttles the pool to 5 requests/s
RETRY_ROUNDS = 2
COST_CAP_USD = 5.0
DISCLOSURES = [
    "pplx-decider-v1.2 and pplx-decider-flash-v1.2 were sent the same Noul question sets as every other Noul model, in "
    "the System One request shape Perplexity's Decisions API takes, all of a row's questions in one request.",
    "The unpublished slice was sent to Perplexity for pplx-decider-v1.2 and pplx-decider-flash-v1.2 (owner ruling 37, as "
    "ruling 21 did for pplx-decider-v1-27b). Perplexity's default API data handling applies; no zero-retention "
    "agreement is in place.",
    "Each model was requested under its versioned id (pplx-decider-v1.2, pplx-decider-flash-v1.2), and a response "
    "reporting any other model name would have failed the row. The reported name echoes the request, so it guards "
    "against misrouting but does not prove which weights served. The open weights are recorded for provenance "
    "(perplexity-ai/pplx-decider-v1.2 at 225c913d, perplexity-ai/pplx-decider-flash-v1.2 at 6d771ad7).",
    "Perplexity's documentation (read 27 October 2026) says requests naming pplx-decider-v1-27b are now served by "
    "pplx-decider-v1.2. The pplx-decider-v1-27b results on this board come from the full run of 5 October 2026, before "
    "v1.2's release on 15 October 2026; that system cannot be re-run on the hosted API.",
    "pplx-decider-v1.2 and pplx-decider-flash-v1.2 ran after the other twenty systems, under their own freeze manifest "
    "committed before the first test call (benchmark/subsets/edition2/freeze-manifest-pplx-decider-v1-2.json).",
    "Both ran after the ruling 32 label review. They were sent the reviewed build's test rows, whose text is the frozen "
    "version's; the rows that review removed were not sent, and every system is scored without them.",
]
CAVEATS = ["pplx-decider-v1.2 and pplx-decider-flash-v1.2: the hosted model is pinned only by the model name each "
           "response reports"]


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

def smoke_ledger(system: str) -> Path:
    return smoke.OUT / f"{system}.jsonl"


def forecast(sel: dict) -> dict:
    """Both models: per-model forecasts and their sum (``total_usd``, ``high_usd``)."""
    per = {s: forecast_one(s, sel) for s in SYSTEMS}
    usd = sum(f["total_usd"] for f in per.values())
    return {"rows": sum(f["rows"] for f in per.values()), "input_tokens": sum(f["input_tokens"] for f in per.values()),
            "total_usd": round(float(usd), 3), "high_usd": round(float(1.5 * usd), 3), "cap_usd": COST_CAP_USD, "by_system": per}


def forecast_one(system: str, sel: dict) -> dict:
    """USD from the smoke test's measured input tokens: per subtask a least-squares line of tokens on state
    characters (the question set is a fixed overhead per subtask), applied to every selected row. High = 1.5 x."""
    import numpy as np
    from goldrails_bench import leaderboard as lb
    model, kind = SYSTEMS[system]
    ledger = smoke_ledger(system)
    if not ledger.exists():
        raise SystemExit(f"no smoke ledger at {full._rel(ledger)}: run e2_smoke.py run --systems {kind} first")
    price = next(e for e in lb.load_tariffs()["entries"] if model in e["match"].get("models", []))
    usd_m = price["prices"]["input_tokens"]["usd_per_million"]
    pts = defaultdict(list)
    for x in ledger.open(encoding="utf-8"):
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
            "total_usd": round(float(usd), 4), "high_usd": round(float(1.5 * usd), 4), "by_subtask": by,
            "basis": f"smoke ledger {full._rel(ledger)}: measured input tokens per subtask fitted on state "
                     "characters, applied to every selected row; high = 1.5 x"}


# --- freeze ----------------------------------------------------------------------------------------------------

def _cfg(model: str, qs: str) -> str:
    return hashlib.sha256(json.dumps({"adapter": NOUL_ADAPTER, "model": model, "endpoint": ENDPOINT,
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16]


def _template_arms() -> list:
    """Clef's eight arms: the primary's for the five kept suites, the r26 extension's for prompt attacks."""
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
    out = []
    for system, (model, _) in SYSTEMS.items():
        # the smoke test's serving must give the same config hash the scorer will compute from the run's records
        srv = {}
        for x in smoke_ledger(system).open(encoding="utf-8"):
            d = json.loads(x)
            srv.setdefault(d["serving"]["question_set"], d["serving"])
        for a in _template_arms():
            qs, su = a["question_set"], a["suite"]
            s = srv.get(qs)
            if s is None or s["adapter"] != NOUL_ADAPTER or s["model_id"] != model:
                raise SystemExit(f"the smoke ledger has no matching {system} record for {qs}")
            cfg = _cfg(model, qs)
            if hashlib.sha256(json.dumps({"adapter": s["adapter"], "model": s["model_id"], "endpoint": s["endpoint"],
                                          "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16] != cfg:
                raise SystemExit(f"{qs}: the smoke record's serving does not reproduce the config hash")
            sha = have[su]
            out.append({"arm_id": f"{system}|{qs}|{cfg}|{sha[:12]}", "system": system, "question_set": qs,
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
               "reason": "two more systems (pplx-decider-v1.2 and pplx-decider-flash-v1.2 on Perplexity's Decisions "
                         "API, released 15 October 2026) on every suite's frozen test rows and unpublished slice "
                         "(ruling 37): the five suites of the primary freeze and the r26 prompt-attack suite; no arm "
                         "of the primary or of any earlier extension changes",
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
                                 "note": f"the same question set, score scale and fixed rule as every Noul model's ({TEMPLATE}'s shown); "
                                         f"config hash from the {out_arm['system']} smoke test's serving"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": list(SYSTEMS),
                "smoke": {s: full._rel(smoke_ledger(s)) for s in SYSTEMS}, "data_handling": DISCLOSURES[1],
                "row_scope": ROW_SCOPE, "pin": {s: m_ for s, (m_, _) in SYSTEMS.items()}}
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"extension manifest: {len(m['arms'])} arms, integrity pass over {m['integrity']['test_rows']} test rows "
          f"({time.time() - t0:.0f}s) -> {full._rel(MANIFEST)}; commit it before any call")
    return m


# --- run -------------------------------------------------------------------------------------------------------

_build_systems = smoke.build_systems     # the real builder; run() swaps smoke's hook for build() below


def build():
    systems, skipped = _build_systems(KINDS, os.environ)
    out = {}
    for s, (_, kind) in SYSTEMS.items():
        if s not in systems:
            raise SystemExit(skipped.get(kind, f"{kind} not configured"))
        out[s] = (systems[s][0], WORKERS)
    return out, {}


def run(retry_failed: bool) -> dict:
    from goldrails_bench import freeze as F
    try:
        _, ident = F.load_committed(MANIFEST)
    except F.FreezeError as e:
        raise SystemExit(f"refusing to run: {e}") from None
    tr = full.TestRows()
    smoke.build_systems = lambda kinds, env=None: build()
    try:
        t = smoke.run_selection(KINDS, select(tr), WORK, None, reruns=False, guard=tr.guard,
                                retry_failed=retry_failed, stamp={"freeze": F.record_stamp(ident)})
    finally:
        smoke.build_systems = _build_systems
    for v in t.values():
        v["retry_failed_only"] = retry_failed
    sample.log_timing(t)
    return t


def failed_latest() -> int:
    n = 0
    for s in SYSTEMS:
        p = WORK / f"{s}.jsonl"
        last = {}
        for x in p.open(encoding="utf-8") if p.exists() else []:
            d = json.loads(x)
            last[(d["suite"], d["subtask"], d["row_id"])] = d["outcome"]
        n += sum(v == "failed" for v in last.values())
    return n


def run_all() -> int:
    from goldrails_bench import freeze as F
    tr = full.TestRows()
    sel = select(tr)
    fc = forecast(sel)
    print("forecast:", json.dumps({k: v for k, v in fc.items() if k != "by_system"}), flush=True)
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
    log_event("runs", {"pass": "main", "at": _now(), "systems": main})
    rounds = []
    for i in range(1, RETRY_ROUNDS + 1):
        n = failed_latest()
        if not n:
            break
        print(f"retry pass {i}: {n} rows", flush=True)
        t = run(True)
        rounds.append({"pass": i, "sent": n, "still_failed": failed_latest(), "systems": t})
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
    run_entry = {"key": "pplx12_extension_run", "date": run_date(), "folder": full._rel(OUT), "suites": "all six",
                 "systems": list(SYSTEMS), "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    return {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
            "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files()}


def score(replicates: int | None = None) -> Path:
    """The full rescore: the eleven, then gpt-6-luna, Jev 1.14.0, the Strands checkpoints, Microsoft-Decision-1 and
    this run."""
    import e2_strands_run as strands
    tr = full.TestRows()
    strands.luna.write_public(tr)
    strands.jev114.write_public(tr)
    strands.write_public(tr)
    msd1.write_public(tr)
    write_public(tr)
    return ar.score(replicates, extra_runs=[strands.luna.extra_run(), strands.jev114.extra_run(), strands.extra_run(),
                                            msd1.extra_run(), extra_run()])


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
