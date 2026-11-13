"""Two classic safety classifiers added to the edition 2 results through OpenRouter's chat API (docs/benchmark/36).

    uv run python benchmark/runs/e2_smoke.py run --systems gpt-oss-safeguard-20b,llama-guard-4-12b --source local
    uv run python benchmark/runs/e2_guards_run.py plan --source local     # rows per subtask, guard, cost forecast
    uv run python benchmark/runs/e2_guards_run.py freeze --source local   # extension manifest; commit it first
    uv run python benchmark/runs/e2_guards_run.py all --source local      # main pass, retries
    uv run python benchmark/runs/e2_guards_run.py report --source local   # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_guards_run.py score --source local   # benchmark/results/final/

- ``gpt-oss-safeguard-20b`` (OpenAI's open-weight policy classifier, served by Groq): every suite. The system prompt
  is the suite's policy file verbatim plus a fixed output section (``goldrails_bench.guards``).
- ``llama-guard-4-12b`` (Meta, served by DeepInfra in bf16): content only. Its fixed S1 to S14 taxonomy has no
  prompt-attack, topic, profanity, per-entity PII or grounding category, so the other five suites are not offered: no
  call is made, the system is shown on the content boards and is not ranked overall (contract v2.0 coverage rule).

Both answer with a label, not a probability, so each row is recorded as the guard's own verdict (1 flagged, 0 passed)
under contract v2.0's verdict rule; no secondary curve metric is reported for them. Each call is pinned to one
OpenRouter provider with fallbacks off, and a response from any other provider fails the row.

Rows: every edition 2 test row and the unpublished slice of the suites each system attempts, owner exclusions left out,
the same rows as every other system. ``e2_full.TestRows.guard`` refuses anything else, before any call and again
before each one. Owner rulings 44 and 45 (13 November 2026) approve the runs and sending the unpublished slice to
OpenRouter, Groq and DeepInfra.

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/classic-guards/private/``;
``report`` and ``score`` write committed ledgers with public test rows only and run the privacy checks. ``score`` is the
full rescore: every earlier run, then this one.
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
import e2_gemini_run as gemini  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_smoke as smoke  # noqa: E402

REPO = full.REPO
from goldrails_bench import guards  # noqa: E402

SAFEGUARD, LLAMA_GUARD = "gpt-oss-safeguard-20b", "llama-guard-4-12b"
SYSTEMS = (SAFEGUARD, LLAMA_GUARD)
OFFERED = {SAFEGUARD: None, LLAMA_GUARD: {"content"}}     # None: every suite
ALL_SUITES = ("content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_info", "grounding")
NOT_OFFERED = {s: [su for su in ALL_SUITES if su not in ok] for s, ok in OFFERED.items() if ok is not None}
RUN_NAME = "classic-guards"
OUT = full.FINAL / "ledgers" / RUN_NAME
WORK = OUT / "private"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / f"freeze-manifest-{RUN_NAME}.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
LABEL = ("Classic safety classifiers extension run (gpt-oss-safeguard-20b on Groq and Llama Guard 4 12B on DeepInfra, "
         "through OpenRouter's chat API): every edition 2 test row and the unpublished slice of the suites each "
         "attempts, contract v2.0 as amended")
APPROVAL = ("gpt-oss-safeguard-20b and Llama Guard 4 12B added at the owner's request of 13 November 2026 (rulings 44 "
            "and 45); spend under the USD 10 cap; unpublished slice sent to OpenRouter, Groq and DeepInfra")
ROW_SCOPE = ("every test row and the unpublished slice of the suites each system attempts: all six for "
             "gpt-oss-safeguard-20b, content for Llama Guard 4 (rulings 44 and 45)")
VERDICT_RULE = {"threshold": 0.5, "scale": "binary", "basis": "verdict",
                "rule": "verdict API: the system's own flag (recorded as 1 flagged, 0 passed)"}
RETRY_ROUNDS = 3
COST_CAP_USD = 10.0
DISCLOSURES = [
    "gpt-oss-safeguard-20b and Llama Guard 4 12B are safety classifiers, not decision models: each answers with its own "
    "label and no probability, so each row is scored as the guard's verdict (contract v2.0 verdict rule) and no curve "
    "metric (AUROC, recall at 5% false blocks, calibration) is reported for them (docs/benchmark/36).",
    "gpt-oss-safeguard-20b was sent each suite's policy file from benchmark/policies/ as its system prompt, verbatim, "
    "followed by a fixed output section asking for 1 or 0 (for PII, a JSON list of the entity types present), at "
    "reasoning effort medium and temperature 0. The row was the user message, serialised as for gpt-6-luna.",
    "Llama Guard 4 12B attempts content only: its fixed S1 to S14 taxonomy has no prompt-attack, denied-topic, "
    "profanity, per-entity PII or grounding category, so those five suites were not offered and the system is not "
    "ranked overall. A content row is flagged when Llama Guard answers unsafe in S1, S2, S3, S4, S9, S10, S11 or S12; "
    "S5, S6, S7, S8, S13 and S14 cover defamation, advice, privacy, IP, elections and code abuse, which the content "
    "policy puts out of scope. Llama Guard has no insults category.",
    "The unpublished slice was sent to OpenRouter, which served gpt-oss-safeguard-20b from Groq and Llama Guard 4 from "
    "DeepInfra (owner rulings 44 and 45). Each call was pinned to that provider with fallbacks off. Each provider's "
    "default API data handling applies; no zero-retention agreement is in place.",
    "Neither OpenRouter slug is dated and neither provider reports a version, so both arms are unversioned, like Bedrock; "
    "the evaluation date is recorded with every score.",
    "Both guards ran after the other systems, under their own freeze manifest committed before the first test call "
    "(benchmark/subsets/edition2/freeze-manifest-classic-guards.json).",
]
CAVEATS = ["gpt-oss-safeguard-20b and Llama Guard 4 are scored on their own verdicts with no score, through "
           "OpenRouter's chat API; Llama Guard 4 attempts content only and is not ranked overall"]


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


def select_for(system: str, tr) -> dict:
    """The system's rows: every task of the suites it attempts."""
    sel = ar._select_all_tasks(tr)
    ok = OFFERED[system]
    return {k: v for k, v in sel.items() if ok is None or k[0] in ok}


