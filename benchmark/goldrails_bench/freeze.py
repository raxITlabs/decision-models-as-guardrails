"""Frozen manifests: what was fixed on tuning rows before any test call, and the Git identity that proves when.

A manifest holds the scoring code identity (leaderboard module sha256 and result schema), the retry policy, the
contract (subtasks, weights, FPR budget, bootstrap seed and replicates) and a list of arms. Each arm is one exact
(system, question_set, config_hash, dataset_sha256) combination, where ``dataset_sha256`` is the test dataset version
the arm will be run on, with the thresholds fit on its tuning rows (and, for binary or step services, the declared
operating point). Write one from a tuning-mode leaderboard result, then commit it:

    doc = leaderboard.evaluate(tune_records, mode="smoke")
    freeze.write_manifest(doc, "benchmark/manifests/v1.json", retry_policy=policy.DEFAULT_POLICY,
                          test_datasets={"denied_topics": "<sha256 of F3.test.jsonl>", ...})

The runner refuses test rows unless a committed manifest lists the exact arm, and stamps the manifest identity on
every test record. The leaderboard's final mode scores with these thresholds and never refits.

A correction after the test is a separate manifest with a ``corrects`` block naming the primary manifest's sha256 and
one entry per corrected arm; it is committed before the corrected run, and the original run stays in the results.

An extension adds arms the primary manifest never listed (a suite whose test rows became eligible later, such as a
reviewed category). It is a separate manifest with an ``extends`` block naming the primary manifest's sha256, frozen
on its own tuning rows and committed before its own test calls. Its arms may not overlap the primary's; the primary's
arms and results are untouched.

Edition 2 (contract v2.0) fits nothing: its manifest records the fixed decision rule per arm and the contract's
frozen service settings, never a threshold, plus the ``integrity`` block of a strict overlap check (see
``write_manifest``). ``goldrails_bench.leaderboard_v2`` refuses to score a test run without such a manifest.

Pure functions plus local ``git`` reads. No network, model or cloud calls.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_VERSION = "goldrails-freeze/1"
REQUIRED_KEYS = ("manifest_version", "frozen_at", "scoring", "retry_policy", "contract", "arms")
ARM_KEYS = ("system", "question_set", "config_hash", "dataset_sha256")
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class FreezeError(RuntimeError):
    """The freeze cannot be proved: no manifest, an uncommitted manifest, or an arm the manifest does not list."""


# --- building a manifest -----------------------------------------------------------------------------------------

def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def scoring_identity() -> dict:
    """The scoring code a manifest freezes: the leaderboard module's sha256 and its result schema."""
    from . import leaderboard as lb
    return {"module": "goldrails_bench.leaderboard", "sha256": _sha256_bytes(Path(lb.__file__).read_bytes()),
            "schema": lb.SCHEMA}


def _policy_identity(retry_policy) -> dict:
    ident = retry_policy.identity() if hasattr(retry_policy, "identity") else dict(retry_policy)
    return json.loads(json.dumps(ident))


def _exact(th: dict | None) -> float | None:
    """The full-precision threshold (the result document rounds floats to 6 places)."""
    if not th:
        return None
    e = th.get("threshold_exact")
    if e is not None:
        return float(e)
    t = th.get("threshold")
    return None if t is None else float(t)


def _contract_block(doc: dict, bootstrap: dict | None) -> dict:
    c = doc.get("contract") or {}
    required = list(c.get("required_suites") or [])
    suites = c.get("suites") or {}
    boot = {**{k: v for k, v in (c.get("bootstrap") or {}).items() if k in ("replicates", "seed", "ci")},
            **(bootstrap or {})}
    return {
        "version": c.get("version"), "status": c.get("status"), "hash": c.get("hash"),
        "required_suites": required,
        "subtasks": {su: {"subtasks": list((spec.get("subtasks") or {})),
                          "optional_subtasks": list((spec.get("optional_subtasks") or {}))}
                     for su, spec in suites.items()},
        "weights": {"suites": {su: 1 / len(required) for su in required} if required else {},
                    "subtasks": {su: {st: 1 / len(spec["subtasks"]) for st in (spec.get("subtasks") or {})}
                                 for su, spec in suites.items()}},
        "fpr_budget": c.get("fpr_budget"),
        "operating_point": c.get("operating_point"),
        "bootstrap": boot,
    }


def _thresholds_of(arm: dict, operating_point) -> dict:
    """Frozen thresholds per subtask from one arm of a tuning-mode result. Subtasks with no fitted threshold are left
    out, so final mode reports them as not evaluated."""
    scale = arm.get("score_scale")
    out = {}
    for st, s in (arm.get("subtasks") or {}).items():
        th = s.get("threshold")
        if not th or th.get("basis") == "not_fit":
            continue
        t = _exact(th)
        sec = s.get("secondary") or {}
        entry = {"threshold": t, "basis": th.get("basis"),
                 "tuning_task_score": th.get("tuning_task_score"),
                 "tuning_false_positive_rate": th.get("tuning_false_positive_rate"),
                 "secondary": {"threshold": _exact(sec), "basis": sec.get("basis"), "status": sec.get("status"),
                               "budget": sec.get("budget"), "tuning_recall": sec.get("tuning_recall"),
                               "tuning_false_positive_rate": sec.get("tuning_false_positive_rate")}}
        if scale == "binary":
            entry["operating_point"] = operating_point
        elif scale == "ordered_steps":
            entry["operating_point"] = t     # a cut between the service's steps, chosen on tuning
        out[st] = entry
    return out


