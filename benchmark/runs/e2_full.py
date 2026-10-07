"""Edition 2 full run: every test row and the unpublished slice, eleven systems, under the signed contract v2.0.

    uv run python benchmark/runs/e2_full.py plan          # offline: rows per subtask, guard check, cost forecast
    uv run python benchmark/runs/e2_full.py preflight     # credentials, VM state, AWS session (no model call)
    uv run python benchmark/runs/e2_full.py freeze        # writes the freeze manifest; commit it before any call
    uv run python benchmark/runs/e2_full.py all           # forecast, then hosted and VM runs in parallel, retry passes
    uv run python benchmark/runs/e2_full.py run --systems jev,clef [--only <name>] [--retry-failed]
    uv run python benchmark/runs/e2_full.py vm-run        # make up, the six VM models, retry passes, make pause
    uv run python benchmark/runs/e2_full.py hosted-run    # Jev, Clef, Clef-flash, pplx-decider, Bedrock, retry passes
    uv run python benchmark/runs/e2_full.py report        # offline: run summary, public ledgers, privacy checks

The run's records feed the published results in ``benchmark/results/final/`` (``e2_openai_run.py score``), which keep
content, denied topics, word filters, PII and grounding from this run and take prompt attacks from the r26 rerun.

What is sent: every row of the edition 2 test split, ``F*.test.jsonl`` of the edition 2 source
(``goldrails_bench.e2_source``: the Hugging Face copy at the pinned revision, withheld text rebuilt locally), plus
the unpublished slice (``private/F*.test.jsonl``, local only), 8,108 rows, for every adapter subtask of
``e2_smoke.TASKS``, custom words included. Owner exclusions are left out. ``TestRows.guard`` refuses any row that is
not a row of those files (same id, same state) or whose split is not ``test``; it runs over the whole selection
before a system is built and again before each call. The owner approved the run, its spend and sending the
unpublished slice to Perplexity (ruling 21, docs/benchmark/29-owner-rulings-2026-10-03.md).

The freeze comes first. ``freeze`` writes ``benchmark/subsets/edition2/freeze-manifest.json`` with
``goldrails_bench.freeze.write_manifest``: one arm per (system, question set, config) as the dev-split sample ran it,
the fixed 0.5 rule or the frozen documented Bedrock setting per arm, and the strict overlap check of every test and
unpublished row against the examined, smoke, pilot and dev rows and the v1 release builds. ``run`` refuses to send
anything until that manifest is committed, and stamps its sha256 and the adapter's retry policy on every record, so
``leaderboard_v2`` can show the freeze predates every attempt.

Privacy (the repository is public). The raw ledgers hold unpublished-slice ids and live in the git-ignored
``benchmark/results/final/ledgers/main-run/private/``. ``report`` writes the committed ledgers
``benchmark/results/final/ledgers/main-run/<system>.jsonl`` with public test rows only (prompt-attack records left out), and check that no committed file
holds an unpublished id or any row text (``e2_sample.fast_leak_check`` and ``e2_local.tracked_leaks``). No ledger
ever holds row text: ``e2_smoke.record`` keeps ids, labels and outputs, and error strings are scrubbed.
"""
from __future__ import annotations

import argparse
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
import e2_smoke as smoke  # noqa: E402
import e2_sample as sample  # noqa: E402

REPO = smoke.REPO
FINAL = REPO / "benchmark" / "results" / "final"     # the published results and the ledgers behind them
OUT = FINAL / "ledgers" / "main-run"
WORK = OUT / "private"            # git-ignored: raw ledgers with unpublished-slice ids
LOGS = OUT / "logs"
RUN_LOG = OUT / "run-log.json"
MANIFEST = REPO / "benchmark" / "subsets" / "edition2" / "freeze-manifest.json"
DEV_SAMPLE = REPO / "benchmark" / "results" / "edition2-dev-sample"
FEATURES = sample.FEATURES
FEATURE_SUITE = {"F1": "content", "F2": "prompt_attacks", "F3": "denied_topics", "F4": "word_filters",
                 "F5": "sensitive_info", "F6": "grounding"}
LABEL = "edition 2 full run: test split and unpublished slice, contract v2.0"
# Suites whose records the committed ledgers leave out: this run's prompt attacks were replaced by the r26 rerun
# (e2_attacks_rerun.py), which scores them; the raw ledgers in private/ keep every record.
PUBLIC_EXCLUDE = {"prompt_attacks"}
HOSTED_KINDS = ("jev", "clef", "clef-flash", "perplexity", "bedrock")
HOSTED_NAMES = {"jev": "jev-1.13.0", "clef": "clef", "clef-flash": "clef-flash", "perplexity": "pplx-decider-v1-27b",
                "bedrock": "bedrock-guardrails"}
VM_SYSTEMS = sample.VM_SYSTEMS
SYSTEMS = tuple(HOSTED_NAMES.values()) + VM_SYSTEMS
COST_CAP_USD = 30.0
RETRY_ROUNDS = 2

