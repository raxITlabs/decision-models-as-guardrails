"""Checks for the static leaderboard shell in site/leaderboard.

Run with `uv run pytest -q site/leaderboard/tests` (the workspace testpaths do not include site/ yet).
The logic tests drive leaderboard.js through node; they skip if node is not installed.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1]
REPO = SITE.parents[1]
SCHEMA = SITE / "results.schema.json"
SAMPLE = SITE / "sample-results.json"
PAGE = SITE / "index.html"
LOGIC = SITE / "leaderboard.js"

ALLOWED_HOSTS = ("cdnjs.cloudflare.com", "fonts.googleapis.com", "fonts.gstatic.com")


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_sample_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(load(SAMPLE)), key=lambda e: e.json_path)
    assert not errors, [f"{e.json_path}: {e.message}" for e in errors[:5]]


def test_sample_is_unmistakably_placeholder():
    data = load(SAMPLE)
    assert data["placeholder"] is True
    assert "PLACEHOLDER" in data["notice"]
    assert "PLACEHOLDER" in data["benchmark"]["dataset_version"]
    for im in data["implementations"]:
        assert "PLACEHOLDER" in im["label"], im["id"]
    for e in data["entries"]:
        assert e["status_note"] and "PLACEHOLDER" in e["status_note"], (e["implementation"], e["suite"])
    # No real system names: invented values must not be attributable to a real product.
    text = SAMPLE.read_text(encoding="utf-8").lower()
    for name in ("jev", "kev", "laya", "bedrock", "open-jev", "typesafe"):
        assert name not in text, name


def test_sample_covers_the_cases_the_page_must_handle():
    data = load(SAMPLE)
    statuses = {e["status"] for e in data["entries"]}
    assert {"evaluated", "not_evaluated", "not_applicable", "failed"} <= statuses
    assert any(not im["frozen"] for im in data["implementations"])
    assert any(e["status"] == "evaluated" and e["cost"] is None for e in data["entries"])
    assert any(e["suite"] == "overall" and e["status"] == "not_evaluated" for e in data["entries"])
    assert any(e["suite"] == "bias" and e["track"] == "decision_bias" and e["status"] == "not_applicable" for e in data["entries"])
    assert sum(1 for im in data["implementations"] if im.get("sweep")) >= 2


def test_overall_scores_are_equal_weight_means_of_six_suites():
    data = load(SAMPLE)
    suites = ("content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_information", "grounding")
    for o in (e for e in data["entries"] if e["suite"] == "overall" and e["status"] == "evaluated"):
        comps = [o["components"][s] for s in suites]
        assert all(c is not None for c in comps)
        assert abs(o["quality"]["score"] - round(sum(comps) / 6, 1)) < 0.051


def test_no_external_hosts_outside_the_allowlist():
    for path in (PAGE, LOGIC):
        text = path.read_text(encoding="utf-8")
        refs = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^"')]+)|@import\s+["']([^"']+)|fetch\(\s*["']([^"']+)""", text)
        for groups in refs:
            ref = next(g for g in groups if g)
            if re.match(r"^(https?:)?//", ref):
                host = re.sub(r"^(https?:)?//", "", ref).split("/")[0]
                assert host in ALLOWED_HOSTS, f"{path.name} loads {ref}"


def test_owned_files_have_no_em_dashes():
    owned = [p for p in SITE.rglob("*") if p.is_file() and p.suffix in {".html", ".js", ".json", ".py"}]
    owned += [REPO / "dataset" / "DATASET_CARD.md", REPO / "docs" / "benchmark" / "22-budget-forecast.md"]
    owner_names = ("Profanity or obscenity " + chr(0x2014) + " Civil Comments",)   # the subtask name the owner chose, 28 Sep 2026
    for p in owned:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            for name in owner_names:
                text = text.replace(name, "")
            assert chr(0x2014) not in text, p


