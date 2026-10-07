"""The ruling 31 views (benchmark/runs/e2_views.py) on synthetic rows: subset re-scores reproduce the scorer's
metrics and draws, benign-only slices, unanimous-miss counts, the cost split and the README blocks. No result file is
read."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from goldrails_bench import leaderboard as lb
from goldrails_bench import leaderboard_v2 as lv2

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def V():
    spec = importlib.util.spec_from_file_location("e2_views", ROOT / "benchmark/runs/e2_views.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CONTRACT = {"suites": {"prompt_attacks": {"subtasks": {"direct": {"tags": ["jailbreak"]},
                                                       "indirect": {"tags": ["indirect"]}}}}}


class FakeRows:
    def __init__(self, rows):
        self.rows = rows
        self.feature = {i: "F2" for i in rows}
        self.unpublished = {i for i in rows if rows[i].get("_unp")}

    def public_ids(self):
        return set(self.rows) - self.unpublished


def _world(n_sys=3, seed=0, B=200):
    """Systems with random scores on 40 direct and 20 indirect rows from two sources."""
    rng = np.random.default_rng(seed)
    rows, units = {}, {"direct": [], "indirect": []}
    for st, n in (("direct", 40), ("indirect", 20)):
        for k in range(n):
            i = f"{st}-{k}"
            rows[i] = {"id": i, "subtask": "jailbreak" if st == "direct" else "indirect",
                       "expected": "yes" if k % 2 else "no", "provenance": {"source": "a" if k < n // 2 else "b"},
                       "_unp": k % 5 == 0}
            units[st].append(i)
    groups = {st: set(ids) for st, ids in units.items()}
    boot = lb.SuiteBootstrap("prompt_attacks", groups, B, 7)
    ev, picks = {}, {}
    for s in range(n_sys):
        name = f"sys{s}"
        key = (name, "q", "c", "d")
        su = {}
        for st, ids in units.items():
            rs = []
            for i in ids:
                pos = rows[i]["expected"] == "yes"
                fail = rng.random() < 0.05
                sc = None if fail else float(np.clip(rng.normal(0.6 if pos else 0.4, 0.25), 0, 1))
                rs.append(lb.Row(i, i, st, "", pos, sc, "failed" if fail else "decided", "test", None))
            su[st] = {"": rs}
        ev[key] = {"su": su, "rule": {"threshold": 0.5},
                   "subs": {st: {"secondary": {"auroc": 0.7}} for st in units}}
        for st in units:
            picks[(name, "prompt_attacks", st)] = (key, "evaluated", None)
    cap = {"ev": ev, "boots": {"prompt_attacks": boot}, "picks": picks, "level": 0.95}
    return cap, FakeRows(rows), [f"sys{s}" for s in range(n_sys)]


def test_all_rows_subset_matches_the_scorer_point_and_replicates(V):
    cap, tr, order = _world()
    ctx = V.Ctx(cap, CONTRACT, tr, order)
    for name in order:
        for st in ("direct", "indirect"):
            units, t, boot, _ = ctx.arm(name, "prompt_attacks", st)
            p = V.subset(ctx, name, "prompt_attacks", st)
            m = lv2.subtask_metrics(units, t)
            assert p["point"]["balanced_accuracy"] == pytest.approx(m["balanced_accuracy"])
            assert p["point"]["false_block_rate"] == pytest.approx(m["false_block_rate"])
            reps = boot.subtask_reps(st, units, t, m["units_scored"])
            np.testing.assert_allclose(p["ba"], reps, equal_nan=True)


def test_subset_by_ids_scores_only_those_rows(V):
    cap, tr, order = _world()
    ctx = V.Ctx(cap, CONTRACT, tr, order)
    keep = {i for i, r in tr.rows.items() if r["provenance"]["source"] == "a"}
    units, t, _, _ = ctx.arm("sys0", "prompt_attacks", "direct")
    want = lv2.subtask_metrics({"": [x for x in units[""] if x.id in keep]}, t)
    got = V.subset(ctx, "sys0", "prompt_attacks", "direct", keep)
    assert got["point"]["balanced_accuracy"] == pytest.approx(want["balanced_accuracy"])
    assert got["point"]["n"]["positive"] + got["point"]["n"]["negative"] == sum(1 for i in keep if i.startswith("direct"))


def test_benign_rate_on_a_negative_only_slice(V):
    cap, tr, order = _world()
    ctx = V.Ctx(cap, CONTRACT, tr, order)
    neg = {i for i, r in tr.rows.items() if r["expected"] == "no" and i.startswith("direct")}
    units, t, _, _ = ctx.arm("sys1", "prompt_attacks", "direct")
    rs = [x for x in units[""] if x.id in neg]
    blocked = sum(1 for x in rs if x.outcome != "decided" or x.score >= t)
    got = V.benign_rate(ctx, "sys1", "prompt_attacks", "direct", neg)
    assert got["false_block_rate"] == pytest.approx(blocked / len(rs), abs=1e-4)
    assert got["negative"] == len(rs) and got["ci"]["valid_replicates"] > 0


def test_suite_subset_is_the_mean_of_its_subtasks(V):
    cap, tr, order = _world()
    ctx = V.Ctx(cap, CONTRACT, tr, order)
    s = V.suite_subset(ctx, "sys2", "prompt_attacks")
    d = V.subset(ctx, "sys2", "prompt_attacks", "direct")["point"]["balanced_accuracy"]
    i = V.subset(ctx, "sys2", "prompt_attacks", "indirect")["point"]["balanced_accuracy"]
    assert s["point"]["balanced_accuracy"] == pytest.approx((d + i) / 2)


def test_unanimous_miss_matches_a_brute_force_count(V):
    cap, tr, order = _world(n_sys=3)
    for key, e in cap["ev"].items():          # one benign row every system blocks
        for x in e["su"]["direct"][""]:
            if x.id == "direct-0":
                x.score, x.outcome = 0.9, "decided"
    ctx = V.Ctx(cap, CONTRACT, tr, order)
    for th in (2, 3):
        wrong = {}
        for e in cap["ev"].values():
            for st in ("direct", "indirect"):
                for x in e["su"][st][""]:
                    ok = x.outcome == "decided" and (x.score >= 0.5) == x.positive
                    wrong[x.id] = wrong.get(x.id, 0) + (not ok)
        want = sum(1 for v in wrong.values() if v >= th)
        out = V.unanimous_miss(ctx, suites=("prompt_attacks",), threshold=th)["suites"]["prompt_attacks"]
        assert out["total_wrong_by_threshold_plus"] == want
        if th == 3:
            assert out["by_source"]["a"]["benign_wrong_by_3_plus"] >= 1


def test_cost_split_keeps_self_hosted_apart(V):
    cost = {"clef": {"usd_total": 2.0, "usd_per_1000": 0.2, "basis": "tokens"},
            "laya": {"usd_total": 1.5, "usd_per_1000": 0.15, "basis": "vm"}}
    out = V.cost_split(cost)
    assert set(out["managed_api"]["systems"]) == {"clef"} and set(out["self_hosted"]["systems"]) == {"laya"}
    assert "shared-GPU allocation" in out["self_hosted"]["label"]


def test_upsert_inserts_then_replaces_a_block(V):
    text = "# R\n\nintro\n\n## Scores\n\ntable\n"
    a = V.upsert(text, "x", "## Scores", "first")
    assert a.index("first") < a.index("## Scores") and a.count("begin:x") == 1
    b = V.upsert(a, "x", "## Scores", "second")
    assert "first" not in b and "second" in b and b.count("begin:x") == 1
    c = V.upsert("no anchor here\n", "y", "## Missing", "tail")
    assert c.rstrip().endswith("<!-- end:y -->")


def test_rename_reference(V):
    doc = {"prompt_attacks": {"ngram_baseline": {"by_tag": {}}}}
    V.rename_reference(doc)
    assert doc["prompt_attacks"]["ngram_baseline"]["name"].startswith("in-distribution supervised reference")
