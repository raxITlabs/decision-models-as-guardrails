"""Liquid AI open d1 extension run: every test row, template arms, config hash, VM identity, rescore, server. No calls."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

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
    r = _load("e2_liquid_run")
    monkeypatch.setattr(r.ar, "_select_all_tasks", lambda t: {("content", "request"): list(t.rows.values())})
    assert [x["id"] for x in r.select(FakeRows())[("content", "request")]] == ["pub-1", "unp-1"]


def test_two_pinned_models_on_one_card_and_their_own_ports():
    r = _load("e2_liquid_run")
    assert set(r.SYSTEMS) == {"liquid-d1-2b", "liquid-d1-3b"}
    for ref, rev, port, gpu, _ in r.SYSTEMS.values():
        assert ref.startswith("LiquidAI/") and len(rev) == 40 and int(rev, 16) >= 0
    assert len({v[2] for v in r.SYSTEMS.values()}) == 2 and {v[3] for v in r.SYSTEMS.values()} == {0}


def test_roster_example_matches_the_run_module():
    r = _load("e2_liquid_run")
    text = r.ROSTER.read_text()
    assert 'machine_type  = "g2-standard-8"' in text and 'zone          = "us-east4-a"' in text
    for name, (ref, rev, port, gpu, _) in r.SYSTEMS.items():
        assert (f'{{ name = "{name}", kind = "liquid", ref = "{ref}", revision = "{rev}", port = {port}, gpu = {gpu} }}'
                in text)


def test_extension_copies_the_eight_noul_arms_per_model(monkeypatch):
    r = _load("e2_liquid_run")
    arms = r._template_arms()
    assert len(arms) == 8 and {a["system"] for a in arms} == {r.TEMPLATE}
    assert len({a["question_set"] for a in arms}) == 8


def test_config_hash_is_the_scorers_formula():
    r = _load("e2_liquid_run")
    want = hashlib.sha256(json.dumps({"adapter": r.NOUL_ADAPTER, "model": "liquid-d1-2b",
                                      "endpoint": "http://localhost:8031", "question_set": "qs"},
                                     sort_keys=True).encode()).hexdigest()[:16]
    assert r._cfg("liquid-d1-2b", "qs") == want


def test_build_refuses_a_vm_serving_another_revision(monkeypatch):
    r = _load("e2_liquid_run")
    wrong = {"name": "liquid-d1-2b", "url": "http://localhost:8031", "model": "liquid-d1-2b", "kind": "liquid",
             "identity": {"ref": "LiquidAI/d1-2B", "revision": "0" * 40, "kind": "liquid"}}
    monkeypatch.setattr(r.smoke, "liquid_models", lambda: ([wrong], None))
    with pytest.raises(SystemExit, match="the VM serves"):
        r.build({"liquid-d1-2b"})


def test_build_takes_the_pinned_vm_models(monkeypatch):
    r = _load("e2_liquid_run")
    found = [{"name": n, "url": f"http://localhost:{v[2]}", "model": n, "kind": "liquid",
              "identity": r.identity(n)} for n, v in r.SYSTEMS.items()]
    monkeypatch.setattr(r.smoke, "liquid_models", lambda: (found, None))
    systems, skipped = r.build(set(r.SYSTEMS))
    assert set(systems) == set(r.SYSTEMS) and not skipped


def test_vm_identity_of_a_liquid_model_is_ref_revision_kind():
    from goldrails_bench.endpoints import identity_of
    m = {"name": "liquid-d1-2b", "kind": "liquid", "ref": "LiquidAI/d1-2B", "revision": "a" * 40}
    r = _load("e2_liquid_run")
    assert identity_of(m) == {"ref": "LiquidAI/d1-2B", "revision": "a" * 40, "kind": "liquid"}
    assert identity_of({**m, "revision": r.SYSTEMS["liquid-d1-2b"][1]}) == r.identity("liquid-d1-2b")


def test_liquid_is_a_smoke_kind_with_documented_limits():
    r = _load("e2_liquid_run")
    assert "liquid" in r.smoke.KINDS
    assert r.smoke.limit_of("liquid-d1-3b")[0] == 32768 and r.smoke.limit_of("liquid-d1-2b")[0] == 128000


def test_self_hosted_cost_uses_the_full_runs_vm_tariff():
    from goldrails_bench import leaderboard as lb
    r = _load("e2_liquid_run")
    assert "liquid" in lb.SELF_HOSTED_KINDS
    hits = [e for e in lb.load_tariffs()["entries"] if r.HARDWARE in e["match"].get("hardware", [])]
    assert len(hits) == 1 and hits[0]["usd_per_hour"]
    for z in r.ZONES.split():
        assert z.startswith(r.ZONE_PREFIXES)
        h = r.hardware_of(z)
        assert len([e for e in lb.load_tariffs()["entries"] if h in e["match"].get("hardware", [])]) == 1, h


def test_score_is_the_full_rescore_with_this_run_last(monkeypatch):
    r = _load("e2_liquid_run")
    import e2_hosted8_run as hosted8
    import e2_msd1_run as msd1
    import e2_pplx12_run as pplx12
    import e2_strands_run as strands
    got = {}
    monkeypatch.setattr(r.full, "TestRows", lambda: None)
    mods = {"luna": strands.luna, "jev114": strands.jev114, "strands": strands, "msd1": msd1, "pplx12": pplx12,
            "hosted8": hosted8, "liquid": r}
    for k, m in mods.items():
        monkeypatch.setattr(m, "write_public", lambda tr: [])
        monkeypatch.setattr(m, "extra_run", lambda k=k: k)
    monkeypatch.setattr(r.ar, "score", lambda rep, extra_runs: got.update(extra=extra_runs) or "out")
    assert r.score() == "out"
    assert got == {"extra": list(mods)}


def _server():
    spec = importlib.util.spec_from_file_location("liquid_server", ROOT / "infra/gcp/liquid_server.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_server_refuses_a_checkpoint_at_another_revision(tmp_path):
    (tmp_path / ".goldrails-revision").write_text("b" * 40)
    with pytest.raises(SystemExit, match="not " + "a" * 40):
        _server().main(["--checkpoint", str(tmp_path), "--revision", "a" * 40, "--model-name", "x"])


def test_server_needs_a_pinned_source():
    with pytest.raises(SystemExit, match="--checkpoint"):
        _server().main(["--model-name", "x"])


def test_startup_builds_and_allows_the_liquid_kind():
    s = (ROOT / "infra/gcp/startup.sh").read_text()
    assert "goldrails-run-liquid" in s and "(kev|openjev|laya|strands|liquid)" in s
    assert 'LIQUID_PIN="transformers==5.21.0 torch==2.15.0' in s
    assert 'liquid-server-py      = file("${path.module}/liquid_server.py")' in (ROOT / "infra/gcp/main.tf").read_text()
