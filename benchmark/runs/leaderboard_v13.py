"""Leaderboard v1.3: profanity is "Profanity or obscenity — Civil Comments"; everything else as in v1.2.

    uv run python benchmark/runs/leaderboard_v13.py
    uv run python benchmark/runs/leaderboard_v13.py --ledgers <ledger> <arms> ... --out <file> --note "<what changed>"
    uv run python benchmark/runs/leaderboard_v13.py --final     # signed contract v1.1 and approval 5: leaderboard-final.json

Runs the unchanged evaluator under contract v1.1, the primary freeze manifest, extension manifests 1 to 4, approval 4
and implementations-v1.3 (the profanity subtask answers v1-f4-obscenity). By default it reads the core ledgers
without their PII rows (AI4Privacy; v1.2 replaced them), the extension ledger without the lexicon-selected profanity
rows (kept as their own challenge set in the v1.2 analysis), the Nemotron PII ledger and the Civil Comments profanity
ledger. Category weights are unchanged. Writes ``leaderboard-v1.3.json``. No model calls.

Run-aware (run_context.py): ``--res`` defaults to ``benchmark/results/<GOLDRAILS_RUN>``, ``--manifests-dir`` to
``benchmark/subsets/<GOLDRAILS_FROZEN_RUN>``, ``--serving`` to ``<res>/serving-v13.json`` (built from that run's own
ledgers by serving_from_ledger.py; it must exist). The implementations declarations always come from
``benchmark/subsets/first-benchmark``. For any run other than the first: the signed contract, no approval records
(``--approvals`` adds some), extension manifests are whichever of 1 to 4 exist, a missing ``test-rerun`` ledger is
skipped, and the superseded arms (core F5, lexicon profanity) are simply absent, so ``--skip-superseded`` only records
that. For the first run everything is as it was.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402

REPO = RC.REPO
CTX = RC.current()
RES = CTX.results
SUB = CTX.frozen_subsets
IMPL_DIR = RC.IMPL_DIR
OPTIONAL = {"test-rerun"}      # a run with no transient failures has no rerun ledger


def default_ledgers(tmp: Path, res: Path = None) -> tuple[list, dict]:
    res = res or RES
    args, dropped = [], {"old PII rows": 0, "lexicon-selected profanity rows": 0}
    drops = {"test": lambda r: r.get("id", "").startswith("f5-"), "test-rerun": lambda r: r.get("id", "").startswith("f5-"),
             "ext-test": lambda r: r.get("id", "").startswith("f4-civil_comments_profanity-")}
    for name in list(drops) + ["pii-v12-test", "prof-v13-test"]:
        if not (res / f"{name}.jsonl").exists() and name not in OPTIONAL:
            raise SystemExit(f"missing ledger {RC.rel(res / f'{name}.jsonl')}")
    for name, drop in drops.items():
        if name in OPTIONAL and not (res / f"{name}.jsonl").exists():
            continue
        dst = tmp / f"{name}.jsonl"
        with (res / f"{name}.jsonl").open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
            for line in fin:
                if drop(json.loads(line)):
                    dropped["old PII rows" if name != "ext-test" else "lexicon-selected profanity rows"] += 1
                    continue
                fout.write(line)
        args += [str(dst), str(res / f"{name}.arms.jsonl")]
    for name in ("pii-v12-test", "prof-v13-test"):
        args += [str(res / f"{name}.jsonl"), str(res / f"{name}.arms.jsonl")]
    return args, dropped


def inputs(final: bool, res: Path, sub: Path, serving: Path | None = None, approvals=None, first: bool = None,
           contract: str | None = None) -> dict:
    """Everything the evaluator is given besides the ledgers. ``first`` (default: ``sub`` is the first run's) keeps
    the first run's fixed choices: all four extension manifests, approval 4 or 5, the draft contract unless --final."""
    first = RC.is_protected(sub) if first is None else first
    if contract is None:
        contract = ("benchmark/contracts/v1.1-signed.json" if final or not first else "benchmark/contracts/v1.1.json")
    if approvals is None:
        approvals = ((sorted(sub.glob("analysis-approval-5*.json")) if final else [sub / "analysis-approval-4.json"])
                     if first else [])
    exts = [sub / f"freeze-extension-{n}.json" for n in (1, 2, 3, 4)]
    if not first:
        exts = [x for x in exts if x.exists()]
    return {"contract": contract, "approvals": [Path(x) for x in approvals], "manifest": sub / "freeze-manifest.json",
            "extensions": exts, "implementations": IMPL_DIR / "implementations-v1.3.json",
            "serving": Path(serving) if serving else res / "serving-v13.json"}


def command(args: list, inp: dict, out: str) -> list:
    return [sys.executable, "-m", "goldrails_bench.leaderboard", *args, "--mode", "final",
            "--contract", inp["contract"], "--freeze-manifest", str(inp["manifest"]),
            *[x for p in inp["extensions"] for x in ("--extension-manifest", str(p))],
            *[x for p in inp["approvals"] for x in ("--analysis-approval", str(p))],
            "--implementations", str(inp["implementations"]),
            "--serving", str(inp["serving"]), "--out", out]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledgers", nargs="*")
    ap.add_argument("--res", default=str(RES), help="results directory of the run (default benchmark/results/<GOLDRAILS_RUN>)")
    ap.add_argument("--manifests-dir", default=str(SUB),
                    help="directory holding the freeze manifests (default benchmark/subsets/<GOLDRAILS_FROZEN_RUN>)")
    ap.add_argument("--serving", help="allocated serving time records (default <res>/serving-v13.json)")
    ap.add_argument("--approvals", nargs="*", help="analysis approval records; default: approval 5 (--final) or 4 for "
                                                    "the first run, none for any other run")
    ap.add_argument("--contract", help="evaluation contract (default: signed v1.1 with --final or for a new run)")
    ap.add_argument("--skip-superseded", action="store_true",
                    help="record that the superseded arms (core F5, lexicon profanity) were not run; the default for "
                         "any run other than the first")
    ap.add_argument("--out")
    ap.add_argument("--note")
    ap.add_argument("--final", action="store_true",
                    help="signed contract v1.1 and the approval-5 records (one per freeze manifest); default out "
                         "leaderboard-final.json. Without it, the draft contract and approval 4, as first built")
    a = ap.parse_args(argv)
    res, sub = Path(a.res), Path(a.manifests_dir)
    first = RC.is_protected(sub)
    a.out = a.out or str(res / ("leaderboard-final.json" if a.final else "leaderboard-v1.3.json"))
    inp = inputs(a.final, res, sub, a.serving, a.approvals, first, a.contract)
    if not inp["serving"].exists():
        raise SystemExit(f"no serving records at {RC.rel(inp['serving'])}: build them from this run's own test ledgers "
                         "with serving_from_ledger.py (another run's serving time would price the wrong windows)")
    missing = [RC.rel(p) for p in [inp["manifest"], *inp["approvals"]] if not Path(p).exists()]
    if missing:
        raise SystemExit(f"missing inputs: {missing}")
    with tempfile.TemporaryDirectory() as td:
        args, dropped = (a.ledgers, {}) if a.ledgers else default_ledgers(Path(td), res)
        cmd = command(args, inp, a.out)
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:])
            return r.returncode
    doc = json.loads(Path(a.out).read_text())
    doc.setdefault("provenance", {})["v1_3"] = {
        "analysis": "v1.3: profanity subtask is 'Profanity or obscenity — Civil Comments' (original obscene rater "
                    "fractions, >= 0.5 yes, 0 no); PII on Nemotron-PII (v1.2); category weights unchanged",
        "rows_left_out": dropped, "note": a.note}
    if a.skip_superseded or not first:
        doc["provenance"]["v1_3"]["superseded_not_run"] = {**RC.SUPERSEDED["core"], **RC.SUPERSEDED["extension"]}
        doc["provenance"]["v1_3"]["extension_manifests"] = [p.name for p in inp["extensions"]]
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "done", dropped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
