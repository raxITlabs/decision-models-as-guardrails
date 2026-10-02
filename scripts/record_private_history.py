"""Record the git dates of the frozen benchmark files from the archived private history, for the page checks.

    uv run python scripts/record_private_history.py --bundle PATH/jev-powered-guardrails-archive-2026-10-02.bundle
    uv run python scripts/record_private_history.py --bundle PATH/... --check     # rebuild and compare, write nothing

Until 2 October 2026 this repository was an export of a private working repository. The private history is what
dates the freeze manifests before the test ledgers: in this repository those files arrived together in export
commits, so ``git log`` here cannot show the order. The private history is archived offline as a git bundle. This
script reads that bundle (a temporary clone of its ``main``) and writes ``benchmark/history/private-history.json``:

- ``commits``: every commit reachable from the private ``main``, with its commit time. All of them are ancestors of
  the private head, and this repository continues from that head.
- ``files``: for every file under ``benchmark/subsets/`` and ``benchmark/results/{first,second}-benchmark/`` that is
  also in this repository, the private ``git log`` lines (``%ct`` and full hash, newest first, plain and
  ``--diff-filter=A``), the file's sha256 at the private head, and its sha256 here. Where the two differ, the
  difference must be the export's recorded redaction (``export-manifest.json``); anything else stops the script.
- ``first_test_call``: the earliest test attempt in each run's test ledgers, as the checks compute it.

``benchmark/runs/private_history.py`` reads the record when the private head is not in this repository's history.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "benchmark/history/private-history.json"
PREFIXES = ("benchmark/subsets/", "benchmark/results/first-benchmark/", "benchmark/results/second-benchmark/")
SKIP = ("page-check.json",)   # rewritten by every page check; nothing reads its history
TEST_LEDGERS = ("test.jsonl", "test-bias.jsonl", "ext-test.jsonl", "ext-test-bias.jsonl", "pii-v12-test.jsonl",
                "prof-v13-test.jsonl")


def run(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def first_call(run_dir: Path, names: tuple) -> str | None:
    ats = [a["at"] for n in names if (run_dir / n).exists() for line in (run_dir / n).open(encoding="utf-8")
           if line.strip() for a in json.loads(line)["attempts"]]
    return min(ats) if ats else None


def build(private: Path, bundle: Path) -> dict:
    head = run(private, "rev-parse", "main")
    commits = {}
    for line in run(private, "log", "--format=%H %ct", "main").splitlines():
        h, ct = line.split()
        commits[h] = int(ct)
    export = {f["path"]: f for f in json.loads((REPO / "export-manifest.json").read_text(encoding="utf-8"))["files"]}
    files, problems = {}, []
    for path in run(private, "ls-tree", "-r", "--name-only", "main").splitlines():
        if not path.startswith(PREFIXES) or path.endswith(SKIP) or not (REPO / path).is_file():
            continue
        log = run(private, "log", "--format=%ct %H", "main", "--", path).splitlines()
        added = run(private, "log", "--diff-filter=A", "--format=%ct %H", "main", "--", path).splitlines()
        private_sha = sha256(subprocess.run(["git", "show", f"main:{path}"], cwd=private, capture_output=True,
                                            check=True).stdout)
        here = sha256((REPO / path).read_bytes())
        e = export.get(path) or {}
        redactions = None
        if here != private_sha:
            if e.get("private_sha256") == private_sha and e.get("public_sha256") == here and e.get("redactions"):
                redactions = e["redactions"]
            else:
                problems.append(path)
        files[path] = {"log": log, "added": added, "private_sha256": private_sha, "sha256": here,
                       **({"export_redactions": redactions} if redactions else {})}
    if problems:
        raise SystemExit("differ from the private head by more than the export's recorded redactions: "
                         + ", ".join(problems))
    res = REPO / "benchmark/results"
    return {
        "about": "Git dates of the frozen benchmark files, read from the archived private history. This repository "
                 "was an export of that private repository until 2026-10-02 and continues from its head; the export "
                 "commits here do not date the freeze. Written by scripts/record_private_history.py; rebuild it from "
                 "the bundle with --check to verify.",
        "source": {"bundle": bundle.name, "bundle_sha256": sha256(bundle.read_bytes()), "ref": "main", "head": head,
                   "head_committed_at": datetime.fromtimestamp(commits[head], timezone.utc).isoformat()},
        "first_test_call": {
            "second-benchmark": first_call(res / "second-benchmark", TEST_LEDGERS),
            "first-benchmark": first_call(res / "first-benchmark", TEST_LEDGERS),
            "first-benchmark profanity (tuning or test)": first_call(res / "first-benchmark",
                                                                     ("prof-v13-tune.jsonl", "prof-v13-test.jsonl")),
        },
        "commits": commits,
        "files": files,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", type=Path, required=True, help="the archived private repository (git bundle)")
    ap.add_argument("--check", action="store_true", help="rebuild and compare with the committed record")
    a = ap.parse_args(argv)
    run(REPO, "bundle", "verify", str(a.bundle.resolve()))
    with tempfile.TemporaryDirectory() as tmp:
        private = Path(tmp) / "private"
        subprocess.run(["git", "clone", "-q", "--no-checkout", "-b", "main", str(a.bundle.resolve()), str(private)],
                       check=True)
        rec = build(private, a.bundle)
    text = json.dumps(rec, indent=1, sort_keys=False) + "\n"
    if a.check:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print(f"{OUT.relative_to(REPO)} {'matches' if same else 'DIFFERS FROM'} the bundle ({len(rec['files'])} files, "
              f"{len(rec['commits'])} commits)")
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}: {len(rec['files'])} files, {len(rec['commits'])} commits, head "
          f"{rec['source']['head'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
