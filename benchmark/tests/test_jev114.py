"""Jev 1.14.0 wiring: the smoke kind, the tariff, and the extension run's template arms and config hash. No calls."""
import importlib.util
import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "runs"


def _load(name):
    sys.path.insert(0, str(RUNS))
    spec = importlib.util.spec_from_file_location(name, RUNS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_smoke_skips_jev_114_without_a_key():
    m = _load("e2_smoke")
    systems, skipped = m.build_systems({"jev-1.14"}, env={})
    assert systems == {} and skipped["jev-1.14"].startswith("not_configured")


def test_smoke_pins_jev_114_by_its_versioned_id():
    m = _load("e2_smoke")
    systems, skipped = m.build_systems({"jev-1.14"}, env={"TYPESAFE_API_KEY": "k"})
    assert skipped == {} and set(systems) == {"jev-1.14.0"}
    adapter, workers = systems["jev-1.14.0"]
    assert adapter.client.model == "jev-1.14.0" and adapter.endpoint == "https://api.typesafe.ai" and workers == 8
    assert m.limit_of("jev-1.14.0") == (32000, "documented")


def test_tariff_prices_jev_114():
    from goldrails_bench import leaderboard as lb
    hits = [e for e in lb.load_tariffs()["entries"] if "jev-1.14.0" in e["match"].get("models", [])]
    assert len(hits) == 1 and hits[0]["prices"]["input_tokens"]["usd_per_million"] == 0.042


def test_extension_copies_jev_113s_eight_arms_and_its_config_hash_rule():
    r = _load("e2_jev114_run")
    arms = r._template_arms()
    assert len(arms) == 8 and {a["system"] for a in arms} == {"jev-1.13.0"}
    assert len({a["question_set"] for a in arms}) == 8
    # the same hash rule, given Jev 1.13.0's model id, reproduces every frozen Jev 1.13.0 arm
    for a in arms:
        assert r._cfg(a["question_set"]) != a["config_hash"]
        r.SYSTEM, saved = "jev-1.13.0", r.SYSTEM
        try:
            assert r._cfg(a["question_set"]) == a["config_hash"]
        finally:
            r.SYSTEM = saved
    assert not r.MANIFEST.exists() or json.loads(r.MANIFEST.read_text())["run"]["systems"] == ["jev-1.14.0"]