NODE_SCRIPT = r"""
const G = require(process.argv[1]);
const data = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = { validate: G.validate(data), views: {} };
for (const v of G.VIEWS) {
  const tracks = v.id === 'bias' ? G.BIAS_TRACKS.map(t => t.id) : [null];
  for (const track of tracks) {
    for (const axis of Object.keys(G.AXES)) {
      const rows = G.rowsFor(data, v.id, track);
      const plan = G.plotPlan(data, rows, axis);
      out.views[`${v.id}|${track}|${axis}`] = {
        rows: rows.length,
        points: plan.points.map(p => ({ id: p.impl.id, frozen: p.impl.frozen, status: p.entry.status, x: p.x, y: p.y })),
        excluded: plan.excluded.map(x => ({ id: x.impl.id, status: x.entry.status, reason: x.reason })),
        sweeps: G.sweepLines(plan.points).map(l => l.points.map(p => p.impl.id)),
      };
    }
  }
}
const clone = () => JSON.parse(JSON.stringify(data));
const zero = clone(); zero.entries.find(e => e.status === 'evaluated' && e.cost).cost.usd_per_1000 = 0;
out.zeroCost = G.validate(zero).errors;
const badOverall = clone(); const o = badOverall.entries.find(e => e.suite === 'overall' && e.status === 'not_evaluated');
o.status = 'evaluated'; o.quality = { score: 70, interval: null };
out.badOverall = G.validate(badOverall).errors;
out.badOverallPlan = G.plotPlan(badOverall, G.rowsFor(badOverall, 'overall', null), 'cost').points.map(p => p.impl.id);
const unmarked = clone(); unmarked.implementations[0].label = 'Real-looking name';
out.unmarked = G.validate(unmarked).errors;
const scored = clone(); const ne = scored.entries.find(e => e.status === 'not_evaluated'); ne.quality = { score: 0 };
out.scoredUnevaluated = G.validate(scored).errors;
out.csv = G.toCSV(G.tableRows(data, G.rowsFor(data, 'content', null)));
out.csvInjection = G.toCSV([{ implementation: '=HYPERLINK("x")', placeholder: '' }]);
out.ticks = [G.fmtTick(0.01, 'cost'), G.fmtTick(1, 'cost'), G.fmtTick(0.001, 'p95'), G.fmtTick(2, 'p95')];
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def logic():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    res = subprocess.run([node, "-e", NODE_SCRIPT, str(LOGIC), str(SAMPLE)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_sample_passes_page_validation(logic):
    assert logic["validate"]["errors"] == []


def test_only_frozen_evaluated_entries_with_positive_axis_values_are_plotted(logic):
    data = load(SAMPLE)
    for key, view in logic["views"].items():
        assert view["rows"] == len(data["implementations"]), key
        assert len(view["points"]) + len(view["excluded"]) == view["rows"], key
        for p in view["points"]:
            assert p["frozen"] and p["status"] == "evaluated", (key, p)
            assert p["x"] > 0 and 0 <= p["y"] <= 100, (key, p)


def test_unevaluated_suites_are_listed_not_plotted(logic):
    view = logic["views"]["grounding|null|cost"]
    assert "self-b-large" not in {p["id"] for p in view["points"]}
    ex = {x["id"]: x for x in view["excluded"]}
    assert ex["self-b-large"]["status"] == "not_evaluated"
    assert "Not evaluated" in ex["self-b-large"]["reason"]


def test_overall_needs_all_six_suites(logic):
    overall = {p["id"] for p in logic["views"]["overall|null|cost"]["points"]}
    assert overall and not overall & {"self-b-small", "self-b-large", "regex-e", "self-c"}
    assert any("all six suites" in e or "these suites are not" in e for e in logic["badOverall"])
    assert not set(logic["badOverallPlan"]) & {"self-b-small", "self-b-large", "regex-e"}


def test_missing_cost_keeps_point_on_latency_axis_only(logic):
    cost = logic["views"]["content|null|cost"]
    p95 = logic["views"]["content|null|p95"]
    assert "self-b-small" in {x["id"] for x in cost["excluded"]}
    assert "self-b-small" in {p["id"] for p in p95["points"]}


def test_not_applicable_decision_bias_is_not_zero(logic):
    view = logic["views"]["bias|decision_bias|cost"]
    ex = {x["id"]: x for x in view["excluded"]}
    assert ex["managed-d"]["status"] == "not_applicable"
    assert "managed-d" not in {p["id"] for p in view["points"]}


def test_page_rejects_zero_cost_unmarked_placeholders_and_scored_gaps(logic):
    assert any("cost of exactly 0" in e for e in logic["zeroCost"])
    assert any("not marked PLACEHOLDER" in e for e in logic["unmarked"])
    assert any("carries a score" in e for e in logic["scoredUnevaluated"])


def test_lines_only_for_declared_sweeps(logic):
    data = load(SAMPLE)
    swept = {im["id"] for im in data["implementations"] if im.get("sweep")}
    for key, view in logic["views"].items():
        for line in view["sweeps"]:
            assert set(line) <= swept and len(line) >= 2, key


def test_csv_download(logic):
    header = logic["csv"].splitlines()[0].split(",")
    assert header[:2] == ["placeholder", "view"]
    assert "score" in header and "cost_usd_per_1000" in header and "p95_s" in header
    rows = logic["csv"].strip().splitlines()[1:]
    assert len(rows) == len(load(SAMPLE)["implementations"])
    assert all(r.startswith("PLACEHOLDER,") for r in rows)
    assert "'=HYPERLINK" in logic["csvInjection"]


def test_axis_ticks_are_clean(logic):
    assert logic["ticks"] == ["$0.01", "$1", "1 ms", "2 s"]


# ---------- evaluator output (benchmark/goldrails_bench/leaderboard.py) through the page's adapter ----------

ADAPTER_SCRIPT = r"""
const G = require(process.argv[1]);
const doc = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const run = (d) => {
  const data = G.normalise(d);
  const views = {};
  for (const v of G.VIEWS) {
    const rows = G.rowsFor(data, v.id, 'guardrail_fairness');
    const plan = G.plotPlan(data, rows, 'p95');
    views[v.id] = { rows: rows.length, points: plan.points.map(p => ({ id: p.impl.id, status: p.entry.status, y: p.y })),
                    excluded: plan.excluded.length };
  }
  return { converted: G.isEvaluatorDoc(d), validate: G.validate(data), views, split: data.benchmark.split,
           blockers: data.blockers, placeholder: data.placeholder };
};
const final = JSON.parse(JSON.stringify(doc)); final.mode = 'final'; final.valid_for_publication = true; final.publication_blockers = [];
console.log(JSON.stringify({ smoke: run(doc), final: run(final) }));
"""


def _run_adapter(doc: dict, tmp_path: Path) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    p = tmp_path / "evaluator.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    res = subprocess.run([node, "-e", ADAPTER_SCRIPT, str(LOGIC), str(p)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _subtask(score, recall, bpr, pos, neg, tp, fp, basis="fit_on_tuning_max_task_score"):
    return {"status": "evaluated", "threshold": {"threshold": 0.5, "basis": basis}, "task_score": score, "recall": recall,
            "benign_pass_rate": bpr, "conditional_task_score": score,
            "n": {"positive": pos, "negative": neg, "failed": 0, "no_decision": 0, "tp": tp, "fp": fp},
            "secondary": {"budget": 0.05, "status": "met", "held_out_recall": recall, "held_out_false_positive_rate": 0.02}}


def _arm(system, suite, score, itype, cost, complete=True):
    return {"arm_id": f"{system}|{suite}|cfg|abc", "system": system, "question_set": "qs", "config_hash": "cfg", "suite": suite,
            "model": system, "dataset": {"sha256": "abc" * 21 + "d"},
            "sample_sizes": {"records": 40, "report_rows": 40, "report_groups": 30},
            "subtasks": {"t": _subtask(score, 0.8, 0.9, 20, 20, 16, 2)},
            "suite_score": {"value": score, "complete": complete, "subtasks_in_mean": ["t"], "not_evaluated": [] if complete else ["u"],
                            "optional_not_evaluated": [], "coverage_note": None if complete else "incomplete: u not evaluated",
                            "ci": {"low": score - 3, "high": score + 3}},
            "cost": {"implementation_type": itype, "basis": "measured_usage_x_dated_tariff", "usd_per_1000": cost, "reason": None},
            "latency": {"p50_s": 0.2, "p95_s": 0.5, "throughput_per_s": None}}


def _synthetic_evaluator_doc() -> dict:
    suites = ("content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_info", "grounding")
    arms = [_arm("sys-a", s, 80.0 + i, "hosted_api", 0.03) for i, s in enumerate(suites)]
    arms += [_arm("sys-b", s, 70.0, "managed_service", 0.0 if s == "word_filters" else 0.2) for s in suites[:5]]
    arms.append(_arm("sys-b", "grounding", 60.0, "managed_service", 0.4, complete=False))
    overall = {"implementations": [
        {"implementation": "sys-a", "declared": True, "ranked": True, "overall_score": 82.5, "ci": {"low": 80.0, "high": 85.0},
         "usd_per_1000": 0.03, "p95_s": 0.5, "p50_s": 0.2,
         "suites": {s: {"status": "complete", "arm_id": f"sys-a|{s}|cfg|abc", "task_score": 80.0 + i} for i, s in enumerate(suites)}},
        {"implementation": "sys-b", "declared": True, "ranked": False, "overall_score": None, "not_ranked_reason": "grounding incomplete",
         "suites": {s: {"status": "incomplete" if s == "grounding" else "complete", "arm_id": f"sys-b|{s}|cfg|abc", "task_score": 70.0}
                    for s in suites}},
    ]}
    return {"schema": "goldrails-leaderboard/0.1", "label": "synthetic", "mode": "smoke", "valid_for_publication": False,
            "publication_blockers": ["SMOKE: synthetic"], "rules": {"intervals": "group bootstrap", "cost": "c", "latency": "l",
                                                                      "task_score": "ts", "overall": "ov"},
            "contract": {"version": "v1.0-draft", "status": "draft, not signed off", "fpr_budget": 0.05},
            "arms": arms, "suites": {s: {"declared_subtasks": ["t"], "bootstrap": {"ci": 0.95}} for s in suites},
            "overall": overall, "provenance": {"generated_at": "synthetic", "dataset_versions": ["abc" * 21 + "d"],
                                               "tariffs": {"as_of": "2026-09-23"}}}


def test_adapter_converts_evaluator_output(tmp_path):
    out = _run_adapter(_synthetic_evaluator_doc(), tmp_path)
    smoke, final = out["smoke"], out["final"]
    assert smoke["converted"] and smoke["validate"]["errors"] == []
    assert smoke["split"] == "tune" and smoke["blockers"] == ["SMOKE: synthetic"] and smoke["placeholder"] is False
    assert all(not v["points"] for v in smoke["views"].values()), "a smoke run must plot nothing"
    assert final["validate"]["errors"] == []
    assert {p["id"] for p in final["views"]["overall"]["points"]} == {"sys-a"}
    assert {p["id"] for p in final["views"]["grounding"]["points"]} == {"sys-a"}   # sys-b grounding incomplete
    assert {p["id"] for p in final["views"]["word_filters"]["points"]} == {"sys-a", "sys-b"}  # zero tariff still on p95


def test_adapter_accepts_the_real_evaluator_on_existing_ledgers(tmp_path):
    lb = pytest.importorskip("goldrails_bench.leaderboard")
    ledgers = sorted(str(p) for p in (REPO / "benchmark" / "results").glob("*.jsonl"))
    if not ledgers:
        pytest.skip("no ledgers")
    doc = lb.build(ledgers, mode="smoke", replicates=20)          # pure computation over saved ledgers; no model calls
    out = _run_adapter(doc, tmp_path)
    assert out["smoke"]["converted"], "evaluator schema changed; update leaderboard.js fromEvaluator"
    assert out["smoke"]["validate"]["errors"] == []
    assert all(not v["points"] for v in out["smoke"]["views"].values())
    for v in out["final"]["views"].values():
        assert all(p["status"] == "evaluated" for p in v["points"])
