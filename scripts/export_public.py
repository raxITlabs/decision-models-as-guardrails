"""Build the public jev-as-a-guardrails repository as a clean, allowlisted export of this private repository. No push.

    uv run python scripts/export_public.py                      # build and scan into ../goldrails, report only
    uv run python scripts/export_public.py --commit              # also create the export's single commit and tag
    uv run python scripts/export_public.py --commit              # into an existing clone: one new commit on top, no tag

A revision of the public version keeps the earlier export commit and its tag: when ``--out`` already holds a git
clone, the files are replaced in its working tree and committed on top, so the commit the first dataset upload names
stays reachable.

The private repository keeps its full history, including the freeze evidence. Deleting files in a new commit would
leave them in that history, so the public repository starts fresh from an allowlist of committed files at HEAD:

1. Take only the files matched by INCLUDE and not by EXCLUDE, from ``git archive HEAD`` (uncommitted changes never
   leak in).
2. Apply recorded redactions: AI4Privacy rows and ids leave machine-readable files and are masked in prose; raw
   service responses are dropped for rows from ids-only sources; the AWS account number and local paths are masked.
3. Scan every exported file for withheld text (50-character windows of every row from a withheld or ids-only source,
   plus the committed AI4Privacy sample rows), AI4Privacy ids, secrets and local paths. Any hit stops the export.
4. Write EXPORT.md and export-manifest.json: the private commit, every file with its private and public sha256, and
   the redactions applied to it.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TAG = "v0.0.1"
FIRST_UPLOAD = "internal dataset release v1.2, Hugging Face revision 3e3ed7f3bbed, code commit 26b578fea60c"
CURRENT = "v1.3"   # internal dataset release of the current revision of the public version
DATASET_URL = "https://huggingface.co/datasets/raxITLabs/jev-as-a-guardrails"
BRAND = "jev-as-a-guardrails"   # display name; the benchmark was called [gold]rails until 30 September 2026
PUBLIC_URL = "https://github.com/raxITlabs/jev-as-a-guardrails"

INCLUDE = [
    "README.md", "VISION.md", "PRODUCT.md", "pyproject.toml", "uv.lock", "Makefile", ".gitignore", ".env.example",
    "benchmark/pyproject.toml", "benchmark/contracts/*", "benchmark/goldrails_bench/*", "benchmark/question_sets/*",
    "benchmark/runs/*", "benchmark/subsets/*", "benchmark/suites/*", "benchmark/tests/*",
    "benchmark/results/first-benchmark/*", "benchmark/results/second-benchmark/*", "benchmark/results/smoke-word-filters*",
    "dataset/pyproject.toml", "dataset/goldrails_dataset/*", "dataset/tests/*", "dataset/release/*",
    "dataset/publish/v1.2-full/*", "dataset/publish/v1.3-full/*", "dataset/frozen/*",
    "site/leaderboard/*", "infra/*", "scripts/export_public.py",
    "docs/*",                                                  # every tracked doc (owner, 29 Sep 2026)
]
EXCLUDE = [
    "dataset/samples/*",                                      # 180 AI4Privacy rows with text, plus old pilot samples
    "dataset/frozen/corrections/pii-negatives-*",             # labels derived from AI4Privacy rows
    "dataset/frozen/reviews/ai-pii-negatives-*",              # audit verdicts on AI4Privacy rows
    "dataset/frozen/review-packets/_lead/f5-*",               # AI4Privacy review keys
    "dataset/frozen/packet/*",                                # pilot review packet with source rows
    "dataset/frozen/release-trial/*",
    "dataset/DATASET_CARD.md",                                # v1.0 card, superseded by dataset/publish/v1.1-ai/README.md
    "dataset/release/v1.0/*",
    "dataset/release/rights-confirmation-*",                   # AI4Privacy record, superseded by v1.2
    "*.ipynb",
    "docs/requests/*",                                        # unsent AI4Privacy permission draft; AI4Privacy stays out
]
AI4P_ID = re.compile(r"f5-ai4privacy-[0-9a-f]{10}")
ACCOUNT = "<aws-account>"
HOME = re.compile(r"/Users/[A-Za-z0-9._-]+(/Documents/Test-temp-folder/jev-powered-guardrails)?/?")
SECRET = re.compile(r"AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH|EC|PRIVATE)|hf_[A-Za-z0-9]{30,}|"
                    r"(TYPESAFE|OPENAI)_API_KEY[ \t]*=[ \t]*\S+|aws_secret_access_key[ \t]*=[ \t]*\S+")
IDS_ONLY: set = set()   # since v1.2 the dataset publishes full text for RAGTruth, Civil Comments identity rows and B2
WITHHELD = {"ai4privacy"}


def git(*args, binary=False):
    out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode().strip()


def selected(path: str) -> bool:
    return (any(fnmatch.fnmatch(path, g) for g in INCLUDE) and not any(fnmatch.fnmatch(path, g) for g in EXCLUDE))


def restricted_windows() -> tuple[set, set]:
    """50-character windows of every text from a withheld or ids-only source, and AI4Privacy source ids."""
    rows = []
    for p in (REPO / "dataset/release/v1.1-ai/build").glob("*.jsonl"):
        rows += [json.loads(line) for line in p.open(encoding="utf-8")]
    if not rows:
        raise SystemExit("release build missing; run uv run python -m goldrails_dataset.release --version v1.1-ai")
    for f in git("ls-files", "dataset/samples").splitlines():
        if f.endswith(".jsonl"):
            rows += [json.loads(x) for x in git("show", f"HEAD:{f}").splitlines() if x.strip()]
    seen, source_ids = Counter(), set()
    for r in rows:
        src = r["provenance"]["source"]
        if src not in WITHHELD | IDS_ONLY:
            continue
        if src in WITHHELD:
            source_ids.add(str(r["provenance"]["source_id"]))
        mine = set()
        for k in ("text", "source", "query"):
            t = " ".join(str((r.get("state") or {}).get(k) or "").split())
            for i in range(0, max(len(t) - 50, 0) + 1, 25):
                if len(t) >= 50:
                    mine.add(t[i:i + 50])
        seen.update(mine)
    # a window shared by 3 or more rows is boilerplate (task templates, HTML headers), not any one row's content
    # standard HTML head lines (the viewport meta tag) appear in a few source documents and in our own page; they are
    # web boilerplate, not any row's content
    html_head = ('name="viewport"', "width=device-width", "initial-scale=")
    windows = {w for w, n in seen.items() if n < 3 and not any(h in w for h in html_head)}
    restricted_windows.boilerplate = len(seen) - len(windows)
    return windows, source_ids


def redact_row(r: dict, notes: Counter) -> dict | None:
    src = r.get("source") or (r.get("provenance") or {}).get("source")
    if src in WITHHELD or AI4P_ID.search(str(r.get("id", ""))):
        notes["AI4Privacy row removed"] += 1
        return None
    if src in IDS_ONLY and r.get("raw") is not None:
        r = {**r, "raw": None, "raw_redacted": "ids-only source"}
        notes["raw response dropped (ids-only source)"] += 1
    return r


def scrub_json(x, notes: Counter):
    """Remove AI4Privacy rows and ids from any JSON structure."""
    if isinstance(x, list):
        out = []
        for v in x:
            if isinstance(v, str) and AI4P_ID.fullmatch(v):
                notes["AI4Privacy id removed"] += 1
                continue
            if isinstance(v, dict) and AI4P_ID.fullmatch(str(v.get("id", ""))):
                notes["AI4Privacy row removed"] += 1
                continue
            out.append(scrub_json(v, notes))
        return out
    if isinstance(x, dict):
        return {k: scrub_json(v, notes) for k, v in x.items()}
    return x


def transform(path: str, data: bytes, source_ids: set) -> tuple[bytes, Counter]:
    notes = Counter()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data, notes
    if path.endswith(".jsonl"):
        lines = []
        for line in text.splitlines():
            if not line.strip():
                continue
            r = redact_row(json.loads(line), notes)
            if r is not None:
                lines.append(json.dumps(scrub_json(r, notes), ensure_ascii=False))
        text = "\n".join(lines) + ("\n" if lines else "")
    elif path.endswith(".json"):
        doc = json.loads(text)
        new = scrub_json(doc, notes)
        if notes:
            text = json.dumps(new, indent=1, ensure_ascii=False) + "\n"
    elif path.endswith(".txt"):
        kept = [x for x in text.splitlines() if not AI4P_ID.search(x)]
        if len(kept) != len(text.splitlines()):
            notes["AI4Privacy id line removed"] += len(text.splitlines()) - len(kept)
            text = "\n".join(kept) + "\n"
    if AI4P_ID.search(text):
        notes["AI4Privacy id masked"] += len(AI4P_ID.findall(text))
        text = AI4P_ID.sub("f5-ai4privacy-[withheld]", text)
    for sid in ([] if path.endswith(".py") else source_ids):   # never rewrite code; ids in code are examples
        pattern = re.compile(rf"(?<![0-9A-Za-z]){re.escape(sid)}(?![0-9A-Za-z])")
        if pattern.search(text):
            notes["AI4Privacy source id masked"] += len(pattern.findall(text))
            text = pattern.sub("[AI4Privacy id]", text)
    if ACCOUNT in text:
        notes["AWS account masked"] += text.count(ACCOUNT)
        text = text.replace(ACCOUNT, "<aws-account>")
    if HOME.search(text):
        notes["local path masked"] += len(HOME.findall(text))
        text = HOME.sub("", text)
    return text.encode("utf-8"), notes


def scan(path: str, data: bytes, windows: set) -> list:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    hits = []
    flat = " ".join(text.replace("\\n", " ").split())
    if any(flat[i:i + 50] in windows for i in range(0, max(len(flat) - 49, 0))):
        hits.append("text from a withheld or ids-only source")
    if AI4P_ID.search(text):
        hits.append("AI4Privacy id")
    if SECRET.search(text):
        hits.append("secret-like string")
    if ACCOUNT in text or HOME.search(text):
        hits.append("account number or local path")
    return hits


def export_md(private: str, files: list, notes: dict) -> str:
    total = Counter()
    for n in notes.values():
        total.update(n)
    lines = ["# About this repository", "",
             f"This is the public export of the {BRAND} benchmark, public version `{TAG}`, revision built from internal "
             f"dataset release {CURRENT}. The first upload of `{TAG}` used {FIRST_UPLOAD} (tag `{TAG}` in both places). "
             f"This export was built from commit `{private}` "
             "of the private development repository by `scripts/export_public.py`, from an allowlist of files. The "
             f"dataset is published separately at {DATASET_URL}.", "",
             "The private repository keeps the full history, including the git commits that date the freeze manifests "
             "before the test runs. This repository starts fresh, so its own history does not prove when anything was "
             "frozen. The freeze manifests, approvals, ledgers and their sha256 values are included; "
             "`export-manifest.json` maps every file to its private sha256.", "",
             f"The benchmark was called [gold]rails until 30 September 2026. Code identifiers keep the old name "
             "(the `goldrails_bench` and `goldrails_dataset` packages, `GOLDRAILS_*` variables, file names), and so do "
             "dated records written before the rename. The Hugging Face dataset moved from `raxITLabs/goldrails` to `raxITLabs/jev-as-a-guardrails`.", "",
             "## What was left out or changed", "",
             "- AI4Privacy, the PII source before dataset v1.2: its rows, ids, labels and audit files are withheld "
             "(its licence needs written permission to redistribute). The v1.1 PII results that used it are kept as "
             "numbers only; v1.2 measures PII on NVIDIA Nemotron-PII, which is fully included.",
             "- Pilot samples, review packets with source text, notebooks, internal reports, downloaded transcripts and "
             "vendor documents.",
             "- The AWS account number and local file paths are masked.", "",
             "| Redaction | Count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(total.items())]
    lines += ["", f"{len(files)} files. {BRAND} is a non-commercial research benchmark; each source's rows stay under "
              "that source's licence (dataset/publish/v1.1-ai/SOURCES.md).", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO.parent / "goldrails")
    ap.add_argument("--commit", action="store_true", help="create the export's single commit and tag")
    a = ap.parse_args(argv)
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("commit or stash tracked changes first: the export reads committed files only")
    private = git("rev-parse", "HEAD")
    windows, source_ids = restricted_windows()
    tar = tarfile.open(fileobj=io.BytesIO(git("archive", "HEAD", binary=True)))
    revise = (a.out / ".git").exists()   # an existing clone: replace the working tree, keep its history and tag
    if a.out.exists():
        for child in a.out.iterdir():
            if child.name == ".git":
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    a.out.mkdir(parents=True, exist_ok=True)
    files, notes, problems = [], {}, defaultdict(list)
    for m in tar.getmembers():
        if not m.isfile() or not selected(m.name):
            continue
        raw = tar.extractfile(m).read()
        new, n = transform(m.name, raw, source_ids)
        hits = scan(m.name, new, windows)
        if hits:
            problems[m.name] += hits
        dst = a.out / m.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(new)
        if m.mode & 0o111:
            dst.chmod(0o755)
        files.append({"path": m.name, "private_sha256": hashlib.sha256(raw).hexdigest(),
                      "public_sha256": hashlib.sha256(new).hexdigest(), "redactions": dict(n)})
        if n:
            notes[m.name] = n
    report = {"private_commit": private, "tag": TAG, "public_url": PUBLIC_URL, "files": files,
              "scan": {"windows": len(windows), "boilerplate_windows_skipped": restricted_windows.boilerplate,
                       "ai4privacy_source_ids": len(source_ids),
                       "problems": dict(problems)}}
    (a.out / "export-manifest.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    (a.out / "EXPORT.md").write_text(export_md(private[:12], files, notes), encoding="utf-8")
    print(f"exported {len(files)} files from {private[:12]} to {a.out}; scan problems: {len(problems)}")
    for p, h in sorted(problems.items())[:20]:
        print(f"  {p}: {', '.join(h)}")
    if problems:
        return 1
    if a.commit:
        def g(*args):
            subprocess.run(["git", *args], cwd=a.out, check=True, capture_output=True)
        if not revise:
            g("init", "-q", "-b", "main")
        g("add", "-A")
        g("-c", f"user.name={git('config', 'user.name')}", "-c", f"user.email={git('config', 'user.email')}", "commit", "-q",
          "-m", f"{BRAND} {TAG}{' revision (internal dataset ' + CURRENT + ')' if revise else ''}: public export of "
                f"private commit {private[:12]}")
        if not revise:
            g("tag", TAG)
        print(f"committed{'' if revise else ' and tagged ' + TAG} in {a.out}; not pushed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
