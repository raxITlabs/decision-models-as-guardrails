"""gpt-6-luna (OpenAI Decisions API) as the twelfth system: all six suites on the rows the other eleven were scored on.

    uv run python benchmark/runs/e2_openai_run.py plan --source local       # rows per subtask, guard, cost forecast
    uv run python benchmark/runs/e2_openai_run.py freeze --source local     # extension manifest; commit it first
    uv run python benchmark/runs/e2_openai_run.py all --source local        # forecast, main pass, retry passes
    uv run python benchmark/runs/e2_openai_run.py report --source local     # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_openai_run.py score --source local   # benchmark/results/final/

The rows are exactly the eleven systems' rows: the five full-run suites (content, denied topics, word filters, PII,
grounding; their test files hash as the primary freeze recorded) and the r26 prompt-attack suite (hashes as the r26
extension recorded), test split plus the unpublished slice, owner exclusions left out. ``e2_full.TestRows.guard``
refuses anything else, before any call and again before each one.

The freeze is an extension manifest (``goldrails_bench.freeze``) that extends the primary
(``benchmark/subsets/edition2/freeze-manifest.json``) with one arm per gpt-6-luna question set: the same eight sets,
fixed 0.5 rule and retry policy as every Noul model, on the same dataset versions. Nothing is fitted. The contract is
unchanged since the r26 extension, so this manifest records no contract amendment. ``run`` refuses to send until it
is committed, and every record carries its sha256.

Data handling. The unpublished slice goes to OpenAI. Zero Data Retention is offered only to eligible customers under
a separate agreement, so OpenAI's default API data retention applies. The owner waived the equivalent check for
Perplexity (ruling 21); the coordinator's brief of 7 October 2026 treats that waiver as covering OpenAI.

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/gpt-6-luna/private/``; ``report`` and
``score`` write committed ledgers with public test rows only and run the privacy checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_attacks_rerun as ar  # noqa: E402  (points e2_full's globals at the r26 rerun, which its score reads)
import e2_full as full  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_smoke as smoke  # noqa: E402

REPO = full.REPO
SYSTEM = "gpt-6-luna"
OUT = full.FINAL / "ledgers" / "gpt-6-luna"
WORK = OUT / "private"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / "freeze-manifest-gpt-6-luna.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
SMOKE = REPO / "benchmark" / "results" / "edition2-smoke" / f"{SYSTEM}.jsonl"
LABEL = "gpt-6-luna extension run: every edition 2 test row and the unpublished slice, contract v2.0 as amended"
APPROVAL = ("gpt-6-luna added as the twelfth system on the coordinator's brief of 7 October 2026 (owner request); spend "
            "under the USD 30 cap; unpublished slice sent to OpenAI under the ruling 21 waiver")
NOUL_ADAPTER = {"name": "noul-e2", "version": "1"}
WORKERS, RATE = 8, 10.0          # 600 requests/min, well under the account's 5,000/min and 2M tokens/min
RETRY_ROUNDS = 2
COST_CAP_USD = 30.0
DISCLOSURES = [
    "gpt-6-luna's Decisions API takes one text string or user messages, with no system, assistant or tool role. Each "
    "row goes to it as one string: earlier turns as 'Role: text' lines, then the source document and the query when "
    "the row has them, then the text under review labelled with its role. Retrieved content (indirect prompt "
    "attacks) carries the '[Untrusted retrieved content]' tag, as Bedrock's does. Each yes/no question becomes a "
    "predicate made of the question's instructions and its true and false criteria, and all of a row's questions go "
    "in one request. Content's severity question is not sent: it is a score, outside every decision list.",
    "The unpublished slice was sent to OpenAI. Zero Data Retention is available only to eligible customers under a "
    "separate agreement, so OpenAI's default API data retention applies to those rows. The owner's waiver of the "
    "data-retention check for Perplexity (ruling 21) is taken to cover OpenAI as well.",
    "204 of the public content test rows (239 with the unpublished slice) come from OpenAI's own moderation evaluation "
    "set. "
    "OpenAI may have trained or tuned gpt-6-luna on them. Content is also reported without those rows "
    "(content view excluding_openai_owned).",
    "gpt-6-luna refused one question on 10 of its 10,053 rows (9 PII rows, 7 of them on the Social Security number "
    "question, and 1 content row): the API returned an answer of type 'refusal' with no probability, which its docs "
    "do not describe. Resending gave the same answer. Those rows count as failures, wrong in their class (0.1% of "
    "rows; 1.25% of PII rows, under the 2% cap).",
    "gpt-6-luna ran on 7 October 2026, after the other eleven systems, under its own freeze manifest committed before "
    "its first test call (benchmark/subsets/edition2/freeze-manifest-gpt-6-luna.json).",
]
CAVEATS = ["gpt-6-luna is a hosted public-beta model with no version pin; the response's model field is recorded per "
           "row, and OpenAI returned no version header"]


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
        return full.recorded_forecast()
    price = next(e for e in lb.load_tariffs()["entries"] if SYSTEM in e["match"].get("models", []))
    usd_m = price["prices"]["input_tokens"]["usd_per_million"]
    pts = defaultdict(list)
    for x in SMOKE.open(encoding="utf-8"):
        d = json.loads(x)
        if d["outcome"] == "decided" and (d.get("usage") or {}).get("input_tokens"):
            pts[(d["suite"], d["subtask"])].append((d["state_chars"], d["usage"]["input_tokens"]))
    by, total_tok = {}, 0
    for k, rows in sel.items():
        xs, ys = zip(*pts[k])
        slope, icpt = np.polyfit(xs, ys, 1) if len(set(xs)) > 1 else (0.0, float(np.mean(ys)))
        tok = sum(max(icpt + slope * smoke.state_chars(r), 1.0) for r in rows)
        by[f"{k[0]}/{k[1]}"] = {"rows": len(rows), "tokens": round(tok), "tokens_per_char": round(float(slope), 4),
                                "overhead_tokens": round(float(icpt))}
        total_tok += tok
    usd = total_tok * usd_m / 1e6
    return {"rows": sum(len(v) for v in sel.values()), "input_tokens": round(total_tok), "usd_per_million": usd_m,
            "total_usd": round(usd, 3), "high_usd": round(1.5 * usd, 3), "cap_usd": COST_CAP_USD, "by_subtask": by,
            "basis": f"smoke ledger {SMOKE.relative_to(REPO)}: measured input tokens per subtask fitted on state "
                     "characters, applied to every selected row; high = 1.5 x"}


# --- freeze ----------------------------------------------------------------------------------------------------

def _cfg(qs: str) -> str:
    from goldrails_bench.hosted import OPENAI_URL
    return hashlib.sha256(json.dumps({"adapter": NOUL_ADAPTER, "model": SYSTEM, "endpoint": OPENAI_URL,
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16]


def _template_arms() -> list:
    """The question set, suite, score scale and rule of every Noul model's arm: Clef's arms in the primary for the five
    kept suites and in the r26 extension for prompt attacks (every Noul model has the same eight)."""
    from goldrails_bench import freeze as F
    pm, _ = F.load_committed(PRIMARY)
    xm, _ = F.load_committed(R26)
    arms = [a for a in pm["arms"] if a["system"] == "clef" and a["suite"] != ar.SUITE]
    arms += [a for a in xm["arms"] if a["system"] == "clef"]
    if len(arms) != 8:
        raise SystemExit(f"expected 8 Noul arms to copy, found {len(arms)}")
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
            raise SystemExit(f"the smoke ledger has no matching gpt-6-luna record for {qs}")
        cfg = _cfg(qs)
        if hashlib.sha256(json.dumps({"adapter": s["adapter"], "model": s["model_id"], "endpoint": s["endpoint"],
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16] != cfg:
            raise SystemExit(f"{qs}: the smoke record's serving does not reproduce the config hash")
        sha = have[su]
        out.append({"arm_id": f"{SYSTEM}|{qs}|{cfg}|{sha[:12]}", "system": SYSTEM, "question_set": qs,
                    "config_hash": cfg, "suite": su, "score_scale": a["score_scale"],
                    "decision_rule": a["decision_rule"], "dataset": {"sha256": sha},
                    "_template": f"clef|{qs}|{a['config_hash']}|{a['dataset_sha256'][:12]}"})
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
               "reason": "a twelfth system (gpt-6-luna, OpenAI Decisions API, public beta from 7 October 2026) on every "
                         "suite's frozen test rows: the five suites of the primary freeze and the r26 prompt-attack "
                         "suite; no arm of the primary or the r26 extension changes",
               "after_extension": {"manifest_sha256": xident["manifest_sha256"], "manifest_path": xident["path"],
                                   "note": "the prompt-attack arms use the r26 dataset version that extension froze; "
                                           "the contract is the one it amended to, unchanged since"}}
    t0 = time.time()
    m = F.write_manifest(doc, MANIFEST, retry_policy=DEFAULT_POLICY,
                         test_datasets={full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES},
                         test_files={full.FEATURE_SUITE[f]: tr.files[f] for f in full.FEATURES},
                         references=F.default_references(), edition=2, extends=extends, contract=contract)
    probs = F.validate(m) + F.integrity_problems(m, recompute=False)
    if probs:
        MANIFEST.unlink()
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    for out_arm, a in zip(m["arms"], arms):
        out_arm["checked_on"] = {"template_arm": a["_template"],
                                 "note": "the same question set, score scale and fixed rule as every Noul model's arm "
                                         "(Clef's shown); config hash from the gpt-6-luna smoke test's serving"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": [SYSTEM],
                "smoke": full._rel(SMOKE), "data_handling": DISCLOSURES[1]}
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"extension manifest: {len(m['arms'])} arms, integrity pass over {m['integrity']['test_rows']} test rows "
          f"({time.time() - t0:.0f}s) -> {full._rel(MANIFEST)}; commit it before any call")
    return m


# --- run -------------------------------------------------------------------------------------------------------

def build():
    from goldrails_bench import hosted
    from goldrails_bench.adapters import NoulAdapter
    c = hosted.OpenAIDecisionsClient.from_env(throttle=hosted.Throttle(RATE))
    if c is None:
        raise SystemExit(hosted.not_configured("openai"))
    return {c.system: (NoulAdapter(c, endpoint=c.endpoint), WORKERS)}, {}


def run(retry_failed: bool) -> dict:
    from goldrails_bench import freeze as F
    try:
        _, ident = F.load_committed(MANIFEST)
    except F.FreezeError as e:
        raise SystemExit(f"refusing to run: {e}") from None
    tr = full.TestRows()
    smoke.build_systems = lambda kinds: build()
    t = smoke.run_selection({"openai"}, select(tr), WORK, None, reruns=False, guard=tr.guard,
                            retry_failed=retry_failed, stamp={"freeze": F.record_stamp(ident)})
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
    probs = F.integrity_problems(m)
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


def score(replicates: int | None = None) -> Path:
    tr = full.TestRows()
    write_public(tr)
    run_entry = {"key": "openai_extension_run", "date": "2026-10-07", "folder": full._rel(OUT), "suites": "all six",
                 "systems": [SYSTEM], "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    extra = {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
             "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files()}
    return ar.score(replicates, extra_runs=[extra])


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