def write_manifest(doc: dict, path, *, retry_policy, test_datasets: dict, arms=None, bootstrap: dict | None = None,
                   corrects: dict | None = None, extends: dict | None = None, frozen_at: str | None = None,
                   edition: int | None = None, test_rows=None, references=None, pool=(), v1_build_rows=None,
                   contract: dict | None = None, test_files: dict | None = None) -> dict:
    """Build a manifest from a tuning-mode leaderboard result and write it to ``path``. Returns the manifest.

    ``doc`` must be a tuning-mode (``smoke``) result whose thresholds were fit on rows recorded as ``tune``; a row
    with no recorded split, or a final-mode result, raises. ``test_datasets`` maps each suite to the sha256 of the
    test dataset version its arms will run on (it may equal the tuning sha when one file holds both splits).
    ``arms`` restricts the manifest to those arm ids. ``bootstrap`` overrides the contract's seed and replicates.
    ``corrects`` makes this a correction manifest: {"manifest_sha256": <primary>, "corrections": [{system,
    question_set, original_config_hash, corrected_config_hash, dataset_sha256, reason, informed_by_test}]}.
    ``extends`` makes this an extension manifest: {"manifest_sha256": <primary>, "reason": ...}.

    Edition 2 (a contract version 2.x, or ``edition=2``) fits nothing. Each arm records the fixed decision rule of
    contract v2.0 (probability >= 0.5, the verdict API's own flag, or the frozen documented setting of a service's
    answer basis) and the manifest records the contract's headline rule and frozen service settings; no arm carries a
    ``thresholds`` block. ``doc`` is a tuning-mode (``smoke``) result or a ``goldrails_bench.leaderboard_v2`` result.
    An explicit ``edition=1`` with a v2.x contract raises.

    Edition 2 also runs the overlap check (``goldrails_bench.overlap``) in strict mode before anything is written.
    The test rows are read from the frozen dataset files, never taken from the caller: ``test_files`` maps every suite
    in ``test_datasets`` to its test file or files (``F<n>.test.jsonl``, public and private), each suite's rows must
    hash (``goldrails_dataset.records.dataset_hash``, the hash the runner stamps) to that suite's ``test_datasets``
    sha256, and the integrity block records each suite's sha256, row count and file sha256s, so it is tied to the
    arms' ``dataset_sha256``. ``test_rows`` is refused for edition 2. ``references`` are the examined, smoke, pilot and
    tuning rows or ids by role, and ``pool`` rows to look up bare ids in. The v1 release builds (``dataset/release/*/build``, in this
    checkout or the main checkout of a worktree) are added as a reference role and to the pool; ``v1_build_rows``
    supplies them instead. Empty test rows, empty references, an empty reference role or missing v1 release builds
    raise: without the builds a bare examined id would be checked by id only. Any overlap by id, text or group raises
    and no manifest is written; a clean check is recorded in the manifest's ``integrity`` block. Edition 1 is
    unchanged."""
    if _is_edition2(doc, edition):
        if test_rows is not None:
            raise FreezeError("an edition-2 freeze reads its test rows from the frozen dataset files (test_files), "
                              "not from rows the caller passes")
        return _write_edition2(doc, path, retry_policy=retry_policy, test_datasets=test_datasets, arms=arms,
                               bootstrap=bootstrap, corrects=corrects, extends=extends, frozen_at=frozen_at,
                               test_files=test_files, references=references, pool=pool, v1_build_rows=v1_build_rows,
                               contract=contract)
    if doc.get("mode") != "smoke":
        raise FreezeError(f"a manifest is written from a tuning-mode result; this one is mode {doc.get('mode')!r}")
    wanted = set(arms) if arms is not None else None
    chosen = [a for a in doc.get("arms", []) if wanted is None or a["arm_id"] in wanted]
    if wanted is not None and len(chosen) != len(wanted):
        missing = sorted(wanted - {a["arm_id"] for a in chosen})
        raise FreezeError(f"arms not in the tuning result: {missing}")
    op = (doc.get("contract") or {}).get("operating_point")
    out_arms = []
    for a in chosen:
        unknown = (a.get("sample_sizes") or {}).get("rows_split_unknown") or 0
        if unknown:
            raise FreezeError(f"{a['arm_id']}: {unknown} rows have no recorded split, so its thresholds were not fit "
                              "on tune rows only")
        if a["suite"] not in test_datasets:
            raise FreezeError(f"{a['arm_id']}: no test dataset version given for suite {a['suite']}")
        out_arms.append({
            "system": a["system"], "question_set": a["question_set"], "config_hash": a["config_hash"],
            "dataset_sha256": test_datasets[a["suite"]], "suite": a["suite"], "score_scale": a.get("score_scale"),
            "tuned_on": {"arm_id": a["arm_id"], "dataset_sha256": (a.get("dataset") or {}).get("sha256"),
                         "fit_rows": (a.get("sample_sizes") or {}).get("fit_rows")},
            "thresholds": _thresholds_of(a, op),
        })
    m = {
        "manifest_version": MANIFEST_VERSION,
        "frozen_at": frozen_at or time.strftime(TIME_FORMAT, time.gmtime()),
        "scoring": scoring_identity(),
        "retry_policy": _policy_identity(retry_policy),
        "contract": _contract_block(doc, bootstrap),
        "arms": out_arms,
    }
    if corrects is not None and extends is not None:
        raise FreezeError("a manifest either corrects or extends the primary, not both")
    if corrects is not None:
        m["corrects"] = corrects
    if extends is not None:
        m["extends"] = extends
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return m


