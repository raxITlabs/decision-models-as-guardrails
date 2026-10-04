"""Edition 2 rows whose text is in a benchmarked model's published training or development data.

Two models we benchmark publish the recipe they were trained with: Strands Decider 2B (github.com/strands-labs/
strands-decider, ``data/sources.md`` and ``src/strands_decider/data/recipes.py``) and pplx-decider-v1-27b
(huggingface.co/perplexity-ai/pplx-decider-v1-27b, ``source/src/autojev/data.py`` at 5117a6c). A row whose text sits
in a split such a recipe trains or tunes on may have been seen by that model, so it cannot be a fair test row for it.

The check streams each upstream split named in ``CHECKS`` (no full download; the datasets library's streaming mode),
normalises every text field (casefold, whitespace collapsed, at least MIN_CHARS characters) and keeps an 8-byte
BLAKE2b digest of each. Every text field of an edition 2 row (the text, each context turn, a grounding source or
query) is normalised the same way and looked up. A match means the row's text is in that split, not that it was in
the model's actual sample, so counts are an upper bound. Digests are cached in the git-ignored ``CACHE`` folder.

    uv run python -m goldrails_dataset.model_overlap hashes            # stream the upstream splits into the cache
    uv run python -m goldrails_dataset.model_overlap report            # scan the build -> MODEL-TRAINING-OVERLAP.json
    uv run python -m goldrails_dataset.model_overlap exclude           # test and unpublished candidate matches -> EXCLUDED
    uv run python -m goldrails_dataset.model_overlap purge             # drop every excluded id from the suite files

``exclude`` covers the splits in ``EXCLUDE_ROLES`` (pplx-decider-v1-27b's training and development splits) and
writes the reason ``REASON``. As with vendor_overlap, a public id goes to ``dataset/edition2/EXCLUDED.jsonl`` and an
unpublished-slice id to the git-ignored ``<suite>/private/EXCLUDED.jsonl``. Dev rows stay and are flagged in the
report. ``report`` writes public ids to ``dataset/edition2/MODEL-TRAINING-OVERLAP.json`` and unpublished-slice ids to
the git-ignored ``build/private/MODEL-TRAINING-OVERLAP.unpublished.json``. Builders call ``seen_by_model`` to keep a
new row out when any of its texts is in any split in ``CHECKS``. Nothing here prints row text.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from . import e2_local

E2 = e2_local.E2
CACHE = E2 / ".model-overlap-cache"          # git-ignored: digests of upstream texts, rebuilt by ``hashes``
REPORT = E2 / "MODEL-TRAINING-OVERLAP.json"
PRIVATE_REPORT = E2 / "build" / "private" / "MODEL-TRAINING-OVERLAP.unpublished.json"
MIN_CHARS = 20
REASON = "text in pplx-decider-v1-27b training or development data"

SOURCES = {
    "strands-decider-2b": "github.com/strands-labs/strands-decider data/sources.md and src/strands_decider/data/recipes.py "
                          "(civil_comments train, 6,000 sampled with seed 0; PubMedQA pqa_labeled, all 1,000; "
                          "measuring-hate-speech held out, not trained)",
    "pplx-decider-v1-27b": "huggingface.co/perplexity-ai/pplx-decider-v1-27b source/src/autojev/data.py at 5117a6c "
                           "(civil_comments train 8,000 and validation for development; Aegis 2.0 train 6,000 and "
                           "validation for development; PubMedQA quota 0, evaluation only)",
}
AEGIS_REV = "d86bb8bedff51d25ac834ab7838f1cc61acb7a2c"
CC_REV = "f2970eb3a55777454c94069077cc8d9b5866312d"
# (model, upstream, config, split, revision, text fields, role)
CHECKS = (
    ("strands-decider-2b", "google/civil_comments", None, "train", None, ("text",), "train (6,000 sampled)"),
    ("strands-decider-2b", "qiaojin/PubMedQA", "pqa_labeled", "train", None, ("question",), "train (all 1,000)"),
    ("pplx-decider-v1-27b", "google/civil_comments", None, "train", CC_REV, ("text",), "train (8,000 sampled)"),
    ("pplx-decider-v1-27b", "google/civil_comments", None, "validation", CC_REV, ("text",), "development"),
    ("pplx-decider-v1-27b", "nvidia/Aegis-AI-Content-Safety-Dataset-2.0", None, "train", AEGIS_REV,
     ("prompt", "response"), "train (6,000 sampled)"),
    ("pplx-decider-v1-27b", "nvidia/Aegis-AI-Content-Safety-Dataset-2.0", None, "validation", AEGIS_REV,
     ("prompt", "response"), "development"),
)
# The splits whose test and unpublished matches are taken out of edition 2 (owner request, 5 October 2026).
EXCLUDE_ROLES = {("pplx-decider-v1-27b", "google/civil_comments", "validation"),
                 ("pplx-decider-v1-27b", "nvidia/Aegis-AI-Content-Safety-Dataset-2.0", "train"),
                 ("pplx-decider-v1-27b", "nvidia/Aegis-AI-Content-Safety-Dataset-2.0", "validation")}


def norm(s) -> str:
    return " ".join(str(s).casefold().split())


def digest(s) -> bytes | None:
    n = norm(s)
    if len(n) < MIN_CHARS:
        return None
    return hashlib.blake2b(n.encode("utf-8"), digest_size=8).digest()


def _key(check) -> tuple:
    _, repo, cfg, split, rev, fields, _ = check
    return repo, cfg, split, rev, fields


def _cache_file(check) -> Path:
    repo, cfg, split, rev, fields = _key(check)
    name = f"{repo.replace('/', '__')}.{cfg or 'default'}.{split}.{(rev or 'main')[:12]}.{'+'.join(fields)}.bin"
    return CACHE / name


def _stream(check) -> tuple[set, int]:
    from datasets import load_dataset
    repo, cfg, split, rev, fields = _key(check)
    got, n = set(), 0
    for row in load_dataset(repo, cfg, split=split, revision=rev, streaming=True):
        n += 1
        for f in fields:
            v = row.get(f)
            if isinstance(v, str):
                d = digest(v)
                if d:
                    got.add(d)
    return got, n


def upstream_digests(check, refresh: bool = False) -> tuple[set, int]:
    """(digests, upstream rows scanned) of one upstream split, from the cache or streamed into it."""
    path = _cache_file(check)
    meta = path.with_suffix(".json")
    if path.exists() and meta.exists() and not refresh:
        raw = path.read_bytes()
        return {raw[i:i + 8] for i in range(0, len(raw), 8)}, json.loads(meta.read_text())["rows"]
    got, n = _stream(check)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(sorted(got)))
    meta.write_text(json.dumps({"check": list(_key(check)), "rows": n, "digests": len(got)}))
    return got, n


_INDEX: dict | None = None


def index(refresh: bool = False) -> dict:
    """{check key: (digests, rows scanned)} for every split in CHECKS (shared between checks of the same split)."""
    global _INDEX
    if _INDEX is None or refresh:
        _INDEX = {}
        for c in CHECKS:
            if _key(c) not in _INDEX:
                _INDEX[_key(c)] = upstream_digests(c, refresh)
    return _INDEX


def texts_of(obj) -> list:
    """Every string of at least MIN_CHARS normalised characters in a row's text fields (walks dicts and lists)."""
    out = []

    def walk(o):
        if isinstance(o, str):
            if len(norm(o)) >= MIN_CHARS:
                out.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return out