# e2_sample's run-log, VM-session, summary and cost helpers read these module globals.
sample.OUT, sample.RUN_LOG = OUT, RUN_LOG


# --- what may be sent ------------------------------------------------------------------------------------------

def _rel(p: Path) -> str:
    p = Path(p).resolve()
    return p.relative_to(REPO).as_posix() if p.is_relative_to(REPO) else str(p)


# Owner ruling 32 (7 October 2026) corrected or removed labels after the runs, on rows at least 11 of the 12 systems
# got wrong. The runs answered the build as it was; this git-ignored copy of that build's test files is the dataset
# version the freeze manifests record (its paths mirror the repository's, so a manifest's integrity block is
# recomputed from it). ``TestRows`` scores the current build's labels under that frozen version: see
# ``label_amendment``.
FROZEN = REPO / "dataset" / "edition2" / ".frozen" / "before-ruling32"
FROZEN_BUILD = FROZEN / "dataset" / "edition2" / "build"
AMENDMENT_RULING = 32


class TestRows:
    """The edition 2 test rows (public test files plus the unpublished slice) and the guard that refuses the rest.
    Duck-types ``e2_sample.PublicDev`` (rows, feature, file_sha) so its scorer record can be reused; ``file_sha`` is
    each suite's dataset version: ``dataset_hash`` over its public and unpublished test rows together, the hash the
    freeze manifest records.

    After a label amendment (owner ruling 32) ``rows`` are the current build's rows, with the corrected labels and
    without the removed rows, while ``file_sha`` stays the frozen version the systems answered (``FROZEN``);
    ``amended_sha`` is the current build's hash, ``removed`` the ids taken out and ``relabelled`` {id: (old, new)}.
    The amendment is refused unless every difference between the two versions is a ruling 32 correction or exclusion."""

    def __init__(self):
        from goldrails_dataset.records import dataset_hash, read_jsonl
        d = smoke.data_dir()
        self.dir = d
        self.rows, self.feature, self.file_sha, self.files, self.unpublished = {}, {}, {}, {}, set()
        self.removed, self.removed_unpublished, self.removed_rows, self.relabelled = set(), set(), {}, {}
        self.amended_sha, self.amendment = {}, None
        for f in FEATURES:
            files = [d / f"{f}.test.jsonl", d / "private" / f"{f}.test.jsonl"]
            self.files[f] = files
            self.file_sha[f] = dataset_hash([r for p in files for r in read_jsonl(p)])
            for p in files:
                for x in p.open(encoding="utf-8"):
                    r = json.loads(x)
                    if r["id"] in self.rows:
                        raise SystemExit(f"duplicate test row id across files of {f}")
                    self.rows[r["id"]] = r
                    self.feature[r["id"]] = f
                    if p.parent.name == "private":
                        self.unpublished.add(r["id"])
        self.hashes = {i: sample._state_hash(r) for i, r in self.rows.items()}
        priv = smoke.private_ids()
        if self.unpublished - priv:
            raise SystemExit("an unpublished test row is missing from the local private slice")
        if (set(self.rows) - self.unpublished) & priv:
            raise SystemExit("a public test id is in the private slice")
        dev = {json.loads(x)["id"] for f in FEATURES for x in (d / f"{f}.dev.jsonl").open(encoding="utf-8")}
        if dev & set(self.rows):
            raise SystemExit("a dev id is also a test id")
        if d.resolve() == smoke.BUILD.resolve() and FROZEN_BUILD.is_dir():
            self.amendment = label_amendment(self, FROZEN_BUILD)

    def guard(self, r: dict) -> None:
        rid = r.get("id")
        if rid not in self.rows:
            raise PermissionError(f"refused: {rid!r} is not a row of the edition 2 test files")
        if r.get("split") != "test":
            raise PermissionError(f"refused: {rid} has split {r.get('split')!r}")
        if sample._state_hash(r) != self.hashes[rid]:
            raise PermissionError(f"refused: {rid} differs from the frozen test file's row")

    def public_ids(self) -> set:
        return set(self.rows) - self.unpublished


def _same_but_label(a: dict, b: dict) -> bool:
    """True when two rows differ only in what a ruling 32 correction changes: the label (``expected``, ``labels``,
    ``expected_distribution``), its category, ``label_basis`` and the row's ``attribute.e2`` annotations."""
    def strip(r):
        r = json.loads(json.dumps(r))
        for k in ("expected", "labels", "expected_distribution", "category", "attribute"):
            r.pop(k, None)
        r.get("provenance", {}).pop("label_basis", None)
        return r
    return strip(a) == strip(b)