def selection(tr):
    return lambda system: select_for(system, tr)


# --- forecast --------------------------------------------------------------------------------------------------

def smoke_ledger(system: str) -> Path:
    return smoke.OUT / f"{system}.jsonl"


def forecast(tr) -> dict:
    per = {s: forecast_one(s, select_for(s, tr)) for s in SYSTEMS}
    usd = sum(f["total_usd"] for f in per.values())
    return {"rows": sum(f["rows"] for f in per.values()), "total_usd": round(float(usd), 3),
            "high_usd": round(float(1.5 * usd), 3), "cap_usd": COST_CAP_USD, "by_system": per}


def forecast_one(system: str, sel: dict) -> dict:
    """USD from the smoke test's measured tokens: per subtask a least-squares line of input tokens on state characters,
    and the mean output tokens (safeguard's reasoning trace), applied to every selected row. High = 1.5 x."""
    import numpy as np
    from goldrails_bench import leaderboard as lb
    model = guards.GUARD_MODELS[system]["model"]
    ledger = smoke_ledger(system)
    if not ledger.exists():
        raise SystemExit(f"no smoke ledger at {full._rel(ledger)}: run e2_smoke.py run --systems {system} first")
    price = next(e for e in lb.load_tariffs()["entries"] if model in e["match"].get("models", []))["prices"]
    pin, pout = price["input_tokens"]["usd_per_million"], price["output_tokens"]["usd_per_million"]
    pts, outs = defaultdict(list), defaultdict(list)
    for x in ledger.open(encoding="utf-8"):
        d = json.loads(x)
        u = d.get("usage") or {}
        if d["outcome"] == "decided" and u.get("input_tokens"):
            pts[(d["suite"], d["subtask"])].append((d["state_chars"], u["input_tokens"]))
            outs[(d["suite"], d["subtask"])].append(u.get("output_tokens") or 0)
    by, tin, tout = {}, 0.0, 0.0
    for k, rows in sel.items():
        if not pts[k]:
            raise SystemExit(f"the smoke ledger has no decided {k[0]}/{k[1]} row to forecast from")
        xs, ys = zip(*pts[k])
        slope, icpt = np.polyfit(xs, ys, 1) if len(set(xs)) > 1 else (0.0, float(np.mean(ys)))
        a = sum(max(icpt + slope * smoke.state_chars(r), 1.0) for r in rows)
        b = float(np.mean(outs[k])) * len(rows)
        by[f"{k[0]}/{k[1]}"] = {"rows": len(rows), "input_tokens": round(a), "output_tokens": round(b)}
        tin, tout = tin + a, tout + b
    usd = tin * pin / 1e6 + tout * pout / 1e6
    return {"rows": sum(len(v) for v in sel.values()), "input_tokens": round(tin), "output_tokens": round(tout),
            "total_usd": round(float(usd), 4), "high_usd": round(float(1.5 * usd), 4), "by_subtask": by,
            "basis": f"smoke ledger {full._rel(ledger)}: measured tokens per subtask; high = 1.5 x"}


# --- freeze ----------------------------------------------------------------------------------------------------

