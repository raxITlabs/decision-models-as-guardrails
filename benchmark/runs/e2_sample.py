"""Edition 2 tune-split sample: a dress rehearsal of the full run on every public tune row, all systems.

    uv run python benchmark/runs/e2_sample.py plan                         # offline: rows per subtask, guard check
    uv run python benchmark/runs/e2_sample.py run --systems jev,clef,clef-flash,perplexity,bedrock
    uv run python benchmark/runs/e2_sample.py run --systems open,strands --only kev-4b   # VM models (make up first)
    uv run python benchmark/runs/e2_sample.py vm up|paused                 # record the VM session for serving cost
    uv run python benchmark/runs/e2_sample.py report                       # offline: run summary and leak check
    uv run python benchmark/runs/e2_sample.py score                        # offline: leaderboard.json (diagnostic)

What is sent: every row of ``dataset/edition2/build/F*.tune.jsonl`` (public tune split, 1,422 rows) for every adapter
subtask of ``e2_smoke.TASKS``, the custom-words sanity rows included. Nothing else. ``PublicTune.guard`` refuses any
row that is not a row of a public tune file (same id, same state), any row whose split is not ``tune`` or whose
visibility is not ``public``, and any id in the git-ignored private slice; it runs over the whole selection before a
system is built and again before each call. Test and unpublished rows are never read: they stay untouched until the
owner signs the freeze.

Adapters, the system registry, the retry policy, resume, row-text scrubbing and the ledger record format are
``e2_smoke``'s (``run_selection``, ``record``, ``scrub``). Ledgers in ``benchmark/results/edition2-tune-sample/`` keep
row ids, labels and system outputs, never row text (many tune rows come from ids-only sources, owner ruling 10).

``score`` runs ``goldrails_bench.leaderboard_v2`` in diagnostic mode over these ledgers with the contract's fixed 0.5
rule and the tune split as the report split. Everything it writes is labelled "tune-split sample, not a held-out
result": the tune rows were used to build and check the dataset, so this is a rehearsal, not a result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_smoke as smoke  # noqa: E402

REPO = smoke.REPO
BUILD = smoke.BUILD
OUT = REPO / "benchmark" / "results" / "edition2-tune-sample"
RUN_LOG = OUT / "run-log.json"
FEATURES = ("F1", "F2", "F3", "F4", "F5", "F6")
OVERLAP = REPO / "dataset" / "edition2" / "MODEL-TRAINING-OVERLAP.json"
LABEL = "tune-split sample, not a held-out result"
# The VM the self-hosted models ran on (infra/gcp/terraform.tfvars: g2-standard-24, us-east4-a, on demand) and the
# dated rates in goldrails_bench/tariffs.json: the machine (both L4s) plus the 200 GB balanced disk.
VM_HARDWARE = "g2-standard-24/us-east4/on-demand/third-party"
VM_DISK_USD_PER_HOUR = 200 * 0.11 / 730
VM_SYSTEMS = ("kev-0-8b", "kev-4b", "kev-9b", "open-jev-2b", "laya", "strands-decider-2b")
# Bedrock answers are not probabilities: each answer carries the basis the contract's frozen setting is keyed by.
BEDROCK_BASIS = {("content", "request"): "bedrock_severity", ("content", "reply"): "bedrock_severity",
                 ("prompt_attacks", "direct"): "bedrock_severity",
                 ("sensitive_info", "entity_detection"): "bedrock_confidence",
                 ("denied_topics", "topic"): "bedrock_topic_binary",
                 ("word_filters", "word"): "bedrock_word_binary",
                 ("word_filters", "profanity"): "bedrock_managed_list_binary",
                 ("grounding", "grounding"): "bedrock_grounding_inverted"}
BEDROCK_QSET = {"content": "bedrock-e2-checks", "prompt_attacks": "bedrock-e2-checks",
                "sensitive_info": "bedrock-e2-checks", "denied_topics": "bedrock-e2-topics",
                "word_filters": "bedrock-e2-words", "grounding": "bedrock-e2-grounding"}


# --- what may be sent ------------------------------------------------------------------------------------------

def _state_hash(r: dict) -> str:
    return hashlib.sha256(json.dumps(r["state"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class PublicTune:
    """The public tune rows, read from the build files, and the guard that refuses everything else."""

    def __init__(self):
        self.rows, self.feature, self.file_sha = {}, {}, {}
        for f in FEATURES:
            p = BUILD / f"{f}.tune.jsonl"
            self.file_sha[f] = hashlib.sha256(p.read_bytes()).hexdigest()
            for x in p.open(encoding="utf-8"):
                r = json.loads(x)
                self.rows[r["id"]] = r
                self.feature[r["id"]] = f
        self.hashes = {i: _state_hash(r) for i, r in self.rows.items()}
        self.private = smoke.private_ids()
        assert not set(self.rows) & self.private, "a public tune id is in the private slice"

    def guard(self, r: dict) -> None:
        rid = r.get("id")
        if rid not in self.rows:
            raise PermissionError(f"refused: {rid!r} is not a row of the public tune files")
        if r.get("split") != "tune" or r.get("visibility") != "public":
            raise PermissionError(f"refused: {rid} has split {r.get('split')!r}, visibility {r.get('visibility')!r}")
        if rid in self.private:
            raise PermissionError(f"refused: {rid} is in the private (unpublished) slice")
        if _state_hash(r) != self.hashes[rid]:
            raise PermissionError(f"refused: {rid} differs from the public tune file's row")


def select_all(pt: PublicTune) -> dict:
    """{(suite, subtask): [every public tune row with one of the subtask's tags]}, owner exclusions left out."""
    excl = smoke.excluded_ids()
    out = {}
    for (suite, sub), (feat, tags) in smoke.TASKS.items():
        rows = [r for i, r in pt.rows.items() if pt.feature[i] == feat and r["subtask"] in tags and i not in excl]
        out[(suite, sub)] = sorted(rows, key=lambda r: r["id"])
    return out


# --- run log (timing, VM sessions) -----------------------------------------------------------------------------

def _log() -> dict:
    return json.loads(RUN_LOG.read_text(encoding="utf-8")) if RUN_LOG.exists() else {"systems": {}, "vm": []}


def _save_log(d: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RUN_LOG.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")


def _locked(fn):
    """Run ``fn`` under an exclusive lock on the run log, so parallel runs never drop each other's entries."""
    import fcntl
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / ".run-log.lock").open("w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        return fn()


def log_timing(timing: dict) -> None:
    def go():
        d = _log()
        for name, t in timing.items():
            d["systems"].setdefault(name, []).append(t)
        _save_log(d)
    _locked(go)


def vm_mark(state: str) -> None:
    _locked(lambda: _vm_mark(state))


def _vm_mark(state: str) -> None:
    d = _log()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if state == "up":
        d["vm"].append({"up": now, "paused": None})
    else:
        if not d["vm"] or d["vm"][-1]["paused"]:
            raise SystemExit("no open VM session to close")
        d["vm"][-1]["paused"] = now
    _save_log(d)
    print(f"vm {state} at {now}")


def _ts(s: str) -> float:
    import calendar
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


# --- ledgers -> scorer records ---------------------------------------------------------------------------------

def load_ledgers(out: Path = OUT) -> list:
    recs = []
    for p in sorted(out.glob("*.jsonl")):
        recs += [json.loads(x) for x in p.open(encoding="utf-8") if x.strip()]
    return recs


def latest(recs: list) -> list:
    """One record per (system, suite, subtask, row): the last one written, reruns left out."""
    last = {}
    for d in recs:
        if not d["rerun"]:
            last[(d["system"], d["suite"], d["subtask"], d["row_id"])] = d
    return list(last.values())


def scorer_record(d: dict, pt: PublicTune) -> dict | None:
    """A ledger record in the shape ``goldrails_bench.leaderboard`` scores (runner ledger format). No text."""
    if d["outcome"] == "not_offered":
        return None
    r = pt.rows[d["row_id"]]
    feat = pt.feature[d["row_id"]]
    srv = d.get("serving") or {}
    bedrock = d["system"] == "bedrock-guardrails"
    basis = BEDROCK_BASIS.get((d["suite"], d["subtask"])) if bedrock else None
    qs = BEDROCK_QSET[d["suite"]] if bedrock else srv.get("question_set")
    keys = list(srv.get("decision_keys") or [])
    if bedrock and d["suite"] == "sensitive_info":
        from goldrails_bench.adapters.bedrock import PII_ENTITIES
        keys = list(PII_ENTITIES)   # scored per entity type; the adapter's own decision key is the aggregate
    answers = None
    if d["outcome"] == "decided":
        answers = {k: {"type": "noul", "noul": float(v), **({"basis": basis} if basis else {})}
                   for k, v in (d.get("per_question") or {}).items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)}
    e2 = (r.get("attribute") or {}).get("e2") or {}
    cfg = hashlib.sha256(json.dumps({"adapter": srv.get("adapter"), "model": srv.get("model_id"),
                                     "endpoint": srv.get("endpoint"), "question_set": qs},
                                    sort_keys=True).encode()).hexdigest()[:16]
    return {"id": d["row_id"], "system": d["system"], "model": srv.get("model_id"), "question_set": qs,
            "config_hash": cfg, "decision_keys": keys,
            "dataset": {"sha256": pt.file_sha[feat], "feature": feat, "split": "tune",
                        "source": "dataset/edition2/build"},
            "subtask": r["subtask"], "expected": r["expected"],
            "expected_types": sorted({s["label"] for s in r["spans"]}) if r.get("spans") is not None else None,
            "group": r.get("group") or r["id"], "split": "tune",
            "in_bedrock_five": e2.get("in_bedrock_five"), "vendor_owned": e2.get("vendor_owned"),
            "ok": d["outcome"] == "decided", "answers": answers, "error": d.get("error"),
            "latency_s": d.get("latency_s"), "raw": [{"usage": d.get("usage")}] if d.get("usage") is not None else None}


def overlap_ids(model: str = "pplx-decider-v1-27b") -> list:
    d = json.loads(OVERLAP.read_text(encoding="utf-8"))
    return sorted({i for c in d["checks"] if c["model"] == model for i in c.get("matched_public_row_ids") or []})


# --- report ----------------------------------------------------------------------------------------------------

def fast_leak_check(paths, rows_by_id: dict) -> list:
    """``e2_smoke.leak_check`` for a few thousand rows: the same 8-word runs, looked up in a set of each ledger's
    8-word windows instead of a substring scan per run; a text under 8 words (4 or more) is still a substring scan."""
    bad = set()
    for p in paths:
        words = re.findall(r"\w+", p.read_text(encoding="utf-8").lower())
        blob = " ".join(words)
        wins = {" ".join(words[i:i + 8]) for i in range(max(0, len(words) - 7))}
        for rid, r in rows_by_id.items():
            if rid in bad:
                continue
            s = r["state"]
            for t in (s.get("text"), s.get("source"), s.get("query")):
                w = re.findall(r"\w+", (t or "").lower())
                if len(w) >= 8:
                    if any(" ".join(w[i:i + 8]) in wins for i in range(len(w) - 7)):
                        bad.add(rid)
                        break
                elif len(w) >= 4 and " ".join(w) in blob:
                    bad.add(rid)
                    break
        del words, blob, wins
    return sorted(bad)


def run_summary(recs: list, sel: dict) -> dict:
    """Per system: rows, failures, not offered, truncation and near-limit counts, latency and the wall time."""
    log = _log()
    want = {(su, st): {r["id"] for r in rows} for (su, st), rows in sel.items()}
    by, first = defaultdict(list), defaultdict(list)
    for d in latest(recs):
        by[d["system"]].append(d)
    for d in recs:
        if not d["rerun"] and not d.get("retry_of_failure"):
            first[d["system"]].append(d)
    out = {}
    for sy, ds in sorted(by.items()):
        retried = [d for d in ds if d.get("retry_of_failure")]
        missing = sum(len(ids - {d["row_id"] for d in ds if (d["suite"], d["subtask"]) == k}) for k, ids in want.items())
        c = Counter(d["outcome"] for d in ds)
        lat = sorted(d["latency_s"] for d in ds if d["outcome"] == "decided" and d["latency_s"] is not None)
        q = lambda p: lat[min(len(lat) - 1, int(round(p * (len(lat) - 1))))] if lat else None  # noqa: E731
        runs = log["systems"].get(sy, [])
        per_task = {}
        for d in ds:
            t = per_task.setdefault(f"{d['suite']}/{d['subtask']}", Counter())
            t["rows"] += 1
            t["failed"] += d["outcome"] == "failed"
            t["truncated"] += d.get("truncated") is True
            t["at_cap"] += bool(d.get("at_cap"))
            t["over_limit_est"] += bool(d.get("limit_tokens") and d["est_tokens"] >= d["limit_tokens"])
            t["near_limit"] += bool(d.get("near_limit"))
        out[sy] = {"rows": len(ds), "decided": c["decided"], "failed": c["failed"], "not_offered": c["not_offered"],
                   "never_logged": missing,
                   "first_pass_failed": sum(d["outcome"] == "failed" for d in first[sy]),
                   "retried": len(retried), "recovered_on_retry": sum(d["outcome"] == "decided" for d in retried),
                   "failure_kinds": dict(Counter((d["error"] or "").split(":")[0] for d in ds if d["outcome"] == "failed")),
                   "truncated": sum(d.get("truncated") is True for d in ds),
                   "truncation_reported": sum(d.get("truncation_reported") is True for d in ds),
                   "at_cap": sum(bool(d.get("at_cap")) for d in ds),
                   "over_limit_est": sum(bool(d.get("limit_tokens") and d["est_tokens"] >= d["limit_tokens"]) for d in ds),
                   "near_limit": sum(bool(d.get("near_limit")) for d in ds),
                   "max_usage_input_tokens": max((d.get("usage_input_tokens") or 0 for d in ds), default=0) or None,
                   "limit_tokens": ds[0].get("limit_tokens"), "limit_basis": ds[0].get("limit_basis"),
                   "latency_p50_s": q(0.5), "latency_p95_s": q(0.95),
                   "wall_seconds": round(sum(r["seconds"] for r in runs), 1) if runs else None,
                   "runs": runs, "by_task": {k: dict(v) for k, v in sorted(per_task.items())}}
    return out


# --- score -----------------------------------------------------------------------------------------------------

def vm_serving(log: dict, summary: dict) -> tuple[list, dict]:
    """Serving records for the self-hosted systems: the VM's up-to-paused time, shared across the VM systems by their
    share of the summed run seconds."""
    sessions = [s for s in log.get("vm", []) if s.get("up") and s.get("paused")]
    secs = sum(_ts(s["paused"]) - _ts(s["up"]) for s in sessions)
    run = {s: (summary.get(s) or {}).get("wall_seconds") or 0 for s in VM_SYSTEMS if s in summary}
    total = sum(run.values())
    info = {"sessions": sessions, "vm_seconds": secs, "hardware": VM_HARDWARE,
            "disk_usd_per_hour": round(VM_DISK_USD_PER_HOUR, 4),
            "allocation": "VM up-to-paused seconds split across the VM systems by their share of summed run seconds; "
                          "systems that ran at the same time share the same wall-clock"}
    if not secs or not total:
        return [], info
    return [{"system": s, "hardware": VM_HARDWARE, "allocated_seconds": secs * t / total, "share": 1.0,
             "evaluations": summary[s]["rows"] - summary[s]["not_offered"]} for s, t in run.items()], info


def system_costs(records: list, serving: list, tariffs: dict) -> dict:
    """USD per 1,000 checks per system: measured usage x dated tariff (hosted), or allocated VM time x the dated
    machine rate plus disk (self-hosted). One check is one row sent to one system."""
    from goldrails_bench import leaderboard as lb
    rate = next((e.get("usd_per_hour") for e in tariffs["entries"]
                 if VM_HARDWARE in (e.get("match") or {}).get("hardware", [])), None)
    by = defaultdict(list)
    for r in records:
        by[r["system"]].append(r)
    out = {}
    for sy, rs in sorted(by.items()):
        sv = next((s for s in serving if s["system"] == sy), None)
        if sv:
            usd = sv["allocated_seconds"] / 3600 * ((rate or 0) + VM_DISK_USD_PER_HOUR)
            out[sy] = {"usd_total": round(usd, 4), "checks": len(rs), "usd_per_1000": 1000 * usd / len(rs),
                       "basis": f"allocated VM time ({sv['allocated_seconds']:.0f} s) x {VM_HARDWARE} "
                                f"${rate}/h + disk ${VM_DISK_USD_PER_HOUR:.3f}/h"}
            continue
        if sy in VM_SYSTEMS:
            out[sy] = {"usd_total": None, "checks": len(rs), "usd_per_1000": None, "basis": "no VM session recorded"}
            continue
        total, unknown = 0.0, Counter()
        for r in rs:
            usd, why, _ = lb.record_cost(r, lb.tariff_for(r, None, tariffs))
            if usd is None:
                unknown[why] += 1
            else:
                total += usd
        out[sy] = {"usd_total": round(total, 4) if not unknown else None, "checks": len(rs),
                   "usd_per_1000": 1000 * total / len(rs) if not unknown else None,
                   "basis": "measured usage x dated tariff (goldrails_bench/tariffs.json); retried attempts are not "
                            "billed here",
                   **({"unknown": dict(unknown)} if unknown else {})}
    return out


def implementations(records: list) -> dict:
    """Each system's word-filter subtasks come from different question sets (two arms); declare which is which."""
    out = {}
    for sy in sorted({r["system"] for r in records}):
        qs = {r["subtask"]: r["question_set"] for r in records if r["system"] == sy and r["dataset"]["feature"] == "F4"}
        sel = {}
        if qs:
            sel["word_filters"] = {"subtasks": {"word": {"question_set": qs.get("word")},
                                                "profanity": {"question_set": qs.get("profanity")}}}
        out[sy] = sel
    return out


def evaluate(records: list, drop: set = frozenset(), serving=None, tariffs=None, arms_meta=None,
             replicates=None) -> dict:
    from goldrails_bench import leaderboard_v2 as lv2
    frozen_all = lv2.load_frozen_rows([BUILD / f"{f}.tune.jsonl" for f in FEATURES])
    frozen = {k: {i: v for i, v in rows.items() if i not in drop} for k, rows in frozen_all.items()}
    recs = [dict(r) for r in records if r["id"] not in drop]
    return lv2.evaluate(recs, lv2.load_contract(), implementations(recs), None, "tune", None, replicates, None,
                        tariffs, serving or [], arms_meta or {}, {}, frozen=frozen, diagnostic=True)


def compact(doc: dict) -> dict:
    """The per-system table: overall and per suite (value, interval, tier, catch and false-block rates)."""
    rows = {}
    for e in doc["overall"].get("ranking", []) + doc["overall"].get("unranked", []):
        rows.setdefault(e["name"], {})["overall"] = {k: e.get(k) for k in (
            "rank", "balanced_accuracy", "ci", "tier", "rank_interval", "catch_rate", "false_block_rate", "f1",
            "status", "reason")}
    for su, b in doc["suites"].items():
        for e in b.get("ranking", []) + b.get("unranked", []):
            rows.setdefault(e["name"], {})[su] = {k: e.get(k) for k in (
                "rank", "balanced_accuracy", "ci", "tier", "catch_rate", "false_block_rate", "f1", "status", "reason")}
    return rows


def score(replicates: int | None = None) -> Path:
    from goldrails_bench import leaderboard as lb
    pt = PublicTune()
    sel = select_all(pt)
    recs = load_ledgers()
    summary = run_summary(recs, sel)
    final = latest(recs)
    records = [x for d in final if (x := scorer_record(d, pt))]
    tariffs = lb.load_tariffs()
    serving, vm_info = vm_serving(_log(), summary)
    arms_meta = {}
    for d, x in ((d, scorer_record(d, pt)) for d in final):
        ident = (d.get("serving") or {}).get("identity") or {}
        if x and ident.get("kind"):
            arms_meta[(x["system"], x["config_hash"], x["dataset"]["sha256"])] = {
                "system": x["system"], "model": x["model"], "identity": ident}
    doc = evaluate(records, serving=serving, tariffs=tariffs, arms_meta=arms_meta, replicates=replicates)
    drop = set(overlap_ids())
    sens = evaluate(records, drop=drop, replicates=replicates)
    blocked = {p.name.replace(".blocked.json", ""): json.loads(p.read_text())["reason"]
               for p in OUT.glob("*.blocked.json")}
    pplx = "pplx-decider-v1-27b"
    by_feat = Counter(pt.feature[i] for i in drop if i in pt.rows)
    doc["label"] = f"{LABEL.upper()}: " + doc["label"]
    doc["sample"] = {
        "label": LABEL,
        "what": "every public tune row of edition 2 (dataset/edition2/build/F*.tune.jsonl) sent to every system, "
                "scored at the contract v2.0 fixed 0.5 rule with the tune split as the report split",
        "caveats": [
            "tune split: these rows were used to build, label and check the dataset (shortcut gate, smoke tests), so "
            "this is a rehearsal of the full run, not a held-out result; the test split and unpublished slice were "
            "not sent",
            f"small: {len(pt.rows)} rows over 6 suites (118 to 544 per suite); intervals are wide",
            "prompt attacks are provisional (owner rulings 17 and 18): labels are partly predictable from source and style",
            "custom words (word_filters/word, 11 rows) are a pass/fail sanity check outside the score (owner ruling 13)",
            "DRIVER_ID is an unscored diagnostic (owner ruling 6)",
            f"{len(drop)} tune rows match pplx-decider-v1-27b's training or development data "
            f"({', '.join(f'{k} {v}' for k, v in sorted(by_feat.items()))}); see pplx_overlap_sensitivity",
            "Laya reads at most 512 tokens per question (owner ruling 16); truncated rows are counted in run.systems",
            "Strands Decider 2B has a 4,096-token window and cuts silently; rows estimated over it are counted",
            "latency is per row as recorded under each system's worker count (1 to 8 threads), not a declared-load "
            "measurement; the VM models shared two L4 GPUs",
        ],
        "rows": {f: sum(1 for i in pt.rows if pt.feature[i] == f) for f in FEATURES},
        "rows_total": len(pt.rows),
        "tune_file_sha256": pt.file_sha,
    }
    doc["sample"]["question_set_names"] = question_set_note()
    doc["run"] = {"systems": summary, "blocked": blocked, "vm": vm_info,
                  "cost": system_costs(records, serving, tariffs),
                  "not_run": {f"{k[0]}/{k[1]}": v for k, v in smoke.NOT_RUN.items()}}
    doc["table"] = compact(doc)
    st = compact(sens)
    doc["pplx_overlap_sensitivity"] = {
        "label": f"{LABEL}; sensitivity view: every system rescored without the {len(drop)} tune rows that match "
                 "pplx-decider-v1-27b's training or development data (dataset/edition2/MODEL-TRAINING-OVERLAP.json)",
        "rows_dropped": len(drop), "rows_dropped_by_feature": dict(sorted(by_feat.items())),
        "table": st, "pplx_with": doc["table"].get(pplx), "pplx_without": st.get(pplx),
        "subtasks": {k: {"with": next(({kk: e.get(kk) for kk in ("balanced_accuracy", "ci", "catch_rate", "false_block_rate", "n")}
                                       for e in doc["subtasks"].get(k, {}).get("ranking", []) if e["name"] == pplx), None),
                         "without": next(({kk: e.get(kk) for kk in ("balanced_accuracy", "ci", "catch_rate", "false_block_rate", "n")}
                                          for e in b.get("ranking", []) if e["name"] == pplx), None)}
                     for k, b in sens["subtasks"].items()},
    }
    leaks = fast_leak_check(sorted(OUT.glob("*.jsonl")), pt.rows)
    doc["leak_check"] = {"rows_with_text_in_ledgers": len(leaks), "rows_checked": len(pt.rows)}
    p = OUT / "leaderboard.json"
    p.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    if leaks:
        raise SystemExit(f"row text found in ledgers for {len(leaks)} rows; fix before committing")
    return p


def question_set_note() -> dict:
    """The scorer discloses e2-* set names that differ from the contract's v1-* names; record whether the questions and
    decision lists are the same, so a reader can tell a renamed copy from a revision."""
    qs = REPO / "benchmark" / "question_sets"
    same = {}
    for name in ("f1-bedrock5", "f4-words", "f4-obscenity", "f6-grounding"):
        a, b = (json.loads((qs / ed / f"{name}.json").read_text(encoding="utf-8")) for ed in ("v1", "e2"))
        same[f"e2-{name}"] = a.get("questions") == b.get("questions") and a.get("decision") == b.get("decision")
    return {"identical_to_v1": same,
            "note": "where true, the e2 set is a copy of the contract's frozen v1 set (same questions and decision "
                    "list), so the question-set disclosures for it are name-only"}


def plan() -> None:
    pt = PublicTune()
    sel = select_all(pt)
    for rows in sel.values():
        for r in rows:
            pt.guard(r)
    n = 0
    for (su, st), rows in sel.items():
        n += len(rows)
        print(f"{su}/{st}: {len(rows)} rows {dict(Counter((r['subtask'], r['expected']) for r in rows))}")
    print(f"total {n} rows per system; guard passed; overlap rows for pplx: {len(overlap_ids())}")


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "run", "vm", "report", "score"])
    ap.add_argument("state", nargs="?", choices=["up", "paused"])
    ap.add_argument("--systems", default="jev,clef,clef-flash,perplexity,bedrock")
    ap.add_argument("--only", default=None, help="comma-separated system names to run")
    ap.add_argument("--replicates", type=int, default=None)
    ap.add_argument("--retry-failed", action="store_true", help="send again only rows whose latest record failed")
    a = ap.parse_args(argv)
    if a.stage == "plan":
        plan()
    elif a.stage == "vm":
        if not a.state:
            ap.error("vm needs up or paused")
        vm_mark(a.state)
    elif a.stage == "run":
        pt = PublicTune()
        t = smoke.run_selection(set(a.systems.split(",")), select_all(pt), OUT,
                                set(a.only.split(",")) if a.only else None, reruns=False, guard=pt.guard,
                                retry_failed=a.retry_failed)
        for v in t.values():
            v["retry_failed_only"] = a.retry_failed
        log_timing(t)
    elif a.stage == "report":
        pt = PublicTune()
        s = run_summary(load_ledgers(), select_all(pt))
        for sy, x in s.items():
            print(f"{sy:20s} rows {x['rows']:5d} failed {x['failed']:3d} (first pass {x['first_pass_failed']}) not_offered {x['not_offered']:3d} "
                  f"never_logged {x['never_logged']:3d} truncated {x['truncated']:3d} at_cap {x['at_cap']:3d} "
                  f"over_limit_est {x['over_limit_est']:3d} p95 {x['latency_p95_s']} wall {x['wall_seconds']}")
        leaks = fast_leak_check(sorted(OUT.glob("*.jsonl")), pt.rows)
        print("leaks", len(leaks))
        return 1 if leaks else 0
    else:
        print(score(a.replicates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