def label_amendment(tr: TestRows, frozen: Path) -> dict | None:
    """Score the current build's labels under the frozen dataset version (owner ruling 32). Reads the frozen test
    files, keeps ``tr.file_sha`` at their hashes (the version the freeze manifests record and the systems answered)
    and records what changed. Refuses (SystemExit) unless the current rows are the frozen rows less the ruling 32
    exclusions, with only ruling 32 corrections changing a label. None when the two versions are the same."""
    from goldrails_dataset import edition2
    from goldrails_dataset.records import dataset_hash, read_jsonl
    old, old_feat, old_private, old_sha = {}, {}, set(), {}
    for f in FEATURES:
        files = [frozen / f"{f}.test.jsonl", frozen / "private" / f"{f}.test.jsonl"]
        recs = [r for p in files for r in read_jsonl(p)]
        old_sha[f] = dataset_hash(recs)
        for p in files:
            for x in p.open(encoding="utf-8"):
                r = json.loads(x)
                old[r["id"]], old_feat[r["id"]] = r, f
                if p.parent.name == "private":
                    old_private.add(r["id"])
    if old_sha == tr.file_sha:
        return None
    new_ids = set(tr.rows) - set(old)
    if new_ids:
        raise SystemExit(f"label amendment: {len(new_ids)} test rows are not in the frozen version {_rel(frozen)}")
    reason = edition2.RULING32["exclusion_reason"]
    excl = edition2.excluded()
    removed = set(old) - set(tr.rows)
    bad = sorted(i for i in removed if excl.get(i) != reason)
    if bad:
        raise SystemExit(f"label amendment: {len(bad)} frozen test rows left the build without a ruling 32 exclusion")
    relabelled, problems = {}, []
    for i, r in tr.rows.items():
        o = old[i]
        if o == r:
            continue
        corr = ((r.get("attribute") or {}).get("e2") or {}).get("correction") or {}
        if corr.get("ruling") != AMENDMENT_RULING or not _same_but_label(o, r) or o["expected"] == r["expected"] \
                or (i in old_private) != (i in tr.unpublished) or old_feat[i] != tr.feature[i]:
            problems.append(i)
            continue
        relabelled[i] = (o["expected"], r["expected"])
    if problems:
        raise SystemExit(f"label amendment: {len(problems)} test rows changed other than by a ruling 32 correction")
    tr.amended_sha = dict(tr.file_sha)
    tr.file_sha = old_sha
    tr.removed, tr.removed_unpublished = removed, removed & old_private
    tr.removed_rows = {i: old[i] for i in removed}
    tr.relabelled = relabelled
    by = Counter()
    for i in removed:
        by[f"{FEATURE_SUITE[old_feat[i]]}|{'unpublished' if i in old_private else 'public'}|removed"] += 1
    for i, (a, b) in relabelled.items():
        by[f"{FEATURE_SUITE[tr.feature[i]]}|{'unpublished' if i in tr.unpublished else 'public'}|{a}->{b}"] += 1
    return {"ruling": AMENDMENT_RULING, "frozen_copy": _rel(frozen),
            "frozen_sha256": {FEATURE_SUITE[f]: old_sha[f] for f in FEATURES},
            "amended_sha256": {FEATURE_SUITE[f]: tr.amended_sha[f] for f in FEATURES},
            "relabelled": len(relabelled), "removed": len(removed), "by_suite_split": dict(sorted(by.items()))}


def frozen_integrity(tr: TestRows) -> dict | None:
    """The ``integrity`` arguments that recompute a freeze manifest naming ``dataset/edition2/build`` files from the
    frozen copy after a label amendment (None without one): the copy mirrors the repository's paths, and the
    references are this repository's with the frozen dev rows."""
    if not tr.amendment:
        return None
    from goldrails_bench import freeze as F
    return {"repo": FROZEN, "references": F.default_references(dev_files=sorted(FROZEN_BUILD.glob("F*.dev.jsonl")))}


def amend_ledgers(recs: list, tr: TestRows) -> list:
    """Ledger records under the label amendment: records of removed rows left out, and on a relabelled row the
    ``expected`` label and ``correct`` flag recomputed from the system's own decision (the files are not touched)."""
    if not tr.amendment:
        return recs
    out = []
    for d in recs:
        rid = d.get("row_id")
        if rid in tr.removed:
            continue
        if rid in tr.relabelled:
            new = tr.relabelled[rid][1]
            d = {**d, "expected": new, "correct": None if d.get("decision") is None else d["decision"] == (new == "yes")}
        out.append(d)
    return out


def select_all(tr: TestRows) -> dict:
    """{(suite, subtask): [every test row with one of the subtask's tags]}, owner exclusions left out."""
    excl = smoke.excluded_ids()
    out = {}
    for (suite, sub), (feat, tags) in smoke.TASKS.items():
        rows = [r for i, r in tr.rows.items() if tr.feature[i] == feat and r["subtask"] in tags and i not in excl]
        out[(suite, sub)] = sorted(rows, key=lambda r: r["id"])
    return out


# --- cost forecast ---------------------------------------------------------------------------------------------

