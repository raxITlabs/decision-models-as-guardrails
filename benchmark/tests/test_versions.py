"""Version progress (goldrails_bench.versions): paired deltas on the scorer's own draws, verdicts, McNemar, flips,
public-only examples, calibration, cost comparability, and the run script's site view and privacy scan. Synthetic
ledgers scored by leaderboard_v2 in diagnostic mode; no keys, no private data."""
import copy
import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

from goldrails_bench import leaderboard as lb
from goldrails_bench import leaderboard_v2 as v2
from goldrails_bench import versions as V

CONTRACT = v2.load_contract()
sys.path.insert(0, str(v2.REPO / "benchmark" / "runs"))


def contract():
    c = copy.deepcopy(CONTRACT)
    c["required_suites"] = ["denied_topics"]
    return c


def rec(system, i, expected, score):
    return {"question_set": "v1-f3-topics", "system": system, "id": f"f3-denied_topics-{i}", "subtask": "topic",
            "expected": expected, "ok": score is not None,
            "answers": None if score is None else {"q": {"type": "noul", "noul": score}},
            "config_hash": f"cfg-{system}", "decision_keys": ["q"], "group": f"g{i // 2}", "latency_s": 0.1,
            "model": system, "dataset": {"source": "none", "feature": "F3", "split": "test", "sha256": "d1"}}


def score(systems: dict, labels: list, replicates=300):
    """{name: [score per row]} on the same rows -> (Scored, leaderboard document)."""
    recs = [rec(n, i, "yes" if y else "no", s) for n, ss in systems.items() for i, (s, y) in enumerate(zip(ss, labels))]
    cap, c = {}, contract()
    doc = v2.evaluate(recs, c, report_split="test", replicates=replicates, diagnostic=True, capture=cap)
    return V.Scored(cap, c), doc


def noisy(labels, flip, seed):
    rng = random.Random(seed)
    out = []
    for y in labels:
        right = rng.random() > flip
        p = rng.uniform(0.55, 0.95) if right else rng.uniform(0.05, 0.45)
        out.append(round(p if y else 1 - p, 3))
    return out


LABELS = [i % 3 == 0 for i in range(300)]
PUBLIC = {f"f3-denied_topics-{i}" for i in range(300) if i % 4}


def test_points_intervals_and_paired_test_equal_the_scorer():
    sc, doc = score({"old": noisy(LABELS, 0.25, 1), "new": noisy(LABELS, 0.15, 2)}, LABELS)
    rank = {r["name"]: r for r in doc["overall"]["ranking"]}
    for n in ("old", "new"):
        s = V.system_stats(sc, n)
        assert s["overall"]["point"]["balanced_accuracy"] == pytest.approx(rank[n]["balanced_accuracy"])
        assert lb.ci_of(s["overall"]["reps"]["balanced_accuracy"], sc.level) == rank[n]["ci"]
    c = V.compare(sc, "old", "new", PUBLIC)
    pair = doc["overall"]["paired_differences"][0]
    sign = 1 if pair["a"] == "new" else -1
    d = c["overall"]["delta"]["balanced_accuracy"]
    assert d["point"] == pytest.approx(sign * pair["difference"], abs=1e-6)
    assert d["p"] == pytest.approx(pair["p"], abs=1e-6)
    if sign == 1:
        assert d["ci"] == {"low": pair["ci"]["low"], "high": pair["ci"]["high"]}


def test_identical_versions_are_within_noise_with_no_flips():
    s = noisy(LABELS, 0.2, 3)
    sc, _ = score({"old": s, "new": list(s)}, LABELS)
    c = V.lineage(sc, ["old", "new"], PUBLIC)[0]
    d = c["overall"]["delta"]["balanced_accuracy"]
    assert d["point"] == 0 and d["p"] == 1.0 and d["verdict"] == "within noise"
    assert c["flips"]["fixed"] == c["flips"]["broke"] == 0 and c["mcnemar"]["p"] == 1.0
    assert c["examples"]["denied_topics/topic"] == {"fixed": [], "broke": []}