def _contract_major(version) -> int | None:
    major = str(version or "").lstrip("vV").split(".")[0]
    return int(major) if major.isdigit() else None


def _is_edition2(doc: dict, edition) -> bool:
    """Edition 2 when the contract is v2.x (an explicit ``edition=1`` cannot override it) or ``edition`` >= 2."""
    major = _contract_major((doc.get("contract") or {}).get("version"))
    if major is not None and major >= 2:
        if edition is not None and int(edition) < 2:
            raise FreezeError(f"edition={edition} conflicts with contract {(doc.get('contract') or {}).get('version')}: "
                              "a v2.x contract is frozen as edition 2 (no fitted thresholds, overlap check)")
        return True
    return edition is not None and int(edition) >= 2


# --- edition 2: the fixed rule, no fitted thresholds ---------------------------------------------------------------

EDITION2_SCHEMA = "goldrails-leaderboard/2.0"


def _v2_contract(contract: dict | None) -> dict:
    if contract is not None:
        return contract
    from . import leaderboard_v2
    return leaderboard_v2.load_contract()


def scoring_identity_v2() -> dict:
    from . import leaderboard_v2 as v2
    return {"module": "goldrails_bench.leaderboard_v2", "sha256": _sha256_bytes(Path(v2.__file__).read_bytes()),
            "schema": v2.SCHEMA}


def _fixed_rule(a: dict, contract: dict) -> dict:
    """The arm's decision rule under the v2.0 headline rule. Nothing here is fitted: the threshold is the contract's
    operating point or a frozen documented service setting."""
    r = a.get("decision_rule")
    if r:
        if r.get("threshold") is None:
            raise FreezeError(f"{a.get('arm_id')}: no fixed rule ({r.get('rule')}); it cannot be frozen")
        return {k: r.get(k) for k in ("threshold", "scale", "basis", "rule")}
    op = contract.get("operating_point", 0.5)
    scale = a.get("score_scale")
    if scale == "probability":
        return {"threshold": op, "scale": scale, "basis": "fixed_probability_rule",
                "rule": f"probability >= {op} per question, flagged when any decision question flags (max)"}
    if scale == "binary":
        return {"threshold": op, "scale": scale, "basis": "verdict",
                "rule": "verdict API: the system's own flag (recorded as 1 flagged, 0 passed)"}
    raise FreezeError(f"{a.get('arm_id')}: a {scale} arm's frozen setting depends on its answer bases; freeze from a "
                      "goldrails_bench.leaderboard_v2 result, which records the rule per arm")


def _contract_block_v2(contract: dict, bootstrap: dict | None) -> dict:
    from .leaderboard import _stable_hash
    from .leaderboard_v2 import scored_subtasks, sanity_subtasks, unscored_units
    required = list(contract.get("required_suites") or [])
    suites = contract.get("suites") or {}
    boot = (contract.get("statistics") or {}).get("bootstrap") or contract.get("bootstrap") or {}
    return {
        "version": contract.get("version"), "status": contract.get("status"), "hash": _stable_hash(contract),
        "required_suites": required,
        "subtasks": {su: {"subtasks": list((spec.get("subtasks") or {})),
                          "optional_subtasks": list((spec.get("optional_subtasks") or {}))}
                     for su, spec in suites.items()},
        "weights": {"suites": {su: 1 / len(required) for su in required} if required else {},
                    "subtasks": {su: {st: 1 / len(scored_subtasks(contract, su)) for st in scored_subtasks(contract, su)}
                                 for su in suites if scored_subtasks(contract, su)}},
        "sanity_checks": {su: sanity_subtasks(contract, su) for su in suites if sanity_subtasks(contract, su)},
        "unscored_units": {su: unscored_units(contract, su) for su in suites if unscored_units(contract, su)},
        "operating_point": contract.get("operating_point"),
        "headline_rule": contract.get("headline_rule"),
        "frozen_settings": contract.get("frozen_settings"),
        "binary_bases": contract.get("binary_bases"),
        "step_bases": contract.get("step_bases"),
        "max_failure_rate": (contract.get("coverage") or {}).get("max_failure_rate"),
        "bootstrap": {**{k: v for k, v in boot.items() if k in ("replicates", "seed", "ci")}, **(bootstrap or {})},
    }