def forecast(n_rows: int) -> dict:
    """USD and wall time forecast from the dev-split sample's measurements (its leaderboard.json and run-log.json),
    scaled by rows. VM: the slowest VM model's main-pass seconds per row, plus boot and pause overhead, at the dated
    machine and disk rate. A high estimate allows 50% more tokens per row and 50% more VM time."""
    if not (DEV_SAMPLE / "leaderboard.json").exists():
        return recorded_forecast()
    lbd = json.loads((DEV_SAMPLE / "leaderboard.json").read_text(encoding="utf-8"))
    log = json.loads((DEV_SAMPLE / "run-log.json").read_text(encoding="utf-8"))
    dev_rows = lbd["sample"]["rows_total"]
    scale = n_rows / dev_rows
    from goldrails_bench import leaderboard as lb
    rate = next((e.get("usd_per_hour") for e in lb.load_tariffs()["entries"]
                 if sample.VM_HARDWARE in (e.get("match") or {}).get("hardware", [])), None) or 0.0
    hosted = {s: (lbd["run"]["cost"][s]["usd_total"] or 0) * scale for s in HOSTED_NAMES.values()}
    main_pass = max(r["seconds"] for s in VM_SYSTEMS for r in log["systems"][s] if not r.get("retry_failed_only"))
    overhead = 10 * 60      # make up (about 4 min from a stopped VM) and make pause, plus a retry pass
    vm_s = main_pass * scale + overhead
    vm_usd = vm_s / 3600 * (rate + sample.VM_DISK_USD_PER_HOUR)
    hosted_wall = max(r["seconds"] for s in HOSTED_NAMES.values() for r in log["systems"].get(s, []) if r["sent"]) * scale
    total = sum(hosted.values()) + vm_usd
    return {"rows_per_system": n_rows, "dev_rows": dev_rows, "scale": round(scale, 3),
            "hosted_usd": {k: round(v, 3) for k, v in hosted.items()}, "hosted_usd_total": round(sum(hosted.values()), 2),
            "vm_seconds": round(vm_s), "vm_usd": round(vm_usd, 2), "vm_rate_usd_per_hour": rate,
            "total_usd": round(total, 2), "high_usd": round(1.5 * total, 2),
            "wall_hours": round(max(vm_s, hosted_wall) / 3600, 2), "cap_usd": COST_CAP_USD,
            "basis": "dev-split sample (benchmark/results/edition2-dev-sample): measured hosted cost and VM main-pass "
                     "seconds, scaled by rows; high = 1.5 x"}


def recorded_forecast() -> dict:
    """The forecast this run's log recorded before its first call. The measurements it was made from (the dev-split
    sample, or an earlier run's results) are not kept in the repository, so a rerun repeats the recorded forecast."""
    rec = (sample._log().get("forecasts") or [None])[-1]
    if rec is None:
        raise SystemExit(f"no forecast in {_rel(sample.RUN_LOG)}, and its measurements are not on this machine")
    return {**{k: v for k, v in rec.items() if k != "at"},
            "basis": f"{rec.get('basis')}; recorded in {_rel(sample.RUN_LOG)} before the run"}


# --- run log ---------------------------------------------------------------------------------------------------

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_event(key: str, value) -> None:
    def go():
        d = sample._log()
        d.setdefault(key, []).append(value)
        sample._save_log(d)
    sample._locked(go)


# --- preflight -------------------------------------------------------------------------------------------------

def preflight() -> dict:
    """What can run: credentials present (never printed), the AWS session, the VM state. No model call."""
    env = os.environ
    out = {"typesafe": bool(env.get("TYPESAFE_API_KEY")),
           "cloudflare": bool(env.get("CLOUDFLARE_ACCOUNT_ID") and (env.get("CLOUDFLARE_API_TOKEN") or env.get("CLOUDFLARE_AUTH_TOKEN"))),
           "perplexity": bool(env.get("PERPLEXITY_API_KEY")),
           "aws_profile_set": bool(env.get("AWS_PROFILE")),
           "aws_blocked": smoke.bedrock_blocked(),
           "bedrock_config": bool(smoke.bedrock_config())}
    st = subprocess.run(["infra/ctl.sh", "status"], cwd=REPO, capture_output=True, text=True)
    out["vm_status"] = (st.stdout.strip().splitlines() or ["unknown"])[0]
    return out


def bedrock_ok(pf: dict) -> bool:
    return pf["aws_blocked"] is None and pf["bedrock_config"]


# --- freeze ----------------------------------------------------------------------------------------------------

def dev_arms_doc(replicates: int = 20) -> dict:
    """A leaderboard_v2 result over the dev-split sample ledgers, recomputed with the current code: the arms (system,
    question set, config hash, decision rule) the freeze lists. Arms do not depend on the replicate count."""
    pt = sample.PublicDev()
    recs = sample.latest(sample.load_ledgers(DEV_SAMPLE))
    records = [x for d in recs if (x := sample.scorer_record(d, pt))]
    return sample.evaluate(records, replicates=replicates)