def test_clear_improvement_is_better_and_flips_are_counted_by_class():
    sc, _ = score({"old": noisy(LABELS, 0.35, 4), "new": noisy(LABELS, 0.05, 5)}, LABELS)
    c = V.lineage(sc, ["old", "new"], PUBLIC)[0]
    d = c["overall"]["delta"]["balanced_accuracy"]
    assert d["point"] > 10 and d["ci"]["low"] > 0 and d["verdict"] == "better"
    f = c["flips"]
    assert f["fixed"] == f["catches_gained"] + f["false_blocks_cleared"] > f["broke"]
    assert f["judgments"] == f["positive_judgments"] + f["negative_judgments"] == len(LABELS)
    assert f["both_right"] + f["both_wrong"] + f["fixed"] + f["broke"] == len(LABELS)
    assert c["mcnemar"]["p"] < 0.001
    assert c["suites"]["denied_topics"]["delta"]["balanced_accuracy"]["verdict"] == "better"


def test_a_rise_in_false_blocks_is_worse():
    d = {"point": 0.03, "ci": {"low": 0.01, "high": 0.05}, "p": 0.001}
    assert V.verdict(d, 0.001, 0.05, V.HIGHER_IS_BETTER["false_block_rate"]) == "worse"
    assert V.verdict(d, 0.001, 0.05, V.HIGHER_IS_BETTER["catch_rate"]) == "better"
    assert V.verdict(d, 0.2, 0.05) == "within noise"
    assert V.verdict({"point": 1, "ci": None, "p": None}, None, 0.05) == "not tested"


def test_holm_is_applied_across_the_lineage():
    labels = LABELS
    sc, _ = score({"a": noisy(labels, 0.3, 6), "b": noisy(labels, 0.2, 7), "c": noisy(labels, 0.1, 8)}, labels)
    comps = V.lineage(sc, ["a", "b", "c"], PUBLIC)
    assert [(c["from"], c["to"], c["kind"]) for c in comps] == [("a", "b", "step"), ("b", "c", "step"),
                                                                ("a", "c", "first to last")]
    ps = [c["overall"]["delta"]["balanced_accuracy"]["p"] for c in comps]
    adj = [c["overall"]["delta"]["balanced_accuracy"]["p_holm"] for c in comps]
    assert adj == v2.holm(ps) and all(a >= p for a, p in zip(adj, ps))


def test_examples_come_from_public_rows_only():
    sc, _ = score({"old": noisy(LABELS, 0.4, 9), "new": noisy(LABELS, 0.1, 10)}, LABELS)
    c = V.compare(sc, "old", "new", PUBLIC, k_examples=50)
    ex = c["examples"]["denied_topics/topic"]
    ids = [e["id"] for e in ex["fixed"] + ex["broke"]]
    assert ids and set(ids) <= PUBLIC
    none = V.compare(sc, "old", "new", set())["examples"]["denied_topics/topic"]
    assert none == {"fixed": [], "broke": []}


def test_align_refuses_versions_on_different_rows():
    a = {"": [lb.Row("r1", "g1", "s", "", True, 0.9, "decided", "test")]}
    b = {"": [lb.Row("r2", "g2", "s", "", True, 0.9, "decided", "test")]}
    with pytest.raises(ValueError, match="not paired"):
        V.align(a, 0.5, b, 0.5)


def test_failures_count_wrong_in_flips():
    a = {"": [lb.Row("r1", "g1", "s", "", True, 0.9, "decided", "test"),
              lb.Row("r2", "g2", "s", "", False, 0.1, "decided", "test")]}
    b = {"": [lb.Row("r1", "g1", "s", "", True, None, "failed", "test"),
              lb.Row("r2", "g2", "s", "", False, None, "failed", "test")]}
    f = V.flips(V.align(a, 0.5, b, 0.5))
    assert f["catches_lost"] == 1 and f["false_blocks_added"] == 1 and f["broke"] == 2


def test_exact_binomial_and_mcnemar():
    assert V.binom_two_sided(0, 5) == pytest.approx(2 / 32)
    assert V.binom_two_sided(1, 10) == pytest.approx(2 * 11 / 1024)
    assert V.binom_two_sided(2, 4) == 1.0 and V.binom_two_sided(0, 0) == 1.0
    assert V.binom_two_sided(400, 1000) == pytest.approx(V.binom_two_sided(600, 1000))
    assert V.mcnemar(30, 10)["p"] == pytest.approx(V.binom_two_sided(10, 40))