def _write_edition2(doc: dict, path, *, retry_policy, test_datasets: dict, arms, bootstrap, corrects, extends,
                    frozen_at, test_files, references, pool, v1_build_rows, contract) -> dict:
    if doc.get("mode") != "smoke" and doc.get("schema") != EDITION2_SCHEMA:
        raise FreezeError("an edition-2 manifest is written from a tuning-mode or leaderboard_v2 result; this one is "
                          f"mode {doc.get('mode')!r}, schema {doc.get('schema')!r}")
    if corrects is not None and extends is not None:
        raise FreezeError("a manifest either corrects or extends the primary, not both")
    contract = _v2_contract(contract)
    wanted = set(arms) if arms is not None else None
    chosen = [a for a in doc.get("arms", []) if wanted is None or a["arm_id"] in wanted]
    if wanted is not None and len(chosen) != len(wanted):
        raise FreezeError(f"arms not in the result: {sorted(wanted - {a['arm_id'] for a in chosen})}")
    for a in chosen:
        if a["suite"] not in test_datasets:
            raise FreezeError(f"{a['arm_id']}: no test dataset version given for suite {a['suite']}")
    datasets, test_rows = frozen_test_rows(test_datasets, test_files)
    integrity = _integrity_check(test_rows, references, pool, v1_build_rows)
    integrity["datasets"] = datasets
    out_arms = []
    for a in chosen:
        out_arms.append({
            "system": a["system"], "question_set": a["question_set"], "config_hash": a["config_hash"],
            "dataset_sha256": test_datasets[a["suite"]], "suite": a["suite"], "score_scale": a.get("score_scale"),
            "decision_rule": _fixed_rule(a, contract),
            "checked_on": {"arm_id": a["arm_id"], "dataset_sha256": (a.get("dataset") or {}).get("sha256")},
        })
    m = {
        "manifest_version": MANIFEST_VERSION,
        "edition": 2,
        "thresholds_fitted": False,
        "frozen_at": frozen_at or time.strftime(TIME_FORMAT, time.gmtime()),
        "scoring": scoring_identity_v2(),
        "retry_policy": _policy_identity(retry_policy),
        "contract": _contract_block_v2(contract, bootstrap),
        "arms": out_arms,
        "integrity": integrity,
    }
    if corrects is not None:
        m["corrects"] = corrects
    if extends is not None:
        m["extends"] = extends
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return m


# --- edition 2: the overlap check ------------------------------------------------------------------------------------

V1_BUILD_GLOB = "dataset/release/*/build/*.jsonl"
V1_BUILD_ROLE = "v1_release_builds"
# The reference roles an edition-2 integrity check must cover (contract v2.0 ``freeze.integrity``): rows already
# examined, smoke and pilot ledgers, the edition's tuning rows, and the v1 release builds (added by the check itself).
REQUIRED_REFERENCE_ROLES = ("examined", "smoke", "pilot", "tune")
OPTIONAL_REFERENCE_ROLES = ("diagnostic",)
INTEGRITY_ROLES = REQUIRED_REFERENCE_ROLES + OPTIONAL_REFERENCE_ROLES + (V1_BUILD_ROLE,)


def _main_checkout(repo: Path) -> Path | None:
    """The main checkout when ``repo`` is a git worktree (the v1 release builds are git-ignored and live there)."""
    r = _git(repo, "rev-parse", "--git-common-dir")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    p = (repo / r.stdout.strip()).resolve().parent
    return p if p != repo.resolve() else None


def v1_release_build_files(repo=None) -> list[Path]:
    """The v1 release build files in ``repo`` (default this repository) and, from a worktree, the main checkout."""
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[2]
    files = sorted(repo.glob(V1_BUILD_GLOB))
    main = _main_checkout(repo)
    if main is not None:
        files += sorted(main.glob(V1_BUILD_GLOB))
    return files


_V1_CACHE: dict = {}


def v1_release_rows(repo=None) -> list[dict]:
    """The v1 release build rows (id, group, provenance source ids, and the state's text, context and other fields the
    near-duplicate rule reads), or FreezeError when no build is present,
    as on a clean clone or in CI: the builds are git-ignored and must be rebuilt (``goldrails_dataset``) first."""
    files = v1_release_build_files(repo)
    if not files:
        raise FreezeError("no v1 release builds (dataset/release/*/build/*.jsonl) in this checkout or its main "
                          "checkout; rebuild them before an edition-2 freeze. Without them examined ids would be "
                          "checked by id only")
    key = tuple((str(f), f.stat().st_mtime_ns) for f in files)
    if key not in _V1_CACHE:
        rows = []
        for f in files:
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                x = json.loads(line)
                prov = x.get("provenance") or {}
                st = x.get("state") or {}
                rows.append({"id": x.get("id"), "group": x.get("group"),
                             "provenance": {"source": prov.get("source"), "source_id": prov.get("source_id")},
                             "state": {k: v for k, v in st.items() if k == "text" or (k != "role" and v)}})
        _V1_CACHE.clear()
        _V1_CACHE[key] = rows
    return _V1_CACHE[key]


