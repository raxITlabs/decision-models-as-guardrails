"""A later run's copy of the bias audit, with provenance. No model calls; computes no score.

    GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/bias_audit_copy.py

``benchmark/results/first-benchmark/bias-audit.json`` audits the bias rows: sources, adaptations, row counts, evidence
and flags. A later run on the same subsets tests the same rows, so the audit carries over, but only after checking that
the run's bias ledgers hold exactly the first run's bias row ids (B1, B2, BBQ, discrim-eval). A few sentences in the
audit cite outcomes (Bedrock's misses on B1, zero B2 flips, a flip-rate interval); those describe the first benchmark,
not this run, and the copy marks each one with ``outcomes_from: first-benchmark``. The run's own outcomes are in its
bias.json and bias-parts.json.

Writes ``benchmark/results/<GOLDRAILS_RUN>/bias-audit.json``. Refuses to write into the first run's directory, and
refuses when the row ids differ.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402

CTX = RC.current()
SOURCE_RES = RC.RESULTS / RC.FIRST
SOURCE = SOURCE_RES / "bias-audit.json"
LEDGERS = ("test-bias.jsonl", "ext-test-bias.jsonl")
# Phrases that mark a sentence citing a first-run outcome rather than a property of the rows.
OUTCOME_MARKERS = ("misses", "zero flips", "flip-rate interval")


def bias_ids(res: Path) -> dict:
    """{part: sorted row ids} from a run's bias ledgers."""
    out: dict = {}
    for name in LEDGERS:
        p = res / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            st = d.get("subtask") or ""
            part = ("b1" if st.startswith("b1") else "b2" if st.startswith("b2")
                    else "b3:" + (d.get("source") or "unknown"))
            out.setdefault(part, set()).add(d["id"])
    return {k: sorted(v) for k, v in sorted(out.items())}


def outcome_statements(doc: dict) -> list[tuple[list, str]]:
    """(path, text) for every string field in tasks that cites a first-run outcome."""
    hits = []

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, path + [k])
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, path + [i])
        elif isinstance(x, str) and any(m in x for m in OUTCOME_MARKERS):
            hits.append((path, x))
    walk(doc.get("tasks", []), ["tasks"])
    return hits


def build(source_doc: dict, source_sha256: str, run: str, first_ids: dict, run_ids: dict) -> dict:
    doc = copy.deepcopy(source_doc)
    stmts = outcome_statements(doc)
    for path, _ in stmts:   # mark the object that holds the sentence
        obj = doc
        for k in path[:-1]:
            obj = obj[k]
        if isinstance(obj, dict):
            obj["outcomes_from"] = RC.FIRST
    doc["run_copy"] = {
        "run": run,
        "copied_from": RC.rel(SOURCE),
        "source_sha256": source_sha256,
        "copied_by": "benchmark/runs/bias_audit_copy.py",
        "bias_row_ids": {k: {"rows": len(v), "same_ids_as_first_benchmark": v == first_ids.get(k)}
                         for k, v in run_ids.items()},
        "outcome_statements": [{"path": "/".join(str(p) for p in path), "text": text} for path, text in stmts],
        "note": (f"Row descriptions, counts, evidence and flags describe the bias test rows, which are the same ids in "
                 f"{run} as in the first benchmark (checked above). Statements marked outcomes_from: first-benchmark "
                 f"cite the first benchmark's results, not {run}'s; {run}'s own outcomes are in its bias.json and "
                 "bias-parts.json. The 'reads' list names the files the audit was written from."),
    }
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default=str(CTX.results), help="results directory (default benchmark/results/<GOLDRAILS_RUN>)")
    ap.add_argument("--out", help="output file (default <res>/bias-audit.json)")
    a = ap.parse_args(argv)
    res = Path(a.res)
    out = Path(a.out) if a.out else res / "bias-audit.json"
    if out.resolve() == SOURCE.resolve() or RC.is_protected(out):
        raise SystemExit(f"{RC.rel(out)} is in the first run's records; set GOLDRAILS_RUN to the run to copy the audit into")
    first_ids, run_ids = bias_ids(SOURCE_RES), bias_ids(res)
    if not run_ids:
        raise SystemExit(f"no bias ledgers in {RC.rel(res)} ({', '.join(LEDGERS)}); run the test stages first")
    if run_ids != first_ids:
        diff = {k: (len(first_ids.get(k, [])), len(run_ids.get(k, []))) for k in set(first_ids) | set(run_ids)
                if first_ids.get(k) != run_ids.get(k)}
        raise SystemExit(f"bias row ids differ from the first benchmark (first, this run): {diff}; the audit's row "
                         "descriptions would not apply")
    doc = build(json.loads(SOURCE.read_text(encoding="utf-8")), hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                res.name, first_ids, run_ids)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{sum(len(v) for v in run_ids.values())} bias rows match; {len(doc['run_copy']['outcome_statements'])} "
          f"outcome statements marked; wrote {RC.rel(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