def test_calibration_matches_the_scorer_and_has_replicates():
    sc, doc = score({"old": noisy(LABELS, 0.2, 11), "new": noisy(LABELS, 0.2, 12)}, LABELS)
    cs = V.calibration_stats(sc, "old", "denied_topics", "topic")
    arm = next(a for a in doc["arms"] if a["system"] == "old")
    want = arm["subtasks"]["topic"]["secondary"]["calibration"]
    assert cs["point"]["ece"] == pytest.approx(want["ece"], abs=1e-6)
    assert cs["point"]["brier"] == pytest.approx(want["brier"], abs=1e-6)
    assert cs["reps"]["ece"].shape == (300,) and np.isfinite(cs["reps"]["ece"]).all()
    assert sum(b["n"] for b in cs["reliability"]) == len(LABELS)
    c = V.compare(sc, "old", "new", PUBLIC)
    cal = c["subtasks"]["denied_topics/topic"]["calibration"]
    assert cal["delta_ece"]["verdict"] in V.VERDICTS and "p_holm" in cal["delta_ece"]


def test_multi_question_units_get_no_calibration():
    sc, _ = score({"old": noisy(LABELS, 0.2, 13), "new": noisy(LABELS, 0.2, 14)}, LABELS)
    units = sc.arm("old", "denied_topics", "topic")[0]
    for rs in units.values():
        for x in rs:
            x.record["decision_keys"] = ["q", "q2"]
    assert V.calibration_stats(sc, "old", "denied_topics", "topic") is None


def test_cost_is_comparable_only_on_the_same_tariff_or_machine():
    metered = {"usd_per_1000": 0.0386, "usd_total": 0.38, "basis": "measured usage x dated tariff (tariffs.json)"}
    assert V.cost_summary(metered, dict(metered))["comparable"] is True
    vm24 = {"usd_per_1000": 0.12, "basis": "allocated VM time (2202 s) x g2-standard-24/us-east4/on-demand $1.99/h"}
    vm48 = {"usd_per_1000": 0.37, "basis": "allocated VM time (2976 s) x g2-standard-48/ne2/on-demand $4.41/h"}
    s = V.cost_summary(vm24, vm48)
    assert s["comparable"] is False and "g2-standard-24" in s["why_not_comparable"]
    assert s["delta_pct"] == pytest.approx(208.33, abs=0.01)
    assert V.cost_summary(vm48, dict(vm48))["comparable"] is True
    assert V.cost_summary(None, metered) is None


def test_token_summary_pairs_on_checks_both_versions_report():
    t = V.token_summary({"a": 100, "b": 200, "c": None}, {"a": 110, "b": 220, "d": 5})
    assert t["checks"] == 2 and t["old_mean"] == 150 and t["new_mean"] == 165 and t["delta_pct"] == 10.0


def test_site_view_has_no_row_ids_and_privacy_scan_removes_leaky_files(tmp_path):
    import e2_versions as run
    sc, _ = score({"old": noisy(LABELS, 0.3, 15), "new": noisy(LABELS, 0.1, 16)}, LABELS)
    comps = V.lineage(sc, ["old", "new"], PUBLIC)
    for c in comps:
        c["board"], c["cost"], c["tokens"] = None, None, {"checks": 0}
    doc = {"method": run.METHOD, "lineages": {"x": {"label": "X", "vendor": "V", "versions": ["old", "new"],
                                                    "board": {}, "comparisons": comps}}}
    site = json.dumps(run.site_view(doc))
    assert "f3-denied_topics" not in site and '"verdict": "better"' in site

    class TR:
        unpublished = {"f3-denied_topics-1"}
    ok, bad = tmp_path / "ok.json", tmp_path / "bad.json"
    ok.write_text(site)
    run.privacy([ok], TR())
    assert ok.exists()
    bad.write_text('{"id": "f3-denied_topics-1"}')
    with pytest.raises(SystemExit, match="privacy"):
        run.privacy([ok, bad], TR())
    assert not bad.exists() and not ok.exists()
