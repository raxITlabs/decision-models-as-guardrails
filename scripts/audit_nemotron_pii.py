"""Quality audit of NVIDIA Nemotron-PII as a replacement PII source. Read-only on the source; no model calls.

    uv run python scripts/audit_nemotron_pii.py mechanical     # whole test split: spans, formats, duplication
    uv run python scripts/audit_nemotron_pii.py sample         # stratified ~100-document blind-review sample
    uv run python scripts/audit_nemotron_pii.py negatives      # candidate negatives for blind verification
    uv run python scripts/audit_nemotron_pii.py compare        # blind-review verdicts against the source spans

Uses only NVIDIA's test split at a pinned revision, so models trained on the train split have not seen these rows.
Writes to dataset/frozen/reviews/nemotron-pii-audit-2026-09-28/. Review inputs (id and text only) go to the
scratch directory given by --scratch, never next to the labels.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "dataset" / "frozen" / "reviews" / "nemotron-pii-audit-2026-09-28"
REPO_ID, REVISION = "nvidia/Nemotron-PII", "b70ffaf5ff39e079776134c5bf4381f00a9fd1ed"

# Nemotron label -> our supported entity type (the frozen v2-f5-pii definitions). "ssn" maps only on US-locale rows.
MAP = {"first_name": "NAME", "last_name": "NAME", "email": "EMAIL", "phone_number": "PHONE", "fax_number": "PHONE",
       "street_address": "ADDRESS", "city": "ADDRESS", "state": "ADDRESS", "postcode": "ADDRESS",
       "user_name": "USERNAME", "password": "PASSWORD", "ipv4": "IP_ADDRESS", "ipv6": "IP_ADDRESS",
       "ssn": "US_SOCIAL_SECURITY_NUMBER"}
TYPES = ["NAME", "EMAIL", "PHONE", "ADDRESS", "USERNAME", "PASSWORD", "IP_ADDRESS", "DRIVER_ID", "US_SOCIAL_SECURITY_NUMBER"]
FORMAT = {"EMAIL": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
          "IP_ADDRESS": re.compile(r"^(\d{1,3}(\.\d{1,3}){3}|[0-9A-Fa-f:]*:[0-9A-Fa-f:.]*)$"),
          "US_SOCIAL_SECURITY_NUMBER": re.compile(r"^\d{3}[- ]?\d{2}[- ]?\d{4}$"),
          "PHONE": re.compile(r"\d.*\d.*\d.*\d.*\d.*\d.*\d")}


def load() -> list:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    p = hf_hub_download(REPO_ID, "data/test-00000-of-00001.parquet", repo_type="dataset", revision=REVISION)
    rows = pq.read_table(p).to_pylist()
    for r in rows:
        r["spans"] = ast.literal_eval(r["spans"]) if isinstance(r["spans"], str) else r["spans"]
        r["key"] = f"{r['uid']}:{r['locale']}"
    return rows


IPV4 = re.compile(r"(?<![\d.])(\d{1,3}\.){3}\d{1,3}(?![\d.])")


def negative_screen(r: dict) -> str | None:
    """Why an unannotated document still cannot be a negative (the audit found these gaps), or None."""
    labels = {s["label"] for s in r["spans"]}
    if "ssn" in labels:
        return "ssn label on an international row"
    if IPV4.search(r["text"]):
        return "IPv4 address in the text, e.g. inside a URL"
    return None


def mapped(r: dict) -> dict:
    out = defaultdict(list)
    for s in r["spans"]:
        t = MAP.get(s["label"])
        if t == "US_SOCIAL_SECURITY_NUMBER" and r["locale"] != "us":
            t = None
        if t:
            out[t].append(r["text"][s["start"]:s["end"]])
    return out


def mechanical(rows: list) -> dict:
    bounds = fmt = checked = 0
    fmt_bad = Counter()
    for r in rows:
        for s in r["spans"]:
            if not (0 <= s["start"] < s["end"] <= len(r["text"])):
                bounds += 1
        for t, vals in mapped(r).items():
            for v in vals:
                if t in FORMAT:
                    checked += 1
                    if not FORMAT[t].search(v.strip()):
                        fmt += 1
                        fmt_bad[t] += 1
    texts = Counter(r["text"] for r in rows)
    norm = Counter(" ".join(r["text"].lower().split()) for r in rows)
    value_docs = defaultdict(set)
    for r in rows:
        for t in ("EMAIL", "US_SOCIAL_SECURITY_NUMBER", "PHONE"):
            for v in mapped(r).get(t, []):
                value_docs[(t, v.strip().lower())].add(r["uid"])
    shared = {t: sum(1 for (tt, _), u in value_docs.items() if tt == t and len(u) > 1) for t in ("EMAIL", "US_SOCIAL_SECURITY_NUMBER", "PHONE")}
    docs_by_type = Counter(t for r in rows for t in mapped(r))
    return {"rows": len(rows), "documents": len({r["uid"] for r in rows}),
            "structure": "each uid has one us and one intl row, same domain and document type, different text; treated as one group",
            "spans_out_of_bounds": bounds, "format_checked": checked, "format_failures": fmt, "format_failures_by_type": dict(fmt_bad),
            "exact_duplicate_texts": sum(n - 1 for n in texts.values() if n > 1),
            "normalised_duplicate_texts": sum(n - 1 for n in norm.values() if n > 1),
            "values_shared_across_documents": shared,
            "documents_with_type": {t: docs_by_type.get(t, 0) for t in TYPES},
            "unsupported_types": [t for t in TYPES if not docs_by_type.get(t)],
            "documents_without_any_mapped_type": sum(1 for r in rows if not mapped(r))}


def sample(rows: list, n: int, seed: int) -> list:
    """About n documents: every supported type, both locales, both formats; one row per uid."""
    rng = random.Random(seed)
    pools = defaultdict(list)
    for r in rows:
        for t in mapped(r):
            pools[(t, r["locale"], r["document_format"])].append(r)
    picked, uids = [], set()
    cells = sorted(pools)
    while len(picked) < n and cells:
        for c in list(cells):
            cand = [r for r in pools[c] if r["uid"] not in uids]
            if not cand:
                cells.remove(c)
                continue
            r = rng.choice(cand)
            picked.append(r)
            uids.add(r["uid"])
            if len(picked) >= n:
                break
    return picked


def write_inputs(rows: list, scratch: Path, name: str, batches: int) -> None:
    scratch.mkdir(parents=True, exist_ok=True)
    size = -(-len(rows) // batches)
    for i in range(batches):
        with (scratch / f"{name}-{i + 1}.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows[i * size:(i + 1) * size]:
                fh.write(json.dumps({"id": r["key"], "text": r["text"]}, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["mechanical", "sample", "negatives", "compare"])
    ap.add_argument("--scratch", type=Path, default=REPO / ".scratch" / "nemotron")
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load()
    if a.step == "mechanical":
        res = {"source": REPO_ID, "revision": REVISION, "split": "test", **mechanical(rows)}
        (OUT / "mechanical.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(res, indent=1))
    elif a.step == "sample":
        s = sample(rows, a.n, 20260928)
        (OUT / "sample.json").write_text(json.dumps({"seed": 20260928, "keys": [r["key"] for r in s],
                                                     "cells": Counter(f"{t}|{r['locale']}|{r['document_format']}" for r in s for t in mapped(r))},
                                                    indent=1) + "\n", encoding="utf-8")
        write_inputs(s, a.scratch, "sample", 4)
        print(len(s), "documents;", Counter(r["locale"] for r in s), Counter(r["document_format"] for r in s),
              Counter(t for r in s for t in mapped(r)))
    elif a.step == "negatives":
        rng = random.Random(20260929)
        cand = [r for r in rows if not mapped(r)]
        seen = set()
        pick = []
        for r in rng.sample(cand, len(cand)):
            if r["uid"] not in seen:
                pick.append(r)
                seen.add(r["uid"])
            if len(pick) >= a.n:
                break
        (OUT / "negatives-sample.json").write_text(json.dumps({"seed": 20260929, "candidates": len(cand),
                                                               "keys": [r["key"] for r in pick]}, indent=1) + "\n", encoding="utf-8")
        write_inputs(pick, a.scratch, "negatives", 2)
        print(len(pick), "candidate negatives from", len(cand))
    else:
        by = {r["key"]: r for r in rows}
        verdicts = [json.loads(x) for p in sorted(OUT.glob("review-*.jsonl")) for x in p.open(encoding="utf-8")]
        res = Counter()
        missing = Counter()
        for v in verdicts:
            src = set(mapped(by[v["id"]]))
            rev = set(v.get("entities") or [])
            res["documents"] += 1
            for t in rev - src:
                missing[t] += 1
            res["documents_with_unannotated_type"] += bool(rev - src)
            res["documents_with_annotation_reviewer_did_not_find"] += bool(src - rev)
        out = {"summary": dict(res), "unannotated_by_type": dict(missing)}
        (OUT / "compare.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
