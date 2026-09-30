"""Run context for a second benchmark run: default paths are the first run's, a new run writes only under its own
directories, freezes refuse to overwrite or to write into the first run's records, tune and freeze refuse a frozen run
other than their own, superseded arms are skipped outside the first run, the PII question set falls back to the sole
declared candidate, and the offline builders follow the run. No network, model or cloud calls: clients and the runner
are replaced by fakes."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RUNS = REPO / "benchmark" / "runs"
MODULES = ("run_context", "first_benchmark", "extension_run", "pii_v12_run", "profanity_v13_run", "leaderboard_v13",
           "bias_results", "bias_parts", "validate_extension_freeze", "serving_from_ledger", "bias_audit_copy", "plan_run")
BUILDS = all((REPO / "dataset" / "release" / v / "build" / "F1.tune.jsonl").exists() for v in ("v1.0", "v1.1-ai", "v1.2", "v1.3"))
needs_builds = pytest.mark.skipif(not BUILDS, reason="release builds not present (dataset/release/*/build)")


@pytest.fixture
def load(monkeypatch):
    """load(run=None, frozen=None, tmp=None) -> importer; with ``tmp`` the results and subsets roots move there."""
    monkeypatch.syspath_prepend(str(RUNS))

    def purge():
        for m in MODULES:
            sys.modules.pop(m, None)

    def setup(run=None, frozen=None, tmp=None):
        purge()
        for k, v in (("GOLDRAILS_RUN", run), ("GOLDRAILS_FROZEN_RUN", frozen)):
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)
        monkeypatch.delenv("GOLDRAILS_VM_ZONE", raising=False)
        rc = importlib.import_module("run_context")
        if tmp is not None:
            monkeypatch.setattr(rc, "RESULTS", tmp / "results")
            monkeypatch.setattr(rc, "SUBSETS", tmp / "subsets")
        return lambda name: importlib.import_module(name)

    yield setup
    purge()


def files_under(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


# --- default context is today's layout -----------------------------------------------------------------------------

def test_default_context_is_first_run_paths(load):
    imp = load()
    res, sub = REPO / "benchmark" / "results" / "first-benchmark", REPO / "benchmark" / "subsets" / "first-benchmark"
    FB = imp("first_benchmark")
    assert FB.SUBSET == "first-benchmark"
    assert (FB.OUT, FB.MANIFEST, FB.MANIFEST_OUT) == (res, sub / "freeze-manifest.json", sub / "freeze-manifest.json")
    assert FB.SELECTION == FB.SELECTION_OUT == res / "selection.json"
    assert FB.DEFAULT_SUITES == FB.ALL_SUITES
    assert FB.CTX.default_contract(None) is None          # the leaderboard's built-in contract, as before
    EXT = imp("extension_run")
    assert EXT.ext_path(1) == sub / "freeze-extension-1.json"
    assert EXT.selection_path(1) == res / "ext-selection.json" and EXT.selection_path(2) == res / "ext-selection-2.json"
    assert EXT.CONTRACT == REPO / "benchmark" / "contracts" / "v1.1.json"
    assert EXT.DEFAULT_STAGES == list(EXT.STAGES)
    PII, PROF = imp("pii_v12_run"), imp("profanity_v13_run")
    assert (PII.EXT, PII.SELECTION) == (sub / "freeze-extension-3.json", res / "pii-v12-selection.json")
    assert (PROF.EXT, PROF.SELECTION) == (sub / "freeze-extension-4.json", res / "prof-v13-selection.json")
    assert PII.CONTRACT == PROF.CONTRACT == REPO / "benchmark" / "contracts" / "v1.1.json"
    LB = imp("leaderboard_v13")
    assert (LB.RES, LB.SUB) == (res, sub)
    BR, BP, VE = imp("bias_results"), imp("bias_parts"), imp("validate_extension_freeze")
    assert (BR.RES, BR.MANIFEST) == (res, sub / "freeze-manifest.json")
    assert (BP.SOURCE, BP.OUT) == (res / "bias.json", res / "bias-parts.json")
    assert (VE.RES, VE.SUB, VE.LEADERBOARD) == (res, sub, res / "leaderboard-v1.3.json")


def test_leaderboard_inputs_for_first_run_match_the_old_command(load):
    imp = load()
    LB = imp("leaderboard_v13")
    res, sub = LB.RES, LB.SUB
    for final in (True, False):
        contract = "benchmark/contracts/v1.1-signed.json" if final else "benchmark/contracts/v1.1.json"
        approvals = sorted(sub.glob("analysis-approval-5*.json")) if final else [sub / "analysis-approval-4.json"]
        old = [sys.executable, "-m", "goldrails_bench.leaderboard", "L", "--mode", "final",
               "--contract", contract, "--freeze-manifest", str(sub / "freeze-manifest.json"),
               *[x for n in (1, 2, 3, 4) for x in ("--extension-manifest", str(sub / f"freeze-extension-{n}.json"))],
               *[x for p in approvals for x in ("--analysis-approval", str(p))],
               "--implementations", str(sub / "implementations-v1.3.json"),
               "--serving", str(res / "serving-v13.json"), "--out", "O"]
        assert LB.command(["L"], LB.inputs(final, res, sub), "O") == old


def test_run_ids_are_checked(load):
    imp = load()
    RC = imp("run_context")
    with pytest.raises(SystemExit):
        RC.current({"GOLDRAILS_RUN": "../first-benchmark"})
    assert RC.current({"GOLDRAILS_RUN": "second-benchmark"}).frozen_run == "second-benchmark"


# --- a new run writes only under its own directories ---------------------------------------------------------------

class _Row:
    def __init__(self, i, subtask="x", source="s", sha="d" * 64):
        self.id, self.subtask, self.dataset = f"r{i}", subtask, {"sha256": sha}
        self.provenance = type("P", (), {"source": source})()


def _fake_doc(suites):
    return {"mode": "smoke", "contract": {"version": "v1.1", "hash": "h", "required_suites": list(suites),
                                          "suites": {s: {"subtasks": {"t": {}}} for s in suites}},
            "arms": [{"arm_id": f"sys|q{s}|c{s}", "system": "sys", "suite": s, "question_set": f"q-{s}",
                      "config_hash": f"c{s}", "suite_score": {"value": 1.0}, "sample_sizes": {"fit_rows": 1},
                      "dataset": {"sha256": "t" * 64}, "subtasks": {}} for s in suites]}


def _fake_freeze_env(monkeypatch, FB, suites_seen):
    import goldrails_bench.leaderboard as lb

    def build(paths, contract_path=None, mode="auto", **kw):
        suites_seen.append(contract_path)
        return _fake_doc(["content", "prompt_attacks", "word_filters", "sensitive_info", "grounding"])
    monkeypatch.setattr(lb, "build", build)
    monkeypatch.setattr(FB, "load_subset_rows", lambda *a: [_Row(0)])
    monkeypatch.setattr(FB, "clients", lambda kinds, suite: {})


def test_new_run_writes_only_under_its_own_directories(load, tmp_path, monkeypatch):
    imp = load("second-benchmark", tmp=tmp_path)
    FB = imp("first_benchmark")
    seen = []
    _fake_freeze_env(monkeypatch, FB, seen)
    calls = []

    def fake_run_matrix(systems, qsets, rows, results_path=None, freeze_manifest=None, **kw):
        calls.append((results_path, freeze_manifest))
        Path(results_path).parent.mkdir(parents=True, exist_ok=True)
        Path(results_path).open("a").write("{}\n")
        return []
    monkeypatch.setattr(FB, "run_matrix", fake_run_matrix)
    monkeypatch.setattr(FB, "clients", lambda kinds, suite: {"fake": (object(), None)})
    monkeypatch.setattr(FB, "load_subset_rows", lambda *a: [_Row(0, "b1_disparate_fpr", "bbq"), _Row(1, "b3_decision", "bbq")])
    FB.main(["tune"])
    _fake_freeze_env(monkeypatch, FB, seen)
    FB.main(["freeze"])
    assert seen[-1] == str(REPO / "benchmark" / "contracts" / "v1.1-signed.json")
    assert {Path(p).parent for p, _ in calls} == {tmp_path / "results" / "second-benchmark"}
    assert not (tmp_path / "results" / "first-benchmark").exists() and not (tmp_path / "subsets" / "first-benchmark").exists()
    assert files_under(tmp_path / "subsets") == ["second-benchmark/freeze-manifest.json", "second-benchmark/selection.json"]
    m = json.loads((tmp_path / "subsets" / "second-benchmark" / "freeze-manifest.json").read_text())
    assert "sensitive_info" not in {a["suite"] for a in m["arms"]}          # superseded core F5 is not frozen
    assert m["run"]["skipped_superseded"].keys() == {"sensitive_info"}
    sel = json.loads((tmp_path / "subsets" / "second-benchmark" / "selection.json").read_text())
    assert sel["run"]["suites"] == ["content", "prompt_attacks", "word_filters", "grounding", "bias_b1", "bias_b3"]


def test_test_stage_reads_frozen_run_and_writes_own_run(load, tmp_path, monkeypatch):
    imp = load("rerun-x", frozen="second-benchmark", tmp=tmp_path)
    FB = imp("first_benchmark")
    assert FB.OUT == tmp_path / "results" / "rerun-x"
    assert FB.MANIFEST == tmp_path / "subsets" / "second-benchmark" / "freeze-manifest.json"
    assert FB.SELECTION == tmp_path / "subsets" / "second-benchmark" / "selection.json"
    EXT = imp("extension_run")
    assert EXT.ext_path(1).parent == EXT.selection_path(1).parent == tmp_path / "subsets" / "second-benchmark"


# --- freeze guards ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("script,path", [("first_benchmark", "freeze-manifest.json"),
                                         ("extension_run", "freeze-extension-1.json"),
                                         ("pii_v12_run", "freeze-extension-3.json"),
                                         ("profanity_v13_run", "freeze-extension-4.json")])
def test_freeze_refuses_to_overwrite(load, tmp_path, script, path):
    imp = load("second-benchmark", tmp=tmp_path)
    mod = imp(script)
    target = tmp_path / "subsets" / "second-benchmark" / path
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    with pytest.raises(SystemExit, match="refuses to overwrite"):
        mod.main(["freeze"])
    assert target.read_text() == "{}"


@pytest.mark.parametrize("script", ["first_benchmark", "extension_run", "pii_v12_run", "profanity_v13_run"])
def test_freeze_refuses_first_benchmark_locations(load, tmp_path, script):
    imp = load(tmp=tmp_path)                                  # nothing set: the first run
    mod = imp(script)
    with pytest.raises(SystemExit, match="first benchmark's records"):
        mod.main(["freeze"])
    assert files_under(tmp_path) == []


def test_call_stages_refuse_first_benchmark_without_flag(load, tmp_path):
    imp = load(tmp=tmp_path)
    FB = imp("first_benchmark")
    with pytest.raises(SystemExit, match="first benchmark's records"):
        FB.main(["tune"])
    RC = imp("run_context")
    assert RC.is_protected(tmp_path / "results" / "first-benchmark-v1.2" / "x.json")
    assert not RC.is_protected(tmp_path / "results" / "second-benchmark" / "x.json")
    RC.refuse_protected([tmp_path / "results" / "first-benchmark" / "x"], True, "t")   # the explicit flag lets it through


@pytest.mark.parametrize("script", ["first_benchmark", "extension_run", "pii_v12_run", "profanity_v13_run"])
@pytest.mark.parametrize("stage", ["tune", "freeze"])
def test_tune_and_freeze_refuse_other_frozen_run(load, tmp_path, script, stage):
    imp = load("second-benchmark", frozen="first-benchmark", tmp=tmp_path)
    with pytest.raises(SystemExit, match="differs"):
        imp(script).main([stage])
    assert files_under(tmp_path) == []


# --- superseded arms ---------------------------------------------------------------------------------------------------

def test_superseded_suites_excluded_for_second_benchmark(load, tmp_path):
    imp = load("second-benchmark", tmp=tmp_path)
    FB, EXT = imp("first_benchmark"), imp("extension_run")
    assert "sensitive_info" not in FB.DEFAULT_SUITES and set(FB.ALL_SUITES) - set(FB.DEFAULT_SUITES) == {"sensitive_info"}
    assert EXT.DEFAULT_STAGES == ["denied_topics", "bias_b2"]
    assert FB.parse_suites("content,sensitive_info") == ["content", "sensitive_info"]   # an explicit list wins
    with pytest.raises(SystemExit):
        FB.parse_suites("nope")


@needs_builds
def test_dry_run_builds_no_client_and_skips_superseded(load, tmp_path, monkeypatch, capsys):
    imp = load("second-benchmark", tmp=tmp_path)
    FB = imp("first_benchmark")
    monkeypatch.setattr(FB, "clients", lambda *a: (_ for _ in ()).throw(AssertionError("built a client")))
    p = FB.plan_stage("tune", {"open", "jev", "regex", "bedrock"}, "tune", None, None, FB.DEFAULT_SUITES)
    assert "sensitive_info" not in {x["suite"] for x in p.lines}
    by = {Path(k).name: v for k, v in p.by_ledger().items()}
    assert by == {"tune.jsonl": 3592, "tune-bias.jsonl": 780}          # first run: 3,942 + 780, less 350 core F5 rows
    assert FB.main(["test", "--dry-run"]) == 0
    assert "DRY RUN" in capsys.readouterr().out
    assert files_under(tmp_path) == []


# --- PII question set --------------------------------------------------------------------------------------------------

def test_pii_question_set_fallback(load, tmp_path):
    imp = load("second-benchmark", tmp=tmp_path)
    PII = imp("pii_v12_run")
    impl = PII.FB.IMPL
    names = set(impl["systems"]["decision_models"]) | {"bedrock-checks"}
    chosen, rule = PII.question_set_rule(tmp_path / "absent.json")            # no core selection yet (at tune time)
    assert chosen == {n: "v2-f5-pii" for n in names} and "sole sensitive_info candidate" in rule
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({"chosen": [{"system": "jev-1.13.0", "suite": "content", "question_set": "v1-f1-bedrock5"}]}))
    assert PII.question_set_rule(sel)[0] == chosen                             # core selection without F5
    two = json.loads(json.dumps(impl))
    two["candidate_question_sets"]["sensitive_info"] = ["v2-f5-pii", "v1-f5-pii"]
    with pytest.raises(SystemExit, match="exactly one"):
        PII.question_set_rule(sel, two)


def test_pii_question_set_unchanged_for_first_run(load):
    imp = load()
    PII = imp("pii_v12_run")
    chosen, rule = PII.question_set_rule()
    first = json.loads((REPO / "benchmark" / "results" / "first-benchmark" / "pii-v12-selection.json").read_text())
    assert rule == first["rule"] == PII.RULE_FROZEN
    assert chosen == {c["system"]: c["question_set"] for c in first["chosen"]}


# --- offline builders ----------------------------------------------------------------------------------------------------

def test_leaderboard_v13_run_aware_paths(load, tmp_path):
    imp = load("second-benchmark", tmp=tmp_path)
    LB = imp("leaderboard_v13")
    res, sub = tmp_path / "results" / "second-benchmark", tmp_path / "subsets" / "second-benchmark"
    assert (LB.RES, LB.SUB) == (res, sub)
    res.mkdir(parents=True); sub.mkdir(parents=True)
    for n in ("freeze-manifest", "freeze-extension-1", "freeze-extension-3", "freeze-extension-4"):
        (sub / f"{n}.json").write_text("{}")
    inp = LB.inputs(False, res, sub)
    assert inp["contract"] == "benchmark/contracts/v1.1-signed.json" and inp["approvals"] == []
    assert [p.name for p in inp["extensions"]] == ["freeze-extension-1.json", "freeze-extension-3.json", "freeze-extension-4.json"]
    assert inp["serving"] == res / "serving-v13.json"
    assert inp["implementations"] == REPO / "benchmark" / "subsets" / "first-benchmark" / "implementations-v1.3.json"
    with pytest.raises(SystemExit, match="no serving records"):               # never the first run's serving file
        LB.main(["--final"])
    with pytest.raises(SystemExit, match="missing ledger"):
        LB.default_ledgers(tmp_path, res)
    for n in ("test", "ext-test", "pii-v12-test", "prof-v13-test"):           # no test-rerun: tolerated
        (res / f"{n}.jsonl").write_text(json.dumps({"id": "f1-x"}) + "\n")
    args, dropped = LB.default_ledgers(tmp_path, res)
    assert not any("test-rerun" in a for a in args) and dropped == {"old PII rows": 0, "lexicon-selected profanity rows": 0}


def test_zone_fields_and_serving_hardware(load, tmp_path):
    imp = load()
    RC, SL = imp("run_context"), imp("serving_from_ledger")
    hw = RC.DEFAULT_HARDWARE
    assert RC.zone_fields(hw, None) == {} and RC.zone_fields(hw, "us-east4-c") == {"zone": "us-east4-c"}
    note = RC.zone_fields(hw, "us-central1-a")
    assert note["zone"] == "us-central1-a" and "us-east4 tariff" in note["pricing_note"]
    ledger = tmp_path / "l.jsonl"
    ledger.write_text(json.dumps({"system": "kev-4b", "question_set": "q", "config_hash": "c", "dataset": {"sha256": "d"},
                                  "attempts": [{"started_at": "2026-09-30T00:00:00.000Z", "ended_at": "2026-09-30T00:00:10.000Z"}]}) + "\n")
    SL.main([str(ledger), "--out", str(tmp_path / "a.json")])
    SL.main([str(ledger), "--out", str(tmp_path / "b.json"), "--zone", "us-west1-a"])
    a, b = json.loads((tmp_path / "a.json").read_text())[0], json.loads((tmp_path / "b.json").read_text())[0]
    assert a["hardware"] == b["hardware"] == hw and "zone" not in a
    assert b["zone"] == "us-west1-a" and "pricing_note" in b


def test_bias_builders_follow_the_run(load, tmp_path):
    imp = load("second-benchmark", tmp=tmp_path)
    BR, BP, VE, BA = imp("bias_results"), imp("bias_parts"), imp("validate_extension_freeze"), imp("bias_audit_copy")
    res = tmp_path / "results" / "second-benchmark"
    assert BR.RES == BP.RES == VE.RES == res and BP.SOURCE == res / "bias.json"
    assert VE.LEADERBOARD == res / "leaderboard-final.json"
    with pytest.raises(SystemExit, match="no bias ledgers"):
        BA.main([])


def test_bias_audit_copy_marks_first_run_outcomes(load):
    imp = load()
    BA = imp("bias_audit_copy")
    with pytest.raises(SystemExit, match="first run's records"):              # never rewrites the source
        BA.main([])
    src = json.loads(BA.SOURCE.read_text())
    ids = BA.bias_ids(BA.SOURCE_RES)
    doc = BA.build(src, "sha", "second-benchmark", ids, ids)
    marked = doc["run_copy"]["outcome_statements"]
    assert {m["path"] for m in marked} == {"tasks/0/flags/2/detail", "tasks/1/evidence/detail"}
    assert doc["tasks"][0]["flags"][2]["outcomes_from"] == "first-benchmark"
    assert all(v["same_ids_as_first_benchmark"] for v in doc["run_copy"]["bias_row_ids"].values())
    assert {k: len(v) for k, v in ids.items()} == {"b1": 100, "b2": 8, "b3:bbq": 150, "b3:discrim_eval": 50}
