"""Run the arms that became eligible after review (denied topics, profanity, B2 pairs) beside the frozen first
benchmark, reusing its clients, question sets and declared load. The review may be human (dataset v1.1) or, for the
provisional extension, a single AI reviewer (dataset v1.1-ai, subset first-benchmark-v1.1-ai); the subset manifest says
which, and every report carries it.

A set of systems can be frozen and run as its own numbered extension (``--extension 2 --systems bedrock``), for example
when one provider's credentials arrive later; each extension manifest is committed before its own test calls.

    uv run python benchmark/runs/extension_run.py tune --systems open,jev,bedrock
    uv run python benchmark/runs/extension_run.py freeze          # writes the extension manifest; commit it
    uv run python benchmark/runs/extension_run.py test --systems open,jev,bedrock
    uv run python benchmark/runs/extension_run.py latency --systems open,jev,bedrock

Rows come from the v1.1 subset (``--subset``, default ``first-benchmark-v1.1-ai``, the provisional AI-reviewed one),
which must keep the first benchmark's core test rows unchanged (``subset --carry-over first-benchmark``). Nothing here
touches a core arm.

Which run: ``GOLDRAILS_RUN`` and ``GOLDRAILS_FROZEN_RUN`` (run_context.py). A run other than the first skips the
superseded lexicon profanity stage and its masked-spelling diagnostic by default (``--stages`` overrides), freezes
against the signed contract v1.1 (``--contract`` overrides), and keeps its extension manifest and selection in
``benchmark/subsets/<RUN>/``. ``--dry-run`` prints what a stage would run and calls nothing.

- Denied topics tunes its candidate question set on the reviewed tuning rows; the best set per system is frozen. Every
  system gets the same topic definitions, examples and order (topics.json; Bedrock's guardrail is built from it).
- Profanity (word filters, contract v1.1) asks decision models ``v1-f4-profanity``; Bedrock answers the same key from
  the frozen word-filter guardrail's managed PROFANITY list only. The masked-spelling rows (``profanity_obfuscated``)
  run with the same frozen arm as a diagnostic: the leaderboard never scores them.
- B2 reuses each system's frozen content question set and ``request`` threshold from the primary manifest; not tuned.

The extension manifest (``freeze-extension-1.json``) names the primary manifest's sha256. The runner refuses test rows
until it is committed. Ledgers: ``ext-tune.jsonl``, ``ext-test.jsonl``, ``ext-test-bias.jsonl``, ``ext-latency.jsonl``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import first_benchmark as FB  # noqa: E402  (the frozen run's clients, question sets, load and paths)
import run_context as RC  # noqa: E402

from goldrails_bench.runner import run_matrix  # noqa: E402
from goldrails_bench.subset import load_subset_rows  # noqa: E402

CTX = FB.CTX
PRIMARY = FB.MANIFEST
EXT_DIR = CTX.frozen_subsets
ext_path = lambda n: EXT_DIR / f"freeze-extension-{n}.json"
selection_path = lambda n: CTX.frozen_selections / ("ext-selection.json" if n == 1 else f"ext-selection-{n}.json")
CONTRACT = CTX.default_contract(FB.REPO / "benchmark" / "contracts" / "v1.1.json")
OUT = FB.OUT
DEFAULT_SUBSET = "first-benchmark-v1.1-ai"
# stage -> (feature, subtasks on tune, subtasks on test, leaderboard suite, client suite, candidate question sets)
STAGES = {
    "denied_topics": ("F3", {"topic"}, {"topic"}, "denied_topics", "denied_topics", ["v1-f3-topics"]),
    "profanity": ("F4", {"profanity"}, {"profanity", "profanity_obfuscated"}, "word_filters", "word_filters", ["v1-f4-profanity"]),
    "bias_b2": ("F7", set(), {"b2_counterfactual"}, "bias_b2", "content", None),
}
DEFAULT_STAGES = [s for s in STAGES if s not in CTX.skipped("extension")]


def rows_for(subset: str, stage: str, split: str) -> list:
    feat, tune_subs, test_subs, *_ = STAGES[stage]
    subs = tune_subs if split == "tune" else test_subs
    return [r for r in load_subset_rows(subset, feat, split) if r.subtask in subs]


def systems_for(stage: str, kinds: set) -> dict:
    systems = FB.clients(kinds, STAGES[stage][4])
    return {k: v for k, v in systems.items() if k != "regex-baseline"}       # the regex baseline covers custom words only


def ledger_of(stage_name: str, stage: str) -> Path:
    return OUT / (f"ext-{stage_name}-bias.jsonl" if stage == "bias_b2" else f"ext-{stage_name}.jsonl")


def names_for(name: str, suite: str, cands, chosen) -> list:
    if chosen is not None:
        return [chosen[(name, suite)]] if (name, suite) in chosen else []
    return cands or []


def run(stage_name: str, subset: str, kinds: set, split: str, chosen=None, serial=False, limit=None, ext=1, stages=None):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = ext_path(ext) if split == "test" else None
    for stage, (feat, _, _, suite, _, cands) in STAGES.items():
        if stage not in (stages or STAGES):
            continue
        rows = rows_for(subset, stage, split)[: limit or None]
        if not rows:
            print(f"{stage_name} {stage}: no eligible {split} rows in {subset}", flush=True)
            continue
        ledger = ledger_of(stage_name, stage)
        for name, (client, gpu) in systems_for(stage, kinds).items():
            names = names_for(name, suite, cands, chosen)
            for q in names:
                out = run_matrix({name: client}, FB.qsets([q]), rows, workers={"jev-1.13.0": 8}, serial=serial,
                                 gpu_of={name: gpu} if gpu is not None else {}, results_path=ledger, load=FB.LOAD,
                                 freeze_manifest=manifest, progress=lambda *_: None)
                print(f"{stage_name} {stage:14s} {name:24s} {q:20s} {len(out):4d} rows, {sum(not r['ok'] for r in out)} failed", flush=True)


def plan(stage_name: str, subset: str, kinds: set, split: str, chosen=None, limit=None, ext=1, stages=None) -> RC.Plan:
    """What ``run`` would run, from the implementations declaration: no clients, no calls."""
    p = RC.Plan(CTX, "extension_run.py", stage_name)
    p.path("results", OUT)
    p.path("subset", FB.REPO / "benchmark" / "subsets" / subset / "manifest.json")
    if split == "test":
        p.path("manifest (read)", ext_path(ext))
    if stage_name in ("test", "latency"):
        p.path("selection (read)", selection_path(ext))
    skipped = [s for s in STAGES if s not in (stages or STAGES)]
    if skipped:
        p.notes.append("stages skipped: " + ", ".join(f"{s} ({CTX.skipped('extension').get(s, 'not selected')})" for s in skipped))
    for stage, (feat, _, _, suite, client_suite, cands) in STAGES.items():
        if stage not in (stages or STAGES):
            continue
        rows = rows_for(subset, stage, split)[: limit or None]
        if not rows:
            p.notes.append(f"{stage}: no eligible {split} rows in {subset}")
            continue
        systems = {k: v for k, v in RC.declared_systems(FB.IMPL, kinds, client_suite).items() if k != "regex-baseline"}
        for name in systems:
            note = None
            if chosen is None and stage_name in ("test", "latency"):   # chosen at the freeze
                if stage == "bias_b2":
                    names, note = ["<frozen content set>"], "the system's frozen content question set and threshold"
                else:
                    names, note = (cands or [])[:1], f"one of {cands}, chosen at the freeze"
            else:
                names = names_for(name, suite, cands, chosen)
            for q in names:
                p.add(stage, name, [q], rows, ledger_of(stage_name, stage), note)
    return p


def chosen_map(ext: int = 1) -> dict:
    sel = json.loads(selection_path(ext).read_text())
    return {(x["system"], x["suite"]): x["question_set"] for x in sel["chosen"]}


def freeze(subset: str, kinds: set, ext: int = 1, stages=None):
    from goldrails_bench import freeze as F
    from goldrails_bench.leaderboard import build
    from goldrails_bench.policy import DEFAULT_POLICY
    from goldrails_bench.runner import config_hash
    primary = json.loads(PRIMARY.read_text())
    primary_sha = hashlib.sha256(PRIMARY.read_bytes()).hexdigest()
    splits = {json.loads(l)["dataset"]["split"] for l in (OUT / "ext-tune.jsonl").read_text().splitlines() if l.strip()}
    if splits != {"tune"}:   # question-set choice and thresholds come from tuning rows only
        raise SystemExit(f"ext-tune.jsonl holds splits {sorted(splits)}; only tuning rows may select or fit anything")
    stages = stages or list(STAGES)
    doc = build([str(OUT / "ext-tune.jsonl"), str(OUT / "ext-tune.arms.jsonl")], contract_path=CONTRACT, mode="smoke")
    names = set(systems_for("denied_topics", kinds)) | (set(systems_for("profanity", kinds)) if "profanity" in stages else set())
    earlier = set()
    for n in range(1, ext):   # arms frozen by an earlier extension stay there
        if ext_path(n).exists():
            earlier |= {a["system"] for a in json.loads(ext_path(n).read_text())["arms"]}
    best = {}
    for a in doc["arms"]:
        if a["system"] not in names or a["system"] in earlier:
            continue
        if not any(STAGES[st][3] == a["suite"] for st in stages if st != "bias_b2"):
            continue
        # a profanity arm covers one of word_filters' two subtasks, so rank by the subtasks it scored
        subs = [x["task_score"] for x in a["subtasks"].values() if x.get("status") == "evaluated" and x.get("task_score") is not None]
        v = (a.get("suite_score") or {}).get("value") or (sum(subs) / len(subs) if subs else None)
        k = (a["system"], a["suite"])
        if v is not None and (k not in best or v > best[k][0] or (v == best[k][0] and a["question_set"] < best[k][1]["question_set"])):
            best[k] = (v, a)
    test_sha = {}
    for stage in ("denied_topics", "profanity"):
        if stage not in stages:
            continue
        feat, suite = STAGES[stage][0], STAGES[stage][3]
        test_sha[suite] = load_subset_rows(subset, feat, "test")[0].dataset["sha256"]
    subset_man = json.loads((FB.REPO / "benchmark" / "subsets" / subset / "manifest.json").read_text())
    basis = ("single-AI reference labels (provisional)" if subset_man.get("provisional_ai_reference") else "human review")
    m = F.write_manifest(doc, ext_path(ext), retry_policy=DEFAULT_POLICY, test_datasets=test_sha,
                         arms=[a["arm_id"] for _, a in best.values()],
                         extends={"manifest_sha256": primary_sha,
                                  "reason": f"denied topics, profanity and B2 pairs became eligible after review: {basis} "
                                            f"(subset {subset}, contract v1.1)", "subset": subset,
                                  "systems": sorted(names - earlier)})
    chosen = [{"system": a["system"], "suite": a["suite"], "question_set": a["question_set"], "tune_task_score": v}
              for v, a in sorted(best.values(), key=lambda t: (t[1]["suite"], t[1]["system"]))]
    b2 = rows_for(subset, "bias_b2", "test") if "bias_b2" in stages else []
    if b2:   # B2 reuses the frozen content arm of each system: same question set, same request threshold
        sha = load_subset_rows(subset, "F7", "test")[0].dataset["sha256"]
        for name, (client, _) in systems_for("bias_b2", kinds).items():
            if name in earlier:
                continue
            content = next((a for a in primary["arms"] if a["system"] == name and a["suite"] == "content"), None)
            if content is None:
                continue
            q = content["question_set"]
            m["arms"].append({"system": name, "question_set": q, "config_hash": config_hash(client, FB.qsets([q])[q]),
                              "dataset_sha256": sha, "suite": "bias_b2", "thresholds": content["thresholds"],
                              "tuned_on": content["tuned_on"]})
            chosen.append({"system": name, "suite": "bias_b2", "question_set": q, "tune_task_score": None})
    sel = {"rule": ("denied topics and profanity: the candidate question set with the highest tuning task score per "
                    "system, ties to the lower name; B2: the system's frozen content question set and request threshold"),
           "contract": str(CONTRACT.relative_to(FB.REPO)), "chosen": chosen}
    if not CTX.is_first:   # the first run's files keep their historical shape
        m["run"] = sel["run"] = {"id": CTX.run, "declaration": RC.rel(CTX.subsets / "run.json"), "subset": subset,
                                 "contract": RC.rel(CONTRACT), "stages": list(stages),
                                 "skipped_superseded": {s: r for s, r in CTX.skipped("extension").items() if s not in stages}}
    probs = F.validate(m)
    if probs:
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    ext_path(ext).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
    selection_path(ext).write_text(json.dumps(sel, indent=1) + "\n")
    FB.arm_summary(m)
    print(f"extension manifest: {len(m['arms'])} arms -> {ext_path(ext).relative_to(FB.REPO)}; commit it before the test stage")


def parse_stages(s: str | None) -> list:
    if not s:
        return DEFAULT_STAGES
    out = [x.strip() for x in s.split(",") if x.strip()]
    bad = [x for x in out if x not in STAGES]
    if bad:
        raise SystemExit(f"unknown stages {bad}; choose from {list(STAGES)}")
    return [x for x in STAGES if x in out]


def main(argv=None) -> int:
    global CONTRACT
    load_dotenv(find_dotenv(usecwd=True))
    RC.check_env_unchanged(CTX)
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("tune", "freeze", "test", "latency"))
    ap.add_argument("--systems", default="open,jev,bedrock")
    ap.add_argument("--subset", default=DEFAULT_SUBSET)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--extension", type=int, default=1, help="which extension manifest to freeze or run under")
    ap.add_argument("--stages", help=f"comma list from {list(STAGES)}; default {DEFAULT_STAGES}")
    ap.add_argument("--contract", help=f"contract the freeze fits under (default {RC.rel(CONTRACT)})")
    ap.add_argument("--dry-run", "--plan", dest="dry_run", action="store_true",
                    help="print paths, stages, systems, rows and already-recorded rows; build no client, call nothing")
    ap.add_argument(RC.I_KNOW_FLAG, dest="i_know", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    kinds = set(a.systems.split(","))
    stages = parse_stages(a.stages)
    if a.contract:
        CONTRACT = Path(a.contract).resolve()
    if a.stage in ("tune", "freeze"):
        RC.require_same_run(CTX, a.stage)
    if a.dry_run:
        print(json.dumps(CTX.describe()))
        if a.stage == "freeze":
            print(f"== extension_run.py freeze (run {CTX.run}) — DRY RUN\n   reads   {RC.rel(OUT / 'ext-tune.jsonl')}\n"
                  f"   reads   {RC.rel(PRIMARY)} (primary manifest sha256 goes in extends)\n"
                  f"   writes  {RC.rel(ext_path(a.extension))}{'  (EXISTS: freeze would refuse)' if ext_path(a.extension).exists() else ''}\n"
                  f"   writes  {RC.rel(selection_path(a.extension))}\n   contract {RC.rel(CONTRACT)}\n   stages  {stages}\n"
                  f"   protected first-benchmark location: {RC.is_protected(ext_path(a.extension))}\n"
                  "   needs live clients (config hashes for the B2 arms): run between make up and make down")
            return 0
        chosen = chosen_map(a.extension) if a.stage != "tune" and selection_path(a.extension).exists() else None
        split = "test" if a.stage == "test" else "tune"
        limit = (a.limit or 50) if a.stage == "latency" else a.limit
        plan(a.stage, a.subset, kinds, split, chosen, limit, a.extension, stages).print()
        return 0
    if a.stage == "freeze":
        RC.refuse_protected([ext_path(a.extension), selection_path(a.extension)], a.i_know, "freeze")
        RC.refuse_existing([ext_path(a.extension), selection_path(a.extension)], "freeze")
    else:
        RC.refuse_protected([OUT], a.i_know, a.stage)
    if a.stage == "tune":
        run("tune", a.subset, kinds, "tune", stages=stages)
    elif a.stage == "freeze":
        freeze(a.subset, kinds, a.extension, stages)
    elif a.stage == "test":
        run("test", a.subset, kinds, "test", chosen=chosen_map(a.extension), ext=a.extension, stages=stages)
    else:
        run("latency", a.subset, kinds, "tune", chosen=chosen_map(a.extension), serial=True, limit=a.limit or 50,
            ext=a.extension, stages=stages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
