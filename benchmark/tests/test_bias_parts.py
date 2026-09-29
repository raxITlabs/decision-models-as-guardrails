"""The three-part bias view copies bias.json exactly: every number, denominator and status, plus flags that follow
bias.json's own low_support and min_support. No score is recomputed."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

RUNS = Path(__file__).resolve().parents[1] / "runs"
_spec = importlib.util.spec_from_file_location("bias_parts", RUNS / "bias_parts.py")
bp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bp)

if not bp.SOURCE.exists():
    pytest.skip("bias.json not present", allow_module_level=True)


@pytest.fixture(scope="module")
def source():
    return json.loads(bp.SOURCE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def bias(source):
    return source["bias"]


@pytest.fixture(scope="module")
def parts(source):
    return bp.build(source, bp.sha256(bp.SOURCE))


def test_three_parts_named_exactly(parts):
    assert parts["parts"] == ["Hate and discrimination detection", "Guardrail fairness diagnostics",
                              "Decision-model bias diagnostics"]
    assert parts["hate_detection"]["part"] == "Hate and discrimination detection"
    assert parts["guardrail_fairness"]["part"] == "Guardrail fairness diagnostics"
    assert parts["decision_model_bias"]["part"] == "Decision-model bias diagnostics"


def test_meta_points_at_source(parts):
    m = parts["meta"]
    assert m["source"] == "benchmark/results/first-benchmark/bias.json"
    assert m["source_sha256"] == bp.sha256(bp.SOURCE) and len(m["source_sha256"]) == 64
    assert m["generated_by"] == "benchmark/runs/bias_parts.py"
    assert "copied from bias.json" in m["note"]
    assert m["aggregate"] is None


def test_hate_detection_is_a_pointer_with_no_number(parts):
    h = parts["hate_detection"]
    assert h["separate_score"] is None
    assert "content suite" in h["location"]
    assert not any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in h.values() if v is not None)


def test_b1_numbers_equal_bias_json(parts, bias):
    src = {(s["system"], s["config_hash"]): s for s in bias["guardrail_fairness"]["systems"]}
    got = parts["guardrail_fairness"]["systems"]
    assert [(s["system"], s["config_hash"]) for s in got] == list(src)
    for s in got:
        b = src[(s["system"], s["config_hash"])]
        for k in ("kind", "threshold", "threshold_policy", "failure_policy"):
            assert s[k] == b[k]
        assert s["B1"]["quality"] == b["B1"]["quality"]
        for k in bp.CELL_KEYS:
            assert s["B1"]["overall"][k] == b["B1"]["overall"][k]
        assert s["B1"]["overall"]["rows_without_annotation"] == b["B1"]["overall"]["rows_without_annotation"]
        assert [g["identity"] for g in s["B1"]["identities"]] == [g["identity"] for g in b["B1"]["identities"]]
        for g, bg in zip(s["B1"]["identities"], b["B1"]["identities"]):
            for side in ("mentioned", "not_mentioned"):
                for k in bp.CELL_KEYS:
                    assert g[side][k] == bg[side][k], (s["system"], g["identity"], side, k)
            assert g["fpr_gap_vs_not_mentioned"] == bg["fpr_gap"]
            assert g["fnr_gap_vs_not_mentioned"] == bg["fnr_gap"]
            assert g["unknown_annotation"] == bg["unknown_annotation"]
            assert g["low_support"] == bg["low_support"]


def test_b1_denominators_carried(parts, bias):
    src = {s["system"]: s for s in bias["guardrail_fairness"]["systems"]}
    for s in parts["guardrail_fairness"]["systems"]:
        for g, bg in zip(s["B1"]["identities"], src[s["system"]]["B1"]["identities"]):
            for side in ("mentioned", "not_mentioned"):
                assert g[side]["n_benign"] == bg[side]["fpr_denominator"]
                assert g[side]["n_harmful"] == bg[side]["fnr_denominator"]
                assert g[side]["benign"] == bg[side]["benign"] and g[side]["harmful"] == bg[side]["harmful"]


def test_insufficient_evidence_follows_low_support_and_min_support(parts, bias):
    ms = bias["guardrail_fairness"]["min_support"]
    assert parts["guardrail_fairness"]["min_support"] == ms
    for s in parts["guardrail_fairness"]["systems"]:
        for g in s["B1"]["identities"]:
            dens = [g[side][k] for side in ("mentioned", "not_mentioned") for k in ("n_benign", "n_harmful")]
            assert g["insufficient_evidence"] == (g["low_support"] or any(d < ms for d in dens))
            assert bool(g["insufficient_evidence_reasons"]) == g["insufficient_evidence"]


def test_identity_view_flags_small_denominator_even_without_low_support():
    c = {k: 0 for k in bp.CELL_KEYS}
    big = {**c, "fpr_denominator": 40, "fnr_denominator": 40}
    small = {**c, "fpr_denominator": 40, "fnr_denominator": 5}
    g = {"identity": "x", "mentioned": small, "not_mentioned": big, "unknown_annotation": {},
         "fpr_gap": {"value": None, "interval": None}, "fnr_gap": {"value": None, "interval": None},
         "low_support": False}
    v = bp.identity_view(g, 30)
    assert v["insufficient_evidence"] is True and v["low_support"] is False
    assert bp.identity_view({**g, "mentioned": big}, 30)["insufficient_evidence"] is False
    assert bp.identity_view({**g, "mentioned": big, "low_support": True}, 30)["insufficient_evidence"] is True


def test_b2_consistency_and_correctness_equal_bias_json(parts, bias):
    src = {s["system"]: s["B2"] for s in bias["guardrail_fairness"]["systems"]}
    ms = bias["guardrail_fairness"]["min_support"]
    for s in parts["guardrail_fairness"]["systems"]:
        b, v = src[s["system"]], s["B2"]
        assert v["n_pairs"] == b["counts"]["sets"]
        assert v["n_pairs_evaluable"] == b["counts"]["evaluable"]
        assert v["counts"] == b["counts"]
        assert v["consistency"]["flip_rate"] == b["flip_rate"]
        assert v["consistency"]["flip_rate_interval"] == b["flip_rate_interval"]
        assert v["consistency"]["flips"] == b["counts"]["flips"]
        c = v["correctness"]
        assert c["paired_correct_rate"] == b["paired_correct_rate"]
        assert c["paired_correct_interval"] == b["paired_correct_interval"]
        assert c["paired_correctness_denominator"] == b["paired_correctness_denominator"]
        assert c["all_correct"] == b["counts"]["all_correct"] and c["all_wrong"] == b["counts"]["all_wrong"]
        assert c["consistent_wrong_rate"] == b["consistent_wrong_rate"]
        assert v["by_expected"] == b["by_expected"] and v["quality"] == b["quality"]
        assert v["too_few_pairs"] == (b["counts"]["evaluable"] < ms)


def test_consistency_sentence_present(parts):
    s = parts["guardrail_fairness"]["consistency_vs_correctness"]
    assert "allows everything" in s and "perfectly consistent" in s and "failing its task" in s


def test_bedrock_not_applicable_in_decision_model_bias(parts, bias):
    src = [e for e in bias["decision_bias"]["systems"] if e["status"] == "not_applicable"]
    assert [e["system"] for e in src] == ["bedrock-checks"]
    v = {s["system"]: s for s in parts["decision_model_bias"]["systems"]}["bedrock-checks"]
    assert v["status"] == "not_applicable" and v["reason"] == src[0]["reason"]
    assert v["bbq"]["status"] == v["discrim_eval"]["status"] == "not_applicable"
    assert "result" not in v["bbq"] and "result" not in v["discrim_eval"]


def test_b3_results_equal_bias_json(parts, bias):
    views = {s["system"]: s for s in parts["decision_model_bias"]["systems"]}
    assert set(views) == {e["system"] for e in bias["decision_bias"]["systems"]}
    for e in bias["decision_bias"]["systems"]:
        v = views[e["system"]]
        if "bbq" in e:
            assert v["bbq"]["result"] == e["bbq"] and v["bbq"]["config_hash"] == e["config_hash"]
        if "discrim_eval" in e:
            assert v["discrim_eval"]["result"] == e["discrim_eval"]
            assert v["discrim_eval"]["config_hash"] == e["config_hash"]
        if e["status"] == "not_evaluated":
            assert {"config_hash": e["config_hash"], "status": "not_evaluated"}.items() <= next(
                c for c in v["not_evaluated_configs"] if c["config_hash"] == e["config_hash"]).items()


def test_discrim_eval_flagged_unmatched(parts, bias):
    why = next(w for w in bias["status"]["why"] if w.startswith("discrim-eval"))
    for s in parts["decision_model_bias"]["systems"]:
        de = s["discrim_eval"]
        if de["status"] == "evaluated":
            assert de["unmatched_scenarios"] is True and de["unmatched_note"] == why
            assert de["insufficient_evidence"] is True and de["isolates_demographic_bias"] is False


def test_not_evaluated_when_no_b3_entry():
    bias = {"status": {"why": [], "reading": "r"}, "notes": {"B3": "n"},
            "decision_bias": {"tracks": ["B3"], "systems": [
                {"system": "m", "kind": "decision_model", "config_hash": "a", "status": "not_evaluated"}]}}
    v = bp.decision_part(bias)["systems"][0]
    assert v["status"] == "not_evaluated"
    assert v["bbq"] == {"status": "not_evaluated"} and v["discrim_eval"] == {"status": "not_evaluated"}


def test_source_is_not_modified(source):
    before = copy.deepcopy(source)
    bp.build(source, "x")
    assert source == before


def test_written_file_is_current(parts):
    if not bp.OUT.exists():
        pytest.skip("bias-parts.json not generated")
    assert json.loads(bp.OUT.read_text(encoding="utf-8")) == json.loads(json.dumps(parts, sort_keys=True))
