"""Where the edition 2 runners take their rows from: the Hugging Face copy by default, rebuilt locally.

    GOLDRAILS_E2_SOURCE=hf:raxITLabs/decision-models-as-guardrails@<commit>   # the published copy, pinned
    GOLDRAILS_E2_SOURCE=dataset/publish/release-1.0.1                             # a staged folder in the Hub layout
    GOLDRAILS_E2_SOURCE=local                                                # dataset/edition2/build as it is

A published copy has no text for licence-withheld rows and no unpublished slice. ``dataset_dir`` downloads (or
reads) it, puts the withheld text back from this machine's local text cache, adds the local-only rows and the
unpublished slice from the local build, and writes the result to ``dataset/edition2/.materialized/<key>/``
(git-ignored) as ``F<n>.<split>.jsonl`` and ``private/F<n>.test.jsonl``. Those files must be byte-identical to the
build's, and ``goldrails_dataset.publish_e2.materialize`` stops when they are not, so ledgers, dataset hashes and
freeze manifests do not change with the source.

The default is ``hf:<HF_REPO>@<E2_HF_REVISION>`` once the owner has filled in ``E2_HF_REVISION``; until then it is the
local staged folder (``uv run python -m goldrails_dataset.publish_e2 stage`` writes it).
"""
from __future__ import annotations

import hashlib
import json
import os
import warnings
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "dataset" / "edition2" / "build"
STAGED = REPO / "dataset" / "publish" / "release-1.0.1"
CACHE = REPO / "dataset" / "edition2" / ".materialized"
HF_REPO = "raxITLabs/decision-models-as-guardrails"
ENV = "GOLDRAILS_E2_SOURCE"

# OWNER: after uploading, set this to the Hub commit sha of the upload (40 hex characters,
# `hf repo tag list raxITLabs/decision-models-as-guardrails --repo-type dataset` or the Hub's "Files and versions").
# None keeps the runners on the local staged folder.
E2_HF_REVISION: str | None = "f88403efb827ba0c2771dd069ec545d35849ff8d"   # 1.0.1


class E2SourceMissing(FileNotFoundError):
    pass


def default_source() -> str:
    if E2_HF_REVISION:
        return f"hf:{HF_REPO}@{E2_HF_REVISION}"
    return str(STAGED.relative_to(REPO))


def source(explicit: str | None = None) -> str:
    """The source string in force: ``explicit``, else $GOLDRAILS_E2_SOURCE, else ``default_source()``."""
    return explicit or os.environ.get(ENV) or default_source()


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO / p


def _hub_folder(spec: str) -> Path:
    """Download the data files and canonical.json of ``<repo>@<revision>`` (pinned: a revision is required)."""
    repo, _, rev = spec.partition("@")
    if not rev:
        raise ValueError(f"hf:{spec}: pin a revision (hf:{repo}@<commit sha or tag>)")
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(repo_id=repo, repo_type="dataset", revision=rev,
                                  allow_patterns=["canonical.json", "data/*/*.jsonl"]))


def _digest(data: Path) -> str:
    """What a materialized folder depends on: the published files, the build manifests and the local text caches."""
    from goldrails_dataset import e2_local
    h = hashlib.sha256()
    parts = [data / "canonical.json", *sorted((data / "data").glob("*/*.jsonl")), BUILD / "manifest.json",
             BUILD / "private" / "manifest.json"]
    for s in e2_local.SUITES:
        sd = e2_local.suite_dir(s)
        parts += [sd / "candidates.jsonl", sd / "resolutions.jsonl", sd / "corrections.jsonl", e2_local.text_cache(s),
                  e2_local.private_dir(s) / "candidates.jsonl"]
    for p in parts:
        h.update(str(p.relative_to(REPO) if p.is_relative_to(REPO) else p.name).encode())
        h.update(hashlib.sha256(p.read_bytes()).digest() if p.exists() else b"-")
    return h.hexdigest()


def published_folder(src: str | None = None) -> Path | None:
    """The folder holding the published files (canonical.json, data/) for a Hub or staged source; None for ``local``
    or a directory already in the build layout."""
    s = source(src)
    if s == "local":
        return None
    if s.startswith("hf:"):
        return _hub_folder(s[3:])
    p = _resolve(s)
    if (p / "canonical.json").exists():
        return p
    if any(p.glob("F*.dev.jsonl")) or any(p.glob("F*.test.jsonl")):
        return None
    hint = " (uv run python -m goldrails_dataset.publish_e2 stage)" if p == STAGED else ""
    raise E2SourceMissing(f"edition 2 source {s}: no canonical.json or F*.jsonl files in {p}{hint}")


def dataset_dir(src: str | None = None) -> Path:
    """A local directory of canonical edition 2 files (``F<n>.<split>.jsonl``, ``private/F<n>.test.jsonl``) for the
    source in force. ``local`` is the build itself; a build-layout directory is used as it is; a Hub or staged copy is
    rebuilt into the git-ignored cache when its inputs changed."""
    s = source(src)
    if s == "local":
        return BUILD
    data = published_folder(s)
    if data is None:
        return _resolve(s)
    from goldrails_dataset.publish_e2 import materialize
    key = hashlib.sha256(s.encode()).hexdigest()[:16]
    dest = CACHE / key
    digest = _digest(data)
    stamp = dest / "stamp.json"
    if stamp.exists() and json.loads(stamp.read_text(encoding="utf-8")).get("digest") == digest:
        return dest
    materialize(data, dest)
    stamp.write_text(json.dumps({"source": s, "digest": digest}, indent=1) + "\n", encoding="utf-8")
    return dest


def describe(src: str | None = None) -> str:
    """The source string a ledger records next to the dataset hash."""
    s = source(src)
    return "dataset/edition2/build" if s == "local" else s


def dev_files(src: str | None = None) -> list[Path]:
    """The edition 2 dev files for the source in force. When the default source is not on this machine (a fresh
    clone, CI) this falls back to whatever the local build has, possibly nothing, with a warning; an explicit source
    that is missing raises."""
    try:
        return sorted(dataset_dir(src).glob("F*.dev.jsonl"))
    except E2SourceMissing:
        if src or os.environ.get(ENV):
            raise
        warnings.warn(f"edition 2 source {source()} is not on this machine; reading dev rows from the local build")
        return sorted(BUILD.glob("F*.dev.jsonl"))