def matched_checks(texts, idx: dict | None = None) -> list:
    """The CHECKS entries (model, upstream, split) whose split holds any of ``texts``."""
    idx = idx or index()
    ds = {d for d in (digest(t) for t in texts) if d}
    return [(c[0], c[1], c[3]) for c in CHECKS if ds & idx[_key(c)][0]]


def seen_by_model(texts, idx: dict | None = None) -> bool:
    """True when any text is in any split of any published recipe in CHECKS: a builder must not add such a row."""
    idx = idx or index()
    ds = {d for d in (digest(t) for t in texts) if d}
    return any(ds & digests for digests, _ in idx.values())


def row_texts(c: dict) -> list:
    """The text fields of a candidate row (``state``, and ``record.state`` for denied topics)."""
    return texts_of([c.get("state"), (c.get("record") or {}).get("state")])


# --- the built splits: the report ------------------------------------------------------------------------------------

def built_rows(build: Path = E2 / "build") -> dict:
    """id -> (feature, split, source, texts) of every built row; split ``unpublished`` for build/private/. Text of
    licence-withheld rows is restored from each suite's local cache."""
    local = {}
    for f in sorted(E2.glob("*/local/text.jsonl")):
        for e in e2_local._jsonl(f):
            local[e["id"]] = e.get("fields") or {}
    out = {}
    for f in sorted(build.glob("F*.jsonl")) + sorted((build / "private").glob("F*.jsonl")):
        split = "unpublished" if f.parent.name == "private" else f.name.split(".")[-2]
        for r in e2_local._jsonl(f):
            out[r["id"]] = (r["feature"], split, r["provenance"]["source"],
                            texts_of([local.get(r["id"]), r.get("state")]))
    return out


