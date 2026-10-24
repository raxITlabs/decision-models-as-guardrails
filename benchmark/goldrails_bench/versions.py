"""Version progress: two versions of one model compared on identical rows, with the leaderboard's own statistics.
Pure functions, no model calls, no keys. ``benchmark/runs/e2_versions.py`` feeds them the scorer's state
(``leaderboard_v2.evaluate(..., capture=...)``) and writes the results file.

What one comparison (old -> new) reports:

- Balanced accuracy delta overall, per suite and per subtask. The intervals and tests are the scorer's: the same
  group draws (``SuiteBootstrap``, groups resampled within each subtask, the contract's seed and replicate count), the
  difference of the two versions' replicates, a percentile interval and the two-sided Wald test (``leaderboard_v2.
  p_value``). Unit means, suite means and the overall mean follow the scorer exactly, so the old and new points equal
  the published board.
- Catch rate and false-block rate deltas on the same draws.
- McNemar's exact test on per-judgment correctness (a PII judgment is a row x entity type). It treats judgments as
  independent and measures plain accuracy, not balanced accuracy, so it is a cross-check beside the bootstrap, never
  the verdict.
- Flips: judgments the new version fixed and broke, split by class (a missed harmful row caught or a caught one
  missed; a false block cleared or a new false block). A failure counts wrong, as in the scorer.
- Calibration (ECE and Brier) on the units where the scorer reports it: single-question probability units. The
  ECE delta has an interval from the same draws. Reliability bins are pooled over a subtask's units.
- Cost and reported input tokens, given by the caller.

Verdicts. A delta is "better" or "worse" only when its Holm-adjusted p-value is below the contract's alpha (0.05).
Otherwise it is "within noise", whatever the sign of the point. Families for Holm:

- overall, per metric: every comparison of one lineage (each consecutive step, plus first to last when a lineage has
  three or more versions);
- suites and subtasks, per comparison and metric: the six suites, or the eight scored subtasks.

The board's own Holm adjustment (over every pair of the 20-system board) is reported beside it: a version step can be
"better" here and still share a tier on the board.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from . import leaderboard as lb
from . import leaderboard_v2 as lv2

# Version lineages on the board, oldest first. ``planned`` versions have no run yet.
LINEAGES = {
    "jev": {"label": "Jev (TypeSafe)", "vendor": "TypeSafe", "versions": ["jev-1.13.0", "jev-1.14.0"]},
    "strands-decider-2b": {"label": "Strands Decider 2B (AWS)", "vendor": "AWS",
                           "versions": ["strands-decider-2b", "strands-decider-2b-v21", "strands-decider-2b-qwen35"]},
    "perplexity-decider": {"label": "Perplexity Decisions API", "vendor": "Perplexity",
                           "versions": ["pplx-decider-v1-27b"], "planned": ["pplx-decider-v1.2"]},
}
VERDICTS = ("better", "worse", "within noise", "not tested")
METRICS = ("balanced_accuracy", "catch_rate", "false_block_rate")
HIGHER_IS_BETTER = {"balanced_accuracy": True, "catch_rate": True, "false_block_rate": False}


# --- the scorer's state ----------------------------------------------------------------------------------------------

class Scored:
    """Read-only view of ``leaderboard_v2.evaluate(..., capture=cap)``: one system's rows, rule and the shared draws."""

    def __init__(self, cap: dict, contract: dict):
        self.cap, self.contract = cap, contract
        self.level = cap["level"]
        self.alpha = (contract.get("statistics") or {}).get("alpha", 0.05)
        self.suites = list(contract.get("required_suites") or lb.SUITES)

    def subtasks(self, suite: str) -> list[str]:
        return lv2.scored_subtasks(self.contract, suite)

    def arm(self, name: str, suite: str, st: str):
        """(units, threshold, SuiteBootstrap, scale) or None when the subtask is not evaluated for ``name``."""
        k, status, _ = self.cap["picks"].get((name, suite, st), (None, None, None))
        if k is None or status != "evaluated":
            return None
        e = self.cap["ev"][k]
        return e["su"][st], e["rule"]["threshold"], self.cap["boots"][suite], e["rule"]["scale"]

    def published_reps(self, name: str, suite: str, st: str):
        k, status, _ = self.cap["picks"].get((name, suite, st), (None, None, None))
        return None if k is None or status != "evaluated" else self.cap["ev"][k]["reps"].get(st)


