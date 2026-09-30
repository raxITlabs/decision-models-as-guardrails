"""Rebuild allocated GPU serving time per self-hosted arm from a ledger's own attempt times.

    uv run python benchmark/runs/serving_from_ledger.py --out serving.json test.jsonl test-rerun.jsonl

Systems ran one after another within each suite, so each arm (system, question set, configuration, dataset) owns a
window of whole-VM time, charged at share 1.0. VM time outside every window (boot, weight loading, idle while the
hosted APIs ran) is overhead, reported in the project-spend reconciliation and not in cost per 1,000.

Window bounds:
- Ledgers from 23 September 2026 onward record ``started_at`` and ``ended_at`` per attempt to the millisecond; the
  window is the earliest start to the latest end.
- Older ledgers record only ``at``, the completion time to the second. The window is reconstructed as the earliest
  (completion minus that attempt's latency) to the latest completion. Such windows carry ``reconstructed: true`` and
  ``precision_s: 1``.

Windows in one ledger must not overlap, since each is charged the whole VM. With one-second completion stamps,
neighbouring arms can overlap by under a second; the overlap is split at its midpoint and recorded in
``trimmed_seconds``. An overlap of more than ``--max-overlap`` seconds means the arms did not run one at a time, and
the script stops rather than charge the VM twice.

``--hardware`` names the tariff key (default the us-east4 on-demand L4 machine the first run used). ``--zone`` records
the zone the VM actually ran in; when it lies outside us-east4 while the key prices us-east4, every record says the GPU
cost uses the us-east4 tariff. Without ``--zone`` the records are exactly as before.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_context import DEFAULT_HARDWARE as HARDWARE, zone_fields  # noqa: E402

GPU = {"kev-0-8b", "kev-4b", "kev-9b", "open-jev-2b", "laya"}


def ts(s: str) -> float:
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in s else "%Y-%m-%dT%H:%M:%SZ"
    return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def windows(path: Path) -> list[dict]:
    spans = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d["system"] not in GPU:
            continue
        ds = d.get("dataset") or {}
        key = (d["system"], d["question_set"], d.get("config_hash"), ds.get("sha256"))
        w = spans.setdefault(key, {"start": None, "end": None, "rows": 0, "attempts": 0, "reconstructed": False,
                                   "feature": ds.get("feature")})
        w["rows"] += 1
        for a in d.get("attempts") or []:
            if a.get("started_at") and a.get("ended_at"):
                s, e = ts(a["started_at"]), ts(a["ended_at"])
            elif a.get("at"):
                e = ts(a["at"])
                s = e - (a.get("latency_s") or 0.0)
                w["reconstructed"] = True
            else:
                continue
            w["attempts"] += 1
            w["start"] = s if w["start"] is None else min(w["start"], s)
            w["end"] = e if w["end"] is None else max(w["end"], e)
    return [dict(key=k, **v) for k, v in spans.items() if v["start"] is not None]


def exclusive(ws: list[dict], max_overlap: float) -> list[dict]:
    ws = sorted(ws, key=lambda w: w["start"])
    for w in ws:
        w["trimmed_seconds"] = 0.0
    for a, b in zip(ws, ws[1:]):
        over = a["end"] - b["start"]
        if over <= 0:
            continue
        if over > max_overlap:
            raise SystemExit(f"{a['key'][:2]} and {b['key'][:2]} overlap by {over:.1f} s: they did not run one at a "
                             "time, so whole-VM windows would charge the VM twice")
        mid = b["start"] + over / 2
        a["trimmed_seconds"] += a["end"] - mid
        b["trimmed_seconds"] += mid - b["start"]
        a["end"], b["start"] = mid, mid
    return ws


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ledgers", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-overlap", type=float, default=2.0)
    ap.add_argument("--hardware", default=HARDWARE, help=f"tariff hardware key (default {HARDWARE})")
    ap.add_argument("--zone", help="zone the VM ran in, recorded on every window (default: not recorded)")
    a = ap.parse_args(argv)
    out = []
    for p in map(Path, a.ledgers):
        for w in exclusive(windows(p), a.max_overlap):
            system, qs, cfg, dsha = w["key"]
            out.append({"stage": p.name, "system": system, "question_set": qs, "config_hash": cfg,
                        "dataset_sha256": dsha, "feature": w["feature"], "hardware": a.hardware,
                        **zone_fields(a.hardware, a.zone),
                        "started": iso(w["start"]), "ended": iso(w["end"]),
                        "allocated_seconds": round(w["end"] - w["start"], 1), "share": 1.0,
                        "evaluations": w["rows"], "attempts": w["attempts"],
                        "trimmed_seconds": round(w["trimmed_seconds"], 2),
                        "reconstructed": w["reconstructed"], "precision_s": 1 if w["reconstructed"] else 0.001,
                        "method": ("reconstructed: earliest completion minus attempt latency to latest completion; "
                                   "sub-second overlaps split at the midpoint") if w["reconstructed"]
                                  else "measured: earliest attempt start to latest attempt end"})
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    total = sum(x["allocated_seconds"] for x in out)
    print(f"{len(out)} windows, {total:.0f} s allocated, {sum(x['trimmed_seconds'] for x in out):.1f} s trimmed; wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
