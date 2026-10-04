"""Edition 2 rows whose text a benchmarked vendor has published.

A row a vendor printed in its own docs (a cookbook example, a model card, a feature page) may have been tuned on or
checked by that vendor, so it cannot be a fair test row. This scans every edition 2 row (tune, test and the unpublished
slice, licence-withheld text included) against every vendor file tracked in the repository and reports each match by
row id and vendor file. It never prints row text.

A match is either
- a shared run of WINDOW (8) consecutive words, after normalisation (NFKC, lower case, apostrophes dropped, HTML tags and
  entities and JSON/Python escapes read as spaces, words are runs of letters and digits), or
- a normalised exact match: a row text of MIN_EXACT (4) to WINDOW - 1 words equal to a whole unit of a vendor file (a
  line, a table cell, a quoted string, a JSON string value). Texts under MIN_EXACT words ("yes", "ok", "hi") are in
  every file and say nothing about where a row came from, so they are not matched.

    uv run python -m goldrails_dataset.vendor_overlap                # report (JSON, ids and files only)
    uv run python -m goldrails_dataset.vendor_overlap --exclude      # append test and unpublished matches to EXCLUDED

``--exclude`` writes the reason ``text published by a benchmarked vendor (<vendor>)``. A public id goes to
``dataset/edition2/EXCLUDED.jsonl``; an id from a suite's private candidates goes to the git-ignored
``<suite>/private/EXCLUDED.jsonl``. Tune rows are not excluded, only flagged in the report. An id already excluded is
left alone. ``dataset/edition2/VENDOR-OVERLAP.md`` records the result (public ids only).
"""
from __future__ import annotations

import argparse
import fnmatch
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

from . import e2_local

WINDOW = 8
MIN_EXACT = 4
REASON = "text published by a benchmarked vendor ({vendor})"

# (glob over tracked paths, vendor). First match wins. Vendor material only: the vendor's own docs, or our files that
# copy them (a "Source: docs.typesafe.ai" primer, a feature inventory "verified against the live AWS docs"). Community
# projects, video transcripts and social-media research are not vendor-published and are not listed here; the
# ``--others`` scan reports them without excluding anything.
VENDOR_FILES = (
    ("docs/reference/typesafe/**", "TypeSafe"),
    ("docs/typesafe-reference/**", "TypeSafe"),
    ("docs/research/early-2026-09-18/01-jev-primer.md", "TypeSafe"),
    ("docs/research/early-2026-09-18/08-sources.md", "TypeSafe"),
    ("docs/09-bedrock-guardrails-feature-inventory.md", "AWS (Bedrock Guardrails)"),
    ("docs/research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md", "AWS (Bedrock Guardrails)"),
    ("docs/research/early-2026-09-18/05-bedrock-guardrails-mapping.md", "AWS (Bedrock Guardrails)"),
    ("docs/archive/2026-09-28-bedrock-feature-map/**", "AWS (Bedrock Guardrails)"),
    ("research_notes/Profanity and denied topic references/bedrock_equivalence.md", "AWS (Bedrock Guardrails)"),
)

# Tracked paths the --others scan skips: the dataset and run outputs hold the rows themselves (that is
# e2_local.tracked_leaks' job), and lockfiles and binaries hold no prose.
OTHER_SKIP = ("dataset/**", "benchmark/results/**", "benchmark/runs/**", "benchmark/history/**", "**/*.lock",
              "**/pnpm-lock.yaml", "**/*.png", "**/*.jpg", "**/*.svg", "**/*.pdf", "**/*.ipynb")

_TAG = re.compile(r"<[^>]+>")
_ESC = re.compile(r"\\(?:u[0-9a-fA-F]{4}|[^u])")
_APOS = re.compile(r"['’‘ʼ`]")
_WORDS = re.compile(r"[^\W_]+")
_QUOTED = re.compile(r"\"([^\"\n]{1,2000})\"|'([^'\n]{1,2000})'|`([^`\n]{1,2000})`|“([^”\n]{1,2000})”")


def _glob(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-2])
    return fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path, pattern.replace("**/", ""))


def vendor_of(path: str) -> str | None:
    for pattern, vendor in VENDOR_FILES:
        if _glob(path, pattern):
            return vendor
    return None


def words(text: str) -> list:
    """The normalised words of a text."""
    t = unicodedata.normalize("NFKC", text or "")
    t = _APOS.sub("", t.lower())
    return _WORDS.findall(t)


