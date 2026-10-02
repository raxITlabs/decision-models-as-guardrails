from pathlib import Path

import pytest

from goldrails_bench.data import load_rows

REPO = Path(__file__).resolve().parents[2]
# dataset/samples holds the pilot and the 1k sample, except sample-1k's F5 (PII) files: those held AI4Privacy text
needs_samples = pytest.mark.skipif(not (REPO / "dataset/samples/sample-1k").exists(),
                                   reason="dataset/samples is missing")


@needs_samples
def test_local_rows_load_with_default_and_explicit_source(monkeypatch):
    monkeypatch.delenv("GOLDRAILS_DATA", raising=False)
    rows = load_rows("F1", "tune")
    assert len(rows) == 20 and rows[0].feature == "F1"
    assert len(load_rows("F1", "tune", source="dataset/samples/pilot")) == 20


@needs_samples
def test_rows_carry_their_dataset_identity():
    rows = load_rows("F2", "tune", source="dataset/samples/sample-1k")
    tag = rows[0].dataset
    assert tag["feature"] == "F2" and tag["split"] == "tune" and len(tag["sha256"]) == 64 and all(r.dataset == tag for r in rows)


def test_state_of_carries_grounding_source_and_query():
    from types import SimpleNamespace
    from goldrails_bench.systemone import state_of
    r = SimpleNamespace(state=SimpleNamespace(role="assistant", text="reply", context=[], tool_call=None, source="the doc", query="the question"))
    assert state_of(r) == {"role": "assistant", "text": "reply", "source": "the doc", "query": "the question"}
