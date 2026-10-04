"""The edition-2 freeze: no fitted thresholds (the fixed rule and frozen service settings only), the overlap check's
bypasses closed (an explicit edition=1 over a v2.0 contract, empty test rows or references, missing v1 release
builds, caller-supplied test rows), the integrity block tied to the frozen dataset files and the arms'
dataset_sha256, and the leaderboard_v2 gate reading a committed manifest end to end, with the v1 record checks
(manifest identity on every record, the frozen retry policy, the commit before the first attempt). The v1 freeze is
unchanged. Local Git only; no network, model or cloud calls."""
import json
import os
import subprocess

import pytest

from goldrails_bench import freeze
from goldrails_bench import leaderboard_v2 as v2
from goldrails_bench.freeze import FreezeError
from goldrails_bench.overlap import OverlapError
from goldrails_bench.policy import DEFAULT_POLICY

BUILDS = [{"id": "f2-v1src-0000000001", "group": "v1g1", "state": {"text": "an examined v1 prompt"},
           "provenance": {"source": "v1src", "source_id": "1"}}]


def row(rid, text, group=None):
    return {"id": rid, "group": group, "state": {"role": "user", "text": text},
            "provenance": {"source": "src", "source_id": rid}}


def record(rid, text, group=None):
    """A valid dataset Record dict (what a frozen F<n>.test.jsonl holds)."""
    return {"id": rid, "feature": "F3", "subtask": "topic", "expected": "no", "labels": ["no", "yes"], "split": "test",
            "group": group, "state": {"role": "user", "text": text, "context": []},
            "category": {"ailuminate": "benign", "bedrock": "NONE", "source_label": "x"},
            "provenance": {"source": "src", "source_id": rid, "licence": "mit", "label_basis": "human",
                           "imported_at": "2026-10-01T00:00:00+00:00"}}


def dataset_file(path, rows):
    """Write rows to a frozen dataset file; returns (path, the runner's dataset hash)."""
    from goldrails_dataset.records import dataset_hash, read_jsonl
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path, (dataset_hash(read_jsonl(path)) if rows else "empty")


TESTS = [record("t1", "first test row"), record("t2", "second test row")]
REFS = {"dev": [row("u1", "a dev row")], "examined": ["x1"], "smoke": ["s1"], "pilot": ["p1"]}
CHECK = {"references": REFS, "v1_build_rows": BUILDS}       # what integrity_problems recomputes the block against


def v1_smoke_doc(scale="probability", version="v1.1"):
    """A tuning-mode (v1 leaderboard) result with one arm and a fitted threshold."""
    return {"mode": "smoke", "contract": {"version": version, "required_suites": ["denied_topics"],
                                          "suites": {"denied_topics": {"subtasks": {"topic": {}}}},
                                          "operating_point": 0.5},
            "arms": [{"arm_id": "m|v1-f3-topics|cfg|tune", "system": "m", "question_set": "v1-f3-topics",
                      "config_hash": "cfg", "suite": "denied_topics", "score_scale": scale,
                      "dataset": {"sha256": "tune"}, "sample_sizes": {"fit_rows": 40},
                      "subtasks": {"topic": {"threshold": {"threshold": 0.37, "threshold_exact": 0.37,
                                                           "basis": "fit"}}}}]}


def write2(tmp_path, doc=None, rows=None, **kw):
    f, sha = dataset_file(tmp_path / "data" / "F3.test.jsonl", TESTS if rows is None else rows)
    args = dict(retry_policy=DEFAULT_POLICY, test_datasets={"denied_topics": sha},
                test_files={"denied_topics": f}, references=REFS, v1_build_rows=BUILDS)
    args.update(kw)
    return freeze.write_manifest(doc or v1_smoke_doc(version="v2.0"), tmp_path / "m.json", **args)


# --- v1 unchanged ----------------------------------------------------------------------------------------------------

def test_v1_freeze_still_writes_fitted_thresholds(tmp_path):
    m = freeze.write_manifest(v1_smoke_doc(), tmp_path / "m.json", retry_policy=DEFAULT_POLICY,
                              test_datasets={"denied_topics": "test"})
    assert m["arms"][0]["thresholds"]["topic"]["threshold"] == 0.37
    assert "edition" not in m and "integrity" not in m and m["scoring"]["module"] == "goldrails_bench.leaderboard"


def test_v1_freeze_with_explicit_edition1_is_unchanged(tmp_path):
    m = freeze.write_manifest(v1_smoke_doc(), tmp_path / "m.json", retry_policy=DEFAULT_POLICY,
                              test_datasets={"denied_topics": "test"}, edition=1)
    assert m["arms"][0]["thresholds"]["topic"]["threshold"] == 0.37