def write_freeze(tr: TestRows) -> dict:
    from goldrails_bench import freeze as F
    from goldrails_bench.policy import DEFAULT_POLICY
    if MANIFEST.exists():
        raise SystemExit(f"{_rel(MANIFEST)} exists; a freeze is written once (a correction is a separate manifest)")
    doc = dev_arms_doc()
    arms = [a for a in doc["arms"] if a["system"] in SYSTEMS]
    missing = sorted(set(SYSTEMS) - {a["system"] for a in arms})
    if missing:
        raise SystemExit(f"the dev-split sample has no arms for {missing}")
    test_datasets = {FEATURE_SUITE[f]: tr.file_sha[f] for f in FEATURES}
    test_files = {FEATURE_SUITE[f]: tr.files[f] for f in FEATURES}
    t0 = time.time()
    m = F.write_manifest(doc, MANIFEST, retry_policy=DEFAULT_POLICY, test_datasets=test_datasets,
                         arms=[a["arm_id"] for a in arms], test_files=test_files,
                         references=F.default_references(), edition=2)
    probs = F.validate(m) + F.integrity_problems(m, recompute=False)
    if probs:
        MANIFEST.unlink()
        raise SystemExit("freeze manifest invalid: " + "; ".join(probs))
    m["run"] = {"label": LABEL, "source": sample._source_label(),
                "arms_from": "benchmark/results/edition2-dev-sample ledgers (the configurations the dev-split sample "
                             "ran), recomputed by leaderboard_v2; nothing fitted",
                "approval": "owner ruling 21 (docs/benchmark/29-owner-rulings-2026-10-03.md)",
                "systems": sorted(SYSTEMS)}
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"freeze manifest: {len(m['arms'])} arms, integrity pass over {m['integrity']['test_rows']} test rows "
          f"({time.time() - t0:.0f}s) -> {_rel(MANIFEST)}; commit it before any call")
    return m


def committed_freeze() -> tuple[dict, dict]:
    """(manifest, identity) of the committed manifest, or SystemExit: no call is made before the freeze."""
    from goldrails_bench import freeze as F
    try:
        return F.load_committed(MANIFEST)
    except F.FreezeError as e:
        raise SystemExit(f"refusing to run: {e}") from None


# --- run -------------------------------------------------------------------------------------------------------

def run(kinds: set, only: set | None, retry_failed: bool) -> dict:
    from goldrails_bench import freeze as F
    _, ident = committed_freeze()
    tr = TestRows()
    t = smoke.run_selection(kinds, select_all(tr), WORK, only, reruns=False, guard=tr.guard,
                            retry_failed=retry_failed, stamp={"freeze": F.record_stamp(ident)})
    for v in t.values():
        v["retry_failed_only"] = retry_failed
    sample.log_timing(t)
    return t


def _failed_latest(system: str) -> int:
    p = WORK / f"{system}.jsonl"
    if not p.exists():
        return 0
    last = {}
    for x in p.open(encoding="utf-8"):
        d = json.loads(x)
        if not d["rerun"]:
            last[(d["suite"], d["subtask"], d["row_id"])] = d["outcome"]
    return sum(v == "failed" for v in last.values())


def _spawn(args: list, log: Path) -> subprocess.Popen:
    LOGS.mkdir(parents=True, exist_ok=True)
    fh = log.open("a", encoding="utf-8")
    fh.write(f"\n=== {_now()} {' '.join(args)}\n")
    fh.flush()
    return subprocess.Popen(["uv", "run", "python", str(Path(__file__).resolve()), *args], cwd=REPO,
                            stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)


def _wait(procs: dict) -> dict:
    return {k: p.wait() for k, p in procs.items()}


def _retry_passes(spawn_args, names: list, tag: str) -> list:
    """Up to RETRY_ROUNDS passes that resend only rows whose latest record failed (transient failures)."""
    rounds = []
    for i in range(1, RETRY_ROUNDS + 1):
        todo = {n: _failed_latest(n) for n in names}
        todo = {n: k for n, k in todo.items() if k}
        if not todo:
            break
        print(f"[{tag}] retry pass {i}: {todo}", flush=True)
        procs = {n: _spawn([*spawn_args(n), "--retry-failed"], LOGS / f"retry{i}-{n}.log") for n in todo}
        codes = _wait(procs)
        rounds.append({"pass": i, "sent": todo, "exit": codes, "still_failed": {n: _failed_latest(n) for n in todo}})
    return rounds