def _file_text(path: Path) -> tuple[str, list]:
    """(the file read as plain text, its units: lines, table cells, quoted strings and JSON string values)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    units = []
    if path.suffix in (".json", ".jsonl"):
        def walk(x):
            if isinstance(x, str):
                units.append(x)
            elif isinstance(x, dict):
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        for chunk in ([raw] if path.suffix == ".json" else raw.split("\n")):
            try:
                walk(json.loads(chunk))
            except json.JSONDecodeError:
                pass
    text = raw
    if path.suffix in (".html", ".htm", ".svg", ".xml"):
        text = html.unescape(_TAG.sub(" ", raw))
    text = _ESC.sub(" ", text)
    lines = text.split("\n")
    units += lines
    units += [c for line in lines if line.lstrip().startswith("|") for c in line.split("|")]
    units += [next(g for g in m.groups() if g is not None) for m in _QUOTED.finditer(text)]
    return text, units


def vendor_index(repo: Path = e2_local.REPO, files: list | None = None, others: bool = False) -> dict:
    """{path: {"vendor", "windows": set of WINDOW-word tuples, "units": set of normalised short units}} for each tracked
    vendor file (or, with ``others``, each other tracked text file outside OTHER_SKIP)."""
    out = {}
    for f in (e2_local.tracked_files(repo) if files is None else files):
        v = vendor_of(f)
        if others:
            if v is not None or any(_glob(f, p) for p in OTHER_SKIP):
                continue
            v = "not a vendor file"
        elif v is None:
            continue
        p = Path(repo) / f
        try:
            if b"\0" in p.read_bytes()[:8192]:
                continue
            text, units = _file_text(p)
        except OSError:
            continue
        w = words(text)
        out[f] = {"vendor": v,
                  "windows": {tuple(w[i:i + WINDOW]) for i in range(len(w) - WINDOW + 1)},
                  "units": {tuple(u) for u in (words(x) for x in units) if MIN_EXACT <= len(u) < WINDOW}}
    return out


def row_texts(c: dict) -> list:
    """Every text a candidate row holds: text, source passage, query and each context turn."""
    return [t for t in e2_local._field_texts(*e2_local._fields(c)) if isinstance(t, str) and t.strip()]


def match_row(c: dict, index: dict) -> list:
    """[{"file", "vendor", "kind", "windows", "coverage"}] for each vendor file the row's text appears in. ``kind`` is
    ``window`` (shared WINDOW-word runs; ``windows`` counts them and ``coverage`` is the share of the row's own windows
    that the file holds, 1.0 for a verbatim copy) or ``exact`` (a short text equal to a unit of the file)."""
    wins, shorts = set(), set()
    for t in row_texts(c):
        w = words(t)
        if len(w) >= WINDOW:
            wins |= {tuple(w[i:i + WINDOW]) for i in range(len(w) - WINDOW + 1)}
        elif len(w) >= MIN_EXACT:
            shorts.add(tuple(w))
    out = []
    for f, ix in sorted(index.items()):
        n = len(wins & ix["windows"])
        if n:
            out.append({"file": f, "vendor": ix["vendor"], "kind": "window", "windows": n,
                        "coverage": round(n / len(wins), 3)})
        elif shorts & ix["units"]:
            out.append({"file": f, "vendor": ix["vendor"], "kind": "exact", "windows": 0, "coverage": 1.0})
    return out


def row_split(c: dict) -> str:
    return c.get("proposed_split") or c.get("split") or "?"


def scan(root: Path = e2_local.E2, repo: Path = e2_local.REPO, index: dict | None = None,
         suites=e2_local.SUITES) -> list:
    """Every match across all edition 2 rows: [{"id", "suite", "split", "public", "matches"}]. ``split`` is tune, test
    or private (the unpublished slice); ``public`` says whether the id is in the tracked candidates file."""
    index = vendor_index(repo) if index is None else index
    out = []
    for s in suites:
        if not (e2_local.suite_dir(s, root) / "candidates.jsonl").exists():
            continue
        public = {c["id"] for c in e2_local.candidates(s, root, private=False, text=False)}
        for c in e2_local.candidates(s, root):
            m = match_row(c, index)
            if m:
                out.append({"id": c["id"], "suite": s, "split": row_split(c), "public": c["id"] in public,
                            "matches": m})
    return out


def _excluded_ids(path: Path) -> set:
    return {d["id"] for d in e2_local._jsonl(path)}


def apply_exclusions(found: list, root: Path = e2_local.E2) -> dict:
    """Append each test or unpublished match to the right EXCLUDED.jsonl. Tune rows stay (flagged in the report).
    Returns {"public": [ids added], "private": {suite: n added}}."""
    added = {"public": [], "private": {}}
    pub_path = Path(root) / "EXCLUDED.jsonl"
    for r in found:
        if r["split"] == "tune":
            continue
        vendors = sorted({m["vendor"] for m in r["matches"]})
        entry = {"id": r["id"], "reason": REASON.format(vendor=", ".join(vendors))}
        path = pub_path if r["public"] else e2_local.private_dir(r["suite"], Path(root)) / "EXCLUDED.jsonl"
        if r["id"] in _excluded_ids(path):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if r["public"]:
            added["public"].append(r["id"])
        else:
            added["private"][r["suite"]] = added["private"].get(r["suite"], 0) + 1
    return added


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--exclude", action="store_true", help="append test and unpublished matches to EXCLUDED.jsonl")
    ap.add_argument("--others", action="store_true",
                    help="also scan every other tracked text file (report only, nothing excluded)")
    ap.add_argument("--public-only", action="store_true", help="print public ids only (safe to paste)")
    a = ap.parse_args(argv)
    index = vendor_index()
    found = scan(index=index)
    rep = {"window": WINDOW, "vendor_files": {f: ix["vendor"] for f, ix in sorted(index.items())},
           "matches": [r for r in found if r["public"] or not a.public_only],
           "private_matches": sum(1 for r in found if not r["public"])}
    if a.others:
        other = vendor_index(others=True)
        rep["other_files_scanned"] = len(other)
        rep["other_matches"] = [r for r in scan(index=other) if r["public"] or not a.public_only]
    if a.exclude:
        rep["excluded"] = apply_exclusions(found)
    json.dump(rep, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