def _rel(p: Path) -> str:
    repo = Path(__file__).resolve().parents[2]
    p = Path(p).resolve()
    return p.relative_to(repo).as_posix() if p.is_relative_to(repo) else str(p)


def frozen_test_rows(test_datasets: dict, test_files: dict | None) -> tuple[dict, list]:
    """({suite: {sha256, rows, files}}, all test rows) read from the frozen dataset files. Every suite in
    ``test_datasets`` needs its files, and its rows must hash (``dataset_hash``) to the given sha256; otherwise
    FreezeError. A suite's files may also be a single file whose own sha256 is the given one."""
    from goldrails_dataset.records import dataset_hash, read_jsonl
    if not test_datasets:
        raise FreezeError("an edition-2 freeze needs test_datasets: the dataset version each suite's arms run on")
    if not test_files:
        raise FreezeError("an edition-2 freeze reads its test rows from the frozen dataset files: give test_files "
                          "({suite: path or [paths]})")
    unknown = sorted(set(test_files) - set(test_datasets))
    if unknown:
        raise FreezeError(f"test_files names suites with no test dataset version: {', '.join(unknown)}")
    datasets, rows = {}, []
    for suite, want in sorted(test_datasets.items()):
        paths = test_files.get(suite)
        if not paths:
            raise FreezeError(f"no frozen test dataset file for suite {suite}")
        paths = [Path(paths)] if isinstance(paths, (str, Path)) else [Path(x) for x in paths]
        missing = [str(x) for x in paths if not x.is_file()]
        if missing:
            raise FreezeError(f"frozen test dataset files of {suite} do not exist: {', '.join(missing)}")
        recs = [r for x in paths for r in read_jsonl(x)]
        if not recs:
            raise FreezeError(f"frozen test dataset of {suite} has no rows")
        got = dataset_hash(recs)
        file_shas = [_sha256_bytes(x.read_bytes()) for x in paths]
        if want != got and not (len(paths) == 1 and want == file_shas[0]):
            raise FreezeError(f"frozen test dataset of {suite} hashes to {got[:12]}, not the arms' dataset version "
                              f"{str(want)[:12]}")
        datasets[suite] = {"sha256": want, "dataset_hash": got, "rows": len(recs),
                           "files": [{"path": _rel(x), "sha256": h} for x, h in zip(paths, file_shas)]}
        rows += recs
    return datasets, rows


def _integrity_check(test_rows, references, pool, v1_build_rows=None) -> dict:
    """The edition-2 overlap check in strict mode: raises (an OverlapError, which is a FreezeError) on any overlap, and
    FreezeError when the check would prove nothing (no test rows, no references, an empty reference role) or when the
    v1 release builds are missing."""
    if test_rows is None or references is None:
        raise FreezeError("an edition-2 freeze runs the overlap check: give test_rows and references")
    from . import overlap
    tests = list(test_rows)
    if not tests:
        raise FreezeError("the overlap check was given no test rows; an empty check proves nothing")
    refs = overlap._references(references)
    if not refs or not sum(len(v) for v in refs.values()):
        raise FreezeError("the overlap check was given no reference rows; an empty check proves nothing")
    empty = sorted(role for role, rows in refs.items() if not rows)
    if empty:
        raise FreezeError(f"reference roles with no rows: {', '.join(empty)}")
    if V1_BUILD_ROLE in refs:
        raise FreezeError(f"reference role {V1_BUILD_ROLE} is reserved; pass those rows as v1_build_rows")
    unknown = sorted(set(refs) - set(INTEGRITY_ROLES))
    if unknown:
        raise FreezeError(f"unknown reference roles: {', '.join(unknown)} (the check's roles are "
                          f"{', '.join(INTEGRITY_ROLES)})")
    missing = [r for r in REQUIRED_REFERENCE_ROLES if r not in refs]
    if missing:
        raise FreezeError(f"the overlap check needs every required reference role; missing: {', '.join(missing)}")
    builds = v1_release_rows() if v1_build_rows is None else list(v1_build_rows)
    if not builds:
        raise FreezeError("no v1 release build rows; without them examined ids would be checked by id only")
    refs[V1_BUILD_ROLE] = builds
    full_pool = list(pool or ()) + builds
    rep = overlap.check(tests, refs, pool=full_pool, strict=True).to_dict()
    pooled = {overlap.row_id(p) for p in full_pool}
    bare = [r for rows in refs.values() for r in rows if isinstance(r, str)]
    return {"check": "goldrails_bench.overlap", "kinds": list(overlap.KINDS), "pass": True,
            "test_rows": rep["test_rows"], "reference_rows": rep["reference_rows"], "overlapping_test_rows": 0,
            "v1_release_build_rows": len(builds),
            "bare_reference_ids": {"total": len(bare), "resolved_through_pool": sum(1 for b in bare if b in pooled)}}