def report(build: Path = E2 / "build") -> tuple[dict, list]:
    """(public report, unpublished-slice ids per check). Public ids are listed, unpublished ones only counted."""
    rows = built_rows(build)
    idx = index()
    by_digest = collections.defaultdict(set)
    for rid, (_, _, _, texts) in rows.items():
        for t in texts:
            by_digest[digest(t)].add(rid)
    checks, private = [], []
    for c in CHECKS:
        model, repo, cfg, split, rev, _, role = c
        digests, n = idx[_key(c)]
        hits = set()
        for d in digests & by_digest.keys():
            hits |= by_digest[d]
        by = collections.Counter((rows[i][0], rows[i][1], rows[i][2]) for i in hits)
        pub = sorted(i for i in hits if rows[i][1] != "unpublished")
        prv = sorted(i for i in hits if rows[i][1] == "unpublished")
        checks.append({"model": model, "upstream": repo, "config": cfg, "split": split, "revision": rev, "role": role,
                       "upstream_rows_scanned": n, "error": None,
                       "test_and_unpublished_matches_excluded": (model, repo, split) in EXCLUDE_ROLES,
                       "matched_by_feature_split_source": [{"feature": a, "split": b, "source": s, "rows": k}
                                                           for (a, b, s), k in sorted(by.items())],
                       "matched_test_rows": sum(rows[i][1] == "test" for i in hits),
                       "matched_dev_rows": sum(rows[i][1] == "dev" for i in hits),
                       "matched_unpublished_rows": len(prv),
                       "matched_public_row_ids": pub})
        private.append({"model": model, "upstream": repo, "split": split, "unpublished_row_ids": prv})
    pub_excl = sum(1 for d in e2_local._jsonl(E2 / "EXCLUDED.jsonl") if d["reason"] == REASON)
    all_excl = sum(1 for r in _all_excluded().values() if r == REASON)
    rep = {"generated": date.today().isoformat(),
           "command": "uv run python -m goldrails_dataset.model_overlap report",
           "method": "exact match after casefolding and collapsing whitespace, on every text field of each edition 2 "
                     f"row (min {MIN_CHARS} characters), against the whole upstream split each model's published "
                     "recipe draws from. A match means the row's text is in that split, not that it was in the model's "
                     "actual sample, so counts are an upper bound.",
           "sources": SOURCES,
           "policy": "test and unpublished rows whose text is in pplx-decider-v1-27b's training or development splits "
                     f"are excluded from edition 2 (EXCLUDED.jsonl, reason '{REASON}'); dev rows stay and are "
                     "listed here",
           "excluded_rows": {"public": pub_excl, "unpublished": all_excl - pub_excl},
           "checks": checks}
    return rep, private


def _all_excluded() -> dict:
    from .edition2 import excluded
    return excluded()


def write_report(build: Path = E2 / "build") -> dict:
    rep, private = report(build)
    REPORT.write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    PRIVATE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_REPORT.write_text(json.dumps(private, indent=1) + "\n", encoding="utf-8")
    return rep


# --- the candidates: exclusions --------------------------------------------------------------------------------------

def candidate_matches(suites=e2_local.SUITES) -> list:
    """[{id, suite, split, public, checks}] for every candidate row (dev, test, unpublished; owner exclusions left
    out) whose text is in an EXCLUDE_ROLES split."""
    from .edition2 import excluded
    drop, idx, out = excluded(), index(), []
    for s in suites:
        for c in e2_local.candidates(s):
            if c["id"] in drop:
                continue
            hit = [m for m in matched_checks(row_texts(c), idx) if m in EXCLUDE_ROLES]
            if hit:
                out.append({"id": c["id"], "suite": s, "split": c["proposed_split"],
                            "public": c["proposed_split"] != "private", "checks": hit})
    return out


def apply_exclusions(found: list, root: Path = E2) -> dict:
    """Append each test or unpublished match to the right EXCLUDED.jsonl; dev rows stay (flagged in the report)."""
    added = {"public": collections.Counter(), "private": collections.Counter()}
    for r in found:
        if r["split"] == "dev":
            continue
        path = (Path(root) / "EXCLUDED.jsonl") if r["public"] else \
            e2_local.private_dir(r["suite"], Path(root)) / "EXCLUDED.jsonl"
        if r["id"] in {d["id"] for d in e2_local._jsonl(path)}:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": r["id"], "reason": REASON}, ensure_ascii=False) + "\n")
        added["public" if r["public"] else "private"][r["suite"]] += 1
    return {k: dict(v) for k, v in added.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("hashes", "report", "exclude", "purge"))
    ap.add_argument("--refresh", action="store_true", help="stream the upstream splits again")
    a = ap.parse_args(argv)
    if a.cmd == "hashes":
        idx = index(refresh=a.refresh)
        print(json.dumps({"/".join(str(x) for x in k[:3]): {"rows": n, "digests": len(d)}
                          for k, (d, n) in idx.items()}, indent=1))
    elif a.cmd == "purge":
        print(json.dumps(e2_local.purge(set(_all_excluded())), indent=1))
    elif a.cmd == "exclude":
        found = candidate_matches()
        tally = collections.Counter(f"{r['suite']}|{r['split']}" for r in found)
        print(json.dumps({"matches": dict(sorted(tally.items())), "added": apply_exclusions(found)}, indent=1))
    else:
        rep = write_report()
        print(json.dumps([{k: c[k] for k in ("model", "upstream", "split", "matched_test_rows", "matched_dev_rows",
                                             "matched_unpublished_rows")} for c in rep["checks"]], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