# --- edition 2 writes no fitted thresholds ---------------------------------------------------------------------------

def test_edition2_manifest_records_the_fixed_rule_and_no_threshold(tmp_path):
    m = write2(tmp_path)
    a = m["arms"][0]
    assert "thresholds" not in a and "tuned_on" not in a and m["thresholds_fitted"] is False and m["edition"] == 2
    assert a["decision_rule"] == {"threshold": 0.5, "scale": "probability", "basis": "fixed_probability_rule",
                                  "rule": a["decision_rule"]["rule"]}
    assert "0.37" not in json.dumps(m)                                  # the tuning fit never reaches the manifest
    c = m["contract"]
    assert c["version"] == "v2.0" and c["frozen_settings"]["bedrock_severity"]["threshold"] == 0.5
    assert c["headline_rule"]["operating_point"] == 0.5 and c["max_failure_rate"] == 0.02
    assert m["scoring"]["module"] == "goldrails_bench.leaderboard_v2"
    assert freeze.integrity_problems(m, **CHECK) == []


def test_edition2_manifest_from_a_leaderboard_v2_result_keeps_each_arms_rule(tmp_path):
    doc = {"schema": v2.SCHEMA, "contract": {"version": "v2.0"},
           "arms": [{"arm_id": "bedrock|bedrock-f1|cfg|tune", "system": "bedrock", "question_set": "bedrock-f1",
                     "config_hash": "cfg", "suite": "denied_topics", "score_scale": "ordered_steps",
                     "decision_rule": {"threshold": 0.5, "scale": "ordered_steps", "basis": "frozen_documented_setting",
                                       "rule": "frozen documented setting: flag at score >= 0.5 (bedrock_severity)"}}]}
    m = write2(tmp_path, doc)
    assert m["arms"][0]["decision_rule"]["basis"] == "frozen_documented_setting"


def test_edition2_refuses_an_arm_without_a_fixed_rule(tmp_path):
    with pytest.raises(FreezeError, match="frozen setting depends"):
        write2(tmp_path, v1_smoke_doc(scale="service_score", version="v2.0"))
    doc = {"schema": v2.SCHEMA, "contract": {"version": "v2.0"},
           "arms": [{"arm_id": "x", "system": "x", "question_set": "q", "config_hash": "c", "suite": "denied_topics",
                     "decision_rule": {"threshold": None, "rule": "no frozen documented setting"}}]}
    with pytest.raises(FreezeError, match="no fixed rule"):
        write2(tmp_path, doc)
    assert not (tmp_path / "m.json").exists()


# --- overlap bypasses ------------------------------------------------------------------------------------------------

def test_explicit_edition1_cannot_override_a_v2_contract(tmp_path):
    with pytest.raises(FreezeError, match="conflicts with contract v2.0"):
        freeze.write_manifest(v1_smoke_doc(version="v2.0"), tmp_path / "m.json", retry_policy=DEFAULT_POLICY,
                              test_datasets={"denied_topics": "test"}, edition=1)
    assert not (tmp_path / "m.json").exists()


@pytest.mark.parametrize("kw,msg", [({"rows": []}, "has no rows"),
                                    ({"references": {}}, "no reference rows"),
                                    ({"references": []}, "no reference rows"),
                                    ({"references": {"dev": [], "examined": []}}, "no reference rows"),
                                    ({"references": {"dev": [row("u1", "x")], "smoke": []}}, "roles with no rows"),
                                    ({"v1_build_rows": []}, "no v1 release build rows")])
def test_empty_inputs_fail_the_integrity_check(tmp_path, kw, msg):
    with pytest.raises(FreezeError, match=msg):
        write2(tmp_path, **kw)
    assert not (tmp_path / "m.json").exists()


def test_missing_v1_release_builds_fail_instead_of_falling_back_to_id_only(tmp_path, monkeypatch):
    monkeypatch.setattr(freeze, "v1_release_build_files", lambda repo=None: [])
    with pytest.raises(FreezeError, match="no v1 release builds"):
        write2(tmp_path, v1_build_rows=None)
    assert not (tmp_path / "m.json").exists()


