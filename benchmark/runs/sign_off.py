"""Owner sign-off for the first benchmark: sign contract v1.1 and confirm the analysis, in one step.

    uv run python benchmark/runs/sign_off.py --by "Full Name" --statement "..."          # shows what it would write
    uv run python benchmark/runs/sign_off.py --by "Full Name" --statement "..." --write  # writes the files

Only the project owner runs this, with their own name and words. It records their decision; nobody runs it for them.

Why one step: the evaluator hashes the whole contract, status included. Changing v1.1 from draft to signed gives it a
new hash, and the primary freeze manifest and both extension manifests pinned the earlier ones (29085f28aec4a4a9 and
463b3349d8c7de6e). So the signature needs, beside it, an approval of that contract change for each manifest. This
script writes:

- benchmark/contracts/v1.1.json: version "v1.1", status "signed off by <by> on <date>". Nothing else changes.
- analysis-approval-5.json: supersedes approval 4. Same scoring code (0744223, sha256 92a74bcc...), contract change
  from the primary manifest's hash to the signed hash, confirmed by the owner.
- analysis-approval-5-ext1.json and analysis-approval-5-ext2.json: the same contract change for each extension
  manifest, confirmed by the owner.

It refuses to run if the scoring code or the draft contract differ from what approval 4 names. Commit the four files,
then build the final leaderboard with the command it prints.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "benchmark"))
from goldrails_bench import leaderboard as lb  # noqa: E402

SUB = REPO / "benchmark" / "subsets" / "first-benchmark"
CONTRACT = REPO / "benchmark" / "contracts" / "v1.1.json"
A4 = SUB / "analysis-approval-4.json"
MANIFESTS = {"": SUB / "freeze-manifest.json", "-ext1": SUB / "freeze-extension-1.json", "-ext2": SUB / "freeze-extension-2.json"}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


STALE = ("sign_off.py is retired and refuses to run. It did its one job on 28 September 2026: contract v1.1 is signed "
         "(benchmark/contracts/v1.1-signed.json) and the approval-5 records exist. Running it again would rewrite "
         "benchmark/contracts/v1.1.json and the first benchmark's approval records. A later run that needs a sign-off "
         "gets its own record, written by the owner for that run.")


def main() -> int:
    raise SystemExit(STALE)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--by", required=True, help="your full name, as the approver")
    ap.add_argument("--statement", required=True, help="your confirmation, in your own words")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--write", action="store_true", help="write the files (default: show them only)")
    args = ap.parse_args()

    a4 = json.loads(A4.read_text(encoding="utf-8"))
    draft = json.loads(CONTRACT.read_text(encoding="utf-8"))
    problems = []
    if sha256(Path(lb.__file__)) != a4["approved_scoring_sha256"]:
        problems.append("the scoring code differs from the code approval 4 names")
    if lb._stable_hash(draft) != a4["approved_contract_hash"]:
        problems.append("contract v1.1 differs from the draft approval 4 names (already signed, or edited)")
    if problems:
        print("Refusing: " + "; ".join(problems) + ".", file=sys.stderr)
        return 1

    signed = {**draft, "version": "v1.1", "status": f"signed off by {args.by} on {args.date}"}
    new_hash = lb._stable_hash(signed)
    confirmation = {"by": args.by, "at": args.date, "statement": args.statement}
    out = {CONTRACT: signed}
    for suffix, man in MANIFESTS.items():
        pinned = json.loads(man.read_text(encoding="utf-8"))["contract"]["hash"]
        ident = lb.freeze_mod.manifest_identity(man)
        rec = {
            "approval_version": lb.APPROVAL_VERSION,
            "name": f"first-benchmark sign-off: contract v1.1 signed, for {man.name} (5{suffix})",
            "supersedes": "analysis-approval-4.json (kept as history)" if not suffix else None,
            "primary_manifest": str(man.relative_to(REPO)),
            "primary_manifest_sha256": sha256(man),
            "primary_manifest_commit": ident.get("commit") if isinstance(ident, dict) else None,
            "schema": lb.SCHEMA,
            "frozen_contract_hash": pinned,
            "approved_contract_hash": new_hash,
            "contract_change": ("benchmark/contracts/v1.1.json signed: version v1.1-draft to v1.1 and status draft to "
                                "signed off. No rule, weight, threshold or suite changes."
                                + (" For the primary manifest this also carries approval 4's change from v1.0 to v1.1."
                                   if not suffix else "")),
            "approved_by": args.by, "approved_at": args.date,
            "recorded_by": f"{args.by}, with benchmark/runs/sign_off.py",
            "basis": "Owner sign-off of contract v1.1 and confirmation of the corrected analysis.",
            "confirmation": confirmation,
        }
        if not suffix:   # the primary manifest's approval also carries approval 4's scoring-code acceptance
            rec.update({k: a4[k] for k in ("frozen_scoring_sha256", "approved_scoring_sha256", "approved_scoring_commit",
                                           "changes", "unchanged")})
        out[SUB / f"analysis-approval-5{suffix}.json"] = {k: v for k, v in rec.items() if v is not None}

    for path, doc in out.items():
        print(f"--- {path.relative_to(REPO)}")
        if path == CONTRACT:
            print(f"version: v1.1, status: {signed['status']}, hash {new_hash}")
        else:
            print(json.dumps({k: doc[k] for k in ("name", "frozen_contract_hash", "approved_contract_hash", "confirmation")}, indent=1))
    if not args.write:
        print("\nNothing written. Re-run with --write to record this sign-off.")
        return 0
    for path, doc in out.items():
        path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    approvals = " ".join(f"--analysis-approval $S/analysis-approval-5{s}.json" for s in MANIFESTS)
    print(f"""
Written. Commit the four files, then build the final results:

git add benchmark/contracts/v1.1.json benchmark/subsets/first-benchmark/analysis-approval-5*.json
git commit -m "Owner sign-off: contract v1.1 signed; corrected analysis confirmed"
R=benchmark/results/first-benchmark S=benchmark/subsets/first-benchmark
uv run python -m goldrails_bench.leaderboard $R/test.jsonl $R/test.arms.jsonl $R/test-rerun.jsonl $R/test-rerun.arms.jsonl $R/ext-test.jsonl $R/ext-test.arms.jsonl --mode final --contract benchmark/contracts/v1.1.json --freeze-manifest $S/freeze-manifest.json --extension-manifest $S/freeze-extension-1.json --extension-manifest $S/freeze-extension-2.json {approvals} --implementations $S/implementations-v1.1.json --serving $R/serving-final.json --out $R/leaderboard-final.json
uv run python benchmark/runs/site_results.py && uv run python benchmark/runs/check_page.py""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
