"""Contamination signal for edition 2: does a system do unusually well on one upstream source?

Offline and free. Reads the per-row matrix that ``e2_saturation.py capture`` wrote (the scorer's own rows and
labels, every system, every test row and the unpublished slice) and the edition 2 build files for each row's
source.

For each job, source and system it computes the source advantage: balanced accuracy on that source's rows minus
balanced accuracy on the job's other rows. A source that is simply easy or hard moves every system the same way,
so the statistic that matters is the excess: a system's advantage minus the median advantage over all systems. A
system that trained on a source, or on text like it, should show a large positive excess there and nowhere else.
Intervals come from 1,000 bootstrap resamples of rows.

Known positives check the method. Strands Decider 2B and Perplexity's decider published that they trained on
Civil Comments, and Perplexity's on Aegis 2.0 (rows whose exact text is in those splits were already excluded, so
what is left is same-distribution text, not the same rows).

    uv run python benchmark/runs/e2_contamination_signal.py [--build <dir with F*.test.jsonl and private/>]

Writes counts and rates only to docs/benchmark/35-contamination-signal.json. No row id, no row text.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CACHE = REPO / ".scratch" / "saturation-matrix.json"
OUT = REPO / "docs" / "benchmark" / "35-contamination-signal.json"
MIN_PER_CLASS = 20
B = 1000

# raxIT-authored sources: no text existed publicly before October 2026
AUTHORED = {"e2_attack_controls", "e2_authored_quote_frames", "e2_denied_topics", "e2_pii_controls"}
KNOWN_TRAINING = {
    "strands-decider-2b": {"e2_profanity_civil_comments": "civil_comments train (published recipe)"},
    "pplx-decider-v1-27b": {"e2_profanity_civil_comments": "civil_comments train (published recipe)",
                            "aegis2": "Aegis 2.0 train (published recipe)",
                            "e2_content_aegis2_test": "Aegis 2.0 train (published recipe)"},
}


def sources(build: Path) -> dict:
    out = {}
    for p in [*build.glob("F*.test.jsonl"), *(build / "private").glob("F*.test.jsonl")]:
        for x in p.open(encoding="utf-8"):
            r = json.loads(x)
            out[r["id"]] = (r.get("provenance") or {}).get("source") or r["id"].split("-")[1]
    return out


def ba(C: np.ndarray, pos: np.ndarray, units: np.ndarray) -> np.ndarray:
    """Balanced accuracy x100 per system column, mean over units with both classes (nan if none)."""
    vals = []
    for u in np.unique(units):
        m = units == u
        p, n = m & pos, m & ~pos
        if p.sum() and n.sum():
            vals.append(50.0 * (C[p].mean(axis=0) + C[n].mean(axis=0)))
    return np.mean(vals, axis=0) if vals else np.full(C.shape[1], np.nan)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=str(REPO / "dataset" / "edition2" / "build"))
    a = ap.parse_args(argv)
    data = json.loads(CACHE.read_text(encoding="utf-8"))
    src = sources(Path(a.build))
    systems = data["systems"]
    rng = np.random.default_rng(0)
    res = {"what": "per-source excess advantage (docs/benchmark/35-contamination-signal.md); counts and rates only",
           "min_rows_per_class": MIN_PER_CLASS, "bootstrap": B, "cells": []}
    for job, rows in data["jobs"].items():
        C = np.array([[d["correct"][s] for s in systems] for d in rows], dtype=float)
        pos = np.array([d["positive"] for d in rows])
        units = np.array([d["unit"] for d in rows])
        sr = np.array([src.get(d["id"], d["id"].split("-")[1]) for d in rows])
        for s_name in sorted(set(sr)):
            m = sr == s_name
            if (m & pos).sum() < MIN_PER_CLASS or (m & ~pos).sum() < MIN_PER_CLASS:
                continue
            if (~m & pos).sum() < MIN_PER_CLASS or (~m & ~pos).sum() < MIN_PER_CLASS:
                continue
            ins, outs = np.where(m)[0], np.where(~m)[0]

            def excess(i_idx, o_idx):
                adv = ba(C[i_idx], pos[i_idx], units[i_idx]) - ba(C[o_idx], pos[o_idx], units[o_idx])
                return adv - np.nanmedian(adv), adv

            point, adv = excess(ins, outs)
            reps = np.array([excess(rng.choice(ins, len(ins)), rng.choice(outs, len(outs)))[0] for _ in range(B)])
            lo, hi = np.nanpercentile(reps, 2.5, axis=0), np.nanpercentile(reps, 97.5, axis=0)
            for k, s in enumerate(systems):
                res["cells"].append({
                    "job": job, "source": s_name, "system": s, "rows": int(m.sum()),
                    "authored": s_name in AUTHORED,
                    "known_training": KNOWN_TRAINING.get(s, {}).get(s_name),
                    "advantage": round(float(adv[k]), 2), "excess": round(float(point[k]), 2),
                    "ci": [round(float(lo[k]), 2), round(float(hi[k]), 2)],
                    "flag": bool(lo[k] > 0 and point[k] >= 5)})
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    flags = [c for c in res["cells"] if c["flag"]]
    print(f"{len(res['cells'])} cells, {len(flags)} flagged (excess >= 5 points, 95% interval above 0)")
    for c in sorted(flags, key=lambda c: -c["excess"]):
        print(f"  {c['system']:26s} {c['job']:10s} {c['source']:30s} excess {c['excess']:6.1f} "
              f"[{c['ci'][0]:.1f}, {c['ci'][1]:.1f}] rows {c['rows']}" + (f"  KNOWN: {c['known_training']}" if c["known_training"] else ""))
    print("known-training cells:")
    for c in res["cells"]:
        if c["known_training"]:
            print(f"  {c['system']:26s} {c['job']:10s} {c['source']:30s} excess {c['excess']:6.1f} [{c['ci'][0]:.1f}, {c['ci'][1]:.1f}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