def test_v1_release_build_rows_resolve_bare_examined_ids(tmp_path):
    # the examined id is bare; only the v1 build row carries its text, so the copy is caught by text
    refs = {**REFS, "examined": ["f2-v1src-0000000001"]}
    with pytest.raises(OverlapError) as e:
        write2(tmp_path, rows=[record("t9", "An  examined V1 prompt")], references=refs)
    assert {"text"} <= {o["kind"] for o in e.value.report.overlaps}
    m = write2(tmp_path, references=refs)
    assert m["integrity"]["bare_reference_ids"] == {"total": 3, "resolved_through_pool": 1}   # examined, smoke, pilot
    assert m["integrity"]["reference_rows"]["v1_release_builds"] == 1


# --- the integrity block is tied to the frozen datasets --------------------------------------------------------------

def test_edition2_refuses_caller_supplied_test_rows(tmp_path):
    with pytest.raises(FreezeError, match="frozen dataset files"):
        write2(tmp_path, test_rows=[row("t1", "x")])
    assert not (tmp_path / "m.json").exists()


def test_edition2_needs_the_dataset_files_of_every_suite(tmp_path):
    with pytest.raises(FreezeError, match="test_files"):
        write2(tmp_path, test_files=None)
    with pytest.raises(FreezeError, match="no frozen test dataset file for suite denied_topics"):
        write2(tmp_path, test_files={"denied_topics": []})
    with pytest.raises(FreezeError, match="no test dataset version: content"):
        write2(tmp_path, test_files={"denied_topics": tmp_path / "data" / "F3.test.jsonl", "content": "x.jsonl"})
    with pytest.raises(FreezeError, match="do not exist"):
        write2(tmp_path, test_files={"denied_topics": tmp_path / "missing.jsonl"})
    assert not (tmp_path / "m.json").exists()


def test_edition2_refuses_files_that_do_not_hash_to_the_arms_dataset(tmp_path):
    with pytest.raises(FreezeError, match="not the arms' dataset version"):
        write2(tmp_path, test_datasets={"denied_topics": "0" * 64})
    assert not (tmp_path / "m.json").exists()


def test_edition2_integrity_records_each_suites_dataset(tmp_path):
    m = write2(tmp_path)
    d = m["integrity"]["datasets"]["denied_topics"]
    assert d["sha256"] == m["arms"][0]["dataset_sha256"] and d["rows"] == 2 == m["integrity"]["test_rows"]
    assert d["files"][0]["path"].endswith("F3.test.jsonl") and len(d["files"][0]["sha256"]) == 64
    assert freeze.integrity_problems(m, **CHECK) == []


def test_edition2_test_rows_come_from_the_files_so_an_overlap_in_them_is_caught(tmp_path):
    # the overlapping row is only in the dataset file; nobody passes it in
    with pytest.raises(OverlapError):
        write2(tmp_path, rows=TESTS + [record("u1", "a dev row")])


@pytest.mark.parametrize("edit,msg", [
    (lambda m: m["integrity"].pop("datasets"), "names no frozen datasets"),
    (lambda m: m["arms"][0].update(dataset_sha256="f" * 64), "did not cover"),
    (lambda m: m["integrity"]["datasets"]["denied_topics"].update(sha256="f" * 64), "did not cover"),
    (lambda m: m["integrity"].update(test_rows=1), "not the 2 rows of its datasets"),
    (lambda m: m["integrity"]["datasets"]["denied_topics"].pop("files"), "lacks its sha256, row count or files"),
])
def test_a_manifest_whose_integrity_block_does_not_match_its_arms_is_rejected(tmp_path, edit, msg):
    m = write2(tmp_path)
    edit(m)
    assert any(msg in p for p in freeze.integrity_problems(m, **CHECK))


# --- the integrity block is recomputed, never taken on trust ----------------------------------------------------------

@pytest.mark.parametrize("refs,msg", [({"dev": [row("u1", "x")], "examined": ["x1"]}, "missing: smoke, pilot"),
                                      ({**REFS, "junk": ["j1"]}, "unknown reference roles: junk")])
def test_edition2_freeze_needs_exactly_the_checks_reference_roles(tmp_path, refs, msg):
    with pytest.raises(FreezeError, match=msg):
        write2(tmp_path, references=refs)
    assert not (tmp_path / "m.json").exists()


