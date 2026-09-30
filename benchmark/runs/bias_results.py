"""Bias results for the first benchmark, from the frozen test ledger. No model calls.

    uv run python benchmark/runs/bias_results.py

Joins benchmark/results/first-benchmark/test-bias.jsonl to the v1.0 release annotations and computes:
- B1: FPR and FNR gaps by identity mention (Civil Comments identity), using each system's frozen content ``request``
  threshold from the freeze manifest (one global threshold per system, fitted on tuning rows only).
- B3: discrim-eval discrimination score and BBQ accuracy and bias score, decision models only; Bedrock is listed as
  not applicable.
B2 is absent: the counterfactual pairs are not reviewed yet, so they are outside the scored subset.

Every ledger record must carry the committed freeze stamp and match a frozen bias arm (system, question set, config
hash); anything else stops the script. Writes benchmark/results/first-benchmark/bias.json.

Run-aware (run_context.py): ``--res`` defaults to ``benchmark/results/<GOLDRAILS_RUN>`` (ledgers in, bias.json out)
and ``--sub`` to ``benchmark/subsets/<GOLDRAILS_FROZEN_RUN>`` (freeze manifests); ``--out`` overrides the output.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from goldrails_bench.bias_metrics import build_bias_section, mentions_from_attribute
from goldrails_bench.score import score_of

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402

REPO = RC.REPO
CTX = RC.current()
RES = CTX.results
SUB = CTX.frozen_subsets
MANIFEST = SUB / "freeze-manifest.json"
RELEASE = REPO / "dataset" / "release" / "v1.0" / "build" / "F7.test.jsonl"
EXTENSIONS = sorted(SUB.glob("freeze-extension-*.json"))


def extension_release(extensions=None) -> Path:
    """The F7 test file of the release the extension subset was drawn from (v1.1, or provisional v1.1-ai)."""
    ext = (extensions or EXTENSIONS)[0]
    subset = json.loads(ext.read_text(encoding="utf-8"))["extends"].get("subset", "first-benchmark-v1.1")
    release = json.loads((REPO / "benchmark" / "subsets" / subset / "manifest.json").read_text(encoding="utf-8"))["release"]
    return REPO / "dataset" / "release" / release / "build" / "F7.test.jsonl"
B1_ROLE = "request"          # Civil Comments rows are user comments


def jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default=str(RES), help="results directory (default benchmark/results/<GOLDRAILS_RUN>)")
    ap.add_argument("--sub", default=str(SUB), help="manifests directory (default benchmark/subsets/<GOLDRAILS_FROZEN_RUN>)")
    ap.add_argument("--out", help="output file (default <res>/bias.json)")
    a = ap.parse_args(argv)
    res, sub = Path(a.res), Path(a.sub)
    out_path = Path(a.out) if a.out else res / "bias.json"
    manifest = sub / "freeze-manifest.json"
    extensions = sorted(sub.glob("freeze-extension-*.json"))
    man = json.loads(manifest.read_text(encoding="utf-8"))
    arms = {(a["system"], a["question_set"], a["config_hash"]): a for a in man["arms"] if a["suite"].startswith("bias_")}
    rows = {r["id"]: r for r in jsonl(RELEASE)}
    ledger = jsonl(res / "test-bias.jsonl")
    b2_ledger = jsonl(res / "ext-test-bias.jsonl") if (res / "ext-test-bias.jsonl").exists() else []
    if b2_ledger:   # B2 arms are frozen by the extension manifest, B2 rows live in release v1.1
        for p in extensions:
            ext = json.loads(p.read_text(encoding="utf-8"))
            arms.update({(a["system"], a["question_set"], a["config_hash"]): a for a in ext["arms"] if a["suite"] == "bias_b2"})
        rows.update({r["id"]: r for r in jsonl(extension_release(extensions))})
        ledger = ledger + b2_ledger

    problems = [r["id"] for r in ledger if not r.get("freeze") or (r["system"], r["question_set"], r["config_hash"]) not in arms]
    if problems:
        raise SystemExit(f"{len(problems)} bias records do not match a frozen arm, e.g. {problems[:3]}")

    identities = sorted({k for r in rows.values() if r["provenance"]["source"] == "civil_comments_identity"
                         for k in (r["attribute"].get("fractions") or {})})
    thresholds, b1, b2, de, bbq = {}, [], [], [], []
    for r in ledger:
        row = rows[r["id"]]
        base = {"id": r["id"], "system": r["system"], "config_hash": r["config_hash"], "ok": bool(r.get("ok")),
                "cluster": r.get("group")}
        if r["subtask"].startswith("b1"):
            arm = arms[(r["system"], r["question_set"], r["config_hash"])]
            thresholds[r["system"]] = arm["thresholds"][B1_ROLE]["threshold"]
            b1.append({**base, "expected": r["expected"],
                       "score": score_of(r) if r.get("ok") and r.get("answers") else None,
                       "identity_mentions": mentions_from_attribute(row["attribute"], identities)})
        elif r["subtask"] == "b2_counterfactual":
            arm = arms[(r["system"], r["question_set"], r["config_hash"])]
            thresholds.setdefault(r["system"], arm["thresholds"][B1_ROLE]["threshold"])
            at = row["attribute"]
            b2.append({**base, "expected": r["expected"], "pair_id": at.get("base") or r["group"],
                       "variant": at.get("value"), "cluster": at.get("template_family") or r.get("group"),
                       "score": score_of(r) if r.get("ok") and r.get("answers") else None})
        elif r["source"] == "discrim_eval":
            at = row["attribute"]
            p = ((r.get("answers") or {}).get("favourable") or {}).get("noul")
            de.append({**base, "decision_question_id": at["decision_question_id"], "age": at["age"],
                       "gender": at["gender"], "race": at["race"], "p_yes": p})
        elif r["source"] == "bbq":
            at = row["attribute"]
            pred = ((r.get("answers") or {}).get("answer") or {}).get("choice")
            bbq.append({**base, "category": at["kind"], "question_index": at["question_index"],
                        "context_condition": at["context_condition"], "label": row["expected"],
                        "target_loc": at["target_option"], "unknown_loc": at["unknown_option"], "prediction": pred})

    out = build_bias_section(b1=b1, b2=b2, discrim_eval=de, bbq=bbq, thresholds=thresholds)
    out["bias"]["status"] = {
        "reading": "exploratory diagnostics, not a fairness ranking",
        "why": ["discrim-eval: the 50 selected cases span 31 scenarios, 19 with a single case, and no case matches the full "
                "reference demographic; groups mostly answered different scenarios, so gaps can reflect scenario "
                "difficulty rather than demographic sensitivity, and bootstrapping does not remove that confounding",
                "Civil Comments: 100 comments with 1 to 18 mentions per identity (for example 3 Muslim, 2 Asian, 1 "
                "transgender), too few for stable group-level comparisons",
                ("B2: evaluated on reviewed pairs" if b2 else "B2 counterfactual pairs are not yet reviewed and not evaluated")],
        "next_run": ("select a small number of discrim-eval scenarios with every matched demographic variant, and sample "
                     "enough harmful and benign comments per compared identity group; grouping matters more than total rows")}
    out["bias"]["inputs"] = {"ledger": str((res / "test-bias.jsonl").resolve().relative_to(REPO)),
                             "freeze_manifest": str(manifest.resolve().relative_to(REPO)), "b1_threshold_role": B1_ROLE,
                             "counts": dict(Counter(f"{r['system']}|{r['question_set']}" for r in ledger)),
                             "b2": (f"{len(b2)} items from ext-test-bias.jsonl under freeze-extension-1.json" if b2 else
                                    "not evaluated: counterfactual pairs await human review (outside the scored subset)")}
    out_path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"B1 {len(b1)} items, B2 {len(b2)}, discrim-eval {len(de)}, BBQ {len(bbq)}; wrote {RC.rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
