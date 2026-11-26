"""Strands Decider v2 extension run: pinned checkpoints, roster, window, config hash, VM identity, rescore, launcher.
No calls."""
import hashlib
import importlib.util
import json
import re
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


@pytest.fixture(scope="module")
def r():
    return _load("e2_strands_v2_run")


def test_five_pinned_checkpoints_on_their_own_ports_in_three_passes(r):
    assert set(r.SYSTEMS) == {"strands-decider-e2b-v2", "strands-decider-e4b-v2", "strands-decider-12b-v2",
                              "strands-decider-26b-a4b-v2", "strands-decider-31b-v2"}
    for ref, rev, port, p, _ in r.SYSTEMS.values():
        assert re.fullmatch(r"StrandsAgents/strands-decider-[0-9A-Za-z-]+-gemma4-v2-2611", ref)
        assert re.fullmatch(r"[0-9a-f]{40}", rev) and p in r.PASSES
    assert len({v[2] for v in r.SYSTEMS.values()}) == 5
    assert r.names_of(2) == ["strands-decider-26b-a4b-v2"] and r.names_of(3) == ["strands-decider-31b-v2"]
    assert re.fullmatch(r"[0-9a-f]{40}", r.CODE_SHA) and r.MAX_LENGTH == 32768


def test_v2_names_do_not_collide_with_v1(r):
    v1 = _load("e2_strands_run")
    assert not set(r.SYSTEMS) & set(v1.SYSTEMS)
    assert set(r.V1_OF.values()) <= set(v1.SYSTEMS) and set(r.V1_OF) < set(r.SYSTEMS)
    assert r.OUT != v1.OUT and r.MANIFEST != v1.MANIFEST


def test_roster_example_matches_the_run_module(r):
    text = r.ROSTER.read_text()
    assert 'machine_type  = "a2-ultragpu-1g"' in text and "boot_disk_gb  = 300" in text
    blocks = re.findall(r"^#?\s*models = \[\n(.*?)^#?\s*\]", text, re.S | re.M)
    assert len(blocks) == len(r.PASSES)
    for name, (ref, rev, port, p, _) in r.SYSTEMS.items():
        line = (f'{{ name = "{name}", kind = "strands", ref = "{ref}", revision = "{rev}", port = {port}, gpu = 0, '
                f'code_sha = "{r.CODE_SHA}", max_length = {r.MAX_LENGTH} }}')
        assert line in blocks[p - 1], name


def test_extension_copies_strands_decider_2bs_eight_arms(r):
    arms = r._template_arms()
    assert len(arms) == 8 and {a["system"] for a in arms} == {r.TEMPLATE}


def test_config_hash_is_the_scorers_formula(r):
    want = hashlib.sha256(json.dumps({"adapter": r.NOUL_ADAPTER, "model": "strands-decider-31b-v2",
                                      "endpoint": "http://localhost:8044", "question_set": "qs"},
                                     sort_keys=True).encode()).hexdigest()[:16]
    assert r._cfg("strands-decider-31b-v2", "qs") == want


def _served(r, name, **over):
    ref, rev, port, _, _ = r.SYSTEMS[name]
    ident = {"ref": ref, "revision": rev, "kind": "strands", "code_sha": r.CODE_SHA, "max_length": r.MAX_LENGTH, **over}
    return {"name": name, "url": f"http://localhost:{port}", "model": name, "kind": "strands", "identity": ident}


def test_build_takes_the_pinned_vm_models(r, monkeypatch):
    monkeypatch.setattr(r.smoke, "strands_models", lambda: ([_served(r, n) for n in r.SYSTEMS], None))
    systems, skipped = r.build(set(r.SYSTEMS))
    assert set(systems) == set(r.SYSTEMS) and not skipped


@pytest.mark.parametrize("over", [{"revision": "0" * 40}, {"code_sha": "1" * 40}, {"max_length": 4096}])
def test_build_refuses_a_vm_serving_something_else(r, monkeypatch, over):
    monkeypatch.setattr(r.smoke, "strands_models", lambda: ([_served(r, "strands-decider-e2b-v2", **over)], None))
    with pytest.raises(SystemExit, match="the VM serves"):
        r.build({"strands-decider-e2b-v2"})


def test_identity_records_a_pinned_max_length_and_v1_is_unchanged():
    from goldrails_bench.endpoints import identity_of
    base = {"name": "x", "kind": "strands", "ref": "a/b", "revision": "c" * 40}
    assert identity_of(base)["max_length"] == 4096
    assert identity_of({**base, "max_length": 32768})["max_length"] == 32768