@pytest.mark.parametrize("edit,msg", [
    (lambda m: m["integrity"]["reference_rows"].update(junk=3), "unknown reference roles: junk"),
    (lambda m: m["integrity"]["reference_rows"].pop("smoke"), "required reference roles: smoke"),
    (lambda m: m["integrity"].update(reference_rows={"junk": 9, "v1_release_builds": 1}), "required reference roles"),
    (lambda m: m["integrity"]["reference_rows"].update(dev=40), "more reference rows than exist for: dev"),
    (lambda m: m["integrity"].update(check="by hand"), "not written by the overlap check"),
    (lambda m: m["integrity"].update(v1_release_build_rows=7), "v1 release build rows"),
])
def test_a_forged_integrity_block_is_rejected(tmp_path, edit, msg):
    m = write2(tmp_path)
    edit(m)
    assert any(msg in p for p in freeze.integrity_problems(m, **CHECK))


def test_a_hand_written_block_with_consistent_numbers_is_rejected(tmp_path):
    """Every number agrees with every other and with the arms, but the rows behind it are not what it says: the
    recomputation reads the files, so the forgery shows."""
    m = write2(tmp_path)
    f = tmp_path / "data" / "F3.test.jsonl"
    # a block claiming three rows in a file that holds two
    d = m["integrity"]["datasets"]["denied_topics"]
    m["integrity"].update(test_rows=3)
    d.update(rows=3)
    assert any("differ from the recomputed" in p or "test rows" in p for p in freeze.integrity_problems(m, **CHECK))
    # a block naming a file that is not there
    m = write2(tmp_path)
    m["integrity"]["datasets"]["denied_topics"]["files"][0]["path"] = str(tmp_path / "nowhere.jsonl")
    assert any("cannot be reproduced" in p and "do not exist" in p for p in freeze.integrity_problems(m, **CHECK))
    # the frozen file edited after the freeze (a row swapped in that a reference already holds)
    m = write2(tmp_path)
    f.write_text(f.read_text().replace("second test row", "a dev row"))
    assert any("no longer has the sha256" in p for p in freeze.integrity_problems(m, **CHECK))


def test_a_block_that_no_longer_passes_against_the_references_is_rejected(tmp_path):
    m = write2(tmp_path)
    assert freeze.integrity_problems(m, **CHECK) == []
    later = {**REFS, "examined": REFS["examined"] + ["t2"]}           # a test row examined since the freeze
    probs = freeze.integrity_problems(m, references=later, v1_build_rows=BUILDS)
    assert any("cannot be reproduced" in p and "overlap" in p.lower() for p in probs)
    assert freeze.integrity_problems(m, references=later, v1_build_rows=BUILDS, recompute=False) == []


def test_recompute_reads_the_repository_references_by_default(tmp_path):
    refs = freeze.default_references()
    assert set(freeze.REQUIRED_REFERENCE_ROLES) <= set(refs)
    assert refs["examined"] and refs["smoke"] and refs["pilot"]


def test_the_v1_build_role_is_reserved(tmp_path):
    with pytest.raises(FreezeError, match="reserved"):
        write2(tmp_path, references={"v1_release_builds": [row("u1", "x")]})


def test_v1_release_rows_read_builds_from_a_checkout(tmp_path):
    b = tmp_path / "dataset" / "release" / "v1.0" / "build"
    b.mkdir(parents=True)
    (b / "F1.test.jsonl").write_text(json.dumps({"id": "f1-a-0000000001", "group": "g", "state": {"text": "hi"},
                                                 "provenance": {"source": "a", "source_id": "1"}, "x": 1}) + "\n")
    rows = freeze.v1_release_rows(tmp_path)
    assert rows == [{"id": "f1-a-0000000001", "group": "g", "provenance": {"source": "a", "source_id": "1"},
                     "state": {"text": "hi"}}]
    with pytest.raises(FreezeError, match="no v1 release builds"):
        freeze.v1_release_rows(tmp_path / "empty")


# --- the leaderboard_v2 gate, end to end -----------------------------------------------------------------------------

def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_DATE="2020-01-01T00:00:00+0000", GIT_COMMITTER_DATE="2020-01-01T00:00:00+0000")
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                          check=True, capture_output=True, text=True, env=env)


def rec(i, split, dsha, score=None):
    pos = i < 20
    return {"question_set": "v1-f3-topics", "system": "m", "id": f"f3-t-{i}", "subtask": "topic",
            "expected": "yes" if pos else "no", "ok": True, "config_hash": "cfg-m", "decision_keys": ["q"],
            "answers": {"q": {"type": "noul", "noul": score if score is not None else (0.9 if pos else 0.1)}},
            "group": f"g{i}", "latency_s": 0.1, "model": "m",
            "dataset": {"source": "none", "feature": "F3", "split": split, "sha256": dsha}}


