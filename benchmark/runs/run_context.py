"""Which benchmark run a script works on, where that run's files live, and the guards that keep runs apart.

    GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py tune --dry-run

``GOLDRAILS_RUN`` (default ``first-benchmark``) names the run. Its ledgers and offline builds go to
``benchmark/results/<RUN>/``; its freeze manifests go to ``benchmark/subsets/<RUN>/``. ``GOLDRAILS_FROZEN_RUN``
(default: the run) names the run whose committed manifests and selections the test and latency stages read. Tune and
freeze refuse when the two differ. Data subsets (``first-benchmark``, ``first-benchmark-v1.1-ai``, ``-v1.2``,
``-v1.3``) and the implementations declaration are data, not run output: every run reads the same ones.

The first run keeps its historical layout, so nothing about it moves: its selections sit beside its ledgers in
``benchmark/results/first-benchmark/``. Any other run keeps its selections beside its manifests in
``benchmark/subsets/<RUN>/``, so everything frozen before the test is in one directory and one commit.

Guards: nothing that makes calls or freezes writes into a ``first-benchmark*`` results or subsets directory unless the
caller passes ``--i-know-this-writes-first-benchmark``; a freeze never overwrites an existing manifest. Superseded
arms (core F5 on AI4Privacy, replaced by the v1.2 Nemotron-PII pass; extension lexicon profanity, replaced by the v1.3
Civil Comments pass) are skipped by default in every run other than the first.

No network, model or cloud calls.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "benchmark" / "results"
SUBSETS = REPO / "benchmark" / "subsets"
CONTRACTS = REPO / "benchmark" / "contracts"
FIRST = "first-benchmark"
DATA_SUBSET = "first-benchmark"                  # core data subset; also holds the implementations declarations
IMPL_DIR = SUBSETS / DATA_SUBSET
SIGNED_CONTRACT = CONTRACTS / "v1.1-signed.json"
DEFAULT_HARDWARE = "g2-standard-24/us-east4/on-demand/third-party"
TARIFF_REGION = "us-east4"
I_KNOW_FLAG = "--i-know-this-writes-first-benchmark"
# Arms the current leaderboard no longer scores, skipped by default outside the first run.
SUPERSEDED = {
    "core": {"sensitive_info": "core F5 on AI4Privacy, replaced by the v1.2 Nemotron-PII pass (pii_v12_run.py)"},
    "extension": {"profanity": "lexicon-selected profanity (and its masked-spelling diagnostic), replaced by the v1.3 "
                               "Civil Comments pass (profanity_v13_run.py)"},
}
_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9.\-]*$")


def zone_fields(hardware: str, zone: str | None) -> dict:
    """Serving-record fields for the VM's zone. Nothing when the zone is unknown (the first run's records are unchanged);
    otherwise the zone, and a pricing note when the VM ran outside the region the tariff key prices. No new tariff
    entry is made: GPU time is still priced at that key."""
    if not zone:
        return {}
    out = {"zone": zone}
    if not zone.startswith(TARIFF_REGION + "-") and f"/{TARIFF_REGION}/" in f"/{hardware}/":
        out["pricing_note"] = (f"VM ran in {zone}; GPU cost is priced at the {TARIFF_REGION} tariff ({hardware}), "
                               "not at that zone's own rate")
    return out


def check_run_id(name: str) -> str:
    if not _RUN_ID.match(name or ""):
        raise SystemExit(f"run id {name!r} must be lowercase letters, digits, dots and hyphens")
    return name


@dataclass(frozen=True)
class RunContext:
    run: str = FIRST
    frozen_run: str = FIRST

    @property
    def is_first(self) -> bool:
        return self.run == FIRST

    @property
    def results(self) -> Path:
        return RESULTS / self.run

    @property
    def subsets(self) -> Path:
        """Where this run's freezes write manifests."""
        return SUBSETS / self.run

    @property
    def frozen_subsets(self) -> Path:
        """Where test, latency and offline builds read manifests."""
        return SUBSETS / self.frozen_run

    @staticmethod
    def selection_dir(run: str) -> Path:
        return RESULTS / FIRST if run == FIRST else SUBSETS / run

    @property
    def selections(self) -> Path:
        """Where this run's freezes write selections."""
        return self.selection_dir(self.run)

    @property
    def frozen_selections(self) -> Path:
        """Where test and latency stages read selections."""
        return self.selection_dir(self.frozen_run)

    def default_contract(self, first_run_default: Path | None) -> Path | None:
        """The first run keeps the contract its scripts always used; any other run freezes against the signed one."""
        return first_run_default if self.is_first else SIGNED_CONTRACT

    def skipped(self, group: str) -> dict:
        """Superseded arms skipped by default in this run: {suite or stage: reason}."""
        return {} if self.is_first else dict(SUPERSEDED[group])

    def vm_zone(self) -> str | None:
        """The zone the serving VM ran in: GOLDRAILS_VM_ZONE, else ``<results>/vm-zone.txt``, else unknown."""
        z = os.environ.get("GOLDRAILS_VM_ZONE")
        if z:
            return z.strip()
        p = self.results / "vm-zone.txt"
        return p.read_text(encoding="utf-8").strip() or None if p.exists() else None

    def describe(self) -> dict:
        return {"run": self.run, "frozen_run": self.frozen_run, "results": rel(self.results),
                "manifests_written_to": rel(self.subsets), "manifests_read_from": rel(self.frozen_subsets),
                "selections_written_to": rel(self.selections), "selections_read_from": rel(self.frozen_selections)}