def hosted_run(pf: dict | None = None) -> dict:
    pf = pf or preflight()
    kinds = [k for k in HOSTED_KINDS if k != "bedrock" or bedrock_ok(pf)]
    if "bedrock" not in kinds:
        reason = pf["aws_blocked"] or "no Bedrock guardrail config (infra/aws Terraform outputs)"
        (OUT / "bedrock-guardrails.blocked.json").write_text(json.dumps(
            {"system": "bedrock-guardrails", "reason": reason, "at": _now(),
             "follow_up": "the owner runs `aws sso login`, then: uv run python benchmark/runs/e2_full.py run --systems bedrock"},
            indent=1) + "\n", encoding="utf-8")
        print(f"[hosted] Bedrock skipped: {reason}", flush=True)
    t0 = time.time()
    procs = {k: _spawn(["run", "--systems", k], LOGS / f"{k}.log") for k in kinds}
    codes = _wait(procs)
    rounds = _retry_passes(lambda n: ["run", "--systems", next(k for k, v in HOSTED_NAMES.items() if v == n)],
                           [HOSTED_NAMES[k] for k in kinds], "hosted")
    res = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "finished": _now(),
           "seconds": round(time.time() - t0, 1), "kinds": kinds, "exit": codes, "retry_passes": rounds}
    log_event("hosted_runs", res)
    print(f"[hosted] done in {res['seconds']:.0f}s, exit codes {codes}", flush=True)
    return res


def _ctl(cmd: str, log: Path) -> tuple[int, str]:
    LOGS.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["make", cmd], cwd=REPO, capture_output=True, text=True)
    text = p.stdout + p.stderr
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n=== {_now()} make {cmd} (exit {p.returncode})\n{text}")
    return p.returncode, text


class _Term(Exception):
    pass