# --- reading a manifest ------------------------------------------------------------------------------------------

def arm_key(a: dict) -> tuple:
    return tuple(a.get(k) for k in ARM_KEYS)


def validate(m: dict) -> list[str]:
    """Problems with a manifest's shape; empty when it is usable."""
    if not isinstance(m, dict):
        return ["manifest is not a JSON object"]
    probs = [f"missing {k}" for k in REQUIRED_KEYS if k not in m]
    if m.get("manifest_version") not in (None, MANIFEST_VERSION):
        probs.append(f"manifest_version {m.get('manifest_version')!r} is not {MANIFEST_VERSION}")
    for i, a in enumerate(m.get("arms") or []):
        miss = [k for k in ARM_KEYS if not a.get(k)]
        if miss:
            probs.append(f"arm {i} lacks {', '.join(miss)}")
    x = m.get("extends")
    if x is not None:
        if not x.get("manifest_sha256"):
            probs.append("extends names no primary manifest_sha256")
        if not x.get("reason"):
            probs.append("extends gives no reason")
        if m.get("corrects") is not None:
            probs.append("a manifest cannot both correct and extend")
    c = m.get("corrects")
    if c is not None:
        if not c.get("manifest_sha256"):
            probs.append("corrects names no primary manifest_sha256")
        for i, e in enumerate(c.get("corrections") or []):
            miss = [k for k in ("system", "question_set", "original_config_hash", "corrected_config_hash",
                                "dataset_sha256", "reason") if not e.get(k)]
            if miss:
                probs.append(f"correction {i} lacks {', '.join(miss)}")
    return probs


def _git(cwd, *args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=20)


