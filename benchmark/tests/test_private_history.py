"""The private history record and the reader the page checks use when the private history is not in this repository."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark/runs"))
from private_history import RECORD, History  # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           "-c", "core.hooksPath=/dev/null", *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def _repo(tmp_path, head="f" * 40):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "frozen.json").write_text("{}\n")
    (tmp_path / "new.json").write_text("[]\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "export")
    rec = {"source": {"head": head, "bundle": "archive.bundle"},
           "commits": {"a" * 40: 100, "b" * 40: 200},
           "files": {"frozen.json": {"log": ["200 " + "b" * 40, "100 " + "a" * 40], "added": ["100 " + "a" * 40],
                                     "sha256": hashlib.sha256(b"{}\n").hexdigest()}}}
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    return History(tmp_path, tmp_path / "rec.json")


def test_recorded_files_are_dated_by_the_record_in_git_format(tmp_path):
    h = _repo(tmp_path)
    assert not h.live
    assert h.log("frozen.json") == "200 bbbbbbb\n100 aaaaaaa"
    assert h.log("frozen.json", added=True) == "100 aaaaaaa"
    assert h.log("frozen.json", reverse=True, fmt="%h") == "aaaaaaa\nbbbbbbb"
    assert h.log("frozen.json", fmt="%ct", added=True) == "100"
    assert "dated by" in h.note(["frozen.json"]) and h.note(["new.json"]) == ""


def test_files_and_commits_the_record_does_not_know_come_from_this_repository(tmp_path):
    h = _repo(tmp_path)
    here = git(tmp_path, "rev-parse", "--short=7", "HEAD")
    assert h.log("new.json", fmt="%h") == here
    assert h.commit_exists("aaaaaaa") and h.in_history("bbbbbbb") and h.commit_exists(here) and h.in_history(here)
    assert not h.commit_exists("ccccccc") and not h.in_history("ccccccc")


def test_a_recorded_file_changed_since_the_record_is_stale(tmp_path):
    h = _repo(tmp_path)
    assert h.stale(["frozen.json", "new.json"]) == []
    (tmp_path / "frozen.json").write_text('{"edited": true}\n')
    assert h.stale(["frozen.json", "new.json"]) == ["frozen.json"]


def test_with_the_private_head_in_history_everything_comes_from_git(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "frozen.json").write_text("{}\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "private")
    head = git(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "rec.json").write_text(json.dumps({"source": {"head": head}, "commits": {"a" * 40: 1},
                                                   "files": {"frozen.json": {"log": ["1 " + "a" * 40]}}}))
    h = History(tmp_path, tmp_path / "rec.json")
    assert h.live and h.log("frozen.json", fmt="%h") == head[:7] and not h.commit_exists("aaaaaaa")


def test_the_committed_record_matches_this_tree_and_dates_the_second_run_freeze_first():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    assert rec["source"]["head"] in rec["commits"]
    for path, e in rec["files"].items():
        assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == e["sha256"], path
        assert e["sha256"] == e["private_sha256"] or e.get("export_redactions"), path
    subs = {p: e for p, e in rec["files"].items() if p.startswith("benchmark/subsets/second-benchmark/")}
    ledgers = {p: e for p, e in rec["files"].items()
               if p.startswith("benchmark/results/second-benchmark/") and p.endswith(".jsonl")}
    assert len(subs) == 9 and len(ledgers) == 33
    assert all(len(e["log"]) == 1 for e in subs.values())
    last_sub = max(int(e["added"][-1].split()[0]) for e in subs.values())
    first_ledger = min(int(e["added"][-1].split()[0]) for e in ledgers.values())
    first_call = rec["first_test_call"]["second-benchmark"]
    from datetime import datetime
    assert last_sub < first_ledger and last_sub < datetime.fromisoformat(first_call.replace("Z", "+00:00")).timestamp()
