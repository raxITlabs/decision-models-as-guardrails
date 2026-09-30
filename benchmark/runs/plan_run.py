"""The whole run as a plan: every call-making stage in runbook order, with no client built and nothing called.

    GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/plan_run.py            # summary per stage and totals
    GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/plan_run.py --verbose  # plus every stage's full plan

Each stage is planned by its own script's ``--dry-run`` code (systems from the implementations declaration, rows from
the subsets, already-recorded rows from the run's ledgers). Totals are evaluations (ledger rows): one request per row
for every system here, since no question set exceeds the 16-question GPU chunk, and before any retry. The first run's
counts are read from its own ledgers for comparison.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402
import first_benchmark as FB  # noqa: E402
import extension_run as EXT  # noqa: E402
import pii_v12_run as PII  # noqa: E402
import profanity_v13_run as PROF  # noqa: E402

ALL = {"open", "jev", "regex", "bedrock"}


def stages(ctx: RC.RunContext) -> list[tuple[str, RC.Plan]]:
    core_chosen = FB.load_chosen() if FB.SELECTION.exists() else None
    ext_chosen = EXT.chosen_map(1) if EXT.selection_path(1).exists() else None
    out = [
        ("core tune", FB.plan_stage("tune", ALL, "tune", None, None, FB.DEFAULT_SUITES)),
        ("extension tune", EXT.plan("tune", EXT.DEFAULT_SUBSET, {"open", "jev", "bedrock"}, "tune", None, None, 1, EXT.DEFAULT_STAGES)),
        ("pii-v12 tune", PII.plan("tune", {"open", "jev", "bedrock"}, "tune")),
        ("prof-v13 tune", PROF.plan("tune", {"open", "jev", "bedrock"}, "tune")),
        ("core test", FB.plan_stage("test", ALL, "test", core_chosen, None, FB.DEFAULT_SUITES)),
        ("extension test", EXT.plan("test", EXT.DEFAULT_SUBSET, {"open", "jev", "bedrock"}, "test", ext_chosen, None, 1, EXT.DEFAULT_STAGES)),
        ("pii-v12 test", PII.plan("test", {"open", "jev", "bedrock"}, "test", manifest=PII.EXT)),
        ("prof-v13 test", PROF.plan("test", {"open", "jev", "bedrock"}, "test", manifest=PROF.EXT)),
        ("core latency", FB.plan_stage("latency", ALL, "tune", core_chosen, 100, FB.DEFAULT_SUITES)),
        ("extension latency (jev, bedrock)", EXT.plan("latency", EXT.DEFAULT_SUBSET, {"jev", "bedrock"}, "tune", ext_chosen, 50, 1, EXT.DEFAULT_STAGES)),
        ("pii-v12 latency", PII.plan("latency", {"open", "jev", "bedrock"}, "tune", limit=50)),
        ("prof-v13 latency", PROF.plan("latency", {"open", "jev", "bedrock"}, "tune", limit=50)),
    ]
    return out


def first_run_counts() -> dict:
    """{ledger name: {provider: records}} from the first run's own ledgers."""
    res = RC.RESULTS / RC.FIRST
    out = {}
    for p in sorted(res.glob("*.jsonl")):
        if p.name.endswith(".arms.jsonl") or p.name == "serving.jsonl":
            continue
        c = Counter()
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c[RC.provider_of(json.loads(line)["system"])] += 1
        out[p.name] = dict(c)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true", help="print every stage's full plan")
    ap.add_argument("--json", help="also write the plan summary to this file")
    a = ap.parse_args(argv)
    ctx = RC.current()
    print(json.dumps(ctx.describe()))
    first = first_run_counts()
    grand, grand_first = Counter(), Counter()
    summary = []
    for name, p in stages(ctx):
        if a.verbose:
            p.print()
        systems = sorted({x["system"] for x in p.lines})
        suites = sorted({x["suite"] for x in p.lines})
        tot = {k: v["to_run"] for k, v in p.totals().items()}
        rec = sum(v["already_recorded"] for v in p.totals().values())
        ledgers = p.by_ledger()
        base = {Path(l).name: sum(first.get(Path(l).name, {}).values()) for l in ledgers}
        grand.update(tot)
        for l in ledgers:
            grand_first.update(first.get(Path(l).name, {}))
        summary.append({"stage": name, "suites": suites, "systems": systems, "ledgers": ledgers,
                        "to_run_by_provider": tot, "already_recorded": rec, "first_run": base, "notes": p.notes})
        print(f"\n## {name}\n   suites   {', '.join(suites)}\n   systems  {len(systems)}: {', '.join(systems)}")
        for l, n in ledgers.items():
            print(f"   ledger   {l}: {n} to run   (first run {Path(l).name}: {base[Path(l).name]})")
        print("   by provider  " + ", ".join(f"{k} {v}" for k, v in sorted(tot.items())) + f";  already recorded {rec}")
        for n in p.notes:
            print(f"   note     {n}")
    print("\n## totals (evaluations = requests before retries)")
    for k in sorted(set(grand) | set(grand_first)):
        print(f"   {k:22s} this run {grand[k]:6d}   first run, same ledgers {grand_first[k]:6d}")
    print(f"   {'all':22s} this run {sum(grand.values()):6d}   first run, same ledgers {sum(grand_first.values()):6d}")
    extra = {k: sum(v.values()) for k, v in first.items() if k not in {Path(l).name for s in summary for l in s["ledgers"]}}
    if extra:
        print("   first-run ledgers with no counterpart in this plan: " + ", ".join(f"{k} {v}" for k, v in extra.items()))
    if a.json:
        Path(a.json).write_text(json.dumps({"context": ctx.describe(), "stages": summary,
                                            "totals": dict(grand), "first_run_totals": dict(grand_first)}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
