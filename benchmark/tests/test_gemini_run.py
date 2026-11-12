"""Gemini Decision 1 extension run: every test row, the pinned OpenRouter model, rescore order. No calls."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "benchmark" / "runs"


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
    r = _load("e2_gemini_run")
    monkeypatch.setattr(r.ar, "_select_all_tasks", lambda t: {("content", "request"): list(t.rows.values())})
    assert [x["id"] for x in r.select(FakeRows())[("content", "request")]] == ["pub-1", "unp-1"]


def test_one_openrouter_model_pinned_to_its_snapshot():
    r = _load("e2_gemini_run")
    from goldrails_bench import hosted
    assert r.SYSTEMS == {"gemini-decision-1": ("google/gemini-decision-1", "gemini-decision-1")}
    assert r.PINS == {"gemini-decision-1": "google/gemini-decision-1-20261111"}
    assert r.endpoint_of("gemini-decision-1") == hosted.OPENROUTER_URL
    assert r.MANIFEST.name == "freeze-manifest-gemini-decision-1.json"
    assert r.WORK.parent.name == "gemini-decision-1" and r.WORK.name == "private"


def test_earlier_hosted_run_keeps_its_seven_models():
    h = _load("e2_hosted8_run")
    assert "gemini-decision-1" not in h.SYSTEMS
    assert set(h.SYSTEMS) == {"drex-max", "span-02", "liquid-d1-ultra", "liquid-d1.1", "solar-decide",
                              "solar-decide-flash", "mercury-decide", "clef-omni"}


def test_score_is_the_full_rescore_with_this_run_last(monkeypatch):
    r = _load("e2_gemini_run")
    import e2_strands_run as strands
    got = {}
    monkeypatch.setattr(r.full, "TestRows", lambda: None)
    mods = {"luna": strands.luna, "jev114": strands.jev114, "strands": strands, "msd1": r.msd1, "pplx12": r.pplx12,
            "hosted8": r.hosted8, "liquid": r.liquid, "gemini": r}
    for k, m in mods.items():
        monkeypatch.setattr(m, "write_public", lambda tr: [])
        monkeypatch.setattr(m, "extra_run", lambda k=k: k)
    monkeypatch.setattr(r.ar, "score", lambda rep, extra_runs: got.update(extra=extra_runs) or "out")
    assert r.score() == "out"
    assert got == {"extra": list(mods)}
