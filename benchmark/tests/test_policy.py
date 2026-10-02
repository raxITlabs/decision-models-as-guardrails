"""The frozen failure/retry policy, the zero-credit primary score, dataset-origin reporting, and resume keys."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from goldrails_bench import policy as P
from goldrails_bench.runner import run_matrix
from goldrails_bench.score import load_ledger, primary_credit, summarise
from goldrails_dataset.records import Category, Provenance, Record, State

REPO = Path(__file__).resolve().parents[2]
QS = {"s": {"questions": {"q": {"type": "noul", "instructions": "?"}}, "decision": ["q"]}}


class Scripted:
    """Returns the scripted outcomes in order: an error string fails that attempt, None succeeds with noul 0.8."""
    def __init__(self, script, system="api"):
        self.script, self.system, self.calls = list(script), system, 0

    def ask(self, state, questions):
        self.calls += 1
        err = self.script.pop(0) if self.script else None
        ok = err is None
        return SimpleNamespace(ok=ok, error=err, model="m", latency_s=0.01, usage={"input_tokens": 2},
                               answers={k: {"type": "noul", "noul": 0.8} for k in questions} if ok else None, raw={})


def row(i=0, text="hello", sha=None):
    r = Record(id=f"r{i}", feature="F2", subtask="injection", state=State(role="user", text=text), labels=["no", "yes"],
               category=Category(ailuminate=None, bedrock=None, source_label="x"), expected="yes", split="tune",
               provenance=Provenance(source="t", source_id=str(i), licence="cc0", label_basis="deterministic", imported_at="2026-09-23"))
    r.dataset = {"source": "fixture", "feature": "F2", "split": "tune", "sha256": sha} if sha else None
    return r


quiet = {"progress": lambda *_: None}


# --- retries -----------------------------------------------------------------------------------------------------

def test_no_retry_policy_makes_one_attempt_and_the_failure_is_exhausted():
    c = Scripted(["APIConnectionError: reset"])
    out = run_matrix({"api": c}, QS, [row()], policy=P.NO_RETRY, **quiet)
    r = out[0]
    assert c.calls == 1 and not r["ok"] and r["exhausted"] and r["retries"] == 0
    assert r["retry_policy"]["max_retries"] == 0 and len(r["attempts"]) == 1 and r["attempts"][0]["error"].startswith("APIConnectionError")


def test_default_policy_retries_transient_errors_only():
    assert P.DEFAULT_POLICY.max_retries == 3
    assert P.DEFAULT_POLICY.retryable("APIConnectionError: reset") and not P.DEFAULT_POLICY.retryable("ValueError: bad answer")


def test_transient_errors_are_retried_within_budget_and_every_attempt_is_kept():
    c = Scripted(["APITimeoutError: slow", "ThrottlingException: busy", None])
    pol = P.RetryPolicy(max_retries=3, name="t3")
    r = run_matrix({"api": c}, QS, [row()], policy=pol, **quiet)[0]
    assert r["ok"] and not r["exhausted"] and r["retries"] == 2 and c.calls == 3
    assert [a["ok"] for a in r["attempts"]] == [False, False, True] and all(a["usage"] for a in r["attempts"])


def test_retry_budget_runs_out_and_the_row_is_exhausted():
    c = Scripted(["ReadTimeout: x"] * 5)
    r = run_matrix({"api": c}, QS, [row()], policy=P.RetryPolicy(max_retries=2), **quiet)[0]
    assert c.calls == 3 and r["exhausted"] and not r["ok"] and r["retries"] == 2


def test_non_transient_failures_are_never_retried():
    c = Scripted(["UnrepresentableState: cannot carry context", None])
    r = run_matrix({"api": c}, QS, [row()], policy=P.RetryPolicy(max_retries=3), **quiet)[0]
    assert c.calls == 1 and r["exhausted"]


def test_backoff_doubles_and_negative_budgets_are_rejected():
    waits = []
    P.RetryPolicy(max_retries=3, backoff_s=1.5).wait(1, waits.append)
    P.RetryPolicy(max_retries=3, backoff_s=1.5).wait(3, waits.append)
    assert waits == [1.5, 6.0]
    with pytest.raises(ValueError):
        P.RetryPolicy(max_retries=-1)


def test_exhausted_failures_are_final_on_resume(tmp_path):
    path = tmp_path / "run.jsonl"
    run_matrix({"api": Scripted(["APIConnectionError: x"])}, QS, [row()], results_path=path, **quiet)
    again = Scripted([])
    assert run_matrix({"api": again}, QS, [row()], results_path=path, policy=P.RetryPolicy(max_retries=3), **quiet) == [] and again.calls == 0


# --- primary credit --------------------------------------------------------------------------------------------

def rec(expected, ok=True, noul=None, system="a", sha="d1", dataset=True, note=None, rid=None):
    answers = None if not ok else ({"q": {"type": "noul", "noul": noul}} if noul is not None else {})
    d = {"source": "fixture", "feature": "F2", "split": "tune", "sha256": sha} if dataset else None
    if d and note:
        d["rehash_note"] = note
    return {"system": system, "question_set": "s", "config_hash": "c", "dataset": d, "id": rid or f"{expected}{noul}{ok}",
            "ok": ok, "answers": answers, "expected": expected, "subtask": "injection", "decision_keys": ["q"]}


@pytest.mark.parametrize("expected", ["yes", "no"])
def test_failed_and_no_decision_rows_earn_no_credit_in_either_class(expected):
    assert primary_credit(rec(expected, ok=False)) == 0
    assert primary_credit(rec(expected, ok=True, noul=None)) == 0
    right = 0.9 if expected == "yes" else 0.1
    assert primary_credit(rec(expected, noul=right)) == 1 and primary_credit(rec(expected, noul=1 - right)) == 0


def test_primary_score_counts_failures_as_misses_while_diagnostics_are_unchanged():
    rs = [rec("yes", noul=0.9, rid="p1"), rec("yes", ok=False, rid="p2"), rec("yes", noul=None, rid="p3"), rec("yes", noul=0.2, rid="p4"),
          rec("no", noul=0.1, rid="n1"), rec("no", ok=False, rid="n2")]
    line, = P.primary_summary(rs)
    assert (line["failed"], line["no_decision"], line["decided"]) == (2, 1, 3)
    assert line["violation_recall"] == 1 / 4 and line["benign_pass_rate"] == 1 / 2
    assert line["primary_score"] == pytest.approx(100 * 0.5 * (0.25 + 0.5))
    assert line["conditional_score"] == pytest.approx(100 * 0.5 * (0.5 + 1.0)) and line["failure_rate"] == pytest.approx(3 / 6)
    # the existing diagnostic still excludes failures by default: accuracy over the 3 decided rows only
    diag, = summarise(rs)
    assert diag["decided"] == 3 and diag["failed"] == 2 and diag["accuracy"] == pytest.approx(2 / 3)


def test_always_block_scores_fifty_under_the_primary_metric():
    rs = [rec("yes", noul=1.0, rid=f"p{i}") for i in range(9)] + [rec("no", noul=1.0, rid="n0")]
    assert P.primary_summary(rs)[0]["primary_score"] == 50.0


def test_unlabelled_rows_are_counted_and_not_scored():
    rs = [rec("yes", noul=0.9, rid="p"), rec("no", noul=0.1, rid="n"), rec(None, noul=0.9, rid="u")]
    line, = P.primary_summary(rs)
    assert line["unlabelled"] == 1 and line["primary_score"] == 100.0


# --- dataset origin --------------------------------------------------------------------------------------------

def versions(rel):
    return [{"ref": "working", "sha_old": "w_old", "sha_new": "work", "rows": {}},
            {"ref": "abc1234", "sha_old": "c_old", "sha_new": "committed", "rows": {"r1": "rh1"}}]


def test_origin_is_verified_only_when_the_version_is_in_a_commit():
    base = {"source": "fixture", "feature": "F2", "split": "tune"}
    assert P.origin_of({"id": "r1", "dataset": {**base, "sha256": "committed"}}, versions)[0] == P.VERIFIED
    assert P.origin_of({"id": "r1", "dataset": {**base, "sha256": "c_old"}}, versions)[0] == P.VERIFIED
    assert P.origin_of({"id": "r1", "dataset": {**base, "sha256": "work"}}, versions) == (P.UNVERIFIABLE, "matches the uncommitted working copy only")
    assert P.origin_of({"id": "r1", "dataset": {**base, "sha256": "gone"}}, versions)[0] == P.UNVERIFIABLE
    assert P.origin_of({"id": "r1", "row_hash": "other", "dataset": {**base, "sha256": "committed"}}, versions)[0] == P.UNVERIFIABLE
    assert P.origin_of({"id": "r1", "dataset": None}, versions) == (P.UNVERIFIABLE, "no dataset identity on the record")
    noted = {**base, "sha256": "committed", "rehash_note": "kept: origin version not in git"}
    assert P.origin_of({"id": "r1", "dataset": noted}, versions)[0] == P.UNVERIFIABLE
    assert P.origin_of({"id": "r1", "dataset": {**base, "sha256": "committed"}})[0] == P.UNCHECKED   # no git lookup given


def test_unverifiable_rows_are_never_pooled_with_verified_rows():
    rs = [rec("yes", noul=0.9, sha="committed", rid="r1"), rec("no", noul=0.1, sha="committed", rid="r2"),
          rec("yes", noul=0.1, sha="committed", note="kept: origin version not in git", rid="r3"),
          rec("no", noul=0.9, dataset=False, rid="r4")]
    lines = P.primary_summary(rs, versions_of=versions)
    by = {(l["dataset_sha"], l["origin"]): l for l in lines}
    assert set(by) == {("committed", P.VERIFIED), ("committed", P.UNVERIFIABLE), (None, P.UNVERIFIABLE)}
    assert by[("committed", P.VERIFIED)]["n"] == 2 and by[("committed", P.VERIFIED)]["primary_score"] == 100.0
    md = P.origin_report(rs, versions_of=versions)
    assert "2 of 4 records have **origin unverifiable**" in md and "no dataset identity on the record" in md


@pytest.mark.skipif(not (REPO / "benchmark/results/pilot-cloud-pass.jsonl").exists(),
                    reason="checks the committed pilot ledger, benchmark/results/pilot-cloud-pass.jsonl, which is missing")
def test_existing_ledgers_report_their_earliest_rows_as_origin_unverifiable():
    """Read-only check against committed evidence: the word-filter smoke ledger's first 21 rows name a dataset version
    that is in no commit, and the pilot ledger predates dataset tags altogether."""
    words = load_ledger(REPO / "benchmark/results/smoke-word-filters.jsonl", dedupe=False)
    get = P.cached_versions()
    flagged = [r for r in words if "not in git" in ((r.get("dataset") or {}).get("rehash_note") or "")]
    assert len(flagged) == 21 and all(P.origin_of(r, get)[0] == P.UNVERIFIABLE for r in flagged)
    assert "origin unverifiable" in P.origin_report(words, versions_of=get)
    pilot = load_ledger(REPO / "benchmark/results/pilot-cloud-pass.jsonl", dedupe=False)
    assert {P.origin_of(r, get)[0] for r in pilot} == {P.UNVERIFIABLE}


# --- resume keys -----------------------------------------------------------------------------------------------

def test_resume_reruns_a_row_whose_content_changed_under_the_same_id_and_dataset_tag(tmp_path):
    path = tmp_path / "run.jsonl"
    run_matrix({"api": Scripted([])}, QS, [row(0, "original", sha="same")], results_path=path, **quiet)
    unchanged = Scripted([])
    assert run_matrix({"api": unchanged}, QS, [row(0, "original", sha="same")], results_path=path, **quiet) == [] and unchanged.calls == 0
    edited = Scripted([])
    out = run_matrix({"api": edited}, QS, [row(0, "edited text", sha="same")], results_path=path, **quiet)
    assert edited.calls == 1 and len(out) == 1
    hashes = [json.loads(l)["row_hash"] for l in path.read_text().splitlines()]
    assert len(set(hashes)) == 2


def test_resume_reruns_a_changed_row_even_without_a_dataset_tag(tmp_path):
    path = tmp_path / "run.jsonl"
    run_matrix({"api": Scripted([])}, QS, [row(0, "original")], results_path=path, **quiet)
    c = Scripted([])
    run_matrix({"api": c}, QS, [row(0, "edited")], results_path=path, **quiet)
    assert c.calls == 1


def test_resume_reruns_after_an_edited_question_wording(tmp_path):
    path = tmp_path / "run.jsonl"
    run_matrix({"api": Scripted([])}, QS, [row()], results_path=path, **quiet)
    edited = {"s": {"questions": {"q": {"type": "noul", "instructions": "reworded"}}, "decision": ["q"]}}
    c = Scripted([])
    assert len(run_matrix({"api": c}, edited, [row()], results_path=path, **quiet)) == 1 and c.calls == 1


def test_legacy_records_without_a_row_hash_are_rerun_not_trusted(tmp_path):
    path = tmp_path / "run.jsonl"
    run_matrix({"api": Scripted([])}, QS, [row(sha="same")], results_path=path, **quiet)
    legacy = [json.loads(l) for l in path.read_text().splitlines()]
    for r in legacy:
        r.pop("row_hash")
    path.write_text("".join(json.dumps(r) + "\n" for r in legacy))
    c = Scripted([])
    run_matrix({"api": c}, QS, [row(sha="same")], results_path=path, **quiet)
    assert c.calls == 1


def test_sdk_prefixed_transient_errors_are_retryable():
    assert P.TRANSIENT_3.retryable("TypeSafeAPIConnectionError: Connection error: reset by peer")
    assert not P.TRANSIENT_3.retryable("TypeSafeBadRequestError: 400")


def test_attempts_record_measured_start_and_end_times():
    """Serving windows need the call's real start: ``at`` is the completion time, to the second."""
    import re
    from types import SimpleNamespace
    from goldrails_bench.policy import attempt_record
    call = SimpleNamespace(ok=True, error=None, latency_s=1.25, usage={})
    a = attempt_record(call, 0, 1, started=1_790_000_000.125, ended=1_790_000_001.375)
    assert a["started_at"] == "2026-09-21T14:13:20.125Z" and a["ended_at"] == "2026-09-21T14:13:21.375Z"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", a["at"])