def current(env=None) -> RunContext:
    env = os.environ if env is None else env
    run = check_run_id(env.get("GOLDRAILS_RUN") or FIRST)
    frozen = check_run_id(env.get("GOLDRAILS_FROZEN_RUN") or run)
    return RunContext(run, frozen)


def rel(p: Path) -> str:
    p = Path(p)
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p)


# --- guards ------------------------------------------------------------------------------------------------------

def is_protected(path) -> bool:
    """True for anything under a ``first-benchmark*`` results or subsets directory: the first run's records."""
    p = Path(path).resolve()
    for base in (RESULTS, SUBSETS):
        try:
            part = p.relative_to(base.resolve()).parts
        except ValueError:
            continue
        if part and part[0].startswith(FIRST):
            return True
    return False


def refuse_protected(paths, i_know: bool, what: str) -> None:
    hit = [rel(p) for p in paths if is_protected(p)]
    if hit and not i_know:
        raise SystemExit(f"{what} would write into the first benchmark's records ({', '.join(hit)}). Set "
                         f"GOLDRAILS_RUN to a new run id, or pass {I_KNOW_FLAG} if that is really intended.")


def refuse_existing(paths, what: str) -> None:
    hit = [rel(p) for p in paths if Path(p).exists()]
    if hit:
        raise SystemExit(f"{what} refuses to overwrite {', '.join(hit)}: a manifest is written once, committed, and "
                         "never rewritten. Choose a new GOLDRAILS_RUN.")


def require_same_run(ctx: RunContext, stage: str) -> None:
    if ctx.frozen_run != ctx.run:
        raise SystemExit(f"{stage} fits and freezes for its own run only: GOLDRAILS_FROZEN_RUN={ctx.frozen_run} differs "
                         f"from GOLDRAILS_RUN={ctx.run}. Unset GOLDRAILS_FROZEN_RUN for {stage}.")


def git_tracked(path) -> bool:
    p = Path(path).resolve()
    return subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", "--", str(p.relative_to(REPO))],
                          capture_output=True, text=True).returncode == 0


def check_env_unchanged(ctx: RunContext) -> None:
    """Scripts resolve paths at import; a .env loaded later must not change the run under them."""
    now = current()
    if now != ctx:
        raise SystemExit(f"run context changed after import ({ctx.run}/{ctx.frozen_run} -> {now.run}/{now.frozen_run}); "
                         "set GOLDRAILS_RUN and GOLDRAILS_FROZEN_RUN on the command line, not in .env")


# --- declared systems and plans (no clients) ---------------------------------------------------------------------

def load_impl() -> dict:
    return json.loads((IMPL_DIR / "implementations.json").read_text(encoding="utf-8"))


def declared_systems(impl: dict, kinds: set, suite: str) -> dict:
    """{system: kind} as ``first_benchmark.clients`` would build them for this suite, read from the implementations
    declaration instead of live endpoints."""
    sy = impl["systems"]
    out = {}
    if "jev" in kinds:
        out["jev-1.13.0"] = "jev"
    if "open" in kinds:
        out.update({n: "open" for n in sy["decision_models"] if n != "jev-1.13.0"})
    comp = sy["managed_service"]["composite_of"]
    if "bedrock" in kinds and suite in comp:
        out[comp[suite]] = "bedrock"
    if "regex" in kinds and suite in (sy.get("code_baselines") or {}).get("regex-baseline", []):
        out["regex-baseline"] = "regex"
    return out


