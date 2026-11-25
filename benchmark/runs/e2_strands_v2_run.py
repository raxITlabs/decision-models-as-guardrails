"""Strands Decider v2: five checkpoints added to the edition 2 results, all six suites on the rows the other systems ran.

    uv run python benchmark/runs/e2_strands_v2_run.py plan --source local          # rows per subtask, window, guard
    uv run python benchmark/runs/e2_strands_v2_run.py roster --pass 1              # point the VM at pass 1 (VM stopped)
    uv run python benchmark/runs/e2_strands_v2_run.py smoke --pass 1 --source local   # 20 dev rows per subtask
    uv run python benchmark/runs/e2_strands_v2_run.py freeze --source local        # extension manifest; commit it first
    uv run python benchmark/runs/e2_strands_v2_run.py vm-pass --pass 1 --source local   # up, smoke, run, retry, pause
    uv run python benchmark/runs/e2_strands_v2_run.py roster --pass 2   # then vm-pass --pass 2; likewise pass 3
    uv run python benchmark/runs/e2_strands_v2_run.py report --source local        # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_strands_v2_run.py score --source local   # benchmark/results/final/

The systems are Strands Decider v2 (released 17 November 2026 by Strands Labs, Apache-2.0): five Gemma 4 instruction
models fine-tuned for decisions, at E2B, E4B, 12B, 26B-A4B and 31B. Each is pinned to its Hugging Face commit and served
on the project VM by the vendor's own package at a pinned commit of github.com/strands-labs/strands-decider, through
the same System One request, the same eight question sets and the same fixed 0.5 rule as Strands Decider 2B and the
six v1 checkpoints (``e2_strands_run.py``). The bnb-4bit preview of the 31B (24 November 2026) is not run: it is a
preview of a quantised copy, not a release.

What differs from v1, and what the run checks:
- Window. A v2 checkpoint reads up to 32,768 tokens (``decision_config.json`` ``max_length_validated``) and refuses a
  longer prompt with HTTP 422 instead of cutting it. Each model entry pins ``max_length = 32768``; the identity records
  it and ``build`` refuses a VM that serves another. ``plan`` counts rows estimated over it.
- Calibration. Each checkpoint applies its own fitted temperature (1.41 to 1.62) to the option scores. A temperature
  does not move which option is larger, so a yes/no probability is >= 0.5 exactly when it was before scaling: the fixed
  0.5 rule is unaffected. The probabilities, and so the curve metrics, are the calibrated ones the vendor serves.
- Weights. A v2 checkpoint holds the merged weights (no LoRA adapter, no base model download).

The rows are exactly the other systems' rows: the five full-run suites and the r26 prompt-attack suite, test split plus
the unpublished slice, owner exclusions left out. ``e2_full.TestRows.guard`` refuses anything else, before any call and
again before each one. The unpublished slice goes only to the project's own VM.

The freeze is an extension manifest (``goldrails_bench.freeze``) that extends the primary
(``benchmark/subsets/edition2/freeze-manifest.json``) with one arm per checkpoint and question set: Strands Decider 2B's
eight arms with this checkpoint's model name and endpoint. The config hash is the scorer's
(``e2_sample.scorer_record``: adapter, model, endpoint, question set), so it is known before any call; ``run`` refuses a
checkpoint whose smoke-test serving does not reproduce it, and refuses to send anything until the manifest is
committed. ``freeze`` refuses until ``APPROVAL`` records the owner's approval of the VM spend. Nothing is fitted.

Hardware. The vendor's model cards say the 26B-A4B and the 31B need one 80 GB GPU and cannot be split, and the 12B one
48 GB GPU, so the run uses one A100 80 GB (a2-ultragpu-1g) in three passes: the E2B, E4B and 12B together (about
50 GB of weights), then the 26B-A4B, then the 31B. The VM goes to us-central1, or to us-east4 or us-east5 when
us-central1 has no A100 capacity (``REGIONS``). Self-hosted cost is each pass's VM up-to-paused time, at the tariff of
the region it ran in, split across that pass's checkpoints by their run seconds.

Not done here, after the run is scored: the v1 -> v2 lineages in ``goldrails_bench.versions.LINEAGES`` (``V1_OF``) and
this folder in ``e2_versions.SOURCES``; both read scored ledgers, so they are added with the score.

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/strands-deciders-v2/private/``;
``report`` and ``score`` write committed ledgers with public test rows only and run the privacy checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_attacks_rerun as ar  # noqa: E402  (points e2_full's globals at the r26 rerun, which its score reads)
import e2_full as full  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_smoke as smoke  # noqa: E402

REPO = full.REPO
CODE_SHA = "6d85079caf1f1906ebb0f1370b56ef28ba7aa93e"   # github.com/strands-labs/strands-decider main, 24 November 2026
MAX_LENGTH = 32768   # every v2 checkpoint's decision_config.json max_length_validated, and the package default
# name: (Hugging Face repo, commit, VM port, pass, display name)
SYSTEMS = {
    "strands-decider-e2b-v2": ("StrandsAgents/strands-decider-E2B-gemma4-v2-2611",
                               "eca68159a790d1e7ff93559d166dc3fbe24d5975", 8040, 1, "Strands Decider v2 E2B"),
    "strands-decider-e4b-v2": ("StrandsAgents/strands-decider-E4B-gemma4-v2-2611",
                               "1717bca732ba4ef8c8c531fbc9875fafaf858811", 8041, 1, "Strands Decider v2 E4B"),
    "strands-decider-12b-v2": ("StrandsAgents/strands-decider-12B-gemma4-v2-2611",
                               "41d5dc0d20a4deb2835690eb7529ee92463f6c9f", 8042, 1, "Strands Decider v2 12B"),
    "strands-decider-26b-a4b-v2": ("StrandsAgents/strands-decider-26B-A4B-gemma4-v2-2611",
                                   "099eb33e6c4ac0dafc967f73c0042a0cf3e78758", 8043, 2, "Strands Decider v2 26B-A4B"),
    "strands-decider-31b-v2": ("StrandsAgents/strands-decider-31B-gemma4-v2-2611",
                               "ddaf9e068f5277e17a3e1d7ae7ffdecbd67fbebb", 8044, 3, "Strands Decider v2 31B"),
}
NAMES = {k: v[4] for k, v in SYSTEMS.items()}
# The v1 checkpoint of the same size (e2_strands_run.SYSTEMS), for the version lineages once v2 is scored. v1 had no 31B.
V1_OF = {"strands-decider-e2b-v2": "strands-decider-e2b", "strands-decider-e4b-v2": "strands-decider-e4b",
         "strands-decider-12b-v2": "strands-decider-12b", "strands-decider-26b-a4b-v2": "strands-decider-26b-a4b"}
PASSES = (1, 2, 3)
TEMPLATE = "strands-decider-2b"
OUT = full.FINAL / "ledgers" / "strands-deciders-v2"
WORK = OUT / "private"
SMOKE = WORK / "smoke"
LOGS = OUT / "logs"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / "freeze-manifest-strands-deciders-v2.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
TFVARS = REPO / "infra" / "gcp" / "terraform.tfvars"
ROSTER = REPO / "infra" / "gcp" / "terraform.tfvars.strands-deciders-v2.example"
HARDWARE = "a2-ultragpu-1g/us-central1/on-demand"
PASS_HARDWARE = {p: HARDWARE for p in PASSES}
DISK = "pd-balanced/us-central1/third-party"
# Regions the VM may land in, each with its own dated machine and disk tariff. us-central1 is the plan; us-east4 and
# us-east5 were added on 25 November 2026 when us-central1 had no A100 80 GB capacity (ruling 48). Each VM session
# records the tariff of the region it actually ran in.
REGIONS = {
    "us-central1": (HARDWARE, DISK),
    "us-east4": ("a2-ultragpu-1g/us-east4/on-demand", "pd-balanced/us-east4/third-party"),
    "us-east5": ("a2-ultragpu-1g/us-east5/on-demand", "pd-balanced/us-east5/catalog"),
}


def region_of(zone: str) -> str:
    return zone.rsplit("-", 1)[0]
LABEL = ("Strands Decider v2 extension run: five checkpoints on every edition 2 test row and the unpublished slice, "
         "contract v2.0 as amended")
# The owner's approval of the VM spend, in their words and with its date. ``freeze`` refuses while it is None, so no
# manifest (and so no test call) exists before the approval does.
APPROVAL: str | None = ("Strands Decider v2 (five checkpoints) added at the owner's request of 25 November 2026; the owner "
                         "approved the A100 VM spend (forecast USD 40-60) the same day")
NOUL_ADAPTER = {"name": "noul-e2", "version": "1"}
WORKERS = 4
RETRY_ROUNDS = 2
# Every frozen checkpoint ran; a checkpoint frozen but not run would be listed here with the reason.
NOT_RUN: dict = {}
DISCLOSURES = [
    "Five Strands Decider v2 checkpoints (released 17 November 2026) ran after the other systems, under their own "
    "freeze manifest committed before their first test call "
    "(benchmark/subsets/edition2/freeze-manifest-strands-deciders-v2.json). They use Strands Decider 2B's question "
    "sets, request and fixed 0.5 rule; only the checkpoint and the package commit differ.",
    "The five were served by strands-decider at commit 6d85079 of its repository, each on one A100 80 GB "
    "(a2-ultragpu-1g): the E2B, E4B and 12B together on the card, then the 26B-A4B, then the 31B. The VM ran in "
    "us-central1, or in us-east4 or us-east5 when us-central1 had no A100 capacity; the run log records each pass's "
    "zone, and each pass is costed at its region's list price.",
    "Each v2 checkpoint applies the temperature fitted by the vendor and stored in its decision_config.json (E2B "
    "1.5456, E4B 1.4052, 12B 1.5571, 26B-A4B 1.502, 31B 1.6186). A temperature does not change which side of 0.5 a "
    "yes/no probability falls on, so the fixed rule's decisions are the unscaled model's; the probabilities the curve "
    "metrics read are the calibrated ones.",
    "v2 reads up to 32,768 tokens and refuses a longer prompt (HTTP 422) instead of cutting it, as v1 did at 4,096. A "
    "refused row is a failed row, scored wrong as contract v2.0 scores any failed row.",
    "Strands Labs trained v2 on 17.5 million rows, 22% of them converted from more than 200 public datasets listed in "
    "the vendor's data card. A row taken from one of those datasets may have been seen in training; the "
    "unpublished-slice view is the check.",
]
CAVEATS = ["the five Strands Decider v2 checkpoints ran on one A100 80 GB (a2-ultragpu-1g) rather than the full run's "
           "VM models' g2-standard-24 (L4), so their cost is not an equal-hardware comparison"]


def use_paths() -> None:
    sample.OUT, sample.RUN_LOG = OUT, RUN_LOG


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_event(key: str, value) -> None:
    def go():
        d = sample._log()
        d.setdefault(key, []).append(value)
        sample._save_log(d)
    sample._locked(go)


def select(tr) -> dict:
    return ar._select_all_tasks(tr)


def names_of(pass_no: int | None) -> list[str]:
    return [n for n, v in SYSTEMS.items() if pass_no is None or v[3] == pass_no]


def endpoint(name: str) -> str:
    return f"http://localhost:{SYSTEMS[name][2]}"


def _cfg(name: str, qs: str) -> str:
    """The scorer's config hash (``e2_sample.scorer_record``) for this checkpoint's arm on ``qs``."""
    return hashlib.sha256(json.dumps({"adapter": NOUL_ADAPTER, "model": name, "endpoint": endpoint(name),
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16]


# --- systems ---------------------------------------------------------------------------------------------------

def build(names: set) -> tuple[dict, dict]:
    """The served checkpoints in ``names``, each checked against its pinned repo, commit and package commit."""
    from goldrails_bench.adapters import NoulAdapter
    from goldrails_bench.systemone import SystemOneClient
    found, why = smoke.strands_models()
    out, skipped = {}, {}
    for m in found:
        if m["name"] not in names:
            continue
        ref, rev = SYSTEMS[m["name"]][:2]
        ident = m["identity"]
        if (ident.get("ref"), ident.get("revision"), ident.get("code_sha"), ident.get("max_length")) != \
                (ref, rev, CODE_SHA, MAX_LENGTH):
            raise SystemExit(f"{m['name']}: the VM serves {ident}, not {ref}@{rev} with strands-decider {CODE_SHA} "
                             f"and max_length {MAX_LENGTH}")
        c = SystemOneClient(m["name"], base_url=m["url"], model=m["model"], identity=ident, timeout=600)
        out[m["name"]] = (NoulAdapter(c, endpoint=m["url"]), WORKERS)
    for n in sorted(names - set(out)):
        skipped[n] = f"not served on the VM ({why or 'not in the current roster'})"
    return out, skipped


# --- smoke -----------------------------------------------------------------------------------------------------

def run_smoke(names: list[str]) -> dict:
    """20 dev rows per subtask through each served checkpoint (``e2_smoke``'s selection), with the determinism reruns.
    A compatibility check: nothing here is scored."""
    smoke.build_systems = lambda kinds, env=None: build(set(names))
    t = smoke.run_selection({"strands"}, smoke.select(), SMOKE, only=set(names), reruns=True)
    for n in names:
        p = SMOKE / f"{n}.jsonl"
        recs = [json.loads(x) for x in p.open(encoding="utf-8")] if p.exists() else []
        c = Counter(d["outcome"] for d in recs if not d["rerun"])
        right = sum(1 for d in recs if not d["rerun"] and d.get("correct"))
        print(f"smoke {n:28s} {dict(c)} correct {right}/{c.get('decided', 0)}", flush=True)
    return t


def smoke_serving(name: str) -> dict:
    """{question set: serving} from this checkpoint's smoke ledger."""
    p = SMOKE / f"{name}.jsonl"
    srv = {}
    for x in p.open(encoding="utf-8") if p.exists() else []:
        d = json.loads(x)
        if d.get("outcome") == "decided":
            srv.setdefault(d["serving"]["question_set"], d["serving"])
    return srv


def check_smoke(name: str, arms: list) -> None:
    """Refuse a checkpoint whose smoke test did not answer, or whose serving does not give its frozen config hash."""
    srv = smoke_serving(name)
    for a in arms:
        s = srv.get(a["question_set"])
        if s is None:
            raise SystemExit(f"{name}: no decided smoke record for {a['question_set']}; run the smoke stage first")
        got = hashlib.sha256(json.dumps({"adapter": s["adapter"], "model": s["model_id"], "endpoint": s["endpoint"],
                                         "question_set": a["question_set"]}, sort_keys=True).encode()).hexdigest()[:16]
        if got != a["config_hash"]:
            raise SystemExit(f"{name}/{a['question_set']}: smoke serving gives config {got}, frozen {a['config_hash']}")


# --- freeze ----------------------------------------------------------------------------------------------------

def _template_arms() -> list:
    """Strands Decider 2B's eight arms: the primary's for the five kept suites and the r26 extension's for prompt
    attacks."""
    from goldrails_bench import freeze as F
    pm, _ = F.load_committed(PRIMARY)
    xm, _ = F.load_committed(R26)
    arms = [a for a in pm["arms"] if a["system"] == TEMPLATE and a["suite"] != ar.SUITE]
    arms += [a for a in xm["arms"] if a["system"] == TEMPLATE]
    if len(arms) != 8:
        raise SystemExit(f"expected 8 {TEMPLATE} arms to copy, found {len(arms)}")
    return arms


def extension_arms(tr) -> list:
    from goldrails_bench import freeze as F
    pm, _ = F.load_committed(PRIMARY)
    xm, _ = F.load_committed(R26)
    want = {su: d["sha256"] for su, d in pm["integrity"]["datasets"].items() if su != ar.SUITE}
    want[ar.SUITE] = xm["integrity"]["datasets"][ar.SUITE]["sha256"]
    have = {full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES}
    if want != have:
        raise SystemExit(f"test rows differ from the frozen ones: {sorted(k for k in want if want[k] != have.get(k))}")
    out = []
    for name in SYSTEMS:
        for a in _template_arms():
            qs, su = a["question_set"], a["suite"]
            cfg, sha = _cfg(name, qs), have[su]
            out.append({"arm_id": f"{name}|{qs}|{cfg}|{sha[:12]}", "system": name, "question_set": qs,
                        "config_hash": cfg, "suite": su, "score_scale": a["score_scale"],
                        "decision_rule": a["decision_rule"], "dataset": {"sha256": sha},
                        "_template": f"{TEMPLATE}|{qs}|{a['config_hash']}|{a['dataset_sha256'][:12]}"})
    return out


def write_freeze(tr) -> dict:
    from goldrails_bench import freeze as F
    from goldrails_bench import leaderboard_v2 as lv2
    from goldrails_bench.leaderboard import _stable_hash
    from goldrails_bench.policy import DEFAULT_POLICY
    if MANIFEST.exists():
        raise SystemExit(f"{full._rel(MANIFEST)} exists; a freeze is written once")
    if not APPROVAL:
        raise SystemExit("APPROVAL is empty: record the owner's approval of the VM spend before freezing")
    pm, pident = F.load_committed(PRIMARY)
    xm, xident = F.load_committed(R26)
    contract = lv2.load_contract()
    if _stable_hash(contract) != xm["contract"]["hash"]:
        raise SystemExit("the contract changed since the r26 extension; this run would need a contract amendment")
    arms = extension_arms(tr)
    for name in SYSTEMS:                     # checkpoints already smoke-tested must reproduce their hashes now
        if (SMOKE / f"{name}.jsonl").exists():
            check_smoke(name, [a for a in arms if a["system"] == name])
    doc = {"schema": F.EDITION2_SCHEMA, "arms": [{k: v for k, v in a.items() if not k.startswith("_")} for a in arms]}
    extends = {"manifest_sha256": pident["manifest_sha256"], "manifest_path": pident["path"],
               "reason": "five Strands Decider v2 checkpoints released by Strands Labs after the full run, on every "
                         "suite's frozen test rows: the five suites of the primary freeze and the r26 prompt-attack "
                         "suite; no arm of the primary, the r26 extension or any other extension changes",
               "after_extension": {"manifest_sha256": xident["manifest_sha256"], "manifest_path": xident["path"],
                                   "note": "the prompt-attack arms use the r26 dataset version that extension froze; "
                                           "the contract is the one it amended to, unchanged since"}}
    # owner ruling 32: the dataset version every arm records is the frozen copy the other systems answered, so the
    # manifest is written from that copy and names its files by the repository paths the copy mirrors
    integ = full.frozen_integrity(tr)
    files = {full.FEATURE_SUITE[f]: [full.FROZEN / q.relative_to(REPO) if integ else q for q in tr.files[f]]
             for f in full.FEATURES}
    t0 = time.time()
    m = F.write_manifest(doc, MANIFEST, retry_policy=DEFAULT_POLICY,
                         test_datasets={full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES},
                         test_files=files, references=integ["references"] if integ else F.default_references(),
                         edition=2, extends=extends, contract=contract)
    if integ:
        prefix = full._rel(full.FROZEN) + "/"
        for d in m["integrity"]["datasets"].values():
            for x in d["files"]:
                x["path"] = x["path"].removeprefix(prefix)
    probs = F.validate(m) + F.integrity_problems(m, **(integ or {}))
    if probs:
        MANIFEST.unlink()
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    for out_arm, a in zip(m["arms"], arms):
        out_arm["checked_on"] = {"template_arm": a["_template"],
                                 "note": f"{TEMPLATE}'s question set, score scale and fixed rule; config hash from "
                                         "this checkpoint's model name and VM endpoint (the scorer's formula), checked "
                                         "against its smoke-test serving before any test call"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": list(SYSTEMS),
                "checkpoints": {n: {"ref": v[0], "revision": v[1], "code_sha": CODE_SHA, "pass": v[3],
                                    "max_length": MAX_LENGTH}
                                for n, v in SYSTEMS.items()},
                "smoke": full._rel(SMOKE), "data_handling": "the unpublished slice goes only to the project's own VM"}
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"extension manifest: {len(m['arms'])} arms, integrity pass over {m['integrity']['test_rows']} test rows "
          f"({time.time() - t0:.0f}s) -> {full._rel(MANIFEST)}; commit it before any call")
    return m


