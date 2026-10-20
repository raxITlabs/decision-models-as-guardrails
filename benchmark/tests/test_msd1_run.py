"""Microsoft-Decision-1 extension run: every test row, template arms, config hash, run hook, rescore. No calls."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

RUNS = Path(__file__).resolve().parents[1] / "runs"


def _load(name):
    sys.path.insert(0, str(RUNS))
    spec = importlib.util.spec_from_file_location(name, RUNS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class FakeRows:
    """Duck-types e2_full.TestRows for select() and the guard."""

    def __init__(self):
        self.rows = {"pub-1": {"id": "pub-1", "split": "test"}, "unp-1": {"id": "unp-1", "split": "test"}}
        self.unpublished = {"unp-1"}
        self.guarded = []

    def public_ids(self):
        return set(self.rows) - self.unpublished

    def guard(self, r):
        self.guarded.append(r["id"])


def test_select_keeps_the_unpublished_slice(monkeypatch):
    r = _load("e2_msd1_run")
    tr = FakeRows()
    monkeypatch.setattr(r.ar, "_select_all_tasks", lambda t: {("content", "request"): list(t.rows.values())})
    assert [x["id"] for x in r.select(tr)[("content", "request")]] == ["pub-1", "unp-1"]


def test_extension_copies_the_eight_noul_arms():
    r = _load("e2_msd1_run")
    arms = r._template_arms()
    assert len(arms) == 8 and {a["system"] for a in arms} == {r.TEMPLATE}
    assert len({a["question_set"] for a in arms}) == 8


def test_config_hash_is_reproduced_by_the_smoke_ledger():
    r = _load("e2_msd1_run")
    if not r.SMOKE.exists():
        pytest.skip("no smoke ledger")
    seen = {}
    for x in r.SMOKE.open(encoding="utf-8"):
        s = json.loads(x)["serving"]
        seen.setdefault(s["question_set"], s)
    assert set(seen) == {a["question_set"] for a in r._template_arms()}
    for qs, s in seen.items():
        h = hashlib.sha256(json.dumps({"adapter": s["adapter"], "model": s["model_id"], "endpoint": s["endpoint"],
                                       "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16]
        assert h == r._cfg(qs)


def test_run_hook_builds_msd1_without_recursing(monkeypatch):
    r = _load("e2_msd1_run")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(r.smoke, "build_systems", lambda kinds, env=None: r.build())   # as run() installs it
    systems, _ = r.smoke.build_systems({"microsoft"})
    assert set(systems) == {"microsoft-decision-1"} and systems["microsoft-decision-1"][1] == r.WORKERS


def test_score_is_the_full_rescore_with_this_run_ranked(monkeypatch):
    r = _load("e2_msd1_run")
    import e2_strands_run as strands
    got = {}
    monkeypatch.setattr(r.full, "TestRows", lambda: None)
    for m in (strands.luna, strands.jev114, strands, r):
        monkeypatch.setattr(m, "write_public", lambda tr: [])
    monkeypatch.setattr(strands.luna, "extra_run", lambda: "luna")
    monkeypatch.setattr(strands.jev114, "extra_run", lambda: "jev114")
    monkeypatch.setattr(strands, "extra_run", lambda: "strands")
    monkeypatch.setattr(r, "extra_run", lambda: "msd1")
    monkeypatch.setattr(r.ar, "score", lambda rep, extra_runs: got.update(extra=extra_runs) or "out")
    assert r.score() == "out"
    assert got == {"extra": ["luna", "jev114", "strands", "msd1"]}


def test_manifest_if_present_covers_every_row_and_names_the_superseded_one():
    r = _load("e2_msd1_run")
    if not r.MANIFEST.exists():
        pytest.skip("not frozen yet")
    run = json.loads(r.MANIFEST.read_text())["run"]
    assert run["systems"] == ["microsoft-decision-1"] and "ruling 36" in run["row_scope"]
    assert run["supersedes"]["manifest"].endswith("freeze-manifest-microsoft-decision-1.json")


def test_tariff_matches_the_model_id_the_records_carry():
    from goldrails_bench import leaderboard as lb
    t = lb.load_tariffs()
    e = lb.tariff_for({"model": "microsoft/microsoft-decision-1"}, None, t)
    assert e is not None and e["prices"]["input_tokens"]["usd_per_million"] == 0.042
