"""Saturation check for edition 2: how much discriminating power each job has left.

Offline and free. It reruns the published scoring path (``e2_msd1_run.score``, the same rows, labels after the
ruling 32 amendment, the fixed 0.5 rule) with every file write switched off, takes the scorer's captured per-row
state, and reports per job:

- the top tier's score spread (from ``site/data/board.json``, the published board);
- the share of judgments every system gets right, every top-tier system gets right, and no system gets right;
- item difficulty (share of the 20 systems right) and item discrimination (point-biserial correlation between a
  row being right and the system's job score), and the share of rows that separate anything at all;
- how many tier boundaries the job has and the gap between tier 1 and the rest.

Needs the maintainers' local ledgers and the unpublished slice, like ``score``; on any other machine it fails.

    uv run python benchmark/runs/e2_saturation.py capture     # writes the per-row matrix to .scratch/ (git-ignored)
    uv run python benchmark/runs/e2_saturation.py report      # aggregate numbers only, to docs/benchmark/

The per-row matrix holds unpublished-slice ids, so it stays in ``.scratch/``. The report holds counts and rates only:
no row id and no row text.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
CACHE = REPO / ".scratch" / "saturation-matrix.json"
OUT = REPO / "docs" / "benchmark" / "32-saturation.json"
BOARD = REPO / "site" / "data" / "board.json"

# board job key -> (suite, subtask)
JOBS = {"input": ("content", "request"), "output": ("content", "reply"),
        "direct": ("prompt_attacks", "direct"), "indirect": ("prompt_attacks", "indirect"),
        "topics": ("denied_topics", "topic"), "profanity": ("word_filters", "profanity"),
        "pii": ("sensitive_info", "entity_detection"), "grounding": ("grounding", "grounding")}
JOB_NAME = {"input": "Content: requests", "output": "Content: replies", "direct": "Prompt attacks: direct",
            "indirect": "Prompt attacks: indirect", "topics": "Denied topics", "profanity": "Profanity",
            "pii": "Sensitive information (PII)", "grounding": "Grounding"}


class _Captured(Exception):
    pass


def capture() -> Path:
    import e2_msd1_run as msd1
    import e2_smoke as smoke
    import e2_strands_run as strands
    import e2_full as full
    from goldrails_bench import leaderboard_v2 as lv2

    smoke.use_source("local")
    for m in (strands.luna, strands.jev114, strands, msd1):     # no public-ledger writes
        m.write_public = lambda tr: []
    orig = lv2.evaluate

    def grab(*a, **k):
        cap = k["capture"]
        orig(*a, **k)
        raise _Captured(cap)

    lv2.evaluate = grab
    try:
        msd1.score(replicates=20)
    except _Captured as e:
        cap = e.args[0]
    else:
        raise SystemExit("the scorer finished without reaching evaluate; nothing captured")
    tr = full.TestRows()
    systems = [s["id"] for s in json.loads(BOARD.read_text())["systems"]]
    out = {"systems": systems, "jobs": {}}
    for job, (suite, st) in JOBS.items():
        rows = {}                                   # (id, unit) -> {label, source, unpublished, correct{sys}, score{sys}}
        for name in systems:
            k, status, _ = cap["picks"].get((name, suite, st), (None, None, None))
            if k is None or status != "evaluated":
                raise SystemExit(f"{name} {suite}/{st}: {status}")
            e = cap["ev"][k]
            t = e["rule"]["threshold"]
            for unit, rs in e["su"][st].items():
                for x in rs:
                    d = rows.setdefault((x.id, unit), {
                        "positive": x.positive, "unit": unit,
                        "source": (tr.rows.get(x.id) or {}).get("source"),
                        "unpublished": x.id in tr.unpublished, "correct": {}, "score": {}})
                    ok = x.outcome == "decided" and ((x.score >= t) == x.positive)
                    d["correct"][name] = ok
                    d["score"][name] = x.score if x.outcome == "decided" else None
        out["jobs"][job] = rows
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out["jobs"] = {j: [{"id": i, **d} for (i, _), d in rs.items()] for j, rs in out["jobs"].items()}
    CACHE.write_text(json.dumps(out), encoding="utf-8")
    return CACHE


def _ba(correct: np.ndarray, pos: np.ndarray, units: np.ndarray) -> np.ndarray:
    """Balanced accuracy x100 per system (columns), mean over units with both classes, as the scorer does."""
    vals = []
    for u in np.unique(units):
        m = units == u
        p, n = m & pos, m & ~pos
        if p.sum() and n.sum():
            vals.append(50.0 * (correct[p].mean(axis=0) + correct[n].mean(axis=0)))
    return np.mean(vals, axis=0)


def _sources() -> dict:
    """Row id -> upstream source, from the edition 2 build files (public and the local unpublished slice)."""
    out = {}
    build = REPO / "dataset" / "edition2" / "build"
    for p in [*build.glob("F*.test.jsonl"), *(build / "private").glob("F*.test.jsonl")]:
        for x in p.open(encoding="utf-8"):
            r = json.loads(x)
            out[r["id"]] = (r.get("provenance") or {}).get("source") or r["id"].split("-")[1]
    return out


def report() -> Path:
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    srcmap = _sources()
    board = json.loads(BOARD.read_text())
    systems = data["systems"]
    res = {"what": "edition 2 saturation check (docs/benchmark/32-saturation.md); counts and rates only",
           "systems": len(systems), "jobs": {}}
    for job, rows in data["jobs"].items():
        rows = {(d["id"], d["unit"]): d for d in rows}
        keys = sorted(rows)
        C = np.array([[rows[k]["correct"][s] for s in systems] for k in keys], dtype=float)
        pos = np.array([rows[k]["positive"] for k in keys])
        units = np.array([rows[k]["unit"] for k in keys])
        unp = np.array([rows[k]["unpublished"] for k in keys])
        src = [rows[k]["source"] or srcmap.get(k[0]) or k[0].split("-")[1] for k in keys]
        ba = _ba(C, pos, units)
        bj = {e["system"]: e for e in board["jobs"][job]}
        board_ba = np.array([bj[s]["score"] for s in systems])
        drift = float(np.max(np.abs(ba - board_ba)))
        tier = np.array([bj[s]["tier"] for s in systems])
        top = tier == 1
        n = len(keys)
        k_right = C.sum(axis=1)
        all_right = k_right == len(systems)
        none_right = k_right == 0
        top_right = C[:, top].all(axis=1)
        top_wrong = (~C[:, top].astype(bool)).all(axis=1)
        # discrimination: point-biserial r between row correctness and system job score
        z = (ba - ba.mean()) / (ba.std() or 1)
        Cc = C - C.mean(axis=1, keepdims=True)
        sd = C.std(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = (Cc @ z) / (len(systems) * sd)
        r = np.where(sd > 0, r, np.nan)
        informative = ~(all_right | none_right)
        # among top-tier systems: rows where they disagree (the only rows that can reorder tier 1)
        top_split = ~(top_right | top_wrong)
        diff = k_right / len(systems)
        # ceiling: a row counts right when any tier-1 system gets it right (an oracle over tier 1)
        oracle = _ba(C[:, top].max(axis=1, keepdims=True), pos, units)[0]
        # what the top tier misses: by class and by source
        miss_top = ~top_right
        by_src = Counter(s for s, m in zip(src, miss_top) if m)
        tot_src = Counter(src)
        scores = sorted((bj[s]["score"] for s in systems), reverse=True)
        tiers = sorted(set(tier.tolist()))
        t1 = [bj[s]["score"] for s in systems if bj[s]["tier"] == 1]
        rest_best = max([bj[s]["score"] for s in systems if bj[s]["tier"] > 1], default=None)
        res["jobs"][job] = {
            "name": JOB_NAME[job], "judgments": n, "positive": int(pos.sum()), "negative": int((~pos).sum()),
            "units": int(len(np.unique(units))), "unpublished_share": round(float(unp.mean()), 4),
            "recomputed_vs_board_max_abs_diff": round(drift, 4),
            "top_score": scores[0], "median_score": float(np.median(scores)),
            "tier1": {"systems": int(top.sum()), "min": min(t1), "max": max(t1), "spread": round(max(t1) - min(t1), 2),
                      "gap_to_tier2_best": round(min(t1) - rest_best, 2) if rest_best is not None else None,
                      "headroom_to_100": round(100 - max(t1), 2)},
            "tiers": len(tiers),
            "tier1_oracle_score": round(float(oracle), 2),
            "share_all_20_right": round(float(all_right.mean()), 4),
            "share_all_tier1_right": round(float(top_right.mean()), 4),
            "share_no_system_right": round(float(none_right.mean()), 4),
            "share_no_tier1_right": round(float(top_wrong.mean()), 4),
            "share_tier1_disagree": round(float(top_split.mean()), 4),
            "share_informative": round(float(informative.mean()), 4),
            "no_system_right_by_class": {"positive": int((none_right & pos).sum()), "negative": int((none_right & ~pos).sum())},
            "tier1_miss_by_class": {"positive": int((miss_top & pos).sum()), "negative": int((miss_top & ~pos).sum())},
            "difficulty": {"mean_share_right": round(float(diff.mean()), 4),
                           "bins": {f"{lo}-{hi}": int(((k_right >= lo) & (k_right <= hi)).sum())
                                    for lo, hi in ((0, 0), (1, 5), (6, 10), (11, 15), (16, 19), (20, 20))}},
            "discrimination": {"median_r_informative": round(float(np.nanmedian(r[informative])), 3) if informative.any() else None,
                               "share_r_ge_0.3": round(float(np.nansum(r >= 0.3) / n), 4),
                               "share_r_lt_0": round(float(np.nansum(r < 0) / n), 4)},
            "tier1_misses_by_source": {s: {"missed": c, "rows": tot_src[s], "rate": round(c / tot_src[s], 3)}
                                       for s, c in by_src.most_common(8)},
            "no_system_right_by_source": dict(Counter(s for s, m in zip(src, none_right) if m).most_common(8)),
        }
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    return OUT


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["capture", "report"])
    a = ap.parse_args(argv)
    print(capture() if a.stage == "capture" else report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