def manifest_identity(path) -> dict:
    """{path, manifest_sha256, commit, committed_at} for a committed manifest file. ``commit`` is the last commit
    that touched it and ``committed_at`` that commit's committer time in UTC. Raises FreezeError when the file is
    missing, outside a Git repository, untracked, never committed, or has uncommitted (staged or unstaged) changes."""
    p = Path(path).resolve()
    if not p.is_file():
        raise FreezeError(f"manifest {path} does not exist")
    top = _git(p.parent, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or not top.stdout.strip():
        raise FreezeError(f"manifest {path} is not in a Git repository")
    root = Path(top.stdout.strip()).resolve()
    rel = p.relative_to(root).as_posix()
    if _git(root, "ls-files", "--error-unmatch", "--", rel).returncode != 0:
        raise FreezeError(f"manifest {rel} is not committed (untracked)")
    st = _git(root, "status", "--porcelain", "--untracked-files=all", "--", rel)
    if st.returncode != 0:
        raise FreezeError(f"cannot read Git status of {rel}: {st.stderr.strip()}")
    if st.stdout.strip():
        raise FreezeError(f"manifest {rel} has uncommitted changes")
    log = _git(root, "log", "-1", "--format=%H %ct", "--", rel)
    if log.returncode != 0 or not log.stdout.strip():
        raise FreezeError(f"manifest {rel} is not committed")
    commit, ts = log.stdout.split()
    return {"path": rel, "manifest_sha256": _sha256_bytes(p.read_bytes()), "commit": commit,
            "committed_at": datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime(TIME_FORMAT)}


def record_stamp(identity: dict) -> dict:
    """What the runner writes on every test record and in the arms sidecar."""
    return {k: identity[k] for k in ("manifest_sha256", "commit", "committed_at")}


@dataclass
class FrozenManifest:
    """A loaded manifest with its Git identity, or the reason the identity could not be proved."""
    manifest: dict
    identity: dict | None = None
    error: str | None = None
    path: str | None = None

    @property
    def sha256(self) -> str | None:
        return (self.identity or {}).get("manifest_sha256")


def load(path) -> FrozenManifest:
    """Read a manifest and prove its identity. An identity failure is kept in ``error`` (the leaderboard turns it
    into a publication blocker); a missing or unparseable file raises."""
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        ident, err = manifest_identity(path), None
    except FreezeError as e:
        ident, err = None, str(e)
    return FrozenManifest(m, ident, err, str(path))


def load_committed(path) -> tuple[dict, dict]:
    """(manifest, identity) or FreezeError: the runner's strict read."""
    ident = manifest_identity(path)
    m = json.loads(Path(path).read_text(encoding="utf-8"))
    probs = validate(m)
    if probs:
        raise FreezeError(f"manifest {path}: " + "; ".join(probs))
    return m, ident


def default_references(repo=None, tune_files=None) -> dict:
    """The edition-2 reference rows as this repository records them, by role: ``examined`` (examined-ids.txt less
    documented clearances, plus every id in a ledger, output or notebook: ``overlap.repo_examined_ids``), ``smoke`` and
    ``pilot`` (the ids in those ledgers), ``diagnostic`` (when any diagnostic ledger exists) and ``tune`` (the edition 2
    tuning rows, ``dataset/edition2/build/F*.tune.jsonl`` unless ``tune_files`` names them). A required role with no
    rows is left in, so the check that uses it fails rather than passing on less."""
    from . import overlap
    from goldrails_dataset.records import read_jsonl
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[2]
    results = repo / "benchmark" / "results"
    tune_files = sorted((repo / "dataset" / "edition2" / "build").glob("F*.tune.jsonl")) if tune_files is None \
        else [Path(f) for f in tune_files]
    refs = {"examined": sorted(overlap.repo_examined_ids(repo)),
            "smoke": sorted(overlap.ledger_ids(results, ("smoke-*.jsonl",))),
            "pilot": sorted(overlap.ledger_ids(results, ("pilot-*.jsonl",))),
            "tune": [r for f in tune_files for r in read_jsonl(f)]}
    diag = sorted(overlap.ledger_ids(results, ("diagnostics/**/*.jsonl",)))
    if diag:
        refs["diagnostic"] = diag
    return refs


def _resolve(path: str, repo: Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else repo / p


_RECOMPUTED: dict = {}


def recompute_integrity(m: dict, *, references=None, pool=(), v1_build_rows=None, repo=None) -> dict:
    """The integrity block a strict overlap check gives today for the datasets the manifest's block names: each
    suite's files are read from their recorded paths (relative to the repository), every file must still have its
    recorded sha256 and the suite's rows must hash to its sha256 (``frozen_test_rows``), and the check runs against
    ``references`` (default ``default_references``: examined, smoke, pilot and tuning rows) plus the v1 release
    builds. Raises FreezeError (an OverlapError on an overlap) when any of that fails."""
    import hashlib
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[2]
    i = m.get("integrity") if isinstance(m.get("integrity"), dict) else {}
    ds = i.get("datasets")
    if not isinstance(ds, dict) or not ds:
        raise FreezeError("the integrity block names no frozen datasets to recompute it from")
    files = {}
    for su, d in sorted(ds.items()):
        entries = (d or {}).get("files") if isinstance(d, dict) else None
        if not entries or not all(isinstance(e, dict) and e.get("path") for e in entries):
            raise FreezeError(f"the integrity block gives no dataset file paths for {su}")
        files[su] = [_resolve(e["path"], repo) for e in entries]
        for e, f in zip(entries, files[su]):
            if f.is_file() and _sha256_bytes(f.read_bytes()) != e.get("sha256"):
                raise FreezeError(f"dataset file {e['path']} of {su} no longer has the sha256 the integrity block "
                                  "records")
    key = None
    if references is None and v1_build_rows is None and not pool:
        stamp = [(str(f), f.stat().st_mtime_ns) for fs in files.values() for f in fs if f.is_file()]
        key = hashlib.sha256(json.dumps([i, stamp, str(repo)], sort_keys=True, default=str).encode()).hexdigest()
        if key in _RECOMPUTED:
            return copy.deepcopy(_RECOMPUTED[key])
    datasets, rows = frozen_test_rows({su: (d or {}).get("sha256") for su, d in ds.items()}, files)
    refs = default_references(repo) if references is None else references
    block = _integrity_check(rows, refs, pool, v1_build_rows)
    block["datasets"] = datasets
    if key is not None:
        _RECOMPUTED.clear()
        _RECOMPUTED[key] = copy.deepcopy(block)
    return block


def integrity_problems(m: dict, *, recompute: bool = True, references=None, pool=(), v1_build_rows=None,
                       repo=None) -> list[str]:
    """Why a manifest cannot back an edition-2 test run; empty when it is an edition-2 manifest with no fitted
    thresholds and an integrity block that a fresh check reproduces. The block is never taken on trust: its reference
    roles must be exactly the check's (examined, smoke, pilot, tune and the v1 release builds, optionally diagnostic,
    each with rows), and ``recompute_integrity`` reruns the strict overlap check from the dataset files the block
    names (their sha256 checked) and the references (default: this repository's, ``default_references``). The
    recomputed block must match the recorded one: the same datasets, files and row count, the same v1 build rows, the
    same roles, and no role recorded with more rows than exist. ``recompute=False`` checks the shape only."""
    probs = []
    if m.get("edition") != 2:
        probs.append(f"not an edition-2 manifest (edition {m.get('edition')!r})")
    if m.get("thresholds_fitted") is not False or any("thresholds" in a for a in m.get("arms") or []):
        probs.append("the manifest carries fitted thresholds; edition 2 freezes the fixed rule only")
    i = m.get("integrity")
    if not isinstance(i, dict):
        return probs + ["no integrity block"]
    refs = i.get("reference_rows") or {}
    if i.get("check") != "goldrails_bench.overlap":
        probs.append(f"integrity block was not written by the overlap check (check {i.get('check')!r})")
    if i.get("pass") is not True:
        probs.append("integrity block does not record a passing check")
    if i.get("overlapping_test_rows") != 0:
        probs.append(f"integrity block records {i.get('overlapping_test_rows')!r} overlapping test rows")
    if not i.get("test_rows"):
        probs.append("integrity check ran on no test rows")
    if not isinstance(refs, dict) or not refs or not all(refs.values()):
        probs.append("integrity check ran with no or empty reference roles")
        refs = refs if isinstance(refs, dict) else {}
    unknown = sorted(set(refs) - set(INTEGRITY_ROLES))
    if unknown:
        probs.append(f"integrity block names unknown reference roles: {', '.join(map(str, unknown))}")
    missing = [r for r in REQUIRED_REFERENCE_ROLES if not refs.get(r)]
    if missing:
        probs.append(f"integrity check ran without the required reference roles: {', '.join(missing)}")
    if not i.get("v1_release_build_rows") or not refs.get(V1_BUILD_ROLE):
        probs.append("integrity check ran without the v1 release builds")
    probs += _integrity_dataset_problems(m, i)
    if recompute and not probs:
        probs += _recomputed_problems(m, i, references=references, pool=pool, v1_build_rows=v1_build_rows, repo=repo)
    return probs


def _recomputed_problems(m: dict, i: dict, **kw) -> list[str]:
    try:
        fresh = recompute_integrity(m, **kw)
    except FreezeError as e:
        return [f"integrity block cannot be reproduced: {e}"]
    probs = []
    if fresh["datasets"] != i.get("datasets"):
        probs.append("integrity block's datasets differ from the recomputed ones (sha256, rows or files)")
    if fresh["test_rows"] != i.get("test_rows"):
        probs.append(f"integrity block records {i.get('test_rows')!r} test rows; the recomputed check ran on "
                     f"{fresh['test_rows']}")
    if fresh["v1_release_build_rows"] != i.get("v1_release_build_rows"):
        probs.append(f"integrity block records {i.get('v1_release_build_rows')!r} v1 release build rows; there are "
                     f"{fresh['v1_release_build_rows']}")
    got, rec = fresh["reference_rows"], i.get("reference_rows") or {}
    if set(got) != set(rec):
        probs.append(f"integrity block's reference roles {sorted(rec)} differ from the recomputed {sorted(got)}")
    over = sorted(r for r in set(got) & set(rec) if not isinstance(rec[r], int) or rec[r] > got[r])
    if over:
        probs.append("integrity block records more reference rows than exist for: " + ", ".join(over))
    return probs


def _integrity_dataset_problems(m: dict, i: dict) -> list[str]:
    """The integrity block must be tied to the frozen datasets: one entry per suite with its sha256, row count and
    file sha256s, every arm's (suite, dataset_sha256) among them, and the checked row count their sum."""
    ds = i.get("datasets")
    if not isinstance(ds, dict) or not ds:
        return ["integrity block names no frozen datasets, so it is not tied to the arms' dataset_sha256"]
    probs = []
    for su, d in sorted(ds.items()):
        if not isinstance(d, dict) or not d.get("sha256") or not d.get("rows") or not d.get("files"):
            probs.append(f"integrity block entry for {su} lacks its sha256, row count or files")
    ok = {(su, d.get("sha256")) for su, d in ds.items() if isinstance(d, dict)}
    for a in m.get("arms") or []:
        if (a.get("suite"), a.get("dataset_sha256")) not in ok:
            probs.append(f"arm {a.get('system')}|{a.get('question_set')} runs on {a.get('suite')} dataset "
                         f"{str(a.get('dataset_sha256'))[:12]}, which the integrity check did not cover")
    n = sum(d.get("rows") or 0 for d in ds.values() if isinstance(d, dict))
    if i.get("test_rows") != n:
        probs.append(f"integrity check ran on {i.get('test_rows')!r} test rows, not the {n} rows of its datasets")
    return probs


def threshold_map(primary: FrozenManifest | dict | None, corrections=(), extensions=()) -> dict:
    """Arm key -> {role, manifest_sha256, thresholds, score_scale} from the primary manifest and any extension
    manifests (role ``frozen``) and any correction manifests (role ``corrected``)."""
    out = {}
    for role, fm in ([("frozen", primary)] + [("frozen", x) for x in extensions or ()]
                     + [("corrected", c) for c in corrections or ()]):
        if fm is None:
            continue
        m = fm.manifest if isinstance(fm, FrozenManifest) else fm
        sha = fm.sha256 if isinstance(fm, FrozenManifest) else None
        for a in m.get("arms") or []:
            out[arm_key(a)] = {"role": role, "manifest_sha256": sha, "thresholds": a.get("thresholds") or {},
                               "score_scale": a.get("score_scale")}
    return out


def parse_time(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, TIME_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


__all__ = ["MANIFEST_VERSION", "FreezeError", "FrozenManifest", "write_manifest", "manifest_identity", "load",
           "load_committed", "validate", "arm_key", "threshold_map", "record_stamp", "scoring_identity", "parse_time",
           "scoring_identity_v2", "v1_release_rows", "v1_release_build_files", "integrity_problems",
           "frozen_test_rows", "recompute_integrity", "default_references", "REQUIRED_REFERENCE_ROLES",
           "INTEGRITY_ROLES"]
