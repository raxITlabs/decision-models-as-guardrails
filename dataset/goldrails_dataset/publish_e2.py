"""Stage edition 2 for Hugging Face and rebuild its canonical rows locally. Nothing here uploads.

    uv run python -m goldrails_dataset.publish_e2 stage                 # dataset/publish/release-<VERSION>/, gates, load check
    uv run python -m goldrails_dataset.publish_e2 gates [--data DIR]    # the privacy gates on a staged folder
    uv run python -m goldrails_dataset.publish_e2 parity [--data DIR]   # staged rows + local parts == the build
    uv run python -m goldrails_dataset.publish_e2 materialize --data DIR --out DIR

``stage`` reads the edition 2 build (``dataset/edition2/build/F*.{dev,test}.jsonl``, checked against its manifest)
and writes one config per suite with ``dev`` and ``test`` splits in the Hugging Face layout
(``data/<config>/<split>.jsonl``), the card and the side files. What it leaves out:

- the unpublished slice (``build/private/``, ruling 15). Its rows never enter the staged folder;
- every row whose id appears in any git-ignored ``*/private/`` file (``local_only_ids``). The build makes a few of them
  public rows (a private candidate that the near-duplicate rule moved to test, or a public row whose text repeats an
  unpublished candidate's). They stay on this machine and are attached locally, like the slice;
- the text of every row whose source licence is not cleared (``e2_local.text_cleared``, ruling 10). Those rows ship
  id, labels, spans and ``canonical_row_hash``; the state's text fields and any other field that quotes a withheld
  text are null and listed in ``withheld.paths``;
- rows in ``EXCLUDED.jsonl`` (the build already drops them; a gate checks again).

``gates`` fails the command when the staged folder breaks any of these. It reuses ``e2_local.leak_needles`` (every
unpublished-slice id and text, every withheld text, every held-out authored case) and scans every staged file the
way ``e2_local.tracked_leaks`` scans tracked files.

``materialize`` is the reverse, for the runners: it reads a staged or downloaded folder, puts withheld text back from
the local text cache (``<suite>/local/text.jsonl``, rebuilt from the original sources by ``e2_local rehydrate``), adds
the local-only rows and the unpublished slice from the local build, and writes ``F<n>.<split>.jsonl`` files
byte-identical to the build's. Every rebuilt row must match its ``canonical_row_hash`` and every file the hashes
recorded in ``canonical.json``, or it stops.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from . import e2_local

BRAND = "decision-models-as-guardrails"
PUBLIC_REPO = "https://github.com/raxITlabs/decision-models-as-guardrails"
HF_DATASET = "https://huggingface.co/datasets/raxITLabs/decision-models-as-guardrails"
INTENDED_USE = (f"{BRAND} is a non-commercial research benchmark by raxIT Labs. It compares guardrail systems and "
                "publishes the results for research, with credit to every upstream source. It is not a commercial product "
                "or deployment. Publishing it changes no source's licence: each row stays under its source's own terms, "
                "listed in SOURCES.md.")
ROOT = Path(__file__).resolve().parents[1]          # dataset/
REPO = ROOT.parent
E2 = ROOT / "edition2"
BUILD = E2 / "build"
VERSION = "1.0.0"   # owner ruling 29: the first public release; no earlier version is named in public text
STAGE = ROOT / "publish" / f"release-{VERSION}"
HUB_REPO = "raxITLabs/decision-models-as-guardrails"
CONFIGS = {"F1": "content", "F2": "prompt_attacks", "F3": "denied_topics", "F4": "word_filters",
           "F5": "sensitive_information", "F6": "grounding"}
SUITE_OF = {"F1": "content", "F2": "prompt_attacks", "F3": "denied_topics", "F4": "word_filters", "F5": "pii",
            "F6": "grounding"}
SPLITS = ("dev", "test")
CANONICAL = "canonical.json"
PUBLISHED_ONLY = ("redistribution", "canonical_row_hash", "withheld")
WITHHELD_REASON = ("licence: the source's licence review is not finished, so its text does not ship here; rebuild it "
                   "locally, see RECONSTRUCT.md")
DISCLOSURES = E2 / "card-disclosures.md"
# Public files describe this dataset as a first release: no internal history, owner process or open placeholders.
PUBLIC_TEXT_BANNED = re.compile(r"\bedition\b|release candidate|\bTODO\b|\bruling\b|\bowner\b|\btune split\b|"
                                r"\bv1\.\d\b|\bprovisional\b|\blatency\b", re.I)
PLACEHOLDER = re.compile(r"\[[^\]\n]*\](?!\()")   # an unfilled [bracket] in Markdown, not a [link](url)


class PublishError(RuntimeError):
    pass


# --- row hashing and stripping ---------------------------------------------------------------------------------------

def canonical_hash(d: dict) -> str:
    """sha256 of the row as ``records.canonical`` sees it: published-only keys and ``provenance.imported_at`` left
    out, keys sorted, non-ASCII kept."""
    d = {k: v for k, v in d.items() if k not in PUBLISHED_ONLY}
    d["provenance"] = {k: v for k, v in d["provenance"].items() if k != "imported_at"}
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _get(d, path):
    for k in path:
        d = d[k]
    return d


def _set(d, path, value):
    for k in path[:-1]:
        d = d[k]
    d[path[-1]] = value


def _state_texts(d: dict) -> list:
    return e2_local._field_texts({k: d["state"].get(k) for k in e2_local.STRIP})


def strip_row(d: dict, also: tuple = ((), ())) -> dict:
    """An ids-only copy of build row ``d``: the state's text fields and any other string field that quotes a
    withheld text (``e2_local._quoting_paths``, with ``also`` holding windows of every other withheld text) are null,
    and their paths are listed in ``withheld``. The caller adds ``canonical_row_hash`` of the full row."""
    paths = [["state", k] for k in e2_local.STRIP if d["state"].get(k) not in (None, [], "")]
    paths += e2_local._quoting_paths(d, _state_texts(d), also)
    out = copy.deepcopy(d)
    for p in paths:
        _set(out, p, None)
    out["withheld"] = {"paths": paths, "sha256": e2_local.fields_sha256([_get(d, p) for p in paths]),
                       "reason": WITHHELD_REASON}
    out["redistribution"] = "ids_only"
    return out


# --- what stays on this machine ---------------------------------------------------------------------------------------

def _ids_in(path: Path) -> set:
    out = set()
    try:
        lines = Path(path).read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError):
        return out
    for line in lines:
        if line.strip():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(d, dict) and isinstance(d.get("id"), str):
                out.add(d["id"])
    return out


def local_only_ids(root: Path = E2) -> set:
    """Ids of rows whose record lives in a git-ignored ``private/`` folder: each suite's ``private/candidates.jsonl``
    (the unpublished candidates, and public rows whose text repeats one of theirs) and every row file of
    ``build/private/`` (the unpublished slice, its disputed and dropped rows). Such a row never enters the staged
    folder, whatever split the build gave it. Owner-only label files under ``private/`` (first labels, second labels,
    review packets) name public rows too; they do not make a row local."""
    root = Path(root)
    ids = set()
    for p in sorted(root.glob("*/private/candidates.jsonl")) + sorted((root / "build" / "private").glob("*.jsonl")):
        ids |= _ids_in(p)
    return ids


def excluded_ids(root: Path = E2) -> set:
    from .edition2 import excluded
    return set(excluded(Path(root)))


def _read_rows(path: Path) -> list:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").split("\n") if line.strip()]


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(*args) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def build_manifest(build: Path = BUILD) -> dict:
    """The build manifest, after checking every listed file against its dataset hash."""
    from .records import dataset_hash, read_jsonl
    man = json.loads((Path(build) / "manifest.json").read_text(encoding="utf-8"))
    for f in man["files"]:
        got = dataset_hash(read_jsonl(Path(build) / f["path"]))
        if got != f["sha256"]:
            raise PublishError(f"{f['path']} hashes to {got[:12]}, the build manifest says {f['sha256'][:12]}: rebuild "
                               "(uv run python -m goldrails_dataset.edition2)")
    return man


# --- staging ----------------------------------------------------------------------------------------------------------

def stage(out: Path = STAGE, build: Path = BUILD, root: Path = E2, check_load: bool = True,
          code_ref: str | None = None) -> dict:
    """Write the staged folder and run the gates. Returns the staging report; ``report["problems"]`` is empty when
    every gate and the load check pass."""
    out, build, root = Path(out), Path(build), Path(root)
    pol = e2_local.policy()
    man = build_manifest(build)
    keep_out = local_only_ids(root)
    excl = excluded_ids(root)
    rows_by_file = {f["path"]: _read_rows(build / f["path"]) for f in man["files"]}
    cleared = lambda r: e2_local.text_cleared(r["provenance"]["source"], pol)    # noqa: E731
    # windows of every text that must not appear in a published field: withheld texts, the unpublished slice's
    # texts and held-out authored cases
    texts = [t for rows in rows_by_file.values() for r in rows if not cleared(r) for t in _state_texts(r)]
    for p in sorted((build / "private").glob("F*.test.jsonl")):
        texts += [t for r in _read_rows(p) for t in _state_texts(r)]
    try:
        texts += list(e2_local.held_out_texts(root).values())
    except e2_local.LocalDataMissing:
        pass
    also = e2_local._quote_windows(texts)

    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    files, counts = [], {}
    for f in sorted(man["files"], key=lambda f: (f["feature"], SPLITS.index(f["split"]))):
        config, split = CONFIGS[f["feature"]], f["split"]
        staged, c = [], Counter()
        for r in rows_by_file[f["path"]]:
            c["build"] += 1
            if r["id"] in keep_out:
                c["local_only"] += 1
                continue
            if r["id"] in excl:
                raise PublishError(f"{r['id']} is in EXCLUDED.jsonl but in the build: rebuild")
            if cleared(r):
                row = copy.deepcopy(r)
                row["redistribution"] = "text"
            else:
                row = strip_row(r, also)
            row["canonical_row_hash"] = canonical_hash(r)
            c["text" if row["redistribution"] == "text" else "ids_only"] += 1
            staged.append(row)
        p = out / "data" / config / f"{split}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in staged), encoding="utf-8")
        files.append({"feature": f["feature"], "config": config, "split": split, "path": f"data/{config}/{split}.jsonl",
                      "n": len(staged), "sha256": _sha(p), "rows_text": c["text"], "rows_ids_only": c["ids_only"],
                      "rows_local_only": c["local_only"], "build_file": f["path"], "build_rows": c["build"],
                      "build_dataset_sha256": f["sha256"], "build_file_sha256": _sha(build / f["path"])})
        counts[f"{config}/{split}"] = dict(c)

    commit = _git("rev-parse", "HEAD")
    code_ref = code_ref or commit
    canonical = {"version": VERSION, "code": {"repository": PUBLIC_REPO, "ref": code_ref},
                 "build_manifest_sha256": _sha(build / "manifest.json"),
                 "rule": "rows ship in build order; a row's canonical_row_hash is sha256 of the full row "
                         "(records.canonical); build_dataset_sha256 is records.dataset_hash of the full build file "
                         "and build_file_sha256 its bytes, local-only rows included",
                 "unpublished_slice_rows": man.get("private_slice", {}).get("rows"),
                 "files": files}
    (out / CANONICAL).write_text(json.dumps(canonical, indent=1) + "\n", encoding="utf-8")
    _write_docs(out, man, files, pol, code_ref, root, build)

    gate = gates(out, root, build)
    problems = [f"{g}: {p}" for g, ps in gate.items() for p in ps]
    load = load_check(out, files) if check_load else []
    problems += load
    wording = public_text_problems(out)
    problems += [f"public_text: {w}" for w in wording]
    report = {"version": VERSION, "code_commit": commit,
              "staged": str(out.relative_to(REPO)) if out.is_relative_to(REPO) else str(out), "counts": counts,
              "totals": {k: sum(c.get(k, 0) for c in counts.values()) for k in ("build", "text", "ids_only", "local_only")},
              "unpublished_slice_rows": canonical["unpublished_slice_rows"],
              "gates": {g: ("pass" if not ps else ps[:20]) for g, ps in gate.items()},
              "load_check": "skipped" if not check_load else ("pass" if not load else load),
              "public_text": "pass" if not wording else wording[:40],
              "problems": problems}
    (out / "staging-report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def load_check(out: Path, files: list) -> list:
    """Load every config of the staged folder with the ``datasets`` library, as the Hub would, into a fresh cache
    (a reused cache can return an earlier staging's rows), and compare the split sizes with the staged files."""
    from datasets import load_dataset
    problems = []
    with tempfile.TemporaryDirectory() as cache:
        for config in dict.fromkeys(f["config"] for f in files):
            want = {f["split"]: f["n"] for f in files if f["config"] == config}
            try:
                ds = load_dataset(str(out), name=config, cache_dir=cache)
                got = {k: len(v) for k, v in ds.items()}
                if got != want:
                    problems.append(f"{config}: loaded {got}, staged {want}")
            except Exception as e:  # noqa: BLE001
                problems.append(f"{config}: {type(e).__name__}: {str(e)[:200]}")
    return problems


# --- gates ------------------------------------------------------------------------------------------------------------

GATES = ("no_private_or_local_paths", "no_unpublished_slice", "no_withheld_text", "no_excluded_rows")


def _staged_rows(data: Path) -> dict:
    return {p: _read_rows(p) for p in sorted((Path(data) / "data").glob("*/*.jsonl"))}


def gates(data: Path = STAGE, root: Path = E2, build: Path = BUILD, needles: list | None = None) -> dict:
    """{gate: [problem]} for a staged folder; every list is empty when it may be uploaded.

    - no_private_or_local_paths: no staged path has a ``private`` or ``local`` part, and no staged row's id is in a
      git-ignored ``*/private/`` file (``local_only_ids``);
    - no_unpublished_slice: no unpublished-slice id, no unpublished-slice text and no held-out authored text in any
      staged file (``e2_local.leak_needles``, scanned like ``tracked_leaks``);
    - no_withheld_text: a row from a source whose text is not cleared ships ``ids_only`` with every text field null,
      no staged file carries a withheld text, and a ``text`` row's source is cleared;
    - no_excluded_rows: no staged row is excluded, and the staged EXCLUDED.jsonl names public exclusions only."""
    data, root, build = Path(data), Path(root), Path(build)
    pol = e2_local.policy()
    out = {g: [] for g in GATES}
    all_files = sorted(p for p in data.rglob("*") if p.is_file())
    for p in all_files:
        if set(p.relative_to(data).parts) & {"private", "local"}:
            out["no_private_or_local_paths"].append(f"staged path {p.relative_to(data)}")
    rows = _staged_rows(data)
    ids = {r["id"] for rs in rows.values() for r in rs}
    out["no_private_or_local_paths"] += [f"row {i} is in a */private/ file" for i in sorted(ids & local_only_ids(root))]
    slice_ids = e2_local.private_slice_ids(root, build / "private")
    out["no_unpublished_slice"] += [f"row {i} is in the unpublished slice" for i in sorted(ids & slice_ids)]
    out["no_excluded_rows"] += [f"row {i} is excluded" for i in sorted(ids & excluded_ids(root))]
    public_excl = _ids_in(root / "EXCLUDED.jsonl")
    out["no_excluded_rows"] += [f"staged EXCLUDED.jsonl names {i}, which is not a public exclusion"
                                for i in sorted(_ids_in(data / "EXCLUDED.jsonl") - public_excl)]
    for rs in rows.values():
        for r in rs:
            ok = e2_local.text_cleared(r["provenance"]["source"], pol)
            if r.get("redistribution") == "text" and not ok:
                out["no_withheld_text"].append(f"{r['id']}: text row from uncleared source {r['provenance']['source']}")
            if not ok:
                if r.get("redistribution") != "ids_only" or not r.get("withheld"):
                    out["no_withheld_text"].append(f"{r['id']}: uncleared source, not marked ids_only")
                filled = [k for k in e2_local.STRIP if r["state"].get(k) not in (None, [], "")]
                if filled:
                    out["no_withheld_text"].append(f"{r['id']}: ids-only row carries {', '.join(filled)}")
    needles = e2_local.leak_needles(root, True, build / "private") if needles is None else needles
    scan = e2_local.tracked_leaks(root, data, True, needles, build / "private",
                                  files=[str(p.relative_to(data)) for p in all_files])
    for leak in scan["leaks"]:
        gate = "no_withheld_text" if leak["kind"] == "withheld_text" else "no_unpublished_slice"
        out[gate].append(f"{leak['kind']} {leak['key']} in {leak['file']}")
    return {g: v[:50] for g, v in out.items()}


# --- rebuilding canonical rows locally ---------------------------------------------------------------------------------

def _local_variants(suites: set, root: Path = E2) -> dict:
    """{id: [record dict]} for the public candidates of ``suites``, text restored from the local cache: the record as
    the suite converter makes it, and again with the row's owner-ruling resolution or correction applied. A withheld
    field is taken from whichever variant gives the row its canonical hash."""
    from . import edition2
    out = defaultdict(list)
    for s in edition2.SUITES:
        if s.name not in suites:
            continue
        res, fixes = edition2.resolutions(s, root), edition2.corrections(s, root)
        for c in e2_local.candidates(s.name, e2_local.scored_root(s.name, root), private=False, text=True):
            tries = [c]
            for extra in (res.get(c["id"]), fixes.get(c["id"])):
                if extra and extra.get("status") in ("resolved", "applied"):
                    try:
                        tries.append(edition2.apply_resolution(s, c, extra))
                    except ValueError:
                        pass
            for t in tries:
                try:
                    out[c["id"]].append(s.to_record(t).to_dict())
                except Exception:  # noqa: BLE001  (a variant that does not convert is simply not a match)
                    pass
    return out


def rehydrate_rows(rows: list, root: Path = E2, variants: dict | None = None) -> tuple[list, Counter]:
    """(rows with withheld fields restored and published-only keys removed, tally). A row is restored only when the
    result matches its ``canonical_row_hash``; any row that cannot be raises PublishError."""
    need = [r for r in rows if r.get("redistribution") == "ids_only"]
    if variants is None:
        variants = _local_variants({SUITE_OF[r["feature"]] for r in need}, root) if need else {}
    tally, out = Counter(), []
    for r in rows:
        if r.get("redistribution") == "ids_only":
            full = None
            for v in variants.get(r["id"], []):
                cand = copy.deepcopy(r)
                try:
                    for p in r["withheld"]["paths"]:
                        _set(cand, p, _get(v, p))
                except (KeyError, IndexError, TypeError):
                    continue
                if canonical_hash(cand) == r["canonical_row_hash"]:
                    full = cand
                    break
            if full is None:
                raise PublishError(f"{r['id']}: no local text rebuilds this row to its canonical_row_hash; run "
                                   "uv run python -m goldrails_dataset.e2_local rehydrate")
            r = full
            tally["rehydrated"] += 1
        else:
            if canonical_hash(r) != r["canonical_row_hash"]:
                raise PublishError(f"{r['id']}: row does not match its canonical_row_hash")
            tally["text"] += 1
        out.append({k: v for k, v in r.items() if k not in PUBLISHED_ONLY})
    return out, tally


def _sort_key(d: dict):
    return (d["feature"], d["subtask"], d["id"])


def materialize(data: Path, dest: Path, root: Path = E2, build: Path = BUILD) -> dict:
    """Write the canonical edition 2 files to ``dest`` from a staged or downloaded folder (``data``): public rows
    rehydrated, local-only rows and the unpublished slice (``dest/private/``) from the local build. Each file must
    match the dataset hash and file sha256 recorded in ``canonical.json``. Returns a report."""
    from .records import Record, dataset_hash, read_jsonl
    data, dest, build = Path(data), Path(dest), Path(build)
    can = json.loads((data / CANONICAL).read_text(encoding="utf-8"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{dest.name}-", dir=dest.parent))
    try:
        rep = {"source_canonical_sha256": _sha(data / CANONICAL), "files": {}}
        need = {SUITE_OF[f["feature"]] for f in can["files"] if f["rows_ids_only"]}
        variants = _local_variants(need, root) if need else {}
        for f in can["files"]:
            staged = _read_rows(data / f["path"])
            if len(staged) != f["n"] or _sha(data / f["path"]) != f["sha256"]:
                raise PublishError(f"{f['path']} does not match canonical.json")
            rows, tally = rehydrate_rows(staged, root, variants)
            if f["rows_local_only"]:
                bp = build / f["build_file"]
                if not bp.exists():
                    raise PublishError(f"{bp} is not on this machine: {f['rows_local_only']} local-only rows of "
                                       f"{f['build_file']} come from it")
                local_ids = local_only_ids(root)
                local = [r for r in _read_rows(bp) if r["id"] in local_ids]
                if len(local) != f["rows_local_only"]:
                    raise PublishError(f"{f['build_file']}: {len(local)} local-only rows on this machine, canonical.json "
                                       f"expects {f['rows_local_only']}")
                rows += local
                tally["local_only"] += len(local)
            rows.sort(key=_sort_key)
            recs = [Record.from_dict(r) for r in rows]
            p = tmp / f["build_file"]
            p.write_text("".join(x.to_json() + "\n" for x in recs), encoding="utf-8")
            got = dataset_hash(recs)
            if got != f["build_dataset_sha256"]:
                raise PublishError(f"{f['build_file']}: rebuilt rows hash to {got[:12]}, canonical.json records "
                                   f"{f['build_dataset_sha256'][:12]}")
            if _sha(p) != f["build_file_sha256"]:
                raise PublishError(f"{f['build_file']}: the rebuilt file is not byte-identical to the build file")
            rep["files"][f["build_file"]] = dict(tally)
        priv = build / "private"
        (tmp / "private").mkdir()
        if (priv / "manifest.json").exists():
            pm = json.loads((priv / "manifest.json").read_text(encoding="utf-8"))
            for f in pm["files"]:
                if dataset_hash(read_jsonl(priv / f["path"])) != f["sha256"]:
                    raise PublishError(f"build/private/{f['path']} does not match its manifest")
            for name in [f["path"] for f in pm["files"]] + ["needs-owner-review.jsonl", "dropped.jsonl", "manifest.json"]:
                if (priv / name).exists():
                    shutil.copyfile(priv / name, tmp / "private" / name)
            rep["unpublished_slice_rows"] = sum(f["n"] for f in pm["files"])
        else:
            rep["unpublished_slice_rows"] = None
            rep["warning"] = "no unpublished slice on this machine (build/private/manifest.json is missing)"
        (tmp / "materialized.json").write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        return rep
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


def parity(data: Path = STAGE, root: Path = E2, build: Path = BUILD) -> dict:
    """Materialize ``data`` into a temporary folder and compare every file with the build, the unpublished slice
    included: same bytes and the same dataset hash. Returns {"pass", "files": {name: {...}}, "extra": [...]}."""
    from .records import dataset_hash, read_jsonl
    build = Path(build)
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "e2"
        rep = materialize(data, dest, root, build)
        files = {}
        for p in sorted(build.glob("F*.jsonl")) + sorted((build / "private").glob("F*.jsonl")):
            rel = p.relative_to(build)
            q = dest / rel
            files[str(rel)] = {"byte_identical": q.exists() and q.read_bytes() == p.read_bytes(),
                               "same_dataset_hash": q.exists() and dataset_hash(read_jsonl(q)) == dataset_hash(read_jsonl(p)),
                               "rows": sum(1 for line in p.open(encoding="utf-8") if line.strip()),
                               "rebuilt": rep["files"].get(str(rel), "copied from the local build (unpublished slice)")}
        extra = sorted(str(q.relative_to(dest)) for q in dest.rglob("F*.jsonl") if not (build / q.relative_to(dest)).exists())
    ok = all(v["byte_identical"] and v["same_dataset_hash"] for v in files.values()) and not extra and bool(files)
    return {"pass": ok, "files": files, "extra": extra}


# --- side files ------------------------------------------------------------------------------------------------------

def _public_note(note):
    """Registry notes record who reviewed what; the public files only say whether the review is finished."""
    if note and re.search(r"\bowner\b|\bClaude\b", note):
        return "licence review not finished: ids, labels and hashes ship here, the text does not"
    return note


def _public_evidence(ev):
    return re.sub(r"\s*\([^)]*\bv1\.\d[^)]*\)", "", ev) if ev else ev


def _sources_table(per_source: dict, pol: dict) -> list:
    out = []
    for s in sorted(per_source):
        e = dict(pol["sources"].get(s) or {})
        e["note"], e["evidence"] = _public_note(e.get("note")), _public_evidence(e.get("evidence"))
        out.append({"source": s, "rows": dict(sorted(per_source[s].items())),
                    "here": "text" if e2_local.text_cleared(s, pol) else "ids_only",
                    "basis": e.get("basis") or "no entry in dataset/release/redistribution.json (default ids_only)",
                    "evidence": e.get("evidence"), "attribution": e.get("attribution"), "note": e.get("note"),
                    "reviewed": bool(e.get("reviewed"))})
    return out


def _write_docs(out: Path, man: dict, files: list, pol: dict, code_ref: str, root: Path, build: Path) -> None:
    per_source, subtasks = defaultdict(Counter), defaultdict(Counter)
    for f in files:
        for r in _read_rows(out / f["path"]):
            per_source[r["provenance"]["source"]][f"{f['config']}/{f['split']}"] += 1
            subtasks[(f["config"], r["subtask"])][f["split"]] += 1
    reg = _sources_table(per_source, pol)
    (out / "sources.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "SOURCES.md").write_text(sources_md(reg, code_ref), encoding="utf-8")
    (out / "NOTICE.md").write_text(notice_md(reg), encoding="utf-8")
    (out / "RIGHTS.md").write_text(rights_md(reg), encoding="utf-8")
    (out / "RECONSTRUCT.md").write_text(reconstruct_md(files, code_ref), encoding="utf-8")
    (out / "CHANGELOG.md").write_text(changelog_md(files, code_ref, build), encoding="utf-8")
    shutil.copyfile(root / "EXCLUDED.jsonl", out / "EXCLUDED.jsonl")
    agr = root / "content" / "agreement.json"
    if agr.exists() and json.loads(agr.read_text(encoding="utf-8")).get("status") == "complete":
        doc = json.loads(agr.read_text(encoding="utf-8").replace(
            "the owner-ruling final label of a resolved dispute", "the final label of a resolved dispute"))
        (out / "content-label-agreement.json").write_text(
            json.dumps({"labeller": "the project lead personally, with an AI assistant (Codex)", "design": doc.get("design"),
                        "result": doc.get("result")}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    pa = prompt_attack_agreement(root)
    if pa:
        (out / "prompt-attack-label-agreement.json").write_text(json.dumps(pa, indent=1, ensure_ascii=False) + "\n",
                                                                 encoding="utf-8")
    ann = out / "annotations"
    ann.mkdir(exist_ok=True)
    if (root / "MODEL-TRAINING-OVERLAP.json").exists():
        txt = (root / "MODEL-TRAINING-OVERLAP.json").read_text(encoding="utf-8")
        txt = txt.replace("each edition 2 row", "each row").replace("from edition 2", "from this dataset")
        (ann / "model-training-overlap.json").write_text(txt, encoding="utf-8")
    (out / "README.md").write_text(card(files, man, reg, subtasks, code_ref, root), encoding="utf-8")


SUITE_DOCS = (("content", "content"), ("prompt_attacks", "prompt_attacks"), ("denied_topics", "denied_topics"),
              ("word_filters", "word_filters"), ("sensitive_information", "pii"), ("grounding", "grounding"))
# Where each suite's source list lives: SOURCES.md in the suite folder, or the scored folder's DESIGN.md "Sources"
# table for prompt attacks (e2_local.scored_root).
SUITE_SOURCES = {"prompt_attacks": "r26/prompt_attacks/DESIGN.md#sources"}


def prompt_attack_agreement(root: Path = E2) -> dict | None:
    """The prompt-attack AI second-label result, aggregates only, for the card and the staged folder."""
    p = Path(root) / "r26" / "prompt_attacks" / "label-agreement.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return {"what": "Sealed AI second label of a 400-row blind sample of the prompt-attack rows: a model with no tools "
                    "and no file access, given only the labelling policy and the rows. Not a human review.",
            "labelled_by": "a sealed AI second labeller",
            **{k: d[k] for k in ("overall", "confusion_reference_to_ai", "by_subtask", "by_stratum", "by_source")
               if k in d}}


def sources_md(reg: list, code_ref: str) -> str:
    lines = ["# Sources", "",
             "Each source in this dataset, with its licence basis and the evidence recorded in "
             "`dataset/release/redistribution.json` in the code repository. A source marked `ids_only` ships without "
             "text; RECONSTRUCT.md shows how to rebuild it. The upstream repository, pinned revision and split of "
             "each source are in the suite's own SOURCES.md:", ""]
    lines += [f"- {cfg}: {PUBLIC_REPO}/blob/{code_ref}/dataset/edition2/{SUITE_SOURCES.get(suite, suite + '/SOURCES.md')}"
              for cfg, suite in SUITE_DOCS]
    lines += ["", "| Source | Here | Licence basis | Rows |", "|---|---|---|---|"]
    for e in reg:
        lines.append(f"| {e['source']} | {e['here']} | {e['basis']} | "
                     f"{', '.join(f'{k} {v}' for k, v in e['rows'].items())} |")
    lines += [""]
    for e in reg:
        note = e["note"]
        bits = [f"Evidence: {e['evidence']}" if e["evidence"] else None,
                f"Attribution: {e['attribution']}" if e["attribution"] else None,
                f"Note: {note}" if note else None]
        bits = [b for b in bits if b]
        if bits:
            lines += [f"## {e['source']}", ""] + [f"- {b}" for b in bits] + [""]
    return "\n".join(lines) + "\n"


def notice_md(reg: list) -> str:
    fetched = {x["key"]: x for x in json.loads((ROOT / "release" / "source-attribution-fetched.json").read_text())}
    lines = ["# Notices", "",
             "Copyright and licence notices that the sources shipping text here ask to be kept, copied verbatim from "
             "the publishers' files at the pinned revision.", ""]
    missing = []
    for e in reg:
        if e["here"] != "text":
            continue
        u = fetched.get(e["source"])
        if u and u.get("notice_required") and u.get("copyright_notice"):
            lines += [f"## {u['key']} ({u.get('licence_id')})", "", "```", u["copyright_notice"].strip(), "```", ""]
        elif not e["basis"].startswith("authored") and not (u and u.get("notice_required") is False):
            missing.append(e["source"])
    if missing:
        lines += ["## Sources without a notice file", "",
                  "We found no notice text to copy for " + ", ".join(missing) + ". Their licence and attribution are in "
                  "SOURCES.md.", ""]
    lines += ["Sources that ship ids only carry no text here.", ""]
    return "\n".join(lines) + "\n"


def rights_md(reg: list) -> str:
    text = [e for e in reg if e["here"] == "text"]
    ids = [e for e in reg if e["here"] != "text"]
    lines = ["# Rights", "",
             "While a source's licence review is not finished, this dataset ships its ids, labels and hashes only, "
             "and you rebuild the text locally from the original source. A source ships text only when "
             "`dataset/release/redistribution.json` in the code repository lists it with `mode: text` and "
             "`reviewed: true`.", "",
             f"## Text ships ({len(text)} sources)", "", "| Source | Basis |", "|---|---|"]
    lines += [f"| {e['source']} | {e['basis']} |" for e in text]
    lines += ["", f"## Ids, labels and hashes only ({len(ids)} sources)", "", "| Source | Basis | Why no text yet |",
              "|---|---|---|"]
    lines += [f"| {e['source']} | {e['basis']} | "
              f"{'licence review not recorded as done' if not e['reviewed'] else 'mode is ids_only'} |" for e in ids]
    lines += ["", "This is not legal advice.", ""]
    return "\n".join(lines) + "\n"


def reconstruct_md(files: list, code_ref: str) -> str:
    n_ids = sum(f["rows_ids_only"] for f in files)
    n_local = sum(f["rows_local_only"] for f in files)
    return "\n".join([
        "# Rebuilding withheld text", "",
        f"{n_ids} rows ship without text (`\"redistribution\": \"ids_only\"`). `withheld.paths` lists the fields set to "
        "null, and `canonical_row_hash` is the sha256 of the full row. To put the text back from the original "
        "publishers:", "",
        "```bash", f"git clone {PUBLIC_REPO}", f"cd {PUBLIC_REPO.rsplit('/', 1)[-1]}", f"git checkout {code_ref}", "uv sync",
        "uv run python -m goldrails_dataset.e2_local rehydrate      # downloads each source at its pinned revision",
        "uv run python -m goldrails_dataset.publish_e2 materialize --data <this dataset folder> --out <new folder>",
        "```", "",
        "`e2_local rehydrate` keeps a row's text only when it matches the sha256 in the tracked candidate files. "
        "`materialize` then fills each row and keeps it only when the result matches `canonical_row_hash`. Some "
        "fields our pipeline wrote, such as a rationale that quotes the text, exist in no upstream source, so a few "
        "rows may not rebuild outside the project. You need access to each source under its own licence. Rebuilding "
        "grants no rights that licence withholds.", "",
        "## Not in this dataset", "",
        "- A held-back slice of the test split. Every row in it comes from public upstream data, so anyone can "
        "rebuild it. We keep it for contamination checks, not as a secret test.",
        f"- {n_local} rows held back while their labels are checked. `canonical.json` counts them per file "
        "(`rows_local_only`). Their ids are not published.",
        "- Rows whose label is still disputed. They join their split once resolved.", ""])


def changelog_md(files: list, code_ref: str, build: Path = BUILD) -> str:
    total = sum(f["n"] for f in files)
    return "\n".join([
        "# Changelog", "",
        f"## {VERSION}, {_today()}", "",
        "- First public release.",
        f"- {total} rows in six configs, each with `dev` and `test` splits.",
        "- Label checks: the content second-label sample (`content-label-agreement.json`) and the prompt-attack AI "
        "second label (`prompt-attack-label-agreement.json`).",
        f"- Code: {PUBLIC_REPO} at `{code_ref}`. Manifest sha256 `{_sha(Path(build) / 'manifest.json')}`.",
        "- Load a version by its Hub commit, not by `main`, if you need results to stay reproducible.", ""])


def _today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%-d %B %Y")


def disclosures(path: Path = DISCLOSURES) -> str:
    """The card's disclosures, from the owner-edited file without its leading HTML comment."""
    return re.sub(r"^\s*<!--.*?-->\s*", "", path.read_text(encoding="utf-8"), flags=re.S).strip()


def public_text_problems(out: Path) -> list:
    """Wording that must not reach the public files: internal history, owner process, open placeholders. Row data is
    not scanned; its provenance fields are the build's own record."""
    found = []
    for f in sorted(out.rglob("*")):
        if f.is_file() and f.suffix in (".md", ".json") and f.name != CANONICAL and "data" not in f.relative_to(out).parts:
            txt = f.read_text(encoding="utf-8")
            hits = list(PUBLIC_TEXT_BANNED.finditer(txt))
            if f.suffix == ".md":
                hits += list(PLACEHOLDER.finditer(txt))
            found += [f"{f.relative_to(out)}: {m.group()!r}" for m in hits]
    return found


def _label_notes(review: dict, root: Path) -> list:
    """What a reader needs to know about label quality: disputes left out, and the content second-label sample."""
    notes = []
    if review.get("public", 0):
        notes.append(f"- **Some labels may still change.** {review['public']} rows with a disputed label are left out "
                     "until they are resolved. A later version may add rows or correct labels, and each version has "
                     "its own Hub commit.")
    agr = root / "content" / "agreement.json"
    doc = json.loads(agr.read_text(encoding="utf-8")) if agr.exists() else {}
    o = ((doc.get("result") or {}).get("overall") or {}) if doc.get("status") == "complete" else {}
    if o:
        n = (doc.get("design") or {}).get("n", 400)
        notes.append(f"- **How the labels were checked.** Every row has a first label from its source or our "
                     "labelling rules. Rows outside the content and prompt-attack suites also have a blind second "
                     "label. The project lead personally decided every disagreement, with an AI assistant (Codex). "
                     f"For the content suite, the project lead personally labelled a stratified sample of {n} rows "
                     "blind, with the same AI assistant, without seeing the first label or the source. That second "
                     f"label agreed with the first on {o['agreement_population_weighted']:.1%} "
                     f"of rows (Cohen's kappa {o['kappa_population_weighted']:.2f}, weighted to the population). "
                     "`content-label-agreement.json` breaks this down by subtask and source.")
    else:
        notes.append("- **Content labels are being checked.** A 400-row blind second-label sample of the content suite "
                     "is in progress.")
    pa = prompt_attack_agreement(root)
    if pa:
        o = pa["overall"]
        notes.append(f"- **Prompt-attack labels have a sealed AI second label.** A sealed model with no tools and no "
                     f"file access, given only the labelling policy, labelled a blind sample of {o['n']} prompt-attack rows. It agreed "
                     f"with the reference label on {o['agreement']:.1%} of them (Cohen's kappa {o['kappa']:.2f}). This "
                     "is an AI cross-check, not a human review. `prompt-attack-label-agreement.json` breaks it down by "
                     "subtask and source.")
    return notes


def card(files: list, man: dict, reg: list, subtasks: dict, code_ref: str, root: Path) -> str:
    by_cfg = defaultdict(list)
    for f in files:
        by_cfg[f["config"]].append(f)
    yaml = ["configs:"]
    for config, fs in by_cfg.items():
        yaml += [f"  - config_name: {config}", "    data_files:"]
        for f in fs:
            yaml += [f"      - split: {f['split']}", f"        path: {f['path']}"]
    review = man.get("needs_owner_review", {})
    n_excl = len(_ids_in(root / "EXCLUDED.jsonl"))
    tot = lambda k: sum(f[k] for f in files)   # noqa: E731
    lines = ["---", f"pretty_name: \"{BRAND}\"", "license: other", "license_name: mixed-per-source",
             f"license_link: {HF_DATASET}/blob/main/SOURCES.md", "language:", "  - en", "task_categories:",
             "  - text-classification", "tags:", "  - guardrails", "  - content-moderation", "  - prompt-injection",
             "  - pii-detection", "  - hallucination-detection", *yaml, "---", "",
             f"# {BRAND}", "",
             f"Version {VERSION}. Code: {PUBLIC_REPO} at `{code_ref}`.", "",
             f"{BRAND} tests guardrail systems on six suites: harmful content, prompt attacks, denied topics, word "
             "filters, sensitive information (PII) and grounding. Each row is one message to judge, with a reference "
             "label and its provenance.", "",
             "## Intended use", "", INTENDED_USE, "",
             "## Before you use it", "",
             *_label_notes(review, root),
             "- **One scoring rule.** The benchmark scores every system with a fixed 0.5 rule and fits nothing on "
             "`dev`. Use `dev` for smoke tests and dry runs, and report scores on `test`.",
             "- **Prompt attacks are direct and indirect.** Direct rows are one user message. Indirect rows are a "
             "document the assistant reads (an email, a tool result, a passage), with the system prompt and the "
             "user's request in `state.context`. Judge the document, not the request.",
             f"- **{tot('rows_ids_only')} rows ship without text**, because their sources' licence review is not "
             "finished. RECONSTRUCT.md shows how to rebuild the text from the original publishers.", "",
             "## Configs and splits", "",
             "| Config | Split | Rows | With text | Ids only | File |", "|---|---|---|---|---|---|"]
    lines += [f"| {f['config']} | {f['split']} | {f['n']} | {f['rows_text']} | {f['rows_ids_only']} | `{f['path']}` |"
              for f in files]
    lines += ["", "Rows by subtask:", "", "| Config | Subtask | dev | test |", "|---|---|---|---|"]
    lines += [f"| {c} | {s} | {n.get('dev', 0)} | {n.get('test', 0)} |" for (c, s), n in sorted(subtasks.items())]
    lines += ["", "## Not in this dataset", "",
              f"- **A held-back slice** of the test split ({man.get('private_slice', {}).get('rows', 'n')} rows). "
              "Every row in it comes from public upstream data, so anyone can rebuild it. We keep it for "
              "contamination checks. A system that scores much higher on the public test rows than on these may "
              "have seen the public rows. It is not a secret test set.",
              f"- **{tot('rows_local_only')} rows** held back while their labels are checked.",
              f"- **{n_excl} excluded rows**, listed with reasons in EXCLUDED.jsonl: text in a benchmarked model's "
              "training or development data, text a benchmarked vendor published, and one row we dropped.", "",
              "## Disclosures", "", disclosures(), "",
              "## Record schema", "",
              "`id`, `feature`, `subtask`, `split`, `visibility`, `group` (rows sharing a group share a split), `state` "
              "(`text`, `role`, `context`, `source`, `query`, `tool_call`), `labels`, `expected`, "
              "`expected_distribution`, `spans`, `category`, `attribute` (`attribute.e2` holds the second label, how a "
              "disputed label was resolved and the content harm tags), `review_status`, `provenance`, `canonical_row_hash` "
              "(sha256 of the full row), `redistribution` (`text` or `ids_only`) and, on ids-only rows, `withheld` "
              "(which fields are null and why). `canonical.json` records each file's hashes, so a rebuilt copy can be "
              "checked byte for byte.", "",
              "## Sources and licences", "",
              "SOURCES.md and RIGHTS.md give each source's licence basis and say whether its text ships. NOTICE.md "
              "holds the required notices. `annotations/` holds the model-training overlap scan and the vendor overlap "
              "scan.", "",
              "| Source | Here | Rows |", "|---|---|---|"]
    lines += [f"| {e['source']} | {e['here']} | {sum(e['rows'].values())} |" for e in reg]
    lines += ["", "## Checksums", "", "| File | SHA-256 |", "|---|---|"]
    lines += [f"| `{f['path']}` | `{f['sha256']}` |" for f in files]
    lines += ["", "## Citation", "", "No paper or DOI yet. Cite the upstream sources as listed in SOURCES.md.", ""]
    return "\n".join(lines)


# --- CLI --------------------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stage")
    s.add_argument("--out", type=Path, default=STAGE)
    s.add_argument("--no-load-check", action="store_true")
    s.add_argument("--code-ref", help="code revision the card names (default: HEAD)")
    g = sub.add_parser("gates")
    g.add_argument("--data", type=Path, default=STAGE)
    p = sub.add_parser("parity")
    p.add_argument("--data", type=Path, default=STAGE)
    m = sub.add_parser("materialize")
    m.add_argument("--data", type=Path, required=True)
    m.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "stage":
        rep = stage(a.out, check_load=not a.no_load_check, code_ref=a.code_ref)
        print(json.dumps({k: rep[k] for k in ("staged", "totals", "unpublished_slice_rows", "gates", "load_check")},
                         indent=1))
        for x in rep["problems"][:20]:
            print("PROBLEM:", x)
        return 1 if rep["problems"] else 0
    if a.cmd == "gates":
        rep = gates(a.data)
        print(json.dumps({k: ("pass" if not v else v) for k, v in rep.items()}, indent=1))
        return 1 if any(rep.values()) else 0
    if a.cmd == "parity":
        rep = parity(a.data)
        print(json.dumps(rep, indent=1))
        return 0 if rep["pass"] else 1
    print(json.dumps(materialize(a.data, a.out), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