# --- run -------------------------------------------------------------------------------------------------------

def run(names: list[str], retry_failed: bool) -> dict:
    from goldrails_bench import freeze as F
    try:
        m, ident = F.load_committed(MANIFEST)
    except F.FreezeError as e:
        raise SystemExit(f"refusing to run: {e}") from None
    for n in names:
        check_smoke(n, [a for a in m["arms"] if a["system"] == n])
    tr = full.TestRows()
    smoke.build_systems = lambda kinds, env=None: build(set(names))
    t = smoke.run_selection({"strands"}, select(tr), WORK, set(names), reruns=False, guard=tr.guard,
                            retry_failed=retry_failed, stamp={"freeze": F.record_stamp(ident)})
    for v in t.values():
        v["retry_failed_only"] = retry_failed
    sample.log_timing(t)
    return t


def failed_latest(name: str) -> int:
    p = WORK / f"{name}.jsonl"
    last = {}
    for x in p.open(encoding="utf-8") if p.exists() else []:
        d = json.loads(x)
        if not d["rerun"]:
            last[(d["suite"], d["subtask"], d["row_id"])] = d["outcome"]
    return sum(v == "failed" for v in last.values())


def _spawn(args: list, log: Path, source: str | None) -> subprocess.Popen:
    LOGS.mkdir(parents=True, exist_ok=True)
    fh = log.open("a", encoding="utf-8")
    fh.write(f"\n=== {_now()} {' '.join(args)}\n")
    fh.flush()
    src = ["--source", source] if source else []
    return subprocess.Popen(["uv", "run", "python", str(Path(__file__).resolve()), *args, *src], cwd=REPO,
                            stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)