def _cfg(srv: dict, qs: str) -> str:
    """The config hash ``e2_sample.scorer_record`` computes for a record with this serving."""
    return hashlib.sha256(json.dumps({"adapter": srv.get("adapter"), "model": srv.get("model_id"),
                                      "endpoint": srv.get("endpoint"), "question_set": qs},
                                     sort_keys=True).encode()).hexdigest()[:16]


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
    for system in SYSTEMS:
        adapter = guards.ADAPTERS[system](guards.ChatGuardClient(system, "unused"))
        srv = {}
        for x in smoke_ledger(system).open(encoding="utf-8"):
            d = json.loads(x)
            if d["outcome"] != "not_offered":
                srv.setdefault((d["suite"], d["subtask"]), d["serving"])
        for (su, st) in select_for(system, tr):
            s = srv.get((su, st))
            if s is None:
                raise SystemExit(f"the smoke ledger has no {system} record for {su}/{st}")
            if s["adapter"] != adapter.adapter:
                raise SystemExit(f"{system} {su}/{st}: the smoke test ran adapter {s['adapter']}, the code is "
                                 f"{adapter.adapter}; re-run the smoke test")
            qs = s["question_set"]
            cfg = _cfg(s, qs)
            sha = have[su]
            arm_id = f"{system}|{qs}|{cfg}|{sha[:12]}"
            if any(a["arm_id"] == arm_id for a in out):
                continue
            out.append({"arm_id": arm_id, "system": system, "question_set": qs, "config_hash": cfg, "suite": su,
                        "score_scale": "binary", "decision_rule": VERDICT_RULE, "dataset": {"sha256": sha}})
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
    doc = {"schema": F.EDITION2_SCHEMA, "arms": arms}
    extends = {"manifest_sha256": pident["manifest_sha256"], "manifest_path": pident["path"],
               "reason": "gpt-oss-safeguard-20b on every suite and Llama Guard 4 12B on content (through OpenRouter's "
                         "chat API), on the frozen test rows and unpublished slice (rulings 44 and 45): the five suites "
                         "of the primary freeze and the r26 prompt-attack suite; no arm of the primary or of any "
                         "earlier extension changes",
               "after_extension": {"manifest_sha256": xident["manifest_sha256"], "manifest_path": xident["path"],
                                   "note": "the prompt-attack arms use the r26 dataset version that extension froze; "
                                           "the contract is the one it amended to, unchanged since"}}
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
    for out_arm in m["arms"]:
        out_arm["checked_on"] = {"note": "config hash from the system's smoke test serving (dev rows); the verdict "
                                         "rule of contract v2.0, nothing fitted"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": list(SYSTEMS),
                "smoke": {s: full._rel(smoke_ledger(s)) for s in SYSTEMS}, "data_handling": DISCLOSURES[3],
                "row_scope": ROW_SCOPE, "not_offered": NOT_OFFERED,
                "pin": {s: {"model": guards.GUARD_MODELS[s]["model"], "provider": guards.GUARD_MODELS[s]["provider"]}
                        for s in SYSTEMS}}
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"extension manifest: {len(m['arms'])} arms, integrity pass over {m['integrity']['test_rows']} test rows "
          f"({time.time() - t0:.0f}s) -> {full._rel(MANIFEST)}; commit it before any call")
    return m


# --- run -------------------------------------------------------------------------------------------------------

_build_systems = smoke.build_systems


def run(retry_failed: bool, names=None) -> dict:
    names = list(names or SYSTEMS)
    from goldrails_bench import freeze as F
    try:
        _, ident = F.load_committed(MANIFEST)
    except F.FreezeError as e:
        raise SystemExit(f"refusing to run: {e}") from None
    tr = full.TestRows()
    timing = {}
    for s in names:     # one system at a time, each with its own rows
        t = smoke.run_selection({s}, select_for(s, tr), WORK, None, reruns=False, guard=tr.guard,
                                retry_failed=retry_failed, stamp={"freeze": F.record_stamp(ident)})
        for v in t.values():
            v["retry_failed_only"] = retry_failed
        timing.update(t)
    sample.log_timing(timing)
    return timing


def failed_latest(names=None) -> int:
    n = 0
    for s in names or SYSTEMS:
        p = WORK / f"{s}.jsonl"
        last = {}
        for x in p.open(encoding="utf-8") if p.exists() else []:
            d = json.loads(x)
            last[(d["suite"], d["subtask"], d["row_id"])] = d["outcome"]
        n += sum(v == "failed" for v in last.values())
    return n


