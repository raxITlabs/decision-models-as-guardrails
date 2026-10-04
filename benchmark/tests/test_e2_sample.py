"""The dev-split sample runner (benchmark/runs/e2_sample.py) sends public dev rows only, and its ledger records
convert to the shape leaderboard_v2 scores. No model calls."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "dataset" / "edition2" / "build"
pytestmark = pytest.mark.skipif(not all((BUILD / f"F{i}.dev.jsonl").exists() for i in range(1, 7)),
                                reason="edition 2 dev build not present")


def _sample():
    spec = importlib.util.spec_from_file_location("e2_sample", ROOT / "benchmark/runs/e2_sample.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_selection_is_every_public_dev_row_and_the_guard_passes_it():
    m = _sample()
    pt = m.PublicDev()
    sel = m.select_all(pt)
    ids = {r["id"] for rows in sel.values() for r in rows}
    assert ids == set(pt.rows) - m.smoke.excluded_ids()
    for rows in sel.values():
        for r in rows:
            pt.guard(r)


def test_guard_refuses_anything_not_in_the_public_dev_files():
    m = _sample()
    pt = m.PublicDev()
    r = next(iter(pt.rows.values()))
    for bad in ({**r, "id": "f1-not-a-dev-row"}, {**r, "split": "test"}, {**r, "visibility": "private"}):
        with pytest.raises(PermissionError):
            pt.guard(bad)
    changed = copy.deepcopy(r)
    changed["state"]["text"] = (changed["state"].get("text") or "") + " x"
    with pytest.raises(PermissionError):
        pt.guard(changed)


def test_ledger_record_converts_for_the_scorer_without_text():
    m = _sample()
    pt = m.PublicDev()
    rid = next(i for i, f in pt.feature.items() if f == "F5")
    d = {"system": "bedrock-guardrails", "suite": "sensitive_info", "subtask": "entity_detection", "row_id": rid,
         "outcome": "decided", "per_question": {"NAME": 0.8, "EMAIL": 0.0, "any_supported_entity": 0.8},
         "serving": {"model_id": "bedrock-guardrails/invoke-guardrail-checks", "decision_keys": ["any_supported_entity"]},
         "usage": {"text_units": {"sensitiveInformation": 1}}, "latency_s": 0.3, "error": None}
    x = m.scorer_record(d, pt)
    assert x["answers"]["NAME"] == {"type": "noul", "noul": 0.8, "basis": "bedrock_confidence"}
    assert "NAME" in x["decision_keys"] and x["dataset"]["split"] == "dev" and x["ok"]
    assert "state" not in x and x["expected_types"] is not None
    assert m.scorer_record({**d, "outcome": "not_offered"}, pt) is None