def test_leaderboard_v2_scores_a_test_run_against_a_committed_edition2_manifest(tmp_path):
    c = v2.load_contract()
    c = {**c, "required_suites": ["denied_topics"]}
    dev = v2.evaluate([rec(i, "dev", "ddev") for i in range(40)], c, report_split="dev", replicates=10, seed=1)
    assert dev["arms"][0]["decision_rule"]["threshold"] == 0.5 and dev["arms"][0]["run"]["valid"] is True
    assert dev["mode"] == "not a test run" and dev["valid_for_publication"] is False
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    path = repo / "manifest.json"
    f, dtest = dataset_file(tmp_path / "data" / "F3.test.jsonl", TESTS)
    freeze.write_manifest(dev, path, retry_policy=DEFAULT_POLICY, test_datasets={"denied_topics": dtest},
                          test_files={"denied_topics": f}, references=REFS, v1_build_rows=BUILDS, contract=c)
    with pytest.raises(FreezeError, match="not committed"):
        v2.load_freeze(path, CHECK)
    git(repo, "add", "manifest.json")
    git(repo, "commit", "-q", "-m", "freeze")       # committed at 2020-01-01T00:00:00Z
    with pytest.raises(FreezeError, match="v1 release build"):     # recomputed against this repository's builds
        v2.load_freeze(path)
    m, ident = v2.load_freeze(path, CHECK)
    frozen = {dtest: {f"f3-t-{i}": {"id": f"f3-t-{i}", "subtask": "topic", "expected": "yes" if i < 20 else "no",
                                    "expected_types": None, "group": f"g{i}", "split": "test"} for i in range(40)}}
    pol = json.loads(json.dumps(DEFAULT_POLICY.identity()))
    stamp = freeze.record_stamp(ident)

    def run(over=None):
        recs = []
        for i in range(40):
            r = {**rec(i, "test", dtest), "retry_policy": pol, "freeze": stamp,
                 "attempts": [{"at": "2021-06-01T00:00:00Z"}]}
            r.update((over or {}).get(i, {}))
            recs.append(r)
        return v2.evaluate(recs, c, replicates=10, seed=1, frozen=frozen, manifest=m, manifest_identity=ident,
                           integrity=CHECK)

    doc = run()
    assert doc["mode"] == "frozen" and doc["arms"][0]["run"]["valid"] is True
    assert doc["freeze"]["manifest_sha256"] == ident["manifest_sha256"] and doc["freeze"]["commit"] == ident["commit"]
    assert [e["name"] for e in doc["overall"]["ranking"]] == ["m"]
    assert not any("freeze manifest froze a different contract" in b for b in doc["publication_blockers"])
    assert doc["freeze"]["records"]["pass"] is True and doc["freeze"]["records"]["test_records"] == 40
    assert not any(b.startswith("freeze:") for b in doc["publication_blockers"])
    # the v1 checks, restored: an attempt before the commit, another retry policy, a missing or other manifest stamp
    early = run({0: {"attempts": [{"at": "2019-12-31T23:59:59Z"}]}})
    assert any("not before the first test attempt" in b for b in early["publication_blockers"])
    assert early["valid_for_publication"] is False
    other = run({1: {"retry_policy": {**pol, "max_attempts": 99}}})
    assert any("retry policy other than the frozen one" in b for b in other["publication_blockers"])
    unstamped = run({2: {"freeze": None}, 3: {"freeze": {**stamp, "manifest_sha256": "0" * 64}}})
    bl = unstamped["publication_blockers"]
    assert any("1 test records carry no manifest identity" in b for b in bl)
    assert any("1 test records carry a different manifest sha256" in b for b in bl)
    untimed = run({4: {"attempts": []}})
    assert any("no attempt timestamps" in b for b in untimed["publication_blockers"])
    no_ident = v2.evaluate([{**rec(i, "test", dtest), "retry_policy": pol, "freeze": stamp,
                             "attempts": [{"at": "2021-06-01T00:00:00Z"}]} for i in range(40)], c, replicates=10,
                           seed=1, frozen=frozen, manifest=m, integrity=CHECK)
    assert any("identity" in b for b in no_ident["publication_blockers"])


def test_leaderboard_v2_refuses_a_committed_v1_manifest(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    path = repo / "manifest.json"
    freeze.write_manifest(v1_smoke_doc(), path, retry_policy=DEFAULT_POLICY, test_datasets={"denied_topics": "test"})
    git(repo, "add", "manifest.json")
    git(repo, "commit", "-q", "-m", "v1 freeze")
    with pytest.raises(FreezeError, match="not an edition-2 manifest"):
        v2.load_freeze(path)
