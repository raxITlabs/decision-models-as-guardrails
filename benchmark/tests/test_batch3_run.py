"""Hosted batch 3 extension run: ten OpenRouter decision models, every test row, rescore order. No calls."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "benchmark" / "runs"
TEN = {"heygen-decision-1", "heygen-decision-1-turbo", "mammoth-1", "elephant-1", "joey-1", "morph-reflex",
       "drex-v2.0", "drex-v1.5", "tev1-4b", "liquid-d1"}


def _load(name):
    sys.path.insert(0, str(RUNS))
    spec = importlib.util.spec_from_file_location(name, RUNS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeRows:
    def __init__(self):
        self.rows = {"pub-1": {"id": "pub-1", "split": "test"}, "unp-1": {"id": "unp-1", "split": "test"}}
        self.unpublished = {"unp-1"}


def test_select_keeps_the_unpublished_slice(monkeypatch):
    r = _load("e2_batch3_run")
    monkeypatch.setattr(r.ar, "_select_all_tasks", lambda t: {("content", "request"): list(t.rows.values())})
    assert [x["id"] for x in r.select(FakeRows())[("content", "request")]] == ["pub-1", "unp-1"]


def test_ten_openrouter_models_pinned_to_their_snapshots():
    r = _load("e2_batch3_run")
    from goldrails_bench import hosted
    assert set(r.SYSTEMS) == TEN
    for s in TEN:
        assert r.SYSTEMS[s] == (hosted.OPENROUTER_DECIDERS[s]["model"], s)
        assert r.PINS[s] == hosted.OPENROUTER_DECIDERS[s]["snapshot"]
        assert r.endpoint_of(s) == hosted.OPENROUTER_URL
    assert r.MANIFEST.name == "freeze-manifest-hosted-batch-3.json"
    assert r.WORK.parent.name == "hosted-batch-3" and r.WORK.name == "private"


def test_left_out_models_are_not_in_the_run():
    r = _load("e2_batch3_run")
    assert not {"scaledown-classify-1", "pplx-decider-v1.3-free", "pplx-decider-flash-v1.3-free"} & set(r.SYSTEMS)


def test_every_system_has_a_display_name():
    ar = _load("e2_attacks_rerun")
    assert TEN <= set(ar.NAMES)


def test_score_is_the_full_rescore_with_this_run_last(monkeypatch):
    r = _load("e2_batch3_run")
    import e2_strands_run as strands
    got = {}
    monkeypatch.setattr(r.full, "TestRows", lambda: None)
    mods = {"luna": strands.luna, "jev114": strands.jev114, "strands": strands, "msd1": r.msd1, "pplx12": r.pplx12,
            "hosted8": r.hosted8, "liquid": r.liquid, "gemini": r.gemini, "batch3": r}
    for k, m in mods.items():
        monkeypatch.setattr(m, "write_public", lambda tr: [])
        monkeypatch.setattr(m, "extra_run", lambda k=k: k)
    monkeypatch.setattr(r.ar, "score", lambda rep, extra_runs: got.update(extra=extra_runs) or "out")
    assert r.score() == "out"
    assert got == {"extra": list(mods)}
