"""Extension-specific freeze validation for leaderboard v1.3. No model calls; reads committed files and ledgers only.

    uv run python benchmark/runs/validate_extension_freeze.py

The evaluator (approved as analysis 4, so left unchanged) checks the implementations declaration one link deep: it
compares the file it extends with the earliest test call in any ledger, and the extending file with the earliest call
of any extension. Leaderboard v1.3 declares implementations-v1.3.json, which extends implementations-v1.1.json, which
extends implementations.json. Read one link deep, the chain raises two pre-registration blockers even when every arm's
declaration came before that arm's own test calls.

This script checks the chain per arm instead. For every arm in leaderboard-v1.3.json it finds the first file in the
chain that declared the arm's system and question set, and requires that file's commit to precede the arm's first
test attempt on the arm's own dataset. It also requires the freeze manifest that holds the arm's thresholds to precede
those calls, and each extension's declaration change to name only arms tested after it. Writes
``benchmark/results/first-benchmark/extension-freeze-validation.json`` and exits non-zero on any failure.

Run-aware (run_context.py): ``--res`` defaults to ``benchmark/results/<GOLDRAILS_RUN>`` and ``--sub`` to
``benchmark/subsets/<GOLDRAILS_FROZEN_RUN>``; the declaration chain always comes from ``benchmark/subsets/first-benchmark``.
Missing ledgers (a run with no ``test-rerun``) and missing extension manifests (a run with no extension 2) are skipped
and listed. ``--leaderboard`` defaults to leaderboard-v1.3.json for the first run and leaderboard-final.json otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402

REPO = RC.REPO
CTX = RC.current()
RES = CTX.results
SUB = CTX.frozen_subsets
IMPL_DIR = RC.IMPL_DIR
LEADERBOARD = RES / ("leaderboard-v1.3.json" if CTX.is_first else "leaderboard-final.json")
TEST_LEDGERS = ("test", "test-rerun", "ext-test", "pii-v12-test", "prof-v13-test")
MANIFESTS = ("freeze-manifest.json", *[f"freeze-extension-{n}.json" for n in (1, 2, 3, 4)])


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def added(path: Path) -> tuple[datetime, str]:
    """Commit time (UTC) and short hash of the commit that added the file."""
    out = git("log", "--diff-filter=A", "--format=%ct %h", "--", str(path.relative_to(REPO))).splitlines()
    ts, h = out[-1].split()
    return datetime.fromtimestamp(int(ts), timezone.utc), h


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def at(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def declared(doc: dict) -> tuple[set, set]:
    """Systems and question sets a declaration names."""
    sy = doc["systems"]
    systems = set(sy["decision_models"]) | set(sy["managed_service"]["composite_of"].values()) | set(sy.get("code_baselines", {}))
    qs = {q for v in doc.get("candidate_question_sets", {}).values() if isinstance(v, list) for q in v}
    qs |= {x["question_set"] for subs in doc.get("subtask_composition", {}).values() for x in subs.values()}
    return systems, qs


def chain(name: str) -> list:
    """The declaration chain, oldest first: [(file, committed_at, commit, systems, question sets)]."""
    out = []
    while name:
        p = IMPL_DIR / name
        doc = json.loads(p.read_text(encoding="utf-8"))
        t, h = added(p)
        out.append({"file": str(p.relative_to(REPO)), "committed_at": t, "commit": h, "decl": declared(doc),
                    "composition": doc.get("subtask_composition") or {},
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        name = doc.get("extends")
    return out[::-1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default=str(RES), help="results directory (default benchmark/results/<GOLDRAILS_RUN>)")
    ap.add_argument("--sub", default=str(SUB), help="manifests directory (default benchmark/subsets/<GOLDRAILS_FROZEN_RUN>)")
    ap.add_argument("--leaderboard", help=f"leaderboard to check (default {RC.rel(LEADERBOARD)})")
    ap.add_argument("--out", help="output file (default <res>/extension-freeze-validation.json)")
    a = ap.parse_args(argv)
    res, sub = Path(a.res), Path(a.sub)
    leaderboard = Path(a.leaderboard) if a.leaderboard else (
        LEADERBOARD if res == RES else res / ("leaderboard-v1.3.json" if RC.is_protected(res) else "leaderboard-final.json"))
    out_path = Path(a.out) if a.out else res / "extension-freeze-validation.json"
    lb = json.loads(leaderboard.read_text(encoding="utf-8"))
    decl = chain("implementations-v1.3.json")
    frozen, skipped = {}, []
    for name in MANIFESTS:
        p = sub / name
        if not p.exists():
            skipped.append(RC.rel(p))
            continue
        t, h = added(p)
        for arm in json.loads(p.read_text(encoding="utf-8"))["arms"]:
            frozen[(arm["config_hash"], arm["dataset_sha256"])] = (name, t, h)
    first = {}   # (config_hash, dataset sha256) -> earliest test attempt
    for name in TEST_LEDGERS:
        if not (res / f"{name}.jsonl").exists():
            skipped.append(RC.rel(res / f"{name}.jsonl"))
            continue
        for line in (res / f"{name}.jsonl").open(encoding="utf-8"):
            r = json.loads(line)
            key = (r["config_hash"], (r.get("dataset") or {}).get("sha256"))
            for a in r.get("attempts") or []:
                t = at(a["at"])
                if key not in first or t < first[key]:
                    first[key] = t
    arms, bad = [], []
    for a in lb["arms"]:
        key = (a["config_hash"], a["dataset"]["sha256"])
        t0 = first.get(key)
        d = next((x for x in decl if a["system"] in x["decl"][0] and a["question_set"] in x["decl"][1]), None)
        fz = frozen.get(key)
        ok = bool(t0 and d and fz and d["committed_at"] < t0 and fz[1] < t0)
        arms.append({"arm": a["arm_id"], "first_test_attempt": t0 and iso(t0),
                     "declared_in": d and d["file"], "declared_at": d and iso(d["committed_at"]),
                     "frozen_in": fz and fz[0], "frozen_at": fz and iso(fz[1]), "ok": ok})
        if not ok:
            bad.append(a["arm_id"])
    # each declaration change names only arms first tested after it
    links = []
    for prev, cur in zip(decl, decl[1:]):
        new_qs = cur["decl"][1] - prev["decl"][1]
        affected = [x for x in arms if x["arm"].split("|")[1] in new_qs]
        comp = {su for su in set(cur["composition"]) | set(prev["composition"])
                if cur["composition"].get(su) != prev["composition"].get(su)}
        changed_qs = {v["question_set"] for su in comp for st, v in cur["composition"].get(su, {}).items()
                      if (prev["composition"].get(su) or {}).get(st) != v}   # only subtasks whose declaration changed
        comp_arms = [x for x in arms if x["arm"].split("|")[1] in changed_qs]
        early = [x["arm"] for x in comp_arms if at(x["first_test_attempt"]) < cur["committed_at"]]
        links.append({"file": cur["file"], "committed_at": iso(cur["committed_at"]), "commit": cur["commit"],
                      "changes_composition_of": sorted(comp),
                      "composition_note": (f"{len(early)} arms in this composition were tested before it was declared "
                                           "(the composition aggregates their frozen scores; it changes no score or "
                                           "threshold). Declared under contract v1.1 and analysis approval 4." if early
                                           else None),
                      "adds_question_sets": sorted(new_qs), "arms_using_them": len(affected),
                      "earliest_of_those_test_attempts": min((x["first_test_attempt"] for x in affected), default=None),
                      "ok": all(x["first_test_attempt"] and at(x["first_test_attempt"]) > cur["committed_at"] for x in affected)})
    evaluator = [b for b in lb["publication_blockers"] if "implementations file" in b]
    out = {"leaderboard": RC.rel(leaderboard),
           "leaderboard_sha256": hashlib.sha256(leaderboard.read_bytes()).hexdigest(),
           "declaration_chain": [{"file": x["file"], "committed_at": iso(x["committed_at"]), "commit": x["commit"],
                                  "sha256": x["sha256"]} for x in decl],
           "rule": ("each arm: the first declaration naming its system and question set, and the freeze manifest holding "
                    "its thresholds, were both committed before the arm's first test attempt on its own dataset"),
           "arms_checked": len(arms), "arms_failed": bad, "declaration_links": links,
           "evaluator_blockers_addressed": evaluator,
           "passed": not bad and all(x["ok"] for x in links), "arms": arms}
    if skipped:   # absent in the first run's layout, so its file keeps its shape
        out["inputs_not_present"] = skipped
    out_path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for x in links:
        print(f"{x['file']}: committed {x['committed_at']}; adds {x['adds_question_sets']}; "
              f"{x['arms_using_them']} arms, first test {x['earliest_of_those_test_attempts']}; {'ok' if x['ok'] else 'FAIL'}")
    print(f"{len(arms) - len(bad)} of {len(arms)} arms pass" + (f"; failed: {bad}" if bad else ""))
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
