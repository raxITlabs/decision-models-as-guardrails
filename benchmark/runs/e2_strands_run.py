"""Six Strands Decider checkpoints added to the edition 2 results: all six suites on the rows the other systems ran.

    uv run python benchmark/runs/e2_strands_run.py plan --source local          # rows per subtask, guard
    uv run python benchmark/runs/e2_strands_run.py smoke --source local         # 20 dev rows per subtask, served models
    uv run python benchmark/runs/e2_strands_run.py freeze --source local        # extension manifest; commit it first
    uv run python benchmark/runs/e2_strands_run.py vm-pass --pass 1 --source local   # up, run, retry, pause
    uv run python benchmark/runs/e2_strands_run.py roster --pass 2              # swap the VM's models (VM stopped)
    uv run python benchmark/runs/e2_strands_run.py vm-pass --pass 2 --source local
    uv run python benchmark/runs/e2_strands_run.py report --source local        # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_strands_run.py score --source local   # benchmark/results/final/

The systems are the checkpoints StrandsAgents released on Hugging Face after the full run of 5 October 2026, which had
Strands Decider 2B (hobson-v19): hobson-v21 and the first Qwen 3.5 release at 2B, and Gemma 4 releases at E2B, E4B, 12B
and 26B-A4B. Each is pinned to its Hugging Face commit and served on the project VM by the vendor's own package at a
pinned commit of github.com/strands-labs/strands-decider (Gemma 4 support is not in PyPI 0.1.0), through the same
System One request, the same eight question sets and the same fixed 0.5 rule as Strands Decider 2B.

The rows are exactly the other systems' rows: the five full-run suites and the r26 prompt-attack suite, test split plus
the unpublished slice, owner exclusions left out. ``e2_full.TestRows.guard`` refuses anything else, before any call and
again before each one. The unpublished slice goes only to the project's own VM.

The freeze is an extension manifest (``goldrails_bench.freeze``) that extends the primary
(``benchmark/subsets/edition2/freeze-manifest.json``) with one arm per checkpoint and question set: Strands Decider 2B's
eight arms with this checkpoint's model name and endpoint. The config hash is the scorer's
(``e2_sample.scorer_record``: adapter, model, endpoint, question set), so it is known before any call; ``run`` refuses a
checkpoint whose smoke-test serving does not reproduce it, and refuses to send anything until the manifest is
committed. Nothing is fitted.

Hardware. A 24 GB L4 holds the four small checkpoints two to a card; the 12B (about 23 GB in bf16) and the 26B-A4B
(about 51 GB) are split over two and four cards (``infra/gcp/strands_server.py --split-gpus``). The run used
g2-standard-48 (four L4) in two passes because no zone in the US or the EU had A100s on 15 October 2026. Self-hosted
cost is each pass's VM up-to-paused time split across that pass's checkpoints by their run seconds.

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/strands-deciders/private/``;
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
import e2_openai_run as luna  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_smoke as smoke  # noqa: E402

REPO = full.REPO
CODE_SHA = "6039cf8b64c6074e75804000c07ac3d4cce795f7"   # github.com/strands-labs/strands-decider main, 14 October 2026
# name: (Hugging Face repo, commit, VM port, pass, display name)
SYSTEMS = {
    "strands-decider-2b-v21": ("StrandsAgents/strands-decider-2B-hobson-v21", "2b52a6235c1b8306bbfa30b00b9d4b74b63a39f5",
                               8014, 1, "Strands Decider 2B v21"),
    "strands-decider-2b-qwen35": ("StrandsAgents/strands-decider-2B-qwen3.5-v1-2610",
                                  "216d1ccb46a9e9b036eb9187b248db98480f77d4", 8015, 1, "Strands Decider 2B Qwen3.5"),
    "strands-decider-12b": ("StrandsAgents/strands-decider-12B-gemma4-v1-2610", "1202634aec54c890c3e11b8747db62195f116006",
                            8016, 1, "Strands Decider 12B"),
    "strands-decider-e2b": ("StrandsAgents/strands-decider-E2B-gemma4-v1-2610", "d383ecf8534b13d49b3b567a1b66f88fca6d50ba",
                            8017, 1, "Strands Decider E2B"),
    "strands-decider-e4b": ("StrandsAgents/strands-decider-E4B-gemma4-v1-2610", "1344d44397c457f3be34b8ff15c593b41248c6bf",
                            8018, 1, "Strands Decider E4B"),
    "strands-decider-26b-a4b": ("StrandsAgents/strands-decider-26B-A4B-gemma4-v1-2610",
                                "3ca5dfe2d5aa758ae162b6249729181f1d13ed65", 8019, 2, "Strands Decider 26B-A4B"),
}
NAMES = {k: v[4] for k, v in SYSTEMS.items()}
TEMPLATE = "strands-decider-2b"
OUT = full.FINAL / "ledgers" / "strands-deciders"
WORK = OUT / "private"
SMOKE = WORK / "smoke"
LOGS = OUT / "logs"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / "freeze-manifest-strands-deciders.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
TFVARS = REPO / "infra" / "gcp" / "terraform.tfvars"
ROSTER = REPO / "infra" / "gcp" / "terraform.tfvars.strands-deciders.example"
HARDWARE = "g2-standard-48/northamerica-northeast2/on-demand/third-party"
DISK = "pd-balanced/us-east4/third-party"
LABEL = ("Strands Decider extension run: six checkpoints on every edition 2 test row and the unpublished slice, contract "
         "v2.0 as amended")
APPROVAL = ("six Strands Decider checkpoints added on the owner's request of 15 October 2026, on the project VM, spend "
            "approved up to about USD 70")
NOUL_ADAPTER = {"name": "noul-e2", "version": "1"}
WORKERS = 4
RETRY_ROUNDS = 2
DISCLOSURES = [
    "Six Strands Decider checkpoints ran on 15 October 2026, after the other systems, under their own freeze manifest "
    "committed before their first test call (benchmark/subsets/edition2/freeze-manifest-strands-deciders.json). They "
    "use Strands Decider 2B's question sets, request and fixed 0.5 rule; only the checkpoint and the package commit "
    "differ.",
    "The six were served by strands-decider at commit 6039cf8 of its repository (Gemma 4 support is not in the PyPI "
    "release 0.1.0 that served Strands Decider 2B), on four NVIDIA L4 cards. The 12B ran split over two cards and the "
    "26B-A4B over four; the weights and arithmetic are the package's, only where layers sit differs.",
    "Like Strands Decider 2B, the six read at most 4,096 tokens and cut longer input silently, so rows estimated over "
    "the window are counted, not flagged per row.",
    "StrandsAgents trained these checkpoints on public datasets that include Civil Comments, measuring-hate-speech "
    "(calibration and evaluation only), Anthropic hh-rlhf (2B Qwen3.5) and others listed on each model card. A row "
    "taken from one of those datasets may have been seen in training; the unpublished-slice view is the check.",
]
CAVEATS = ["the six Strands Decider extension checkpoints ran on a different machine type (g2-standard-48) from the "
           "full run's VM models (g2-standard-24), so their cost is not an equal-hardware comparison"]


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
        if (ident.get("ref"), ident.get("revision"), ident.get("code_sha")) != (ref, rev, CODE_SHA):
            raise SystemExit(f"{m['name']}: the VM serves {ident}, not {ref}@{rev} with strands-decider {CODE_SHA}")
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
               "reason": "six Strands Decider checkpoints released by StrandsAgents after the full run, on every "
                         "suite's frozen test rows: the five suites of the primary freeze and the r26 prompt-attack "
                         "suite; no arm of the primary, the r26 extension or any other extension changes",
               "after_extension": {"manifest_sha256": xident["manifest_sha256"], "manifest_path": xident["path"],
                                   "note": "the prompt-attack arms use the r26 dataset version that extension froze; "
                                           "the contract is the one it amended to, unchanged since"}}
    t0 = time.time()
    m = F.write_manifest(doc, MANIFEST, retry_policy=DEFAULT_POLICY,
                         test_datasets={full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES},
                         test_files={full.FEATURE_SUITE[f]: tr.files[f] for f in full.FEATURES},
                         references=F.default_references(), edition=2, extends=extends, contract=contract)
    probs = F.validate(m) + F.integrity_problems(m, recompute=False)
    if probs:
        MANIFEST.unlink()
        raise SystemExit("extension manifest invalid: " + "; ".join(probs))
    for out_arm, a in zip(m["arms"], arms):
        out_arm["checked_on"] = {"template_arm": a["_template"],
                                 "note": f"{TEMPLATE}'s question set, score scale and fixed rule; config hash from "
                                         "this checkpoint's model name and VM endpoint (the scorer's formula), checked "
                                         "against its smoke-test serving before any test call"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": list(SYSTEMS),
                "checkpoints": {n: {"ref": v[0], "revision": v[1], "code_sha": CODE_SHA, "pass": v[3]}
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
        if vt["machine_type"] != HARDWARE.split("/")[0]:
            raise RuntimeError(f"the VM is {vt['machine_type']}, not {HARDWARE.split('/')[0]}")
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
                                 "hardware": HARDWARE})
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
    if len(blocks) != 2:
        raise SystemExit(f"expected two models blocks in {full._rel(ROSTER)}, found {len(blocks)}")
    body = "\n".join(re.sub(r"^#\s?", "", x) for x in blocks[pass_no - 1].splitlines())
    tf = TFVARS.read_text(encoding="utf-8")
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
        if not (sess.get("up") and sess.get("paused")):
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


def extra_run() -> dict:
    """This run as one of ``e2_attacks_rerun.score``'s ``extra_runs``."""
    tr = full.TestRows()
    run_entry = {"key": "strands_extension_run", "date": "2026-10-15", "folder": full._rel(OUT), "suites": "all six",
                 "systems": list(SYSTEMS), "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    return {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
            "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files(),
            "serving": serving(tr), "disk": DISK}


def score(replicates: int | None = None) -> Path:
    """The full rescore: the eleven, gpt-6-luna's extension run and this one."""
    tr = full.TestRows()
    luna.write_public(tr)
    write_public(tr)
    return ar.score(replicates, extra_runs=[luna.extra_run(), extra_run()])


def plan() -> None:
    tr = full.TestRows()
    sel = select(tr)
    n = 0
    for (su, st), rows in sel.items():
        for r in rows:
            tr.guard(r)
        n += len(rows)
        u = sum(r["id"] in tr.unpublished for r in rows)
        print(f"{su}/{st}: {len(rows)} rows ({u} unpublished)")
    print(f"total {n} rows per checkpoint, {n * len(SYSTEMS)} calls; guard passed")


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "smoke", "freeze", "run", "vm-pass", "roster", "report", "score"])
    ap.add_argument("--source")
    ap.add_argument("--pass", dest="pass_no", type=int, choices=[1, 2])
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
