"""Perplexity Decider v1.3 extension run: two models on Perplexity's own API, every test row, rescore order. No calls."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "benchmark" / "runs"
TWO = {"pplx-decider-v1-3", "pplx-decider-flash-v1-3"}


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
    r = _load("e2_pplx13_run")
    monkeypatch.setattr(r.ar, "_select_all_tasks", lambda t: {("content", "request"): list(t.rows.values())})
    assert [x["id"] for x in r.select(FakeRows())[("content", "request")]] == ["pub-1", "unp-1"]


def test_two_models_on_perplexity_pinned_to_their_ids():
    r = _load("e2_pplx13_run")
    from goldrails_bench import hosted
    assert r.SYSTEMS == {"pplx-decider-v1-3": ("pplx-decider-v1.3", "perplexity-v1.3"),
                         "pplx-decider-flash-v1-3": ("pplx-decider-flash-v1.3", "perplexity-flash-v1.3")}
    assert r.PINS == {"pplx-decider-v1-3": "pplx-decider-v1.3", "pplx-decider-flash-v1-3": "pplx-decider-flash-v1.3"}
    assert {r.endpoint_of(s) for s in TWO} == {hosted.PERPLEXITY_URL}
    assert {"pplx-decider-v1.3", "pplx-decider-flash-v1.3"} <= hosted.PPLX_PINNED
    assert r.MANIFEST.name == "freeze-manifest-pplx-decider-v1-3.json"
    assert r.WORK.parent.name == "pplx-decider-v1-3" and r.WORK.name == "private"


def test_every_system_has_a_display_name():
    ar = _load("e2_attacks_rerun")
    assert TWO <= set(ar.NAMES)


def test_score_is_the_full_rescore_with_this_run_last(monkeypatch):
    r = _load("e2_pplx13_run")
    import e2_strands_run as strands
    got = {}
    monkeypatch.setattr(r.full, "TestRows", lambda: None)
    mods = {"luna": strands.luna, "jev114": strands.jev114, "strands": strands, "msd1": r.msd1, "pplx12": r.pplx12,
            "hosted8": r.hosted8, "liquid": r.liquid, "gemini": r.gemini, "batch3": r.batch3, "pplx13": r}
    for k, m in mods.items():
        monkeypatch.setattr(m, "write_public", lambda tr: [])
        monkeypatch.setattr(m, "extra_run", lambda k=k: k)
    monkeypatch.setattr(r.ar, "score", lambda rep, extra_runs: got.update(extra=extra_runs) or "out")
    assert r.score() == "out"
    assert got == {"extra": list(mods)}
