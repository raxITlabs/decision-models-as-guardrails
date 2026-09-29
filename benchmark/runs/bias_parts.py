"""Three-part view of the existing bias results. Copies values from bias.json; computes no score. No model calls.

    uv run python benchmark/runs/bias_parts.py

Reads benchmark/results/first-benchmark/bias.json and writes benchmark/results/first-benchmark/bias-parts.json,
organised into the three parts of the assessment:
- Hate and discrimination detection: a pointer only. That task is scored inside the content suite, so this file
  carries no separate number for it and does not count its rows.
- Guardrail fairness diagnostics: B1 false-positive and false-negative rates per identity group with denominators,
  intervals and the gap against rows that do not mention the group; B2 matched pairs with decision consistency and
  correctness side by side. Evidence flags follow bias.json's own ``low_support`` and ``min_support``.
- Decision-model bias diagnostics: B3 (BBQ, discrim-eval) exactly as bias.json has them; a managed guardrail keeps
  bias.json's not-applicable status and reason.

Every number is copied, never recomputed. The only new fields are grouping, labels and evidence flags derived from
fields bias.json already holds. bias.json, the leaderboards and the six-suite overall are untouched.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "benchmark" / "results" / "first-benchmark"
SOURCE = RES / "bias.json"
OUT = RES / "bias-parts.json"
SCHEMA = "goldrails-bias-parts/0.1"
GENERATED_BY = "benchmark/runs/bias_parts.py"

PART_HATE = "Hate and discrimination detection"
PART_FAIRNESS = "Guardrail fairness diagnostics"
PART_DECISION = "Decision-model bias diagnostics"
PARTS = (PART_HATE, PART_FAIRNESS, PART_DECISION)

# Keys copied unchanged from a B1 cell (mentioned, not mentioned, or overall).
CELL_KEYS = ("benign", "harmful", "benign_failed", "harmful_failed", "label_unknown", "false_positives",
             "false_negatives", "fpr", "fpr_numerator", "fpr_denominator", "fpr_interval", "fnr", "fnr_numerator",
             "fnr_denominator", "fnr_interval")
CONSISTENCY_VS_CORRECTNESS = ("A system that allows everything can be perfectly consistent while failing its task, so "
                              "decision consistency (flip rate) is shown beside paired correctness and is never read "
                              "on its own.")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cell(c: dict) -> dict:
    """One B1 cell with its sample sizes named. ``n_benign`` and ``n_harmful`` are the FPR and FNR denominators used
    under the failure policy; ``benign`` and ``harmful`` are the raw labelled row counts."""
    out = {k: copy.deepcopy(c[k]) for k in CELL_KEYS if k in c}
    out["n_benign"] = c["fpr_denominator"]
    out["n_harmful"] = c["fnr_denominator"]
    return out


def identity_view(g: dict, min_support: int) -> dict:
    m, n = g["mentioned"], g["not_mentioned"]
    small = [f"{side} {label} denominator {d} is below min_support {min_support}"
             for side, c in (("mentioned", m), ("not_mentioned", n))
             for label, d in (("benign", c["fpr_denominator"]), ("harmful", c["fnr_denominator"]))
             if d < min_support]
    reasons = (["bias.json marks low_support"] if g["low_support"] else []) + small
    return {"identity": g["identity"],
            "mentioned": cell(m),
            "not_mentioned": cell(n),
            "unknown_annotation": copy.deepcopy(g["unknown_annotation"]),
            "fpr_gap_vs_not_mentioned": copy.deepcopy(g["fpr_gap"]),
            "fnr_gap_vs_not_mentioned": copy.deepcopy(g["fnr_gap"]),
            "low_support": g["low_support"],
            "insufficient_evidence": bool(reasons),
            "insufficient_evidence_reasons": reasons}


def b2_view(b2: dict, min_support: int) -> dict:
    counts = b2["counts"]
    pairs = counts["evaluable"]
    return {"n_pairs": counts["sets"],
            "n_pairs_evaluable": pairs,
            "counts": copy.deepcopy(counts),
            "consistency": {"flip_rate": b2["flip_rate"], "flip_rate_interval": copy.deepcopy(b2["flip_rate_interval"]),
                            "flips": counts["flips"], "denominator": pairs},
            "correctness": {"paired_correct_rate": b2["paired_correct_rate"],
                            "paired_correct_interval": copy.deepcopy(b2["paired_correct_interval"]),
                            "paired_correctness_denominator": b2["paired_correctness_denominator"],
                            "all_correct": counts["all_correct"], "all_wrong": counts["all_wrong"],
                            "consistent_wrong_rate": b2["consistent_wrong_rate"]},
            "by_expected": copy.deepcopy(b2["by_expected"]),
            "quality": copy.deepcopy(b2["quality"]),
            "too_few_pairs": pairs < min_support,
            "too_few_pairs_reason": (f"{pairs} evaluable pairs, below min_support {min_support}"
                                     if pairs < min_support else None)}


def fairness_part(bias: dict) -> dict:
    gf = bias["guardrail_fairness"]
    ms = gf["min_support"]
    systems = []
    for s in gf["systems"]:
        entry = {k: s[k] for k in ("system", "config_hash", "kind", "threshold", "threshold_policy", "failure_policy")}
        if "B1" in s:
            b1 = s["B1"]
            overall = cell(b1["overall"])
            overall["rows_without_annotation"] = b1["overall"]["rows_without_annotation"]
            entry["B1"] = {"overall": overall,
                           "quality": copy.deepcopy(b1["quality"]),
                           "identities": [identity_view(g, ms) for g in b1["identities"]]}
        entry["B2"] = b2_view(s["B2"], ms) if "B2" in s else None
        systems.append(entry)
    return {"part": PART_FAIRNESS,
            "measures": ("Whether false blocks or missed violations differ across identity groups (B1), and whether "
                         "identity-swapped examples with one shared expected action receive consistent and correct "
                         "decisions (B2)."),
            "placement": "Alongside the core results, outside the six-suite overall score.",
            "reading": bias["status"]["reading"],
            "min_support": ms,
            "consistency_vs_correctness": CONSISTENCY_VS_CORRECTNESS,
            "notes": {k: bias["notes"][k] for k in ("B1", "B2", "quality_guard", "threshold") if k in bias["notes"]},
            "intervals": copy.deepcopy(bias["intervals"]),
            "systems": systems}


def discrim_eval_view(de: dict, config_hash: str, unmatched_note: str | None) -> dict:
    return {"status": "evaluated", "config_hash": config_hash, "result": copy.deepcopy(de),
            "unmatched_scenarios": unmatched_note is not None,
            "unmatched_note": unmatched_note,
            "insufficient_evidence": unmatched_note is not None,
            "isolates_demographic_bias": unmatched_note is None}


def decision_part(bias: dict) -> dict:
    db = bias["decision_bias"]
    unmatched = next((w for w in bias["status"]["why"] if w.startswith("discrim-eval")), None)
    by_system: dict[str, list] = {}
    for e in db["systems"]:
        by_system.setdefault(e["system"], []).append(e)
    systems = []
    for system in sorted(by_system):
        entries = by_system[system]
        na = next((e for e in entries if e["status"] == "not_applicable"), None)
        view = {"system": system, "kind": entries[0]["kind"]}
        if na is not None:
            view.update({"status": "not_applicable", "reason": na["reason"], "config_hash": na["config_hash"],
                         "items_ignored": na["items_ignored"],
                         "bbq": {"status": "not_applicable", "reason": na["reason"]},
                         "discrim_eval": {"status": "not_applicable", "reason": na["reason"]}})
            systems.append(view)
            continue
        bbq = next((e for e in entries if "bbq" in e), None)
        de = next((e for e in entries if "discrim_eval" in e), None)
        view["status"] = "evaluated" if bbq or de else "not_evaluated"
        view["bbq"] = ({"status": "evaluated", "config_hash": bbq["config_hash"], "result": copy.deepcopy(bbq["bbq"])}
                       if bbq else {"status": "not_evaluated"})
        view["discrim_eval"] = (discrim_eval_view(de["discrim_eval"], de["config_hash"], unmatched)
                                if de else {"status": "not_evaluated"})
        view["not_evaluated_configs"] = [
            {"config_hash": e["config_hash"], "status": e["status"],
             "note": "listed by bias.json with no B3 items under this configuration"}
            for e in entries if e["status"] == "not_evaluated"]
        systems.append(view)
    return {"part": PART_DECISION,
            "measures": ("Whether a decision model makes unsupported stereotyped assumptions on the existing dataset "
                         "tasks (BBQ, discrim-eval), with source-defined metrics."),
            "placement": "Separate supplementary evaluation, outside the six-suite overall score.",
            "reading": bias["status"]["reading"],
            "notes": {"B3": bias["notes"]["B3"]},
            "tracks": list(db["tracks"]),
            "systems": systems}


def hate_part() -> dict:
    return {"part": PART_HATE,
            "measures": "Whether the system detects content labelled as hateful or discriminatory.",
            "location": "content suite (F1), inside the six-suite overall",
            "separate_score": None,
            "note": ("This task is scored inside the content suite where the source labels support it. No separate "
                     "number is reported here, and its rows are not repeated in the fairness or decision-model parts. "
                     "The dataset audit records which rows and labels belong to it.")}


def build(bias_doc: dict, source_sha256: str) -> dict:
    bias = bias_doc["bias"]
    return {"meta": {"schema": SCHEMA,
                     "source": str(SOURCE.relative_to(REPO)),
                     "source_sha256": source_sha256,
                     "source_schema": bias["schema"],
                     "generated_by": GENERATED_BY,
                     "note": ("Values are copied from bias.json, not recomputed. Only grouping, labels and evidence "
                              "flags derived from bias.json fields are added. Scores, denominators and the six-suite "
                              "overall are unchanged."),
                     "aggregate": bias["aggregate"],
                     "aggregate_note": bias["notes"]["aggregate"]},
            "parts": list(PARTS),
            "hate_detection": hate_part(),
            "guardrail_fairness": fairness_part(bias),
            "decision_model_bias": decision_part(bias)}


def main() -> int:
    out = build(json.loads(SOURCE.read_text(encoding="utf-8")), sha256(SOURCE))
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    gf, db = out["guardrail_fairness"]["systems"], out["decision_model_bias"]["systems"]
    print(f"{len(gf)} fairness systems, {len(db)} decision-model systems; wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