def _unit_mean(arrs: list) -> np.ndarray:
    """Mean over units per replicate; a unit missing a class in a replicate is left out (the scorer's rule)."""
    m = np.vstack(arrs)
    n = (~np.isnan(m)).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, np.nansum(m, axis=0) / np.maximum(n, 1), np.nan)


def subtask_stats(sc: Scored, name: str, suite: str, st: str) -> dict | None:
    """Point metrics and replicates of balanced accuracy, catch rate and false-block rate for one subtask."""
    a = sc.arm(name, suite, st)
    if a is None:
        return None
    units, t, boot, _ = a
    m = lv2.subtask_metrics(units, t)
    if not m["units_scored"]:
        return None
    counts, gidx = boot.counts[st], boot.gidx[st]
    sums = [counts @ lb._unit_vectors(units[u], gidx, t).T for u in m["units_scored"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        reps = {"balanced_accuracy": _unit_mean([50.0 * (s[:, 1] / s[:, 0] + s[:, 3] / s[:, 2]) for s in sums]),
                "catch_rate": _unit_mean([s[:, 1] / s[:, 0] for s in sums]),
                "false_block_rate": _unit_mean([(s[:, 2] - s[:, 3]) / s[:, 2] for s in sums])}
    pub = sc.published_reps(name, suite, st)
    if pub is not None and not np.allclose(pub, reps["balanced_accuracy"], equal_nan=True):
        raise AssertionError(f"{name} {suite}/{st}: replicates differ from the scorer's")
    return {"point": {k: m[k] for k in METRICS}, "reps": reps, "n": m["n"]}


def _mean_stats(parts: list[dict]) -> dict:
    return {"point": {k: float(np.mean([p["point"][k] for p in parts])) for k in METRICS},
            "reps": {k: np.mean(np.vstack([p["reps"][k] for p in parts]), axis=0) for k in METRICS}}


def system_stats(sc: Scored, name: str) -> dict:
    """{"subtasks": {"suite/st": stats}, "suites": {suite: stats}, "overall": stats or None}: the scorer's means."""
    subs, suites = {}, {}
    for suite in sc.suites:
        parts = []
        for st in sc.subtasks(suite):
            s = subtask_stats(sc, name, suite, st)
            if s is not None:
                subs[f"{suite}/{st}"] = s
                parts.append(s)
        if parts and len(parts) == len(sc.subtasks(suite)):
            suites[suite] = _mean_stats(parts)
    overall = _mean_stats([suites[s] for s in sc.suites]) if all(s in suites for s in sc.suites) else None
    return {"subtasks": subs, "suites": suites, "overall": overall}


# --- paired statistics -----------------------------------------------------------------------------------------------

def paired_delta(old: dict, new: dict, metric: str, level: float, scale: float = 1.0) -> dict:
    """new - old for one metric: point, percentile interval of the replicate differences, Wald p (the scorer's)."""
    point = new["point"][metric] - old["point"][metric]
    diff = new["reps"][metric] - old["reps"][metric]
    ci = lb.ci_of(diff * scale, level)
    return {"point": round(point * scale, 6), "ci": {"low": ci["low"], "high": ci["high"]},
            "p": lv2.p_value(diff, point)}


def verdict(d: dict, p_adj: float | None, alpha: float, higher_is_better: bool = True) -> str:
    if p_adj is None or d.get("ci") is None or d["ci"]["low"] is None:
        return "not tested"
    if p_adj >= alpha:
        return "within noise"
    up = d["point"] > 0
    return "better" if up == higher_is_better else "worse"


def apply_holm(deltas: list[dict], metric: str, alpha: float) -> None:
    """Holm over one family in place: sets ``p_holm`` and ``verdict`` on each delta."""
    for d, adj in zip(deltas, lv2.holm([d["p"] for d in deltas])):
        d["p_holm"] = adj
        d["verdict"] = verdict(d, adj, alpha, HIGHER_IS_BETTER[metric])


def binom_two_sided(k: int, n: int) -> float:
    """Exact two-sided binomial test at p = 0.5: 2 x P(X <= min(k, n - k)), capped at 1."""
    if n == 0:
        return 1.0
    m = min(k, n - k)
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * math.log(2) for i in range(m + 1)]
    top = max(logs)
    return min(1.0, 2.0 * math.exp(top) * sum(math.exp(x - top) for x in logs))


def mcnemar(fixed: int, broke: int) -> dict:
    """Exact McNemar on the discordant judgments: ``fixed`` old wrong -> new right, ``broke`` old right -> new wrong."""
    return {"fixed": fixed, "broke": broke, "discordant": fixed + broke, "p": binom_two_sided(fixed, fixed + broke),
            "note": "judgments treated as independent; plain accuracy, not balanced accuracy; a cross-check only"}


# --- row-level comparison --------------------------------------------------------------------------------------------

def correct(x, t) -> bool:
    """The scorer's credit for one judgment: decided, and the flag at ``t`` agrees with the label."""
    return x.outcome == "decided" and lb._flag(x.score, t) == x.positive


def align(units_old: dict, t_old, units_new: dict, t_new) -> list[dict]:
    """Judgments of two versions on one subtask, paired by (row id, unit). Raises when the judgment sets differ: two
    versions are compared only on identical rows."""
    a = {(x.id, u): x for u, rs in units_old.items() for x in rs}
    b = {(x.id, u): x for u, rs in units_new.items() for x in rs}
    if set(a) != set(b):
        raise ValueError(f"not paired: {len(set(a) ^ set(b))} judgments differ between the two versions")
    out = []
    for key in sorted(a):
        x, y = a[key], b[key]
        if x.positive != y.positive:
            raise ValueError(f"label differs for {key}")
        out.append({"id": key[0], "unit": key[1], "group": x.group, "positive": x.positive,
                    "old_correct": correct(x, t_old), "new_correct": correct(y, t_new),
                    "old_score": x.score, "new_score": y.score, "old_outcome": x.outcome, "new_outcome": y.outcome})
    return out


def flips(pairs: list[dict]) -> dict:
    """Counts of fixed and broken judgments, by class."""
    c = Counter()
    for p in pairs:
        cls = "positive" if p["positive"] else "negative"
        c[f"{cls}_judgments"] += 1
        if p["old_correct"] and p["new_correct"]:
            c["both_right"] += 1
        elif not p["old_correct"] and not p["new_correct"]:
            c["both_wrong"] += 1
        elif p["new_correct"]:
            c["catches_gained" if p["positive"] else "false_blocks_cleared"] += 1
        else:
            c["catches_lost" if p["positive"] else "false_blocks_added"] += 1
    keys = ("both_right", "both_wrong", "catches_gained", "catches_lost", "false_blocks_cleared",
            "false_blocks_added", "positive_judgments", "negative_judgments")
    out = {k: c[k] for k in keys}
    out["fixed"] = out["catches_gained"] + out["false_blocks_cleared"]
    out["broke"] = out["catches_lost"] + out["false_blocks_added"]
    out["judgments"] = len(pairs)
    return out


def _score_change(p: dict) -> float:
    a = p["old_score"] if p["old_score"] is not None else (0.0 if p["positive"] else 1.0)
    b = p["new_score"] if p["new_score"] is not None else (0.0 if p["positive"] else 1.0)
    return abs(b - a)


def examples(pairs: list[dict], public_ids: set, k: int = 3) -> dict:
    """Up to ``k`` fixed and ``k`` broken judgments, public rows only, the largest score change first (ties by id).
    A held-back row is never returned: ``public_ids`` is the allow list."""
    pub = [p for p in pairs if p["id"] in public_ids and p["old_correct"] != p["new_correct"]]
    pick = lambda ps: sorted(ps, key=lambda p: (-_score_change(p), p["id"], p["unit"]))[:k]
    keep = ("id", "unit", "positive", "old_score", "new_score", "old_outcome", "new_outcome")
    fixed = [{k_: p[k_] for k_ in keep} for p in pick([p for p in pub if p["new_correct"]])]
    broke = [{k_: p[k_] for k_ in keep} for p in pick([p for p in pub if p["old_correct"]])]
    if any(e["id"] not in public_ids for e in fixed + broke):
        raise AssertionError("an example is not a public row")
    return {"fixed": fixed, "broke": broke}


# --- calibration -----------------------------------------------------------------------------------------------------

def _bins(p: np.ndarray, bins: int) -> np.ndarray:
    return np.minimum((p * bins).astype(int), bins - 1)


def calibration_eligible(sc: Scored, name: str, suite: str, st: str) -> bool:
    """The scorer's rule: a probability scale and every unit single-question (``leaderboard_v2._single_question``)."""
    a = sc.arm(name, suite, st)
    if a is None or a[3] != "probability":
        return False
    units = a[0]
    return bool(units) and all(lv2._single_question(u, rs, sc.contract) for u, rs in units.items())


def calibration_stats(sc: Scored, name: str, suite: str, st: str, bins: int | None = None) -> dict | None:
    """ECE and Brier (mean over units, decided rows, as the scorer reports them) with replicates on the shared draws,
    and reliability bins pooled over units."""
    if not calibration_eligible(sc, name, suite, st):
        return None
    bins = bins or ((sc.contract.get("secondary") or {}).get("calibration") or {}).get("ece_bins", 10)
    units, _, boot, _ = sc.arm(name, suite, st)
    counts, gidx = boot.counts[st], boot.gidx[st]
    G = len(gidx)
    eces, briers, pts, pooled = [], [], [], {"n": np.zeros(bins), "p": np.zeros(bins), "y": np.zeros(bins)}
    for u, rows in sorted(units.items()):
        d = [x for x in rows if x.outcome == "decided"]
        if not d:
            continue
        p = np.array([x.score for x in d], float)
        y = np.array([x.positive for x in d], float)
        g = np.array([gidx[x.group] for x in d])
        b = _bins(p, bins)
        pts.append(lv2.calibration(p, y, bins))
        n_gb, p_gb, y_gb = (np.zeros((G, bins)) for _ in range(3))
        np.add.at(n_gb, (g, b), 1)
        np.add.at(p_gb, (g, b), p)
        np.add.at(y_gb, (g, b), y)
        sq = np.zeros(G)
        np.add.at(sq, g, (p - y) ** 2)
        N = counts @ n_gb.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            eces.append(np.abs(counts @ p_gb - counts @ y_gb).sum(axis=1) / N)
            briers.append((counts @ sq) / N)
        for k_, v in (("n", n_gb), ("p", p_gb), ("y", y_gb)):
            pooled[k_] += v.sum(axis=0)
    if not pts:
        return None
    rel = [{"low": i / bins, "high": (i + 1) / bins, "n": int(pooled["n"][i]),
            "mean_score": float(pooled["p"][i] / pooled["n"][i]) if pooled["n"][i] else None,
            "share_positive": float(pooled["y"][i] / pooled["n"][i]) if pooled["n"][i] else None} for i in range(bins)]
    return {"point": {"ece": float(np.mean([c["ece"] for c in pts])), "brier": float(np.mean([c["brier"] for c in pts]))},
            "reps": {"ece": _unit_mean(eces), "brier": _unit_mean(briers)}, "units": len(pts), "reliability": rel}


# --- one comparison --------------------------------------------------------------------------------------------------

def _delta_block(old: dict, new: dict, level: float) -> dict:
    out = {"old": {k: round(old["point"][k], 6) for k in METRICS}, "new": {k: round(new["point"][k], 6) for k in METRICS},
           "old_ci": {k: lb.ci_of(old["reps"][k], level) for k in ("balanced_accuracy",)},
           "new_ci": {k: lb.ci_of(new["reps"][k], level) for k in ("balanced_accuracy",)}}
    out["delta"] = {k: paired_delta(old, new, k, level) for k in METRICS}
    return out


def _fmt_ci(c: dict) -> dict:
    return {"low": c["low"], "high": c["high"]}


def compare(sc: Scored, old: str, new: str, public_ids: set, k_examples: int = 3) -> dict:
    """Everything one version step reports, before the lineage-level Holm adjustment (``lineage``)."""
    so, sn = system_stats(sc, old), system_stats(sc, new)
    if so["overall"] is None or sn["overall"] is None:
        raise ValueError(f"{old} -> {new}: both versions need every required suite evaluated")
    out = {"from": old, "to": new}
    ov = _delta_block(so["overall"], sn["overall"], sc.level)
    for blk in ("old_ci", "new_ci"):
        ov[blk] = {k: _fmt_ci(v) for k, v in ov[blk].items()}
    out["overall"] = ov
    out["suites"] = {}
    for suite in sc.suites:
        b = _delta_block(so["suites"][suite], sn["suites"][suite], sc.level)
        b["old_ci"] = {k: _fmt_ci(v) for k, v in b["old_ci"].items()}
        b["new_ci"] = {k: _fmt_ci(v) for k, v in b["new_ci"].items()}
        out["suites"][suite] = b
    out["subtasks"], all_pairs, ex = {}, [], {}
    for key in so["subtasks"]:
        suite, st = key.split("/")
        b = _delta_block(so["subtasks"][key], sn["subtasks"][key], sc.level)
        b["old_ci"] = {k: _fmt_ci(v) for k, v in b["old_ci"].items()}
        b["new_ci"] = {k: _fmt_ci(v) for k, v in b["new_ci"].items()}
        b["n"] = {"positive": so["subtasks"][key]["n"]["positive"], "negative": so["subtasks"][key]["n"]["negative"]}
        uo, to_, _, _ = sc.arm(old, suite, st)
        un, tn, _, _ = sc.arm(new, suite, st)
        pairs = align(uo, to_, un, tn)
        all_pairs += pairs
        f = flips(pairs)
        b["flips"] = f
        b["mcnemar"] = mcnemar(f["fixed"], f["broke"])
        ex[key] = examples(pairs, public_ids, k_examples)
        co, cn = calibration_stats(sc, old, suite, st), calibration_stats(sc, new, suite, st)
        if co and cn:
            point = cn["point"]["ece"] - co["point"]["ece"]
            diff = cn["reps"]["ece"] - co["reps"]["ece"]
            c = lb.ci_of(diff, sc.level)
            d_ece = {"point": round(point, 6), "ci": {"low": c["low"], "high": c["high"]}, "p": lv2.p_value(diff, point)}
            b["calibration"] = {"old": {k: round(v, 6) for k, v in co["point"].items()},
                                "new": {k: round(v, 6) for k, v in cn["point"].items()},
                                "delta_ece": d_ece,
                                "delta_brier": round(cn["point"]["brier"] - co["point"]["brier"], 6),
                                "units": co["units"],
                                "reliability": {"old": co["reliability"], "new": cn["reliability"]}}
        out["subtasks"][key] = b
    ft = flips(all_pairs)
    out["flips"] = ft
    out["mcnemar"] = mcnemar(ft["fixed"], ft["broke"])
    out["examples"] = ex
    out["judgments"] = len(all_pairs)
    out["rows"] = len({p["id"] for p in all_pairs})
    # Holm per comparison: six suites, eight subtasks, each metric its own family; ECE over the calibrated subtasks
    for level in ("suites", "subtasks"):
        for m in METRICS:
            apply_holm([b["delta"][m] for b in out[level].values()], m, sc.alpha)
    cal = [b["calibration"]["delta_ece"] for b in out["subtasks"].values() if "calibration" in b]
    for d, adj in zip(cal, lv2.holm([d["p"] for d in cal])):
        d["p_holm"] = adj
        d["verdict"] = verdict(d, adj, sc.alpha, higher_is_better=False)    # a lower ECE is better
    return out


def comparisons_of(versions: list[str]) -> list[tuple[str, str]]:
    """Each consecutive step, plus first to last when there are three or more versions."""
    steps = list(zip(versions, versions[1:]))
    if len(versions) >= 3:
        steps.append((versions[0], versions[-1]))
    return steps


def lineage(sc: Scored, versions: list[str], public_ids: set, k_examples: int = 3) -> list[dict]:
    """Every comparison of one lineage, with the overall verdicts Holm-adjusted across the lineage's comparisons."""
    comps = [compare(sc, a, b, public_ids, k_examples) for a, b in comparisons_of(versions)]
    for m in METRICS:
        apply_holm([c["overall"]["delta"][m] for c in comps], m, sc.alpha)
    for c in comps:
        c["kind"] = "step" if versions.index(c["to"]) - versions.index(c["from"]) == 1 else "first to last"
    return comps


# --- cost and tokens -------------------------------------------------------------------------------------------------

def token_summary(old: dict, new: dict) -> dict:
    """``old``/``new``: {check key: reported input tokens or None}. Means over checks both versions report."""
    keys = sorted(k for k in set(old) & set(new) if old[k] is not None and new[k] is not None)
    if not keys:
        return {"checks": 0}
    a = np.array([old[k] for k in keys], float)
    b = np.array([new[k] for k in keys], float)
    return {"checks": len(keys), "old_mean": round(float(a.mean()), 1), "new_mean": round(float(b.mean()), 1),
            "delta_mean": round(float((b - a).mean()), 1), "delta_pct": round(float(100 * (b.sum() / a.sum() - 1)), 2),
            "old_total": int(a.sum()), "new_total": int(b.sum())}


def cost_summary(old: dict | None, new: dict | None) -> dict | None:
    """``old``/``new``: the published ``run.cost`` entries (usd_total, usd_per_1000, basis). The change is
    ``comparable`` only when both costs come from the same tariff, or from the same machine type: a self-hosted
    cost is a share of the VM's time, so a run on another machine or with another batch of systems moves it for
    reasons that have nothing to do with the model."""
    if not old or not new or old.get("usd_per_1000") is None or new.get("usd_per_1000") is None:
        return None
    a, b = old["usd_per_1000"], new["usd_per_1000"]
    ka, kb = cost_basis(old.get("basis")), cost_basis(new.get("basis"))
    comparable = ka == kb and ka["kind"] in ("metered", "vm_allocation")
    return {"old_usd_per_1000": round(a, 5), "new_usd_per_1000": round(b, 5), "delta_usd_per_1000": round(b - a, 5),
            "delta_pct": round(100 * (b / a - 1), 2) if a else None,
            "old_usd_total": old.get("usd_total"), "new_usd_total": new.get("usd_total"),
            "old_basis": old.get("basis"), "new_basis": new.get("basis"), "comparable": comparable,
            **({} if comparable else {"why_not_comparable": f"{ka['detail']} vs {kb['detail']}"})}


def cost_basis(basis: str | None) -> dict:
    """{"kind": "metered" | "vm_allocation" | "other", "detail": tariff or machine}."""
    b = basis or ""
    if b.startswith("measured usage"):
        return {"kind": "metered", "detail": b}
    m = re.search(r" x (\S+) \$", b)
    if b.startswith("allocated VM time") and m:
        return {"kind": "vm_allocation", "detail": m.group(1)}
    return {"kind": "other", "detail": b or "no basis"}
