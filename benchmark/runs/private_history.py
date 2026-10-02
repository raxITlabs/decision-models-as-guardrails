"""Git dates for the page checks, from this repository or from the archived private history it continues.

The freeze-order checks ask git when a file was first committed. Until 2 October 2026 this repository was an export of
a private working repository, and the files those checks date arrived here together in export commits, so this
repository's ``git log`` cannot show their order. ``benchmark/history/private-history.json`` records the private
``git log`` for those files and the private commit list (``scripts/record_private_history.py`` writes it from the
archived bundle and can rebuild it to compare).

``History`` answers the few git questions the checks ask, in git's own output format:

- when the private head is in this repository's history (a checkout of the archive), everything comes from git;
- otherwise a file in the record is dated by the record, and only while its bytes here equal the recorded sha256:
  a file changed since then is reported by ``stale`` and fails the check that dated it;
- a file or commit the record does not know comes from this repository's git, so anything committed after the
  consolidation is dated by this repository's own history.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RECORD = REPO / "benchmark/history/private-history.json"


class History:
    def __init__(self, repo: Path = REPO, record: Path = RECORD):
        self.repo = repo
        self.rec = json.loads(record.read_text(encoding="utf-8")) if record.exists() else None
        head = (self.rec or {}).get("source", {}).get("head")
        self.live = self.rec is None or subprocess.run(["git", "merge-base", "--is-ancestor", head, "HEAD"], cwd=repo,
                                                       capture_output=True).returncode == 0
        self.files = {} if self.live else self.rec["files"]
        self.commits = {} if self.live else self.rec["commits"]

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, check=False).stdout.strip()

    def log(self, path: str, fmt: str = "%ct %h", added: bool = False, reverse: bool = False) -> str:
        """``git log [--reverse] [--diff-filter=A] --format=<fmt> -- path`` (fmt: "%ct %h", "%h" or "%ct")."""
        e = self.files.get(path)
        if e is None:
            return self.git("log", *(["--reverse"] if reverse else []), *(["--diff-filter=A"] if added else []),
                            f"--format={fmt}", "--", path)
        lines = [(ct, h[:7]) for ct, h in (x.split() for x in (e["added"] if added else e["log"]))]
        lines = lines[::-1] if reverse else lines
        return "\n".join(fmt.replace("%ct", ct).replace("%h", h) for ct, h in lines)

    def stale(self, paths) -> list[str]:
        """Those of ``paths`` the record dates whose bytes here are not the recorded ones."""
        out = []
        for p in sorted(set(paths) & set(self.files)):
            f = self.repo / p
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != self.files[p]["sha256"]:
                out.append(p)
        return out

    def _known(self, commit: str) -> str | None:
        hits = [h for h in self.commits if h.startswith(commit)] if len(commit) >= 7 else []
        return hits[0] if len(hits) == 1 else None

    def commit_exists(self, commit: str) -> bool:
        return bool(self.git("cat-file", "-t", commit)) or self._known(commit) is not None

    def in_history(self, commit: str) -> bool:
        """An ancestor of HEAD here, or a private commit (every recorded commit is an ancestor of the private head)."""
        here = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=self.repo,
                              capture_output=True).returncode == 0
        return here or self._known(commit) is not None

    def note(self, paths=(), commits=()) -> str:
        """Said beside a check's detail when the record dated any of ``paths`` or knew any of ``commits``."""
        if self.live or not (set(paths) & set(self.files) or any(self._known(c) for c in commits)):
            return ""
        return f"; dated by {RECORD.relative_to(REPO)} (private history, {self.rec['source']['bundle']})"
