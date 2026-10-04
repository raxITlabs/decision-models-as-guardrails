"""Test-set integrity: no test row may overlap a row anyone has already looked at.

Edition 2 (docs/benchmark/26-edition-2-plan.md, Integrity) makes this a check the freeze runs, not a rule people keep.
A test row overlaps a reference row (examined, smoke, pilot, diagnostic or tuning) when any of these match:

- id: the same row id;
- text: the same sha256 of the row's text after lowercasing and collapsing whitespace (a copy under another id or
  source);
- group: the same split group (``goldrails_dataset.build.group_of``: an Aegis conversation, a RAGTruth document, a
  JailbreakBench behaviour), so a sibling of an examined row is caught too;
- near: a near-duplicate body (see below), so a reworded copy or a template filled with a different behaviour is
  caught even when the two rows have different ids, hashes and groups.

A row's body for the near-duplicate rule is every long text the judge sees, not only ``state.text``: the text, each
prior turn in ``state.context``, the grounding ``state.source`` and ``state.query``, and any other string state field
(``row_fields``). Each field is shingled on its own (no shingle spans two fields) and the row's shingle set is the
union (``row_shingles``). So two HarmBench contextual behaviours that quote one context paragraph, or two grounding
replies about one source passage, are near-duplicates even when their short ``text`` differs. The text-hash kind
stays on ``state.text``.

Near-duplicate rule. Each text is lowercased, split into word tokens (runs of letters and digits, so punctuation and
spacing do not count) and turned into its set of word 3-grams (a text of one or two words is one shingle). Two texts
are near-duplicates when either

- their shingle Jaccard similarity is at least ``NEAR_THRESHOLD`` (0.8), or
- the smaller text has at least ``NEAR_MIN_SHINGLES`` (10) shingles and at least ``NEAR_THRESHOLD`` of them occur in
  the other text (containment), which catches a long shared body with a different instruction around it: HarmBench
  contextual behaviours that quote one context paragraph, Mosscap screenplay prompts with a changed last line, a DAN
  prompt with a request appended. The size floor keeps a short phrase that happens to sit inside a long text from
  matching.

0.8 was set by looking at the edition 2 candidates (dataset/edition2): every pair at or above it on either measure was a
copy with edits; pairs between 0.5 and 0.8 are mostly paraphrases or shared jailbreak templates with a different body.
The search is exact (prefix filtering on rare shingles, then the true overlap), not a MinHash estimate.

References may be full rows (Record objects or their dicts) or bare ids, such as the ids in a smoke ledger. A bare id
is checked by id only, unless ``pool`` holds its row, in which case its text, group and near duplicates are checked
as well.

    report = overlap.check(test_rows, {"examined": overlap.repo_examined_ids(), "tune": tune_rows},
                           pool=all_rows, strict=True)      # raises OverlapError on any overlap

    uv run python -m goldrails_bench.overlap --test 'dir/*.test.jsonl' --reference tune='dir/*.tune.jsonl'
    uv run python -m goldrails_bench.overlap --missing-examined [--append]

The second form lists ids that appear in a smoke, pilot or diagnostic ledger or a notebook output but not in
dataset/frozen/examined-ids.txt; ``--append`` appends them (the list is append-only, so its history stays).

Pure functions plus local file reads. No network, model or cloud calls.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Iterable

from .freeze import FreezeError

REPO = Path(__file__).resolve().parents[2]
EXAMINED = REPO / "dataset" / "frozen" / "examined-ids.txt"
RESULTS = REPO / "benchmark" / "results"
# Ledgers of runs that looked at rows outside a frozen test run: smoke tests, pilots, diagnostics.
LEDGER_GLOBS = ("smoke-*.jsonl", "pilot-*.jsonl", "diagnostics/**/*.jsonl")
# Other outputs of those runs, and notebook outputs, scanned for anything shaped like a row id.
TEXT_GLOBS = ("benchmark/results/smoke-*", "benchmark/results/pilot-*", "benchmark/results/diagnostics/**/*",
              "benchmark/results/leaderboard-smoke.json", "benchmark/notebooks/*.ipynb", "dataset/notebooks/*.ipynb")
TEXT_SUFFIXES = (".jsonl", ".json", ".md", ".csv", ".ipynb", ".txt")
ID_PATTERN = re.compile(r"\bf\d+-[a-z0-9_]+-[0-9a-f]{10}\b")
KINDS = ("id", "text", "group", "near")
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"\w+")
NEAR_THRESHOLD = 0.8        # Jaccard, or containment of the smaller text, on word 3-gram sets
NEAR_MIN_SHINGLES = 10      # containment alone counts only when the smaller text has this many shingles
SHINGLE_WORDS = 3


class OverlapError(FreezeError):
    """A test row overlaps an examined, smoke, pilot, diagnostic or tuning row (strict mode)."""

    def __init__(self, report: "OverlapReport"):
        self.report = report
        super().__init__(report.summary())


# --- row access --------------------------------------------------------------------------------------------------

def normalise_text(s: str | None) -> str:
    """Lowercase, whitespace collapsed to single spaces, ends stripped."""
    return _WS.sub(" ", (s or "").lower()).strip()


def text_hash(s: str | None) -> str | None:
    """sha256 of the normalised text, or None for empty text (an empty text matches nothing)."""
    n = normalise_text(s)
    return hashlib.sha256(n.encode("utf-8")).hexdigest() if n else None


def _get(r, key, default=None):
    return r.get(key, default) if isinstance(r, dict) else getattr(r, key, default)


def row_id(r) -> str:
    return r if isinstance(r, str) else _get(r, "id")


def row_text(r) -> str | None:
    """The judged text: ``state.text`` of a record (or of its dict), else a top-level ``text``."""
    if isinstance(r, str):
        return None
    st = _get(r, "state")
    if st is not None:
        return _get(st, "text")
    return _get(r, "text")


# State fields that are not text the judge reads (structured or bookkeeping); every other string field is.
_NON_TEXT_STATE = ("role",)


def _turn_text(t) -> str | None:
    if isinstance(t, str):
        return t
    if isinstance(t, dict):
        v = t.get("text") if t.get("text") is not None else t.get("content")
        return v if isinstance(v, str) else (json.dumps(v, sort_keys=True) if v is not None else None)
    return _get(t, "text")


def row_fields(r) -> list:
    """Every text the judge sees for a row, ``state.text`` first: the text, each turn of ``state.context``, then every
    other string state field (``source``, ``query``, ...) and a ``tool_call`` as JSON. A bare id has none; a row with no
    ``state`` gives its top-level ``text``."""
    if isinstance(r, str):
        return []
    st = _get(r, "state")
    if st is None:
        t = _get(r, "text")
        return [t] if t else []
    out = [_get(st, "text")]
    for turn in _get(st, "context") or ():
        out.append(_turn_text(turn))
    d = st if isinstance(st, dict) else getattr(st, "__dict__", {})
    for k in sorted(d):
        if k in ("text", "context") or k in _NON_TEXT_STATE:
            continue
        v = d[k]
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, (dict, list)) and v:
            out.append(json.dumps(v, sort_keys=True, ensure_ascii=False))
    return [x for x in out if x and x.strip()]


def row_group(r) -> str | None:
    """The split group, computed by the dataset build's own rule so the two never disagree."""
    if isinstance(r, str):
        return None
    from goldrails_dataset.build import group_of
    prov = _get(r, "provenance") or {}
    view = SimpleNamespace(id=_get(r, "id"), group=_get(r, "group"),
                           provenance=SimpleNamespace(source=_get(prov, "source"),
                                                      source_id=str(_get(prov, "source_id") or "")))
    return group_of(view)