def test_freeze_refuses_without_the_owners_approval(r, monkeypatch, tmp_path):
    monkeypatch.setattr(r, "MANIFEST", tmp_path / "m.json")
    monkeypatch.setattr(r, "APPROVAL", None)
    with pytest.raises(SystemExit, match="APPROVAL"):
        r.write_freeze(None)


def test_smoke_knows_the_v2_window(r):
    for n in r.SYSTEMS:
        assert r.smoke.limit_of(n)[0] == r.MAX_LENGTH


def test_cost_tariffs_exist_for_the_vm_and_disk(r):
    from goldrails_bench import leaderboard as lb
    entries = lb.load_tariffs()["entries"]
    for h in {r.HARDWARE, r.DISK, *r.PASS_HARDWARE.values(), *(x for pair in r.REGIONS.values() for x in pair)}:
        assert len([e for e in entries if h in e["match"].get("hardware", [])]) == 1, h
    for region, (vm, disk) in r.REGIONS.items():
        assert f"/{region}/" in vm and f"/{region}/" in disk, region


def test_region_of_a_zone_and_one_disk_per_run(r, monkeypatch, tmp_path):
    assert r.region_of("us-east5-b") == "us-east5" and r.region_of("us-central1-c") in r.REGIONS
    assert "us-central1" == r.region_of("us-central1-a") and r.region_of("europe-west4-a") not in r.REGIONS
    log = tmp_path / "run-log.json"
    monkeypatch.setattr(r, "RUN_LOG", log)
    assert r.run_disk() == r.DISK
    log.write_text(json.dumps({"vm": [{"up": "x", "disk": r.REGIONS["us-east4"][1]}]}))
    assert r.run_disk() == r.REGIONS["us-east4"][1]
    log.write_text(json.dumps({"vm": [{"up": "x", "disk": r.REGIONS["us-east4"][1]}, {"up": "y", "disk": r.DISK}]}))
    with pytest.raises(SystemExit, match="more than one region"):
        r.run_disk()


def test_display_names_are_registered(r):
    for n, label in r.NAMES.items():
        assert r.ar.NAMES[n] == label


def test_score_is_batch_4s_rescore_with_this_run_last(r, monkeypatch):
    import e2_batch4_run as batch4
    import e2_guards_run as guards_run
    import e2_pplx13_run as pplx13
    import e2_strands_run as strands
    from e2_pplx13_run import batch3, hosted8, liquid, msd1, pplx12
    from e2_batch4_run import gemini
    got = {}
    monkeypatch.setattr(r.full, "TestRows", lambda: None)
    mods = {"luna": strands.luna, "jev114": strands.jev114, "strands": strands, "msd1": msd1, "pplx12": pplx12,
            "hosted8": hosted8, "liquid": liquid, "gemini": gemini, "batch3": batch3, "pplx13": pplx13,
            "guards": guards_run, "batch4": batch4, "v2": r}
    for k, m in mods.items():
        monkeypatch.setattr(m, "write_public", lambda tr: [])
        monkeypatch.setattr(m, "extra_run", lambda *a, k=k: k)
    monkeypatch.setattr(r.ar, "score", lambda rep, extra_runs: got.update(extra=extra_runs) or "out")
    assert r.score() == "out"
    assert got == {"extra": list(mods)}


# --- launcher and infra ---------------------------------------------------------------------------------------------

def _server():
    spec = importlib.util.spec_from_file_location("strands_server", ROOT / "infra/gcp/strands_server.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_launcher_passes_max_length_and_queue_timeout_when_create_app_takes_them():
    m = _server()

    def v2(checkpoint, *, device="cuda", max_length=None, queue_timeout=60.0):
        return None
    assert m.limit_kwargs(v2, 32768, 600.0) == {"max_length": 32768, "queue_timeout": 600.0}

    def v1(checkpoint, device="cuda"):
        return None
    assert m.limit_kwargs(v1, None, 600.0) == {}
    with pytest.raises(SystemExit, match="takes no max_length"):
        m.limit_kwargs(v1, 32768, 600.0)


def test_infra_carries_max_length_and_skips_the_base_for_merged_checkpoints():
    s = (ROOT / "infra/gcp/startup.sh").read_text()
    assert 'MODEL_MAX_LENGTH=\\((.max_length // "")|tostring)' in s and '--max-length "$MODEL_MAX_LENGTH"' in s
    assert 'if not (pathlib.Path(out) / "provenance.json").exists():' in s
    v = (ROOT / "infra/gcp/variables.tf").read_text()
    assert "max_length = optional(number)" in v and "model.max_length" in v
