"""Liquid AI's open d1 models (d1-2B and d1-3B) added to the edition 2 results: all six suites on the rows the other
systems ran.

    uv run python benchmark/runs/e2_liquid_run.py plan --source local          # rows per model, guard
    uv run python benchmark/runs/e2_liquid_run.py smoke --local --source local # 20 dev rows per subtask, laptop servers
    uv run python benchmark/runs/e2_liquid_run.py freeze --source local        # extension manifest; commit it first
    uv run python benchmark/runs/e2_liquid_run.py vm-pass --source local       # up, smoke, run, retry, pause
    uv run python benchmark/runs/e2_liquid_run.py report --source local        # run summary, public ledgers, privacy
    uv run --with scikit-learn python benchmark/runs/e2_liquid_run.py score --source local   # benchmark/results/final/

Liquid AI released d1-3B on 5 October 2026 and d1-2B on 24 October 2026 as open weights on Hugging Face, under the
LFM Open License v1.0. OpenRouter does not serve either (its Decisions endpoint answered "Model liquid/d1-2b does not
exist" on 29 October 2026), so they run on the project VM. Each is pinned to its Hugging Face commit and served by
``infra/gcp/liquid_server.py``: the model card's own call, ``AutoModel.from_pretrained(..., trust_remote_code=True)``
and ``model.system_one(state, questions)``, with the model code that ships in the checkpoint at that commit. The
request is every Noul model's: the same System One state, the same eight question sets and the same fixed 0.5 rule.

The rows are exactly the other systems' rows: the five full-run suites and the r26 prompt-attack suite, test split plus
the unpublished slice, owner exclusions left out. ``e2_full.TestRows.guard`` refuses anything else, before any call and
again before each one. The unpublished slice goes only to the project's own VM.

The freeze is an extension manifest (``goldrails_bench.freeze``) that extends the primary
(``benchmark/subsets/edition2/freeze-manifest.json``) with one arm per model and question set: a Noul model's eight
arms with this model's name and VM endpoint. The config hash is the scorer's (``e2_sample.scorer_record``: adapter,
model, endpoint, question set), so it is known before any call; ``run`` refuses a model whose VM smoke test does not
reproduce it, and refuses to send anything until the manifest is committed. Nothing is fitted.

Hardware. Both models fit together on one 24 GB L4 card in bf16 (d1-2B about 3.8 GB, d1-3B about 6.2 GB), so they
run in one pass on g2-standard-8 (one L4), each in its own server process on the shared card. The full run's VM models
used g2-standard-24 (two L4), but on 29 and 30 October 2026 no US or EU zone had g2-standard-24 capacity, and the owner
chose the one-card machine instead. Self-hosted cost is the pass's VM up-to-paused time split across the two models by
their run seconds, at the g2-standard-8 price of the region the VM lands in.

Raw ledgers (unpublished ids) stay in the git-ignored ``benchmark/results/final/ledgers/liquid-open-d1/private/``;
``report`` and ``score`` write committed ledgers with public test rows only and run the privacy checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
# name: (Hugging Face repo, commit, VM port, GPU, display name)
SYSTEMS = {
    "liquid-d1-2b": ("LiquidAI/d1-2B", "cfe5760ff5d5998f91d9ac56bd4b2dbd96996d41", 8031, 0, "d1-2B"),
    "liquid-d1-3b": ("LiquidAI/d1-3B", "051bcc464b01b9f92942b364d9586b0ef5912432", 8032, 0, "d1-3B"),
}
NAMES = {k: v[4] for k, v in SYSTEMS.items()}
KIND = "liquid"
TEMPLATE = "clef"               # a Noul model's arms; every Noul model has the same eight
RUN_NAME = "liquid-open-d1"
OUT = full.FINAL / "ledgers" / RUN_NAME
WORK = OUT / "private"
SMOKE = WORK / "smoke"          # on the VM, before the run
SMOKE_LOCAL = WORK / "smoke-local"   # on a laptop, a compatibility check only; never used for the freeze or the run
LOGS = OUT / "logs"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / "freeze-manifest-liquid-open-d1.json"
PRIMARY = ar.PRIMARY
R26 = ar.MANIFEST
ROSTER = REPO / "infra" / "gcp" / "terraform.tfvars.liquid-open-d1.example"
MACHINE = "g2-standard-8"
HARDWARE = "g2-standard-8/us-east4/on-demand/third-party"   # the first zone tried
# On 29 and 30 October 2026 no US or EU zone had g2-standard-24 capacity, so the owner chose g2-standard-8 (one L4,
# both models on it) across US and EU zones; the VM's actual region names the tariff (one entry per region in
# goldrails_bench/tariffs.json, added once the VM has landed).
ZONES = ("us-east4-a us-east4-c us-central1-a us-central1-b us-central1-c us-east1-b us-east1-c us-east1-d "
         "us-west1-a us-west1-b us-west4-a europe-west4-a europe-west4-b europe-west4-c europe-west1-b europe-west1-c")
ZONE_PREFIXES = ("us-east4-", "us-central1-", "us-east1-", "us-west1-", "us-west4-", "europe-west4-", "europe-west1-")


def hardware_of(zone: str) -> str:
    return f"{MACHINE}/{zone.rsplit('-', 1)[0]}/on-demand/third-party"
DISK = "pd-balanced/us-central1/third-party"   # the VM landed in us-central1-c on 30 October 2026
LABEL = "Liquid AI open d1 extension run: d1-2B and d1-3B on every edition 2 test row and the unpublished slice"
APPROVAL = "Liquid AI's open d1-2B and d1-3B added on the owner's request of 29 October 2026, on the project VM"
NOUL_ADAPTER = {"name": "noul-e2", "version": "1"}
WORKERS = 4
RETRY_ROUNDS = 2
NOT_RUN: dict = {}
DISCLOSURES = [
    "Liquid AI's open d1-2B and d1-3B ran on 29 October 2026, after the other systems, under their own freeze manifest "
    "committed before their first test call (benchmark/subsets/edition2/freeze-manifest-liquid-open-d1.json). They use "
    "every Noul model's question sets, request and fixed 0.5 rule.",
    "Both are open weights (LFM Open License v1.0). OpenRouter does not serve them, so they ran on the project VM "
    "(g2-standard-8, one NVIDIA L4, us-central1-c, the first zone with capacity), both models on the one card in bf16, each served by "
    "infra/gcp/liquid_server.py with "
    "the model card's call: Transformers with the checkpoint's own model code (trust_remote_code) at the pinned commit, "
    "and model.system_one(state, questions). The unpublished slice went only to that VM.",
    "d1-2B reads up to 128K tokens (the card notes answers get less reliable past about 64K) and d1-3B 32,768; no test "
    "row comes near either, and neither server cuts input.",
]
CAVEATS: list = []


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


def endpoint(name: str) -> str:
    return f"http://localhost:{SYSTEMS[name][2]}"


def _cfg(name: str, qs: str) -> str:
    """The scorer's config hash (``e2_sample.scorer_record``) for this model's arm on ``qs``."""
    return hashlib.sha256(json.dumps({"adapter": NOUL_ADAPTER, "model": name, "endpoint": endpoint(name),
                                      "question_set": qs}, sort_keys=True).encode()).hexdigest()[:16]


# --- systems ---------------------------------------------------------------------------------------------------

def identity(name: str) -> dict:
    ref, rev = SYSTEMS[name][:2]
    return {"ref": ref, "revision": rev, "kind": KIND}


def build(names: set, local: bool = False) -> tuple[dict, dict]:
    """The served models in ``names``, each checked against its pinned repo and commit. ``local``: servers started on
    this machine (``liquid_server.py --ref ... --revision ...``) on the same ports, for a compatibility check."""
    from goldrails_bench.adapters import NoulAdapter
    from goldrails_bench.systemone import SystemOneClient
    out, skipped = {}, {}
    if local:
        import urllib.request
        for n in sorted(names):
            try:
                with urllib.request.urlopen(f"{endpoint(n)}/v1/models", timeout=5) as r:
                    m = json.loads(r.read())["models"][0]
            except Exception as e:  # noqa: BLE001
                skipped[n] = f"no local server on {endpoint(n)} ({type(e).__name__})"
                continue
            if (m.get("ref"), m.get("revision")) != SYSTEMS[n][:2]:
                raise SystemExit(f"{n}: the local server runs {m.get('ref')}@{m.get('revision')}, not {SYSTEMS[n][:2]}")
            c = SystemOneClient(n, base_url=endpoint(n), model=n, identity=identity(n), timeout=600)
            out[n] = (NoulAdapter(c, endpoint=endpoint(n)), WORKERS)
        return out, skipped
    found, why = smoke.liquid_models()
    for m in found:
        if m["name"] not in names:
            continue
        ident = m["identity"]
        if (ident.get("ref"), ident.get("revision")) != SYSTEMS[m["name"]][:2]:
            raise SystemExit(f"{m['name']}: the VM serves {ident}, not {SYSTEMS[m['name']][:2]}")
        c = SystemOneClient(m["name"], base_url=m["url"], model=m["model"], identity=ident, timeout=600)
        out[m["name"]] = (NoulAdapter(c, endpoint=m["url"]), WORKERS)
    for n in sorted(names - set(out)):
        skipped[n] = f"not served on the VM ({why or 'not in the current roster'})"
    return out, skipped


# --- smoke -----------------------------------------------------------------------------------------------------

def run_smoke(names: list[str], local: bool = False) -> dict:
    """20 dev rows per subtask through each served model (``e2_smoke``'s selection), with the determinism reruns.
    A compatibility check: nothing here is scored."""
    where = SMOKE_LOCAL if local else SMOKE
    smoke.build_systems = lambda kinds, env=None: build(set(names), local=local)
    t = smoke.run_selection({KIND}, smoke.select(), where, only=set(names), reruns=True)
    for n in names:
        p = where / f"{n}.jsonl"
        recs = [json.loads(x) for x in p.open(encoding="utf-8")] if p.exists() else []
        c = Counter(d["outcome"] for d in recs if not d["rerun"])
        right = sum(1 for d in recs if not d["rerun"] and d.get("correct"))
        print(f"smoke {n:14s} {dict(c)} correct {right}/{c.get('decided', 0)}", flush=True)
    return t


def smoke_serving(name: str) -> dict:
    """{question set: serving} from this model's VM smoke ledger."""
    p = SMOKE / f"{name}.jsonl"
    srv = {}
    for x in p.open(encoding="utf-8") if p.exists() else []:
        d = json.loads(x)
        if d.get("outcome") == "decided":
            srv.setdefault(d["serving"]["question_set"], d["serving"])
    return srv


def check_smoke(name: str, arms: list) -> None:
    """Refuse a model whose VM smoke test did not answer, or whose serving does not give its frozen config hash."""
    srv = smoke_serving(name)
    for a in arms:
        s = srv.get(a["question_set"])
        if s is None:
            raise SystemExit(f"{name}: no decided VM smoke record for {a['question_set']}; run the smoke stage first")
        got = hashlib.sha256(json.dumps({"adapter": s["adapter"], "model": s["model_id"], "endpoint": s["endpoint"],
                                         "question_set": a["question_set"]}, sort_keys=True).encode()).hexdigest()[:16]
        if got != a["config_hash"]:
            raise SystemExit(f"{name}/{a['question_set']}: smoke serving gives config {got}, frozen {a['config_hash']}")


# --- freeze ----------------------------------------------------------------------------------------------------

def _template_arms() -> list:
    """A Noul model's eight arms: the primary's for the five kept suites and the r26 extension's for prompt attacks."""
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
    doc = {"schema": F.EDITION2_SCHEMA, "arms": [{k: v for k, v in a.items() if not k.startswith("_")} for a in arms]}
    extends = {"manifest_sha256": pident["manifest_sha256"], "manifest_path": pident["path"],
               "reason": "Liquid AI's open d1-2B and d1-3B, released after the full run, on every suite's frozen test "
                         "rows: the five suites of the primary freeze and the r26 prompt-attack suite; no arm of the "
                         "primary, the r26 extension or any other extension changes",
               "after_extension": {"manifest_sha256": xident["manifest_sha256"], "manifest_path": xident["path"],
                                   "note": "the prompt-attack arms use the r26 dataset version that extension froze; "
                                           "the contract is the one it amended to, unchanged since"}}
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
                                 "note": f"the same question set, score scale and fixed rule as every Noul model's "
                                         f"({TEMPLATE}'s shown); config hash from this model's name and VM endpoint "
                                         "(the scorer's formula), checked against its VM smoke test before any test call"}
    m["run"] = {"label": LABEL, "source": sample._source_label(), "approval": APPROVAL, "systems": list(SYSTEMS),
                "checkpoints": {n: {"ref": v[0], "revision": v[1], "server": "infra/gcp/liquid_server.py"}
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
    t = smoke.run_selection({KIND}, select(tr), WORK, set(names), reruns=False, guard=tr.guard,
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
    p = subprocess.run(["make", cmd], cwd=REPO, capture_output=True, text=True,
                       env={**os.environ, "GOLDRAILS_ZONES": ZONES})
    text = p.stdout + p.stderr
    with (LOGS / f"make-{cmd}.log").open("a", encoding="utf-8") as fh:
        fh.write(f"\n=== {_now()} make {cmd} (exit {p.returncode})\n{text}")
    return p.returncode, text


def _vm_times() -> dict:
    """The VM's own start and stop times (Compute API), so a session is billed from when the machine started."""
    from goldrails_bench.endpoints import _gcloud, describe
    d = describe()
    raw = json.loads(_gcloud(["compute", "instances", "describe", d["instance"], "--zone", d["zone"], "--project",
                              d["project"], "--format", "json"]))
    return {"status": raw.get("status"), "machine_type": d["machine_type"], "zone": d["zone"],
            "last_start": _utc(raw.get("lastStartTimestamp")), "last_stop": _utc(raw.get("lastStopTimestamp"))}


def _utc(s: str | None) -> str | None:
    from datetime import datetime, timezone
    return s and datetime.fromisoformat(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _Term(Exception):
    pass


def vm_pass(source: str | None) -> dict:
    """make up, smoke any model without a VM smoke ledger, both models' test runs in parallel, retry passes, then make
    pause in ``finally``. The session is logged from the VM's own start to stop times."""
    names = list(SYSTEMS)

    def on_term(*_):
        raise _Term()
    signal.signal(signal.SIGTERM, on_term)
    procs, res, t0 = {}, {"systems": names, "started": _now()}, time.time()
    try:
        code, text = _ctl("up")
        res["make_up"] = code
        if code != 0:
            raise RuntimeError(f"make up failed (exit {code}): {text.strip().splitlines()[-1:]}")
        vt = _vm_times()
        res["vm"] = vt
        if vt["machine_type"] != MACHINE or not vt["zone"].startswith(ZONE_PREFIXES):
            raise RuntimeError(f"the VM is {vt['machine_type']} in {vt['zone']}, not {MACHINE} in {ZONE_PREFIXES}")
        res["hardware"] = hardware_of(vt["zone"])
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
            print(f"retry {i}: {left}", flush=True)
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
        print(f"error: {res['error']}", flush=True)
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
                log_event("vm", {"up": up, "paused": vt["last_stop"], "systems": names, "zone": vt["zone"],
                                 "hardware": hardware_of(vt["zone"])})
        except Exception as e:  # noqa: BLE001
            res["vm_after_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        res.update(finished=_now(), seconds=round(time.time() - t0, 1))
        log_event("vm_runs", res)
        print(f"paused (exit {code}); terminated={res.get('terminated')}", flush=True)
    return res


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
        print(f"{sy:14s} rows {x['rows']:5d} failed {x['failed']:3d} (first pass {x['first_pass_failed']}) "
              f"not_offered {x['not_offered']:3d} never_logged {x['never_logged']:3d} wall {x['wall_seconds']} "
              f"failure kinds {x['failure_kinds']}")
    write_public(tr)
    pc = full.privacy_check(tr, committed_files() + [MANIFEST])
    print("privacy:", json.dumps(pc))
    return 0 if pc["pass"] else 1


def serving(tr) -> list:
    """VM serving per model and dataset: the pass's up-to-paused seconds split across the two models by their share of
    the pass's summed run seconds, then over the six suites by each suite's share of the model's rows."""
    log = json.loads(RUN_LOG.read_text(encoding="utf-8")) if RUN_LOG.exists() else {}
    recs = sample.load_ledgers(WORK)
    summ = ar._with_log(RUN_LOG, lambda: sample.run_summary(recs, select(tr)))
    sha = {full.FEATURE_SUITE[f]: tr.file_sha[f] for f in full.FEATURES}
    out = []
    for sess in log.get("vm", []):
        if not (sess.get("up") and sess.get("paused")) or sess.get("unallocated"):
            continue
        secs = sample._ts(sess["paused"]) - sample._ts(sess["up"])
        run_s = {s: (summ.get(s) or {}).get("wall_seconds") or 0 for s in sess["systems"] if s in summ}
        total = sum(run_s.values())
        for s, t in run_s.items():
            if not total:
                continue
            per_suite = Counter()
            for k, v in summ[s]["by_task"].items():
                per_suite[k.split("/")[0]] += v["rows"]
            n_all = sum(per_suite.values())
            for su, n in per_suite.items():
                out.append({"system": s, "hardware": sess.get("hardware", HARDWARE), "share": 1.0,
                            "allocated_seconds": secs * t / total * n / n_all, "evaluations": n,
                            "dataset_sha256": sha[su],
                            "allocation_note": "VM seconds x this model's share of the pass's run seconds x this "
                                               "suite's share of its rows"})
    return out


def extra_run() -> dict:
    """This run as one of ``e2_attacks_rerun.score``'s ``extra_runs``."""
    tr = full.TestRows()
    run_entry = {"key": "liquid_open_d1_run", "date": "2026-10-29", "folder": full._rel(OUT), "suites": "all six",
                 "systems": [n for n in SYSTEMS if n not in NOT_RUN], "not_run": NOT_RUN,
                 "manifest": full._rel(MANIFEST), "source": sample._source_label()}
    return {"work": WORK, "log": RUN_LOG, "manifest": MANIFEST, "label": LABEL, "run": run_entry,
            "approval": APPROVAL, "disclosures": DISCLOSURES, "caveats": CAVEATS, "public_files": committed_files(),
            "serving": serving(tr), "disk": DISK, "integrity": full.frozen_integrity(tr)}


def score(replicates: int | None = None) -> Path:
    """The full rescore: the eleven, then gpt-6-luna, Jev 1.14.0, the Strands checkpoints, Microsoft-Decision-1,
    Perplexity Decider v1.2, the eight hosted models and this run."""
    import e2_hosted8_run as hosted8
    import e2_msd1_run as msd1
    import e2_pplx12_run as pplx12
    import e2_strands_run as strands
    tr = full.TestRows()
    strands.luna.write_public(tr)
    strands.jev114.write_public(tr)
    strands.write_public(tr)
    msd1.write_public(tr)
    pplx12.write_public(tr)
    hosted8.write_public(tr)
    write_public(tr)
    return ar.score(replicates, extra_runs=[strands.luna.extra_run(), strands.jev114.extra_run(), strands.extra_run(),
                                            msd1.extra_run(), pplx12.extra_run(), hosted8.extra_run(), extra_run()])


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
    print(f"total {n} rows per model, {n * len(SYSTEMS)} calls; guard passed")


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "smoke", "freeze", "run", "vm-pass", "report", "score"])
    ap.add_argument("--source")
    ap.add_argument("--only", help="comma-separated model names")
    ap.add_argument("--local", action="store_true", help="smoke: servers on this machine, not the VM")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--replicates", type=int, default=None)
    a = ap.parse_args(argv)
    smoke.use_source(a.source)
    WORK.mkdir(parents=True, exist_ok=True)
    if a.stage == "score":
        print(score(a.replicates))
        return 0
    use_paths()
    only = a.only.split(",") if a.only else list(SYSTEMS)
    if set(only) - set(SYSTEMS):
        raise SystemExit(f"unknown models {sorted(set(only) - set(SYSTEMS))}")
    if a.stage == "plan":
        plan()
    elif a.stage == "smoke":
        run_smoke(only, local=a.local)
    elif a.stage == "freeze":
        write_freeze(full.TestRows())
    elif a.stage == "run":
        print(run(only, a.retry_failed))
    elif a.stage == "vm-pass":
        res = vm_pass(a.source)
        return 0 if not res.get("error") else 1
    else:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