# --- near duplicates ---------------------------------------------------------------------------------------------

def shingles(s: str | None, n: int = SHINGLE_WORDS) -> frozenset:
    """Word n-grams of the lowercased text; a text shorter than n words is one shingle; empty text has none."""
    words = _TOKEN.findall((s or "").lower())
    if not words:
        return frozenset()
    if len(words) < n:
        return frozenset([" ".join(words)])
    return frozenset(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def row_shingles(r, n: int = SHINGLE_WORDS) -> frozenset:
    """The union of the word n-gram sets of every field in ``row_fields``, each field shingled on its own."""
    out = set()
    for f in row_fields(r):
        out |= shingles(f, n)
    return frozenset(out)


def similarity(a: frozenset, b: frozenset) -> tuple:
    """(jaccard, containment of the smaller set) of two shingle sets."""
    if not a or not b:
        return 0.0, 0.0
    k = len(a & b)
    return k / (len(a) + len(b) - k), k / min(len(a), len(b))


def is_near_duplicate(a: frozenset, b: frozenset, threshold: float = NEAR_THRESHOLD,
                      min_shingles: int = NEAR_MIN_SHINGLES) -> bool:
    jac, con = similarity(a, b)
    return jac >= threshold or (min(len(a), len(b)) >= min_shingles and con >= threshold)


def _prefix_len(n: int, threshold: float) -> int:
    # A pair that is near-duplicate shares at least ceil(threshold * min size) shingles (both rules imply it), so the
    # smaller set's first n - ceil(threshold * n) + 1 shingles, in any fixed order, hold at least one shared shingle.
    return n - math.ceil(threshold * n - 1e-9) + 1


def near_duplicate_pairs(left: list, right: list | None = None, threshold: float = NEAR_THRESHOLD,
                         min_shingles: int = NEAR_MIN_SHINGLES) -> list:
    """Every near-duplicate pair between two lists of shingle sets, as (i, j, jaccard, containment) sorted by (i, j).
    With ``right`` None, pairs within ``left`` (i < j). Exact: candidates come from the rarest shingles of each set
    (prefix filtering), then each candidate's true similarity is computed."""
    self_join = right is None
    right = left if self_join else right
    freq = defaultdict(int)
    for s in (left if self_join else list(left) + list(right)):
        for g in s:
            freq[g] += 1
    order = lambda s: sorted(s, key=lambda g: (freq[g], g))
    full, pref = defaultdict(list), defaultdict(list)
    for j, s in enumerate(right):
        if not s:
            continue
        for g in s:
            full[g].append(j)
        for g in order(s)[:_prefix_len(len(s), threshold)]:
            pref[g].append(j)
    out = []
    for i, s in enumerate(left):
        if not s:
            continue
        cand = set()
        for g in order(s)[:_prefix_len(len(s), threshold)]:
            cand.update(full.get(g, ()))          # this set is the smaller one
        for g in s:
            cand.update(pref.get(g, ()))          # the other set is the smaller one
        for j in sorted(cand):
            if self_join and j <= i:
                continue
            if is_near_duplicate(s, right[j], threshold, min_shingles):
                jac, con = similarity(s, right[j])
                out.append((i, j, round(jac, 4), round(con, 4)))
    return out


# --- the check ---------------------------------------------------------------------------------------------------

@dataclass
class OverlapReport:
    """Every overlap found, one entry per (test row, kind, matched reference row)."""
    test_rows: int
    reference_rows: dict = field(default_factory=dict)      # role -> count of references given
    overlaps: list = field(default_factory=list)             # {kind, test_id, reference_id, role, key}

    @property
    def ok(self) -> bool:
        return not self.overlaps

    def by_kind(self) -> dict:
        out = {k: [] for k in KINDS}
        for o in self.overlaps:
            out[o["kind"]].append(o)
        return out

    def test_ids(self) -> list:
        return sorted({o["test_id"] for o in self.overlaps})

    def summary(self) -> str:
        if self.ok:
            refs = ", ".join(f"{k} {v}" for k, v in sorted(self.reference_rows.items()))
            return f"no overlap: {self.test_rows} test rows against {refs or 'no references'}"
        bk = self.by_kind()
        parts = ", ".join(f"{len({o['test_id'] for o in bk[k]})} by {k}" for k in KINDS if bk[k])
        head = ", ".join(self.test_ids()[:10]) + (" ..." if len(self.test_ids()) > 10 else "")
        return f"{len(self.test_ids())} of {self.test_rows} test rows overlap ({parts}): {head}"

    def to_dict(self) -> dict:
        bk = self.by_kind()
        return {"ok": self.ok, "test_rows": self.test_rows, "reference_rows": dict(self.reference_rows),
                "overlapping_test_rows": len(self.test_ids()),
                "counts": {k: len({o["test_id"] for o in bk[k]}) for k in KINDS},
                "overlaps": list(self.overlaps)}


def _references(references) -> dict:
    if references is None:
        return {}
    if isinstance(references, dict):
        return {role: list(rows) for role, rows in references.items()}
    return {"reference": list(references)}


def check(test_rows: Iterable, references, *, pool: Iterable = (), strict: bool = False,
          near: float | None = NEAR_THRESHOLD) -> OverlapReport:
    """Compare ``test_rows`` with ``references`` (a dict role -> rows or bare ids, or one iterable of them) by id,
    normalised-text hash, group and near-duplicate text (``near`` is the threshold; None turns that kind off).
    ``pool`` supplies rows for bare reference ids so their text, group and near duplicates are checked too. Returns
    the report; with ``strict`` raises OverlapError when anything overlaps."""
    tests = list(test_rows)
    refs = _references(references)
    by_id = {row_id(p): p for p in pool or ()}
    idx = {k: defaultdict(list) for k in KINDS}      # kind -> key -> [(reference_id, role)]
    near_refs = []                                   # (reference_id, role, text hash, shingles)
    for role, rows in refs.items():
        for r in rows:
            rid = row_id(r)
            body = by_id.get(rid, r) if isinstance(r, str) else r
            idx["id"][rid].append((rid, role))
            if near is not None and not isinstance(body, str):
                near_refs.append((rid, role, text_hash(row_text(body)), row_shingles(body)))
            h = text_hash(row_text(body))
            if h:
                idx["text"][h].append((rid, role))
            g = row_group(body)
            if g:
                idx["group"][g].append((rid, role))
    out, seen = [], set()
    for t in tests:
        tid = row_id(t)
        keys = {"id": tid, "text": text_hash(row_text(t)), "group": row_group(t)}
        for kind in ("id", "text", "group"):
            key = keys[kind]
            if not key:
                continue
            for rid, role in idx[kind].get(key, ()):
                if kind != "id" and rid == tid and (tid, "id", rid, role) in seen:
                    continue      # already reported by id; text and group add nothing for the same row
                sig = (tid, kind, rid, role)
                if sig in seen:
                    continue
                seen.add(sig)
                out.append({"kind": kind, "test_id": tid, "reference_id": rid, "role": role,
                            "key": key if kind != "id" else tid})
    if near is not None and near_refs:
        # an exact copy (same id or same text hash) is already reported; near lists the edited copies. Shingles cover
        # every field the judge sees (row_shingles), so a shared context or source counts, not only the text.
        t_sh = [row_shingles(t) for t in tests]
        for i, j, jac, con in near_duplicate_pairs(t_sh, [n[3] for n in near_refs], threshold=near):
            tid, (rid, role, h, _) = row_id(tests[i]), near_refs[j]
            if rid == tid or (h and h == text_hash(row_text(tests[i]))):
                continue
            sig = (tid, "near", rid, role)
            if sig in seen:
                continue
            seen.add(sig)
            out.append({"kind": "near", "test_id": tid, "reference_id": rid, "role": role,
                        "key": f"jaccard={jac} containment={con}", "jaccard": jac, "containment": con})
    report = OverlapReport(len(tests), {role: len(rows) for role, rows in refs.items()}, out)
    if strict and not report.ok:
        raise OverlapError(report)
    return report


# --- what the repository says was examined -----------------------------------------------------------------------

def read_examined(path=EXAMINED) -> set:
    p = Path(path)
    if not p.exists():
        return set()
    return {l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def ledger_ids(root=RESULTS, globs=LEDGER_GLOBS) -> dict:
    """id -> sorted ledger paths (relative to ``root``) for every record with an id in the smoke, pilot and
    diagnostic ledgers."""
    root = Path(root)
    out = defaultdict(set)
    for g in globs:
        for f in sorted(root.glob(g)):
            if not f.is_file():
                continue
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rid = json.loads(line).get("id")
                if rid:
                    out[rid].add(f.relative_to(root).as_posix())
    return {k: sorted(v) for k, v in out.items()}


def scanned_ids(root=REPO, globs=TEXT_GLOBS) -> dict:
    """id -> sorted paths for anything shaped like a row id in smoke, pilot and diagnostic outputs and notebooks."""
    root = Path(root)
    out = defaultdict(set)
    for g in globs:
        for f in sorted(glob.glob(str(root / g), recursive=True)):
            p = Path(f)
            if not p.is_file() or p.suffix not in TEXT_SUFFIXES:
                continue
            for rid in ID_PATTERN.findall(p.read_text(encoding="utf-8", errors="replace")):
                out[rid].add(p.relative_to(root).as_posix())
    return {k: sorted(v) for k, v in out.items()}


def seen_ids(root=REPO) -> dict:
    """id -> where it was seen, across ledgers and scanned outputs."""
    root = Path(root)
    out = defaultdict(set)
    for rid, paths in ledger_ids(root / "benchmark" / "results").items():
        out[rid].update(f"benchmark/results/{p}" for p in paths)
    for rid, paths in scanned_ids(root).items():
        out[rid].update(paths)
    return {k: sorted(v) for k, v in out.items()}


def repo_examined_ids(root=REPO, cleared: set | None = None) -> set:
    """Every id that must never be a test row: examined-ids.txt less documented clearances, plus every id seen in a
    smoke, pilot or diagnostic ledger or output or a notebook (a ledger row was sent to a model, so no clearance
    covers it)."""
    root = Path(root)
    if cleared is None:
        from goldrails_dataset.build import cleared_ids
        cleared = cleared_ids() if root.resolve() == REPO.resolve() else set()
    listed = read_examined(root / "dataset" / "frozen" / "examined-ids.txt") - set(cleared)
    return listed | set(seen_ids(root))


def missing_examined(root=REPO) -> dict:
    """id -> where seen, for ids seen in a ledger, output or notebook but absent from examined-ids.txt."""
    root = Path(root)
    listed = read_examined(root / "dataset" / "frozen" / "examined-ids.txt")
    return {k: v for k, v in sorted(seen_ids(root).items()) if k not in listed}


def append_examined(ids: Iterable[str], note: str, path=EXAMINED) -> int:
    """Append ids not already listed, under a dated comment. Never rewrites existing lines. Returns how many."""
    p = Path(path)
    listed = read_examined(p)
    new = sorted(set(ids) - listed)
    if not new:
        return 0
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    stamp = time.strftime("%Y-%m-%d", time.gmtime())
    p.write_text(text + f"# {stamp}: {note}\n" + "".join(f"{i}\n" for i in new), encoding="utf-8")
    return len(new)


# --- command line ------------------------------------------------------------------------------------------------

def _read_rows(pattern: str) -> list:
    from goldrails_dataset.records import read_jsonl
    rows = []
    for f in sorted(glob.glob(pattern, recursive=True)):
        rows.extend(read_jsonl(f))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--test", help="glob of test jsonl files")
    ap.add_argument("--reference", action="append", default=[], metavar="ROLE=GLOB",
                    help="reference rows, such as tune='dir/*.tune.jsonl'; repeatable")
    ap.add_argument("--pool", action="append", default=[], metavar="GLOB",
                    help="rows to look up bare examined ids in, for their text and group")
    ap.add_argument("--no-examined", action="store_true", help="leave out the repository's examined ids")
    ap.add_argument("--missing-examined", action="store_true",
                    help="list ids seen in smoke, pilot or diagnostic outputs but not in examined-ids.txt")
    ap.add_argument("--append", action="store_true", help="with --missing-examined: append them")
    a = ap.parse_args(argv)
    if a.missing_examined:
        miss = missing_examined()
        for rid, where in miss.items():
            print(rid, " ".join(where))
        print(f"{len(miss)} ids missing from {EXAMINED.relative_to(REPO)}", file=sys.stderr)
        if a.append and miss:
            n = append_examined(miss, "ids found in smoke, pilot and diagnostic ledgers and outputs "
                                      "(goldrails_bench.overlap --missing-examined --append)")
            print(f"appended {n}", file=sys.stderr)
        return 0
    if not a.test:
        ap.error("--test is required unless --missing-examined is given")
    refs = {}
    for spec in a.reference:
        role, _, pattern = spec.partition("=")
        refs.setdefault(role, []).extend(_read_rows(pattern))
    if not a.no_examined:
        refs["examined"] = sorted(repo_examined_ids())
    pool = [r for g in a.pool for r in _read_rows(g)]
    report = check(_read_rows(a.test), refs, pool=pool)
    print(json.dumps(report.to_dict(), indent=1, sort_keys=True))
    print(report.summary(), file=sys.stderr)
    return 0 if report.ok else 1


__all__ = ["OverlapError", "OverlapReport", "normalise_text", "text_hash", "row_id", "row_text", "row_group",
           "row_fields", "row_shingles",
           "NEAR_THRESHOLD", "NEAR_MIN_SHINGLES", "shingles", "similarity", "is_near_duplicate", "near_duplicate_pairs",
           "check", "read_examined", "ledger_ids", "scanned_ids", "seen_ids", "repo_examined_ids",
           "missing_examined", "append_examined"]


if __name__ == "__main__":
    raise SystemExit(main())