def vm_run(systems: list | None = None, sequential: bool = False, retry_only: bool = False) -> dict:
    """make up, the six VM models at once (placement from terraform.tfvars: Kev-0.8B, Kev-4B, Open-Jev-2B and Strands
    on GPU 0, Kev-9B and Laya on GPU 1, as in the dev-split sample), retry passes, then make pause in ``finally``
    and a status check that the VM is TERMINATED. ``sequential`` runs one model at a time (less load on a GPU) and
    ``retry_only`` skips the main pass and resends only failed rows."""
    names = list(systems or VM_SYSTEMS)
    def on_term(*_):
        raise _Term()
    signal.signal(signal.SIGTERM, on_term)
    procs, res, t0 = {}, {"started": _now()}, time.time()
    try:
        sample.vm_mark("up")
        code, text = _ctl("up", LOGS / "make-up.log")
        res["make_up"] = code
        if code != 0:
            raise RuntimeError(f"make up failed (exit {code}): {text.strip().splitlines()[-1:]}")
        res.update(systems=names, sequential=sequential, retry_only=retry_only)
        if not retry_only:
            procs = {n: _spawn(["run", "--systems", "open,strands", "--only", n], LOGS / f"{n}.log") for n in names}
            res["exit"] = _wait(procs)
            procs = {}
        if sequential:
            res["retry_passes"] = [r for n in names for r in _retry_passes(
                lambda m: ["run", "--systems", "open,strands", "--only", m], [n], "vm")]
        else:
            res["retry_passes"] = _retry_passes(lambda n: ["run", "--systems", "open,strands", "--only", n],
                                                names, "vm")
    except (_Term, KeyboardInterrupt) as e:
        res["interrupted"] = type(e).__name__
        raise
    except Exception as e:  # noqa: BLE001  recorded, and the VM is still paused below
        res["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        print(f"[vm] error: {res['error']}", flush=True)
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()
        code, _ = _ctl("pause", LOGS / "make-pause.log")
        try:
            sample.vm_mark("paused")
        except SystemExit:
            pass
        _, status = _ctl("status", LOGS / "make-status.log")
        res.update(make_pause=code, status=[x for x in status.splitlines() if x.startswith("vm:")][-1:] or None,
                   terminated="vm: TERMINATED" in status, finished=_now(), seconds=round(time.time() - t0, 1))
        log_event("vm_runs", res)
        print(f"[vm] paused (exit {code}); {res['status']}; terminated={res['terminated']}", flush=True)
    return res


def run_all() -> int:
    pf = preflight()
    print("preflight:", json.dumps({k: (v if k != "aws_blocked" else (v or "ok")) for k, v in pf.items()}), flush=True)
    tr = TestRows()
    sel = select_all(tr)
    n = sum(len(v) for v in sel.values())
    fc = forecast(n)
    print("forecast:", json.dumps(fc), flush=True)
    log_event("forecasts", {"at": _now(), **fc})
    if fc["high_usd"] > COST_CAP_USD:
        print(f"forecast high {fc['high_usd']} USD is above the {COST_CAP_USD} USD cap: stopping before any call")
        return 2
    m, _ = committed_freeze()
    from goldrails_bench import freeze as F
    probs = F.integrity_problems(m)
    if probs:
        print("freeze manifest cannot back a test run: " + "; ".join(probs))
        return 2
    if not pf["typesafe"] or not pf["cloudflare"] or not pf["perplexity"]:
        print("warning: a hosted credential is missing; that system is reported not_configured", flush=True)
    t0 = time.time()
    hosted = _spawn(["hosted-run"], LOGS / "hosted-run.log")
    vm = vm_run()
    hosted.wait()
    log_event("all_runs", {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "finished": _now(),
                           "seconds": round(time.time() - t0, 1), "vm_terminated": vm.get("terminated")})
    print(f"all done in {(time.time() - t0) / 60:.1f} min; VM terminated: {vm.get('terminated')}", flush=True)
    return 0


# --- report: public ledgers and privacy checks -----------------------------------------------------------------

def load_work() -> list:
    return sample.load_ledgers(WORK)


def write_public_ledgers(work: Path, out_dir: Path, tr: TestRows, exclude_suites=()) -> list[Path]:
    """Committed ledgers from the raw ones in ``work``: every record of a public test row, nothing of the unpublished
    slice, records of ``exclude_suites`` left out. Under a label amendment (owner ruling 32) a removed row's records
    are left out and a relabelled row's record carries the corrected ``expected`` and ``correct``."""
    pub = tr.public_ids()
    out = []
    for p in sorted(Path(work).glob("*.jsonl")):
        keep = []
        for x in p.open(encoding="utf-8"):
            if not x.strip():
                continue
            d = json.loads(x)
            if d["row_id"] not in pub or d["suite"] in exclude_suites:
                continue
            if d["row_id"] in tr.relabelled:
                x = json.dumps(amend_ledgers([d], tr)[0], ensure_ascii=False) + "\n"
            keep.append(x)
        q = Path(out_dir) / p.name
        q.write_text("".join(keep), encoding="utf-8")
        out.append(q)
    return out


def write_public(tr: TestRows) -> list[Path]:
    """Committed ledgers: every record of a public test row, nothing of the unpublished slice."""
    out = write_public_ledgers(WORK, OUT, tr, PUBLIC_EXCLUDE)
    for p in sorted(WORK.glob("*.blocked.json")):
        (OUT / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    return out


def committed_files() -> list[Path]:
    """Every file under the results folder that may be committed (the git-ignored private/ folder excluded)."""
    return sorted(p for p in OUT.rglob("*") if p.is_file() and WORK not in p.parents and p.name != ".run-log.lock")


def privacy_check(tr: TestRows, files=None) -> dict:
    """No unpublished id and no row text in any committed file; ``e2_local.tracked_leaks`` over the same files."""
    files = committed_files() if files is None else [Path(f) for f in files]
    unp = tr.unpublished | tr.removed_unpublished
    id_hits = {}
    for p in files:
        if p.suffix == ".png":
            continue
        s = p.read_text(encoding="utf-8", errors="replace")
        n = sum(1 for i in unp if i in s)
        if n:
            id_hits[_rel(p)] = n
    text_files = [p for p in files if p.suffix in (".jsonl", ".json", ".md", ".log")]
    import re
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # An SVG is scanned on its visible text only: its XML header (namespace URLs) matches a row that quotes the same
        # boilerplate, which is not row text leaking into the plot.
        for i, p in enumerate(f for f in files if f.suffix == ".svg"):
            q = Path(tmp) / f"{i}.txt"
            q.write_text(" ".join(re.findall(r"<text[^>]*>(.*?)</text>", p.read_text(encoding="utf-8"), re.S)),
                         encoding="utf-8")
            text_files.append(q)
        leaks = sample.fast_leak_check(text_files, {**tr.removed_rows, **tr.rows})
    from goldrails_dataset import e2_local
    tl = e2_local.tracked_leaks(files=[_rel(p) for p in files if p.suffix != ".png"])
    return {"files": len(files), "unpublished_ids_found": id_hits, "rows_with_text_in_files": len(leaks),
            "tracked_leaks": len(tl["leaks"]), "tracked_leak_kinds": dict(Counter(x["kind"] for x in tl["leaks"])),
            "pass": not id_hits and not leaks and not tl["leaks"]}


def report() -> int:
    tr = TestRows()
    sel = select_all(tr)
    s = sample.run_summary(load_work(), sel)
    for sy, x in s.items():
        print(f"{sy:20s} rows {x['rows']:5d} failed {x['failed']:3d} (first pass {x['first_pass_failed']}) "
              f"not_offered {x['not_offered']:3d} never_logged {x['never_logged']:3d} truncated {x['truncated']:4d} "
              f"p95 {x['latency_p95_s']} wall {x['wall_seconds']}")
    write_public(tr)
    pc = privacy_check(tr)
    print("privacy:", json.dumps(pc))
    return 0 if pc["pass"] else 1


# --- score -----------------------------------------------------------------------------------------------------

def scorer_record(d: dict, tr: TestRows) -> dict | None:
    """``e2_sample.scorer_record`` (same config hash, so the arms match the freeze) on the test split, with the
    freeze stamp, the retry policy and the attempt times the frozen-mode scorer checks. A row the service refused
    as over its limits (``not_offered`` on one row, e.g. Bedrock's 1,000-character grounding query cap) is scored as
    a failure, wrong in its class, as the contract's frozen row list would score it unlogged."""
    if d["row_id"] in tr.removed:          # taken out by the label amendment (owner ruling 32)
        return None
    if d["outcome"] == "not_offered":
        d = {**d, "outcome": "failed", "error": f"not offered for this row: {d.get('error') or ''}"[:300]}
    x = sample.scorer_record(d, tr)
    if x is None:
        return None
    x["split"] = "test"
    x["dataset"] = {**x["dataset"], "split": "test"}
    x["freeze"] = d.get("freeze")
    x["retry_policy"] = d.get("retry_policy")
    # The ledger keeps each attempt's time but not its usage, and the record's usage is the final call's. The scorer
    # bills attempts, so the final attempt carries the record's usage and a failed attempt bills nothing ({}): a call
    # that returned no answer (HTTP 429/500, connection reset) is not billed, as in the dev-split sample.
    att = [dict(a) for a in d.get("attempts") or []]
    for i, a in enumerate(att):
        a["usage"] = (d.get("usage") or {}) if i == len(att) - 1 and a.get("ok") else {}
    if not att and str(x.get("error") or "").startswith("not offered for this row"):
        # refused by the adapter before any call (a service limit); the time is when the refusal was recorded
        att = [{"attempt": 0, "ok": False, "at": d["at"], "latency_s": None, "usage": {},
                "error": "refused locally before any call: " + str(x["error"])[:200], "local_refusal": True}]
    x["attempts"] = att
    return x


def blocked_systems() -> dict:
    """{system: reason} from every ``<system>.blocked.json`` (results folder and private/)."""
    return {p.name.replace(".blocked.json", ""): json.loads(p.read_text(encoding="utf-8"))["reason"]
            for p in sorted(OUT.glob("*.blocked.json")) + sorted(WORK.glob("*.blocked.json"))}


def frozen_rows(tr: TestRows, keep=None) -> dict:
    from goldrails_bench import leaderboard_v2 as lv2
    out = {}
    for f in FEATURES:
        out[tr.file_sha[f]] = {i: lv2.row_summary(r) for i, r in tr.rows.items()
                               if tr.feature[i] == f and (keep is None or i in keep)}
    return out


def slice_view(records: list, tr: TestRows, keep: set, replicates) -> dict:
    """Diagnostic re-score over one slice (public or unpublished): the contamination check the slice is for."""
    from goldrails_bench import leaderboard_v2 as lv2
    recs = [dict(r) for r in records if r["id"] in keep]
    doc = lv2.evaluate(recs, lv2.load_contract(), sample.implementations(recs), None, "test", None, replicates, None,
                       None, [], {}, {}, frozen=frozen_rows(tr, keep), diagnostic=True)
    return sample.compact(doc)


# --- plan ------------------------------------------------------------------------------------------------------

def plan() -> None:
    tr = TestRows()
    sel = select_all(tr)
    n = 0
    for rows in sel.values():
        for r in rows:
            tr.guard(r)
    for (su, st), rows in sel.items():
        n += len(rows)
        u = sum(r["id"] in tr.unpublished for r in rows)
        print(f"{su}/{st}: {len(rows)} rows ({u} unpublished) {dict(Counter((r['subtask'], r['expected']) for r in rows))}")
    print(f"total {n} rows per system; guard passed")
    print("forecast:", json.dumps(forecast(n), indent=1))


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "preflight", "freeze", "run", "vm-run", "hosted-run", "all", "report"])
    ap.add_argument("--systems", default=",".join(HOSTED_KINDS))
    ap.add_argument("--only", default=None, help="comma-separated system names to run")
    ap.add_argument("--retry-failed", action="store_true", help="send again only rows whose latest record failed")
    ap.add_argument("--sequential", action="store_true", help="vm-run: one VM model at a time")
    ap.add_argument("--retry-only", action="store_true", help="vm-run: only the retry passes")
    ap.add_argument("--replicates", type=int, default=None)
    ap.add_argument("--source", help="edition 2 source (default: the pinned Hugging Face revision)")
    a = ap.parse_args(argv)
    smoke.use_source(a.source)
    WORK.mkdir(parents=True, exist_ok=True)
    if a.stage == "plan":
        plan()
    elif a.stage == "preflight":
        pf = preflight()
        print(json.dumps({k: (v if k != "aws_blocked" else (v or "ok")) for k, v in pf.items()}, indent=1))
    elif a.stage == "freeze":
        write_freeze(TestRows())
    elif a.stage == "run":
        run(set(a.systems.split(",")), set(a.only.split(",")) if a.only else None, a.retry_failed)
    elif a.stage == "vm-run":
        committed_freeze()
        r = vm_run(a.only.split(",") if a.only else None, a.sequential, a.retry_only)
        return 0 if r.get("terminated") and not r.get("error") else 1
    elif a.stage == "hosted-run":
        committed_freeze()
        hosted_run()
    elif a.stage == "all":
        return run_all()
    else:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