def kind_of(system: str) -> str:
    """The ``--systems`` kind that builds this system's client."""
    if system == "jev-1.13.0":
        return "jev"
    if system.startswith("bedrock"):
        return "bedrock"
    return "regex" if system == "regex-baseline" else "open"


def provider_of(system: str) -> str:
    if system == "jev-1.13.0":
        return "jev"
    if system.startswith("bedrock"):
        return "bedrock"
    if system == "regex-baseline":
        return "regex (local, no API)"
    return "gpu"


def recorded_keys(ledger: Path) -> set:
    """(system, question_set, dataset sha256, row id, row hash) of every record in a ledger. The runner's resume key
    also holds the config hash, which needs live clients; a plan leaves it out and says so."""
    keys = set()
    if Path(ledger).exists():
        for line in Path(ledger).read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                keys.add((d["system"], d["question_set"], (d.get("dataset") or {}).get("sha256"), d["id"], d.get("row_hash")))
    return keys


def question_count(qname: str) -> int:
    from goldrails_bench.question_sets import load
    return len(load(*qname.split("-", 1))["questions"])


class Plan:
    """Collects what a stage would run: one line per (suite, system, question set) with rows and already-recorded
    rows, plus totals by provider. Prints; never calls anything."""

    def __init__(self, ctx: RunContext, script: str, stage: str):
        self.ctx, self.script, self.stage = ctx, script, stage
        self.lines, self.notes, self.paths = [], [], {}

    def path(self, label: str, p) -> None:
        self.paths[label] = rel(p) + ("" if Path(p).exists() else "  (absent)")

    def add(self, suite: str, system: str, qsets, rows: list, ledger: Path, note: str | None = None) -> None:
        from goldrails_bench.runner import row_hash_of
        done = recorded_keys(ledger)
        qsets = list(qsets)
        n = len(rows) * len(qsets)
        skip = sum(1 for q in qsets for r in rows
                   if (system, q, (getattr(r, "dataset", None) or {}).get("sha256"), r.id, row_hash_of(r)) in done)
        self.lines.append({"suite": suite, "system": system, "provider": provider_of(system),
                           "question_sets": qsets, "rows": len(rows), "evaluations": n, "already_recorded": skip,
                           "ledger": rel(ledger), "note": note})

    def totals(self) -> dict:
        t: dict = {}
        for x in self.lines:
            e = t.setdefault(x["provider"], {"evaluations": 0, "already_recorded": 0, "to_run": 0})
            e["evaluations"] += x["evaluations"]
            e["already_recorded"] += x["already_recorded"]
            e["to_run"] += x["evaluations"] - x["already_recorded"]
        return t

    def by_ledger(self) -> dict:
        t: dict = {}
        for x in self.lines:
            t[x["ledger"]] = t.get(x["ledger"], 0) + x["evaluations"] - x["already_recorded"]
        return t

    def render(self) -> str:
        out = [f"== {self.script} {self.stage}  (run {self.ctx.run}, frozen run {self.ctx.frozen_run}) — DRY RUN, no calls"]
        for k, v in self.paths.items():
            out.append(f"   {k:22s} {v}")
        cur = None
        for x in self.lines:
            if x["suite"] != cur:
                cur = x["suite"]
                out.append(f"   [{cur}] -> {x['ledger']}")
            out.append(f"     {x['system']:24s} {','.join(x['question_sets']):38s} {x['evaluations']:5d} evals"
                       f"  {x['already_recorded']:5d} already recorded" + (f"  ({x['note']})" if x["note"] else ""))
        for k, v in self.by_ledger().items():
            out.append(f"   ledger {k}: {v} evaluations to run")
        for p, v in sorted(self.totals().items()):
            out.append(f"   total {p:22s} {v['to_run']:6d} to run ({v['evaluations']} planned, {v['already_recorded']} already recorded)")
        out += [f"   note: {n}" for n in self.notes]
        return "\n".join(out)

    def print(self) -> "Plan":
        print(self.render(), flush=True)
        return self


__all__ = ["RunContext", "current", "is_protected", "refuse_protected", "refuse_existing", "require_same_run",
           "declared_systems", "Plan", "SUPERSEDED", "FIRST", "SIGNED_CONTRACT", "DEFAULT_HARDWARE", "IMPL_DIR"]