def _ctl(cmd: str) -> tuple[int, str]:
    LOGS.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["make", cmd], cwd=REPO, capture_output=True, text=True)
    text = p.stdout + p.stderr
    with (LOGS / f"make-{cmd}.log").open("a", encoding="utf-8") as fh:
        fh.write(f"\n=== {_now()} make {cmd} (exit {p.returncode})\n{text}")
    return p.returncode, text


def _vm_times() -> dict:
    """The VM's own start and stop times (Compute API), so a session is billed from when the machine started."""
    from goldrails_bench.endpoints import describe, _gcloud
    d = describe()
    raw = json.loads(_gcloud(["compute", "instances", "describe", d["instance"], "--zone", d["zone"], "--project",
                              d["project"], "--format", "json"]))
    return {"status": raw.get("status"), "machine_type": d["machine_type"], "zone": d["zone"],
            "last_start": _utc(raw.get("lastStartTimestamp")), "last_stop": _utc(raw.get("lastStopTimestamp"))}


def _utc(s: str | None) -> str | None:
    """An RFC 3339 time from the Compute API (local offset) as UTC."""
    from datetime import datetime, timezone
    return s and datetime.fromisoformat(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Term(Exception):
    pass


def vm_pass(pass_no: int, source: str | None) -> dict:
    """make up, smoke any checkpoint of this pass without a smoke ledger, its checkpoints' test runs in parallel,
    retry passes, then make pause in ``finally``. The session is logged from the VM's own start to stop times."""
    names = names_of(pass_no)

    def on_term(*_):
        raise _Term()
    signal.signal(signal.SIGTERM, on_term)
    procs, res, t0 = {}, {"pass": pass_no, "systems": names, "started": _now()}, time.time()
    try:
        code, text = _ctl("up")
        res["make_up"] = code
        if code != 0:
            raise RuntimeError(f"make up failed (exit {code}): {text.strip().splitlines()[-1:]}")
        vt = _vm_times()
        res["vm"] = vt
        want = PASS_HARDWARE[pass_no].split("/")[0]
        if vt["machine_type"] != want:
            raise RuntimeError(f"the VM is {vt['machine_type']}, not {want}")
        if region_of(vt["zone"]) not in REGIONS:
            raise RuntimeError(f"the VM is in {vt['zone']}, outside {sorted(REGIONS)}, whose tariffs the run has")
        res["hardware"], res["disk"] = REGIONS[region_of(vt["zone"])]
        todo = [n for n in names if not smoke_serving(n)]
        if todo:
            run_smoke(todo)
        procs = {n: _spawn(["run", "--only", n], LOGS / f"{n}.log", source) for n in names}
        res["exit"] = {k: p.wait() for k, p in procs.items()}
        procs = {}
        rounds = []
        for i in range(1, RETRY_ROUNDS + 1):
            left = {n: failed_latest(n) for n in names if failed_latest(n)}
            if not left:
                break
            print(f"[pass {pass_no}] retry {i}: {left}", flush=True)
            procs = {n: _spawn(["run", "--only", n, "--retry-failed"], LOGS / f"retry{i}-{n}.log", source)
                     for n in left}
            codes = {k: p.wait() for k, p in procs.items()}
            procs = {}
            rounds.append({"pass": i, "sent": left, "exit": codes, "still_failed": {n: failed_latest(n) for n in left}})
        res["retry_passes"] = rounds
    except (_Term, KeyboardInterrupt) as e:
        res["interrupted"] = type(e).__name__
        raise
    except Exception as e:  # noqa: BLE001  recorded, and the VM is still paused below
        res["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        print(f"[pass {pass_no}] error: {res['error']}", flush=True)
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()
        code, _ = _ctl("pause")
        res["make_pause"] = code
        try:
            vt = _vm_times()
            res["vm_after"] = vt
            res["terminated"] = vt["status"] == "TERMINATED"
            up = (res.get("vm") or {}).get("last_start")
            if up and vt["status"] == "TERMINATED":
                log_event("vm", {"up": up, "paused": vt["last_stop"], "pass": pass_no, "systems": names,
                                 "zone": res["vm"].get("zone"), "hardware": res.get("hardware"),
                                 "disk": res.get("disk"),
                                 # a VM outside REGIONS has no tariff: logged, but not costed
                                 **({} if res.get("hardware") else {"unallocated": True})})
        except Exception as e:  # noqa: BLE001
            res["vm_after_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        res.update(finished=_now(), seconds=round(time.time() - t0, 1))
        log_event("vm_runs", res)
        print(f"[pass {pass_no}] paused (exit {code}); terminated={res.get('terminated')}", flush=True)
    return res


def roster(pass_no: int) -> None:
    """Point terraform.tfvars at this pass's models (from the committed roster example) and apply. The VM must be
    stopped: the new models load on the next start."""
    ex = ROSTER.read_text(encoding="utf-8")
    blocks = re.findall(r"^#?\s*models = \[\n(.*?)^#?\s*\]", ex, re.S | re.M)
    if len(blocks) != len(PASSES):
        raise SystemExit(f"expected {len(PASSES)} models blocks in {full._rel(ROSTER)}, found {len(blocks)}")
    body = "\n".join(re.sub(r"^#\s?", "", x) for x in blocks[pass_no - 1].splitlines())
    tf = TFVARS.read_text(encoding="utf-8")
    want = HARDWARE.split("/")[0]
    if not re.search(rf'^machine_type\s*=\s*"{want}"', tf, re.M) or \
            int((re.search(r"^boot_disk_gb\s*=\s*(\d+)", tf, re.M) or [0, 0])[1]) < 300:
        raise SystemExit(f"{full._rel(TFVARS)} is not set up for this run ({want}, boot_disk_gb >= 300): copy "
                         f"{full._rel(ROSTER)} over it, keeping your own project and access settings")
    tf = re.sub(r"^models = \[\n.*?^\]\n", "models = [\n" + body + "\n]\n", tf, count=1, flags=re.S | re.M)
    TFVARS.write_text(tf, encoding="utf-8")
    vt = _vm_times()
    if vt["status"] != "TERMINATED":
        raise SystemExit(f"the VM is {vt['status']}; run make pause first")
    p = subprocess.run(["terraform", "apply", "-input=false", "-auto-approve", "-no-color"], cwd=TFVARS.parent,
                       capture_output=True, text=True)
    print(p.stdout[-1500:], p.stderr[-1500:])
    if p.returncode:
        raise SystemExit(f"terraform apply failed (exit {p.returncode})")


# --- report, public ledgers, privacy, score ---------------------------------------------------------------------

def write_public(tr) -> list[Path]:
    return full.write_public_ledgers(WORK, OUT, tr)


def committed_files() -> list[Path]:
    return sorted(p for p in OUT.rglob("*") if p.is_file() and WORK not in p.parents and p.name != ".run-log.lock")


def report() -> int:
    tr = full.TestRows()
    recs = sample.load_ledgers(WORK)
    s = sample.run_summary(recs, select(tr))
    for sy, x in s.items():
        print(f"{sy:28s} rows {x['rows']:5d} failed {x['failed']:3d} (first pass {x['first_pass_failed']}) "
              f"not_offered {x['not_offered']:3d} never_logged {x['never_logged']:3d} wall {x['wall_seconds']} "
              f"failure kinds {x['failure_kinds']}")
    write_public(tr)
    pc = full.privacy_check(tr, committed_files() + [MANIFEST])
    print("privacy:", json.dumps(pc))
    return 0 if pc["pass"] else 1


def serving(tr) -> list:
    """VM serving per checkpoint and dataset: each pass's up-to-paused seconds split across its checkpoints by their
    share of the pass's summed run seconds, then over the six suites by each suite's share of the checkpoint's rows."""
    log = json.loads(RUN_LOG.read_text(encoding="utf-8")) if RUN_LOG.exists() else {}
    recs = sample.load_ledgers(WORK)
    with_log = lambda: sample.run_summary(recs, select(tr))  # noqa: E731
    summ = ar._with_log(RUN_LOG, with_log)
    sha = {full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES}
    out = []
    for sess in log.get("vm", []):
        if not (sess.get("up") and sess.get("paused")) or sess.get("unallocated"):
            continue
        secs = sample._ts(sess["paused"]) - sample._ts(sess["up"])
        run = {s: (summ.get(s) or {}).get("wall_seconds") or 0 for s in sess["systems"] if s in summ}
        total = sum(run.values())
        for s, t in run.items():
            if not total:
                continue
            per_suite = Counter()
            for k, v in summ[s]["by_task"].items():
                per_suite[k.split("/")[0]] += v["rows"]
            n_all = sum(per_suite.values())
            for su, n in per_suite.items():
                out.append({"system": s, "hardware": sess.get("hardware", HARDWARE), "share": 1.0,
                            "allocated_seconds": secs * t / total * n / n_all, "evaluations": n,
                            "dataset_sha256": sha[su], "pass": sess.get("pass"),
                            "allocation_note": "pass VM seconds x this checkpoint's share of the pass's run seconds "
                                               "x this suite's share of its rows"})
    return out


def run_date() -> str:
    """The date the first VM pass started (UTC), from the run log."""
    log = json.loads(RUN_LOG.read_text(encoding="utf-8")) if RUN_LOG.exists() else {}
    ups = sorted(s["up"] for s in log.get("vm", []) if s.get("up"))
    if not ups:
        raise SystemExit(f"{full._rel(RUN_LOG)} records no VM pass; run vm-pass before score")
    return ups[0][:10]


def run_disk() -> str:
    """The disk tariff of the region the VM sessions ran in. One VM serves every pass, so one region."""
    log = json.loads(RUN_LOG.read_text(encoding="utf-8")) if RUN_LOG.exists() else {}
    disks = {s.get("disk", DISK) for s in log.get("vm", []) if s.get("up")}
    if len(disks) > 1:
        raise SystemExit(f"VM sessions ran on disks in more than one region ({sorted(disks)}); cost them separately")
    return disks.pop() if disks else DISK


def extra_run() -> dict:
    """This run as one of ``e2_attacks_rerun.score``'s ``extra_runs``."""
    tr = full.TestRows()
    run_entry = {"key": "strands_v2_extension_run", "date": run_date(), "folder": full._rel(OUT), "suites": "all six",
                 "systems": [n for n in SYSTEMS if n not in NOT_RUN], "not_run": NOT_RUN,
                 "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    return {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
            "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files(),
            "serving": serving(tr), "disk": run_disk(), "integrity": full.frozen_integrity(tr)}


def score(replicates: int | None = None) -> Path:
    """The full rescore: every run hosted batch 4's rescore covers, hosted batch 4, then this one."""
    import e2_batch4_run as batch4
    import e2_guards_run as guards_run
    import e2_strands_run as strands
    import e2_pplx13_run as pplx13
    from e2_pplx13_run import batch3, hosted8, liquid, msd1, pplx12
    from e2_batch4_run import gemini
    tr = full.TestRows()
    for m in (strands.luna, strands.jev114, strands, msd1, pplx12, hosted8, liquid, gemini, batch3, pplx13, guards_run,
              batch4):
        m.write_public(tr)
    write_public(tr)
    return ar.score(replicates, extra_runs=[strands.luna.extra_run(), strands.jev114.extra_run(), strands.extra_run(),
                                            msd1.extra_run(), pplx12.extra_run(), hosted8.extra_run(),
                                            liquid.extra_run(), gemini.extra_run(), batch3.extra_run(),
                                            pplx13.extra_run(), guards_run.extra_run(tr), batch4.extra_run(),
                                            extra_run()])


def plan() -> None:
    tr = full.TestRows()
    sel = select(tr)
    n = 0
    for (su, st), rows in sel.items():
        for r in rows:
            tr.guard(r)
        n += len(rows)
        u = sum(r["id"] in tr.unpublished for r in rows)
        toks = [smoke.est_tokens(r, su, st, TEMPLATE) for r in rows]
        over = sum(t >= MAX_LENGTH for t in toks)
        near = sum(t >= smoke.NEAR * MAX_LENGTH for t in toks)
        print(f"{su}/{st}: {len(rows)} rows ({u} unpublished); est tokens max {max(toks, default=0)}, "
              f"near {MAX_LENGTH} {near}, over {over}")
    print(f"total {n} rows per checkpoint, {n * len(SYSTEMS)} calls; guard passed")


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "smoke", "freeze", "run", "vm-pass", "roster", "report", "score"])
    ap.add_argument("--source")
    ap.add_argument("--pass", dest="pass_no", type=int, choices=list(PASSES))
    ap.add_argument("--only", help="comma-separated checkpoint names")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--replicates", type=int, default=None)
    a = ap.parse_args(argv)
    smoke.use_source(a.source)
    WORK.mkdir(parents=True, exist_ok=True)
    if a.stage == "score":
        print(score(a.replicates))
        return 0
    use_paths()
    only = a.only.split(",") if a.only else names_of(a.pass_no)
    if set(only) - set(SYSTEMS):
        raise SystemExit(f"unknown checkpoints {sorted(set(only) - set(SYSTEMS))}")
    if a.stage == "plan":
        plan()
    elif a.stage == "smoke":
        run_smoke(only)
    elif a.stage == "freeze":
        write_freeze(full.TestRows())
    elif a.stage == "run":
        print(run(only, a.retry_failed))
    elif a.stage == "vm-pass":
        if not a.pass_no:
            raise SystemExit("--pass is required")
        res = vm_pass(a.pass_no, a.source)
        return 0 if not res.get("error") else 1
    elif a.stage == "roster":
        if not a.pass_no:
            raise SystemExit("--pass is required")
        roster(a.pass_no)
    else:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