def run_all(names=None) -> int:
    names = list(names or SYSTEMS)
    from goldrails_bench import freeze as F
    tr = full.TestRows()
    fc = forecast(tr)
    print("forecast:", json.dumps({k: v for k, v in fc.items() if k != "by_system"}), flush=True)
    log_event("forecasts", {"at": _now(), **fc})
    if fc["high_usd"] > COST_CAP_USD:
        print(f"forecast high {fc['high_usd']} above the {COST_CAP_USD} USD cap: stopping before any call")
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
    main = run(False, names)
    log_event("runs", {"pass": "main", "at": _now(), "systems": main})
    rounds = []
    for i in range(1, RETRY_ROUNDS + 1):
        n = failed_latest(names)
        if not n:
            break
        print(f"retry pass {i}: {n} rows", flush=True)
        time.sleep(30)
        t = run(True, names)
        rounds.append({"pass": i, "sent": n, "still_failed": failed_latest(names), "systems": t})
    log_event("retry_passes", {"at": _now(), "rounds": rounds,
                               "note": "no row failed after the main pass" if not rounds else None})
    log_event("all_runs", {"systems": names, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
                           "finished": _now(), "seconds": round(time.time() - t0, 1),
                           "failed_after_retries": failed_latest(names)})
    print(f"done in {(time.time() - t0) / 60:.1f} min; failed after retries: {failed_latest(names)}", flush=True)
    return 0


# --- report, public ledgers, privacy ---------------------------------------------------------------------------

def write_public(tr) -> list[Path]:
    return full.write_public_ledgers(WORK, OUT, tr)


def committed_files() -> list[Path]:
    return sorted(p for p in OUT.rglob("*") if p.is_file() and WORK not in p.parents and p.name != ".run-log.lock")


def report() -> int:
    tr = full.TestRows()
    recs = sample.load_ledgers(WORK)
    for sy in SYSTEMS:
        s = sample.run_summary([d for d in recs if d["system"] == sy], select_for(sy, tr)).get(sy)
        if s:
            print(f"{sy:22s} rows {s['rows']:5d} failed {s['failed']:3d} (first pass {s['first_pass_failed']}) "
                  f"never_logged {s['never_logged']:3d} wall {s['wall_seconds']} failure kinds {s['failure_kinds']}")
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


def extra_run(tr=None) -> dict:
    tr = tr or full.TestRows()
    run_entry = {"key": "classic_guards_extension_run", "date": run_date(), "folder": full._rel(OUT),
                 "suites": "all six (gpt-oss-safeguard-20b), content (Llama Guard 4)", "systems": list(SYSTEMS),
                 "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    return {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
            "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files(),
            "selection": selection(tr), "not_offered": NOT_OFFERED}


def score(replicates: int | None = None) -> Path:
    """The full rescore: every run Gemini Decision 1's rescore covers, then this one."""
    import e2_strands_run as strands
    from e2_gemini_run import hosted8, liquid, msd1, pplx12
    tr = full.TestRows()
    strands.luna.write_public(tr)
    strands.jev114.write_public(tr)
    strands.write_public(tr)
    msd1.write_public(tr)
    pplx12.write_public(tr)
    hosted8.write_public(tr)
    liquid.write_public(tr)
    gemini.write_public(tr)
    write_public(tr)
    return ar.score(replicates, extra_runs=[strands.luna.extra_run(), strands.jev114.extra_run(), strands.extra_run(),
                                            msd1.extra_run(), pplx12.extra_run(), hosted8.extra_run(),
                                            liquid.extra_run(), gemini.extra_run(), extra_run(tr)])


def plan() -> None:
    tr = full.TestRows()
    for s in SYSTEMS:
        n = 0
        for (su, st), rows in select_for(s, tr).items():
            for r in rows:
                tr.guard(r)
            n += len(rows)
            u = sum(r["id"] in tr.unpublished for r in rows)
            print(f"{s} {su}/{st}: {len(rows)} rows ({u} unpublished) "
                  f"{dict(Counter((r['subtask'], r['expected']) for r in rows))}")
        print(f"{s}: {n} rows; guard passed")
    print("forecast:", json.dumps(forecast(tr), indent=1))


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "freeze", "all", "run", "report", "score"])
    ap.add_argument("--source")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--replicates", type=int, default=None)
    ap.add_argument("--only", default=None, help="comma-separated systems for all/run")
    a = ap.parse_args(argv)
    smoke.use_source(a.source)
    WORK.mkdir(parents=True, exist_ok=True)
    if a.stage == "score":
        print(score(a.replicates))
        return 0
    use_paths()
    only = [s for s in a.only.split(",") if s] if a.only else None
    if only and set(only) - set(SYSTEMS):
        raise SystemExit(f"unknown --only {sorted(set(only) - set(SYSTEMS))}; known: {', '.join(SYSTEMS)}")
    if a.stage == "plan":
        plan()
    elif a.stage == "freeze":
        write_freeze(full.TestRows())
    elif a.stage == "all":
        return run_all(only)
    elif a.stage == "run":
        print(run(a.retry_failed, only))
    else:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
