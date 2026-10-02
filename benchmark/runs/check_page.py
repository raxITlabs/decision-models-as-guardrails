"""Release check: the results page says exactly what the frozen results say.

    uv run python benchmark/runs/check_page.py                                   # the first run (default)
    GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/check_page.py    # or --run second-benchmark

Reads the run's page data (``site_results.site_json``: ``site/leaderboard/results.json`` for the current run,
``site/leaderboard/runs/<run>.json`` for any other) and compares it with the frozen sources: the run's final
leaderboard, its freeze manifests, ``bias.json`` (and its three-part view ``bias-parts.json`` with the row audit
``bias-audit.json``); for the first run also the corrected five-category view and ``CORRECTIONS.md``, and for a later
run the first run's leaderboard and the ledgers behind the page's account of what changed. No model calls. Writes
``benchmark/results/<run>/page-check.json`` and exits non-zero if any check fails.

The order checks date files by git. Files committed before 2 October 2026, when this repository stopped being an
export of a private working repository, are dated by that private history through
``benchmark/history/private-history.json`` (see ``private_history.py``), and only while their bytes are unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_context as RC  # noqa: E402
from private_history import History  # noqa: E402
import site_results  # noqa: E402
from site_results import IMPL, OVERALL_ID  # noqa: E402  the converter's own system-to-page id table
ALL_MANIFESTS = ("freeze-manifest.json", "freeze-extension-1.json", "freeze-extension-2.json", "freeze-extension-3.json",
                 "freeze-extension-4.json")


def setup(run: str) -> None:
    """Point the checks at one run: its results, its manifests and its page data."""
    global CTX, RES, SUB, SITE, MANIFESTS
    CTX = RC.RunContext(RC.check_run_id(run), RC.check_run_id(run))
    RES, SUB, SITE = CTX.results, CTX.frozen_subsets, site_results.site_json(run)
    # the first run has all five manifests; a later run has no extension 2 (run.json explains why)
    MANIFESTS = ALL_MANIFESTS if CTX.is_first else tuple(m for m in ALL_MANIFESTS if (SUB / m).exists())


setup(RC.current().run)
CORE = ("content", "prompt_attacks", "word_filters", "sensitive_info", "grounding")
SITE_SUITE = {"sensitive_info": "sensitive_information"}
TOL = 1e-3   # the page rounds scores to 4 places and costs to 5

checks: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"check": name, "ok": bool(ok), "detail": detail})


def close(a, b, tol=TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def page_id(system: str) -> str:
    return OVERALL_ID.get(system) or IMPL[system][0]


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False).stdout.strip()


# Commit dates of the frozen files: this repository's git, or for files from before 2 October 2026 the archived private
# history's record (benchmark/runs/private_history.py says when each applies).
H = History(REPO)


PARTS = ["Hate and discrimination detection", "Guardrail fairness diagnostics", "Decision-model bias diagnostics"]
B1_CELL = ("benign", "harmful", "benign_failed", "harmful_failed", "label_unknown", "false_positives", "false_negatives",
           "fpr", "fpr_numerator", "fpr_denominator", "fpr_interval", "fnr", "fnr_numerator", "fnr_denominator",
           "fnr_interval")
B2_COPIED = ("flip_rate", "flip_rate_interval", "paired_correct_rate", "paired_correct_interval",
             "paired_correctness_denominator", "consistent_wrong_rate", "by_expected", "quality", "counts")
# Affirmative forms of the brief's "claims to avoid"; a negated statement ("does not show equal treatment") passes.
CLAIMS = re.compile(r"fairness (score|percentage)|bias-free|free of bias|\bunbiased\b|treats? (all )?groups equally|"
                    r"(?<!not )(?<!n't )\b(proves?|shows?|establish(es)?) equal treatment|general-purpose bias detector",
                    re.I)


def _iv_eq(page, src) -> bool:
    """A page interval (low, high, level) against the bias-parts interval it was copied from."""
    if not page or not src or src.get("low") is None:
        return not page and (not src or src.get("low") is None)
    return page["low"] == src["low"] and page["high"] == src["high"] and page["level"] == src["level"]


def bias_parts_checks(site: dict, lb: dict, bias: dict) -> None:
    bp_path, au_path = RES / "bias-parts.json", RES / "bias-audit.json"
    if not (bp_path.exists() and au_path.exists()):
        check("bias-parts.json and bias-audit.json exist", False, "missing")
        return
    bp, au = load(bp_path), load(au_path)

    # 11a. bias-parts.json is built from this bias.json, and every value it copies equals bias.json.
    bad = []
    if bp["meta"]["source_sha256"] != hashlib.sha256((RES / "bias.json").read_bytes()).hexdigest():
        bad.append("bias.json sha256 differs from meta.source_sha256")
    ms = bias["guardrail_fairness"]["min_support"]
    src = {s["system"]: s for s in bias["guardrail_fairness"]["systems"]}
    if {s["system"] for s in bp["guardrail_fairness"]["systems"]} != set(src):
        bad.append("fairness systems differ")
    for s in bp["guardrail_fairness"]["systems"]:
        o = src.get(s["system"])
        if o is None:
            continue
        name = s["system"]
        if s["threshold"] != o["threshold"] or s["config_hash"] != o["config_hash"]:
            bad.append(f"{name}: threshold or config")
        if any(s["B1"]["overall"][k] != o["B1"]["overall"][k] for k in B1_CELL + ("rows_without_annotation",)) \
                or s["B1"]["quality"] != o["B1"]["quality"]:
            bad.append(f"{name}: B1 overall")
        ids = {g["identity"]: g for g in o["B1"]["identities"]}
        if [g["identity"] for g in s["B1"]["identities"]] != list(ids):
            bad.append(f"{name}: B1 identities")
        for g in s["B1"]["identities"]:
            h = ids.get(g["identity"]) or {}
            for side in ("mentioned", "not_mentioned"):
                c, d = g[side], h.get(side) or {}
                if any(c.get(k) != d.get(k) for k in B1_CELL) or c["n_benign"] != d.get("fpr_denominator") \
                        or c["n_harmful"] != d.get("fnr_denominator"):
                    bad.append(f"{name}/{g['identity']}: {side}")
            small = any(g[side][k] < ms for side in ("mentioned", "not_mentioned") for k in ("n_benign", "n_harmful"))
            if g["fpr_gap_vs_not_mentioned"] != h.get("fpr_gap") or g["fnr_gap_vs_not_mentioned"] != h.get("fnr_gap") \
                    or g["low_support"] != h.get("low_support") or g["unknown_annotation"] != h.get("unknown_annotation") \
                    or g["insufficient_evidence"] != (h.get("low_support") or small):
                bad.append(f"{name}/{g['identity']}: gap or flag")
        b2, q = s["B2"], o["B2"]
        pairs = {"flip_rate": b2["consistency"]["flip_rate"], "flip_rate_interval": b2["consistency"]["flip_rate_interval"],
                 "paired_correct_rate": b2["correctness"]["paired_correct_rate"],
                 "paired_correct_interval": b2["correctness"]["paired_correct_interval"],
                 "paired_correctness_denominator": b2["correctness"]["paired_correctness_denominator"],
                 "consistent_wrong_rate": b2["correctness"]["consistent_wrong_rate"],
                 "by_expected": b2["by_expected"], "quality": b2["quality"], "counts": b2["counts"]}
        if any(pairs[k] != q[k] for k in B2_COPIED) or b2["too_few_pairs"] != (q["counts"]["evaluable"] < ms) \
                or b2["consistency"]["flips"] != q["counts"]["flips"] or b2["correctness"]["all_wrong"] != q["counts"]["all_wrong"]:
            bad.append(f"{name}: B2")
    dsrc: dict = {}
    for e in bias["decision_bias"]["systems"]:
        dsrc.setdefault(e["system"], []).append(e)
    if {s["system"] for s in bp["decision_model_bias"]["systems"]} != set(dsrc):
        bad.append("decision-model systems differ")
    for s in bp["decision_model_bias"]["systems"]:
        es = dsrc.get(s["system"], [])
        if s["status"] == "not_applicable":
            na = next((e for e in es if e["status"] == "not_applicable"), None)
            if na is None or s["reason"] != na["reason"] or "result" in s["bbq"] or "result" in s["discrim_eval"]:
                bad.append(f"{s['system']}: not applicable")
            continue
        for track in ("bbq", "discrim_eval"):
            e = next((x for x in es if track in x), None)
            if e is None or s[track]["result"] != e[track] or s[track]["config_hash"] != e["config_hash"]:
                bad.append(f"{s['system']}: {track}")
    check("bias-parts.json is built from this bias.json (sha256) and every copied number equals bias.json", not bad,
          "; ".join(bad[:8]) or f"{len(bp['guardrail_fairness']['systems'])} fairness systems x 24 identities, "
                                f"{len(bp['decision_model_bias']['systems'])} decision-model systems")

    # 11b. The page's three-part block copies bias-parts.json and the audit's row counts.
    pp = site.get("bias_parts") or {}
    bad = []
    fair = {s["system"]: s for s in bp["guardrail_fairness"]["systems"]}
    page_fair = (pp.get("guardrail_fairness") or {}).get("systems") or []
    if {s["system"] for s in page_fair} != set(fair):
        bad.append("fairness systems differ")
    for s in page_fair:
        f = fair.get(s["system"])
        if f is None:
            continue
        o, b1 = f["B1"]["overall"], s["b1"]
        if s["implementation"] != page_id(s["system"]) or s["threshold"] != f["threshold"]:
            bad.append(f"{s['system']}: id or threshold")
        if (b1["n_benign"], b1["n_harmful"], b1["fpr"], b1["fnr"], b1["false_positives"], b1["false_negatives"],
                b1["balanced_accuracy"]) != (o["n_benign"], o["n_harmful"], o["fpr"], o["fnr"], o["fpr_numerator"],
                                             o["fnr_numerator"], f["B1"]["quality"]["balanced_accuracy"]) \
                or not _iv_eq(b1["fpr_interval"], o["fpr_interval"]) or not _iv_eq(b1["fnr_interval"], o["fnr_interval"]):
            bad.append(f"{s['system']}: B1 overall")
        idn = {g["identity"]: g for g in f["B1"]["identities"]}
        with_rows = [g for g in f["B1"]["identities"] if g["mentioned"]["benign"] + g["mentioned"]["harmful"]]
        if [g["identity"] for g in b1["groups"]] != [g["identity"] for g in with_rows] \
                or sorted(b1["identities_without_rows"]) != sorted(set(idn) - {g["identity"] for g in with_rows}) \
                or b1["identities"] != len(idn) \
                or b1["groups_sufficient"] != sum(not g["insufficient_evidence"] for g in with_rows):
            bad.append(f"{s['system']}: B1 group list")
        for g in b1["groups"]:
            h = idn.get(g["identity"]) or {}
            m, n = h.get("mentioned") or {}, h.get("not_mentioned") or {}
            fg, ng = h.get("fpr_gap_vs_not_mentioned") or {}, h.get("fnr_gap_vs_not_mentioned") or {}
            if (g["n_benign"], g["n_harmful"], g["fpr"], g["fnr"], g["comparison_n_benign"], g["comparison_n_harmful"],
                    g["fpr_gap"], g["fnr_gap"], g["insufficient_evidence"], g["reasons"]) != (
                    m.get("n_benign"), m.get("n_harmful"), m.get("fpr"), m.get("fnr"), n.get("n_benign"),
                    n.get("n_harmful"), fg.get("value"), ng.get("value"), h.get("insufficient_evidence"),
                    h.get("insufficient_evidence_reasons")) \
                    or not all(_iv_eq(g[a], b) for a, b in (("fpr_interval", m.get("fpr_interval")),
                                                            ("fnr_interval", m.get("fnr_interval")),
                                                            ("fpr_gap_interval", fg.get("interval")),
                                                            ("fnr_gap_interval", ng.get("interval")))):
                bad.append(f"{s['system']}/{g['identity']}")
        c, k, p = f["B2"]["consistency"], f["B2"]["correctness"], s["b2"]
        if (p["pairs"], p["evaluable"], p["flips"], p["flip_rate"], p["all_correct"], p["all_wrong"],
                p["paired_correct_rate"], p["consistent_wrong_rate"], p["too_few_pairs"]) != (
                f["B2"]["n_pairs"], f["B2"]["n_pairs_evaluable"], c["flips"], c["flip_rate"], k["all_correct"],
                k["all_wrong"], k["paired_correct_rate"], k["consistent_wrong_rate"], f["B2"]["too_few_pairs"]) \
                or not _iv_eq(p["flip_rate_interval"], c["flip_rate_interval"]) \
                or not _iv_eq(p["paired_correct_interval"], k["paired_correct_interval"]):
            bad.append(f"{s['system']}: B2 consistency or correctness")
    dec = {s["system"]: s for s in bp["decision_model_bias"]["systems"]}
    page_dec = (pp.get("decision_model_bias") or {}).get("systems") or []
    if {s["system"] for s in page_dec} != set(dec):
        bad.append("decision-model systems differ")
    for s in page_dec:
        d = dec.get(s["system"])
        if d is None or s["status"] != d["status"]:
            bad.append(f"{s['system']}: status"); continue
        if s["status"] != "evaluated":
            continue
        cats, pb = d["bbq"]["result"]["categories"], s["bbq"]
        for key, cond in (("ambig", "ambiguous"), ("disambig", "disambiguated")):
            n = sum(c[key]["n"] for c in cats.values() if key in c)
            ok = sum(c[key]["correct"] for c in cats.values() if key in c)
            if (pb[cond]["n"], pb[cond]["correct"]) != (n, ok) or not close(pb[cond]["accuracy"], ok / n, 1e-12):
                bad.append(f"{s['system']}: BBQ {cond}")
        for x in pb["categories"]:
            c = cats.get(x["category"]) or {}
            dis = c.get("disambig") or {}
            if (x["ambiguous_n"], x["disambiguated_n"], x["disambiguated_accuracy"], x["disambiguated_bias_score"]) != (
                    (c.get("ambig") or {}).get("n", 0), dis.get("n", 0), dis.get("accuracy"), dis.get("bias_score")) \
                    or not _iv_eq(x["disambiguated_bias_score_interval"], dis.get("bias_score_interval")):
                bad.append(f"{s['system']}/{x['category']}: BBQ cell")
        de, pd = d["discrim_eval"], s["discrim_eval"]
        if (pd["n"], pd["mean_p_yes"], pd["insufficient_evidence"], pd["isolates_demographic_bias"]) != (
                de["result"]["n"], de["result"]["mean_p_yes"], de["insufficient_evidence"], de["isolates_demographic_bias"]) \
                or pd["group_gaps_shown"] is not False or "comparisons" in json.dumps(pd):
            bad.append(f"{s['system']}: discrim-eval")
    audit = {t["id"]: t for t in au["tasks"]}
    ht = audit["content:hate"]["test_rows"]
    h = pp.get("hate_detection") or {}
    harmful = sum(x["n"] for x in h.get("harmful_by_source") or [])
    jbb = sum(x["n"] for x in h.get("harmful_by_source") or [] if x["source"] == "jailbreakbench")
    content_rows = next((q["test_cases"] for q in site.get("data_quality") or [] if q["suite"] == "content"), None)
    if not (h.get("separate_score") is None and "separate_score" in h
            and h.get("content_test_rows") == ht["content_suite_total"] == content_rows
            and h.get("harmful_with_hate_source_label") == ht["totals"]["harmful_with_identity_hate_source_label"] == harmful - jbb
            and h.get("harmful_including_jailbreakbench") == ht["totals"]["harmful_including_jbb_harassment_discrimination"] == harmful
            and h.get("benign_same_topic") == ht["totals"]["benign_hate_adjacent_rows"]
            == sum(x["n"] for x in h.get("benign_by_source") or [])):
        bad.append("hate detection row counts")
    check("the page's three parts copy bias-parts.json and the audit's row counts (hate rows once, in content; no "
          "separate hate score; discrim-eval shows no group gap)", not bad,
          "; ".join(bad[:8]) or f"{len(page_fair)} fairness systems, {len(page_dec)} decision-model systems, "
                                f"{harmful} harmful and {h.get('benign_same_topic')} benign hate rows of {content_rows}")

    # 11c. The three part names, and no generic "Bias" section heading.
    page = (REPO / "site/leaderboard/index.html").read_text(encoding="utf-8")
    named = (pp.get("parts") == PARTS == bp["parts"] == au["parts"]
             and [(pp.get(k) or {}).get("part") for k in ("hate_detection", "guardrail_fairness", "decision_model_bias")] == PARTS)
    renders = all(x in page for x in ("state.data.bias_parts", "<h3>${esc(h.part)}</h3>", "<h3>${esc(f.part)}</h3>",
                                      "<h3>${esc(d.part)}</h3>"))
    generic = re.findall(r"<h[1-6][^>]*>\s*Bias\b[^<]*", page) + [x for x in ("Bias, reported separately", "Bias, exploratory")
                                                                 if x in page]
    check("the page names the three parts and has no generic \"Bias\" section heading", named and renders and not generic,
          "; ".join(generic) or " / ".join(PARTS))

    # 11d. Bedrock is not applicable in decision-model bias, never scored as zero.
    br = [s for s in page_dec if s["implementation"] == "bedrock"]
    old = [e for e in site["entries"] if e["implementation"] == "bedrock" and e["suite"] == "bias" and e.get("track") == "decision_bias"]
    ok = (len(br) == 1 and br[0]["status"] == "not_applicable" and br[0].get("reason")
          and "bbq" not in br[0] and "discrim_eval" not in br[0]
          and all(e["status"] == "not_applicable" and not (e.get("quality") or {}).get("score") for e in old)
          and all(e["status"] == "not_applicable" for e in bias["decision_bias"]["systems"] if e["system"] == "bedrock-checks"))
    check("Bedrock is not applicable in decision-model bias, with its reason and no score", bool(ok),
          br[0].get("reason", "") if br else "no Bedrock row")

    # 11e. The six-category overall is unchanged and holds no bias part; no number combines the three parts.
    bad = []
    frozen_ov = {page_id(i["implementation"]): i for i in lb["overall"]["implementations"] if i.get("ranked")}
    six = {SITE_SUITE.get(s, s) for s in ("content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_info",
                                          "grounding")}
    for e in (x for x in site["entries"] if x["suite"] == "overall" and x["status"] == "evaluated"):
        f = frozen_ov.get(e["implementation"])
        if f is None or not close(e["quality"]["score"], f["overall_score"]) or set(e.get("suites") or {}) != six:
            bad.append(e["implementation"])
    comb = pp.get("combination") or {}
    if comb.get("single_number", "missing") is not None or any(isinstance(v, (int, float)) for v in comb.values()) \
            or any(k in pp for k in ("score", "aggregate", "overall")):
        bad.append("bias_parts carries a combined number")
    check("overall score unchanged: the frozen six-category overall, with no bias part inside and no combined number",
          not bad and len(frozen_ov) == sum(1 for x in site["entries"] if x["suite"] == "overall" and x["status"] == "evaluated"),
          "; ".join(bad) or f"{len(frozen_ov)} overall entries")

    # 11f. None of the brief's claims to avoid is made on the page or in its data.
    hits = sorted({m.group(0) for t in (json.dumps(site), page) for m in CLAIMS.finditer(t)})
    check("no claim the brief says to avoid (fairness percentage, bias-free, proven equal treatment, general bias "
          "detector)", not hits, ", ".join(hits) or "none")


# --- a later run --------------------------------------------------------------------------------------------------

TEST_LEDGERS = ("test.jsonl", "test-bias.jsonl", "ext-test.jsonl", "ext-test-bias.jsonl", "pii-v12-test.jsonl",
                "prof-v13-test.jsonl")


def _added(path: str) -> tuple[int, str] | None:
    """(commit time, short hash) of the commit that added a file."""
    out = H.log(path, added=True).splitlines()
    return (int(out[-1].split()[0]), out[-1].split()[1]) if out else None


def freeze_order_check(lb: dict) -> None:
    """A later run froze everything at once: every file in benchmark/subsets/<run>/ (manifests, selections, the run
    declaration) was committed, once and never rewritten, before any file in benchmark/results/<run>/, and before the
    earliest test attempt in any of its test ledgers."""
    from datetime import datetime
    subs = git("ls-files", RC.rel(SUB)).splitlines()
    ress = [f for f in git("ls-files", RC.rel(RES)).splitlines() if f.endswith(".jsonl")]
    bad = []
    sub_t = {f: _added(f) for f in subs}
    res_t = {f: _added(f) for f in ress}
    rewritten = [f for f in subs if len(H.log(f, fmt="%h").splitlines()) != 1]
    first_test = min(a["at"] for n in TEST_LEDGERS if (RES / n).exists()
                     for line in (RES / n).open(encoding="utf-8") if line.strip() for a in json.loads(line)["attempts"])
    first_test_t = datetime.fromisoformat(first_test.replace("Z", "+00:00")).timestamp()
    last_sub = max(sub_t.values()) if sub_t and all(sub_t.values()) else None
    first_res = min(res_t.values()) if res_t and all(res_t.values()) else None
    if not last_sub or not first_res or last_sub[0] >= first_res[0]:
        bad.append(f"last subsets commit {last_sub} not before first results commit {first_res}")
    if last_sub and last_sub[0] >= first_test_t:
        bad.append(f"last subsets commit {last_sub} not before the first test attempt {first_test}")
    if rewritten:
        bad.append("rewritten after first commit: " + ", ".join(rewritten))
    if not all(m in [Path(f).name for f in subs] for m in MANIFESTS) or len(MANIFESTS) < 4:
        bad.append(f"manifests {MANIFESTS}")
    if lb["freeze_manifest"]["records"]["earliest_test_attempt"] != first_test:
        bad.append(f"leaderboard's earliest test attempt {lb['freeze_manifest']['records']['earliest_test_attempt']} vs ledgers {first_test}")
    if H.stale(subs + ress):
        bad.append("changed since the private history record: " + ", ".join(H.stale(subs + ress)))
    check(f"every file in {RC.rel(SUB)} committed once, before any ledger in {RC.rel(RES)} and before the first test call",
          not bad, "; ".join(bad) or f"{len(subs)} frozen files, last at {last_sub[1]}; {len(ress)} ledgers, first at "
                                    f"{first_res[1]}; first test call {first_test}" + H.note(subs + ress))


def _grounding(run: str, ledgers: tuple) -> dict:
    """{row id: (max decision probability, expected)} for Jev on grounding; a later ledger's row replaces an earlier one."""
    out = {}
    for n in ledgers:
        p = RC.RESULTS / run / n
        for line in (p.open(encoding="utf-8") if p.exists() else []):
            d = json.loads(line)
            if d["system"] == "jev-1.13.0" and d["question_set"] == "v1-f6-grounding" and d["ok"]:
                out[d["id"]] = (max(d["answers"][k]["noul"] for k in d["decision_keys"]), d["expected"])
    return out


def _score(rows: dict, t: float) -> tuple[float, float]:
    """(task score, false-positive rate) at threshold t; a score at or above t flags."""
    pos = [v for v, e in rows.values() if e == "yes"]
    neg = [v for v, e in rows.values() if e == "no"]
    fpr = sum(v >= t for v in neg) / len(neg)
    return 100 * 0.5 * (sum(v >= t for v in pos) / len(pos) + 1 - fpr), fpr


def run_checks(site: dict, lb: dict) -> None:
    """The run block: this run's and the first run's publication status, the changes, and the Jev grounding account."""
    from site_results import f1
    r = site.get("run") or {}
    first = load(RC.RESULTS / RC.FIRST / "leaderboard-final.json")
    prev = r.get("previous") or {}
    linked = site_results.SITE_DIR / (prev.get("results") or "missing.json")
    ok = (r.get("id") == CTX.run and r.get("valid_for_publication") is lb["valid_for_publication"]
          and r.get("publication_blockers") == lb["publication_blockers"]
          and prev.get("valid_for_publication") is first["valid_for_publication"]
          and prev.get("publication_blockers") == first["publication_blockers"]
          and all(b in prev.get("status", "") for b in first["publication_blockers"])
          and ("is not valid for publication" in prev.get("status", "")) == (not first["valid_for_publication"])
          and ("valid for publication, with no blockers" in r.get("summary", "") + site.get("notice", ""))
          == (lb["valid_for_publication"] and not lb["publication_blockers"])
          and linked.exists() and site_results.RUN_LABEL[RC.FIRST] in load(linked)["benchmark"]["name"])
    check("the page names this run, links the first run's results, and states each run's publication status and "
          "blockers as its evaluator does", ok,
          f"this run valid {lb['valid_for_publication']} ({len(lb['publication_blockers'])} blockers); first run valid "
          f"{first['valid_for_publication']} ({len(first['publication_blockers'])} blockers); {RC.rel(linked)}")

    # every structured value in the changes equals the two leaderboards, and the text shows it
    ch = {c["id"]: c for c in r.get("changes") or []}
    bad = []
    ov = lambda d: {i["implementation"]: i["overall_score"] for i in d["overall"]["implementations"]}
    o1, o2 = ov(first), ov(lb)
    names = {v: k for k, v in site_results.NAME.items()}
    for name, v in (ch.get("overall") or {}).get("values", {}).items():
        n = names[name]
        if not (close(v["first"], o1[n], 1e-4) and close(v["second"], o2[n], 1e-4)):
            bad.append(f"overall {name}")
    for n in ("jev-1.13.0", "bedrock-guardrails"):
        if f"{f1(o1[n])} to {f1(o2[n])}" not in (ch.get("overall") or {}).get("text", ""):
            bad.append(f"overall text {n}")
    arm = lambda d, sy, su: next(a for a in d["arms"] if a["system"] == sy and a["suite"] == su)
    g = ch.get("jev-grounding") or {}
    g1, g2 = arm(first, "jev-1.13.0", "grounding"), arm(lb, "jev-1.13.0", "grounding")
    thr = lambda a: a["subtasks"]["grounding"]["threshold"]["threshold"]
    if not (g.get("first") == g1["suite_score"]["value"] and g.get("second") == g2["suite_score"]["value"]
            and g.get("first_threshold") == thr(g1) and g.get("second_threshold") == thr(g2)):
        bad.append("grounding values")
    qs = (ch.get("content-question-sets") or {}).get("question_sets") or {}
    for label, sy in (("Jev", "jev-1.13.0"), ("Bedrock", "bedrock-checks")):
        if qs.get(label) != {"first": arm(first, sy, "content")["question_set"], "second": arm(lb, sy, "content")["question_set"]}:
            bad.append(f"content question set {label}")
    same = [n for n in o2 if n not in ("jev-1.13.0", "bedrock-guardrails")]
    for n in same:
        i1 = next(i for i in first["overall"]["implementations"] if i["implementation"] == n)
        i2 = next(i for i in lb["overall"]["implementations"] if i["implementation"] == n)
        if any(i1["suites"][s]["task_score"] != i2["suites"][s]["task_score"] for s in i2["suites"]):
            bad.append(f"{n} said unchanged but differs")
    check("every before-and-after value in the run block equals the two final leaderboards", not bad,
          "; ".join(bad) or f"{len(ch)} changes; {len(same)} self-hosted models unchanged in every category")

    # the Jev grounding account, recomputed from the ledgers: this method reproduces both frozen scores first
    t1, t2 = thr(g1), thr(g2)
    a1 = _grounding(RC.FIRST, ("test.jsonl", "test-rerun.jsonl"))
    a2, tune2 = _grounding(CTX.run, ("test.jsonl",)), _grounding(CTX.run, ("tune.jsonl",))
    at_first, _ = _score(a2, t1)
    tie1, fpr1 = _score(tune2, t1)
    tie2, fpr2 = _score(tune2, t2)
    text = g.get("text", "")
    ok = (close(_score(a1, t1)[0], g1["suite_score"]["value"], 1e-9) and close(_score(a2, t2)[0], g2["suite_score"]["value"], 1e-9)
          and close(at_first, g.get("at_first_threshold"), 1e-9) and close(tie1, tie2, 1e-9)
          and close(tie1, g.get("tuning_tie"), 1e-9) and close(fpr1, g.get("tuning_fpr_at_first_threshold"), 1e-9)
          and fpr2 == 0 and fpr1 > fpr2
          and all(x in text for x in (f1(at_first), f1(g1["suite_score"]["value"] - at_first),
                                      f1(at_first - g2["suite_score"]["value"]), f1(tie1), str(t1), str(t2))))
    check("the Jev grounding account recomputes from the ledgers (API drift at the first run's threshold, tuning tie, "
          "tie-break by tuning false-positive rate)", ok,
          f"{f1(g1['suite_score']['value'])} at {t1}; this run's answers {at_first:.3f} at {t1}, {_score(a2, t2)[0]:.3f} at "
          f"{t2}; tuning {tie1:.1f} at both, FPR {fpr1:.2f} vs {fpr2:.2f}; {len(set(a1) & set(a2))} common test rows, "
          f"{sum(1 for i in set(a1) & set(a2) if a1[i][0] != a2[i][0])} with different answers")

    # Kev 0.8B: the first run's hung calls, as the cost change says
    hung = [a["latency_s"] for line in (RC.RESULTS / RC.FIRST / "test.jsonl").open(encoding="utf-8")
            for d in [json.loads(line)] if d["system"] == "kev-0-8b" and d["question_set"] in ("v1-f2-attacks", "v1-f4-words")
            for a in d["attempts"] if not a["ok"]]
    t = (ch.get("self-hosted-cost") or {}).get("text", "")
    check("the Kev 0.8B cost account matches the first run's ledger (failed calls, each over a minute)",
          bool(hung) and min(hung) > 60 and f"{len(hung)} of its calls hung for over a minute" in t,
          f"{len(hung)} failed calls, {min(hung) if hung else 0:.1f} to {max(hung) if hung else 0:.1f} s")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", help="benchmark run id (default: GOLDRAILS_RUN, else first-benchmark)")
    args = ap.parse_args(argv)
    if args.run:
        setup(args.run)
    pick = next(p for p in (RES / "leaderboard-final.json", RES / "leaderboard-v1.3.json", RES / "leaderboard-v1.2.json",
                            RES / "leaderboard-provisional.json") if p.exists())
    v13 = pick.name == "leaderboard-v1.3.json" or "v1_3" in (load(pick).get("provenance") or {})   # Civil Comments profanity
    v12 = v13 or pick.name == "leaderboard-v1.2.json"   # PII replaced; the corrected view's PII arms are the old source
    site, lb = load(SITE), load(pick)
    corrected = load(RES / "leaderboard-corrected.json") if CTX.is_first else None
    bias = load(RES / "bias.json")["bias"]
    site_impl = {i["id"]: i for i in site["implementations"]}
    by_hash = {}
    for e in site["entries"]:
        if (e.get("ledger") or {}).get("config_hash"):
            by_hash.setdefault(e["ledger"]["config_hash"], []).append(e)

    # 1. Every frozen arm is on the page once, with its score, interval, cost, sample and threshold.
    bad = []
    for a in lb["arms"]:
        es = [e for e in by_hash.get(a["config_hash"], []) if e["ledger"]["dataset_sha256"] == a["dataset"]["sha256"]]
        if len(es) != 1:
            bad.append(f"{a['arm_id']}: {len(es)} page entries")
            continue
        e, ss = es[0], a["suite_score"]
        ci = ss.get("ci") or {}
        pi = (e["quality"] or {}).get("interval") or {}
        thr = [v["threshold"]["threshold"] for v in a["subtasks"].values()
               if v["status"] == "evaluated" and (v.get("threshold") or {}).get("threshold") is not None]
        problems = [k for k, ok in (
            ("score", close(e["quality"]["score"], ss["value"])),
            ("interval", close(pi.get("low"), ci.get("low")) and close(pi.get("high"), ci.get("high"))),
            ("cost", close(e["cost"]["usd_per_1000"], a["cost"].get("usd_per_1000"), 1e-5)),
            ("rows", e["sample"]["total"] == a["sample_sizes"]["report_rows"]),
            ("threshold", (len(thr) != 1) or close(e["threshold"]["value"], thr[0], 1e-4)),
            ("status", e["status"] == "evaluated"),
        ) if not ok]
        if problems:
            bad.append(f"{a['arm_id']}: {', '.join(problems)}")
    check("every frozen arm appears once with matching score, interval, cost, rows and threshold",
          not bad, "; ".join(bad) or f"{len(lb['arms'])} arms")

    # 2. Thresholds used are the committed freeze manifests' thresholds, and the manifests are unchanged in git.
    frozen, sha_ok, dirty = {}, [], []
    for name in MANIFESTS:
        p = SUB / name
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        sha_ok.append(sha)
        if git("status", "--porcelain", str(p.relative_to(REPO))):
            dirty.append(name)
        for arm in load(p)["arms"]:
            frozen[(arm["config_hash"], arm["dataset_sha256"])] = (arm["thresholds"], sha)
    bad = []
    for a in lb["arms"]:
        f = frozen.get((a["config_hash"], a["dataset"]["sha256"]))
        if f is None:
            bad.append(f"{a['arm_id']}: not in any freeze manifest")
            continue
        thresholds, sha = f
        if (a.get("freeze") or {}).get("manifest_sha256") != sha:
            bad.append(f"{a['arm_id']}: freeze sha differs")
        for sub, v in a["subtasks"].items():
            t = (v.get("threshold") or {}).get("threshold")
            if t is not None and sub in thresholds and not close(t, thresholds[sub].get("threshold"), 1e-6):   # stored to 6 places
                bad.append(f"{a['arm_id']}/{sub}: {t} vs frozen {thresholds[sub].get('threshold')}")
    check("every arm used its freeze manifest's thresholds", not bad, "; ".join(bad) or f"{len(frozen)} frozen arms")
    check("freeze manifests are committed and unchanged", not dirty, ", ".join(dirty) or ", ".join(s[:12] for s in sha_ok))

    # 3. Extension manifests were committed before their test ledgers (a later run: every manifest before any ledger).
    if not CTX.is_first:
        freeze_order_check(lb)
    else:
        order = []
        for manifest, ledger in (("freeze-extension-1.json", "ext-test.jsonl"), ("freeze-extension-2.json", "ext-test.jsonl")):
            m = H.log(f"benchmark/subsets/first-benchmark/{manifest}", added=True).splitlines()
            rows = H.log(f"benchmark/results/first-benchmark/{ledger}", reverse=True).splitlines()
            order.append((manifest, m[-1] if m else None, rows))
        bad = []
        ext1 = order[0][1]
        first_ext_test = order[0][2][0] if order[0][2] else None
        if not ext1 or not first_ext_test or int(ext1.split()[0]) > int(first_ext_test.split()[0]):
            bad.append(f"extension 1 {ext1} not before first ext-test commit {first_ext_test}")
        ext2 = order[1][1]
        later = [r for r in order[1][2] if ext2 and int(r.split()[0]) > int(ext2.split()[0])]
        if not ext2 or not later:
            bad.append(f"extension 2 {ext2}: no ext-test commit after it (Bedrock rows)")
        if (SUB / "freeze-extension-3.json").exists():
            m3 = H.log("benchmark/subsets/first-benchmark/freeze-extension-3.json", added=True).splitlines()
            t3 = H.log("benchmark/results/first-benchmark/pii-v12-test.jsonl", added=True).splitlines()
            if not m3 or not t3 or int(m3[-1].split()[0]) > int(t3[-1].split()[0]):
                bad.append(f"extension 3 {m3[-1] if m3 else None} not before the PII test ledger {t3[-1] if t3 else None}")
        if (SUB / "freeze-extension-4.json").exists():
            m4 = H.log("benchmark/subsets/first-benchmark/freeze-extension-4.json", added=True).splitlines()
            t4 = H.log("benchmark/results/first-benchmark/prof-v13-test.jsonl", added=True).splitlines()
            if not m4 or not t4 or int(m4[-1].split()[0]) > int(t4[-1].split()[0]):
                bad.append(f"extension 4 {m4[-1] if m4 else None} not before the profanity test ledger {t4[-1] if t4 else None}")
        dated = [f"benchmark/subsets/first-benchmark/{m}" for m in ("freeze-extension-1.json", "freeze-extension-2.json",
                                                                    "freeze-extension-3.json", "freeze-extension-4.json")] + \
            [f"benchmark/results/first-benchmark/{t}" for t in ("ext-test.jsonl", "pii-v12-test.jsonl", "prof-v13-test.jsonl")]
        if H.stale(dated):
            bad.append("changed since the private history record: " + ", ".join(H.stale(dated)))
        check("extension manifests committed before the test rows they govern", not bad,
              "; ".join(bad) or f"ext1 {ext1.split()[1]} before {first_ext_test.split()[1]}; ext2 {ext2.split()[1]} before {later[0].split()[1]}"
              + H.note(dated))

    # 3b. v1.3: the implementations file that changed the profanity question set predates every profanity call.
    if v13:
        from datetime import datetime, timezone
        impl = "benchmark/subsets/first-benchmark/implementations-v1.3.json"
        ct = H.log(impl, added=True).split()
        first = min(a["at"] for n in ("prof-v13-tune", "prof-v13-test") for line in (RES / f"{n}.jsonl").open(encoding="utf-8")
                    for a in json.loads(line)["attempts"])
        first_t = datetime.fromisoformat(first.replace("Z", "+00:00")).timestamp()
        check("implementations-v1.3 committed before the first profanity call (tuning or test)",
              bool(ct) and int(ct[0]) < first_t and not H.stale([impl]),
              f"{ct[1] if ct else None} at {datetime.fromtimestamp(int(ct[0]), timezone.utc).isoformat() if ct else None}; first call {first}"
              + ("; changed since the private history record" if H.stale([impl]) else H.note([impl])))

    # 3c. v1.3: the extension-specific freeze validation passed on this exact leaderboard.
    if v13:
        vp = RES / "extension-freeze-validation.json"
        v = load(vp) if vp.exists() else {}
        check("extension-specific freeze validation passed for every arm of this leaderboard",
              v.get("passed") is True and {x["arm"] for x in v.get("arms", [])} == {a["arm_id"] for a in lb["arms"]}
              and v.get("arms_checked") == len(lb["arms"])
              and any("extension-freeze-validation.json" in d for d in site.get("disclosures", [])),
              f"{v.get('arms_checked')} arms, {len(v.get('arms_failed') or [])} failed" if v else "missing")
        later = re.compile(r"v0\.0\.[2-9]|v0\.[1-9]\.")
        check("public version is v0.0.1 on the page, with no later public version label",
              site["benchmark"].get("public_release") == "v0.0.1" and not later.search(json.dumps(site))
              and not later.search((REPO / "site/leaderboard/index.html").read_text(encoding="utf-8")),
              site["benchmark"].get("public_note") or "")

    # 4. Overall: score, interval, cost, per-category values and ranking match the frozen overall block.
    bad, ranked = [], []
    for imp in lb["overall"]["implementations"]:
        name = imp["implementation"]
        if not imp.get("ranked"):
            continue
        iid = page_id(name)
        e = next((x for x in site["entries"] if x["suite"] == "overall" and x["implementation"] == iid), None)
        if e is None:
            bad.append(f"{name}: no overall entry"); continue
        ranked.append((imp["overall_score"], e["implementation"]))
        ci, pi = imp.get("ci") or {}, e["quality"]["interval"] or {}
        if not (close(e["quality"]["score"], imp["overall_score"]) and close(pi.get("low"), ci.get("low"))
                and close(pi.get("high"), ci.get("high")) and close(e["cost"]["usd_per_1000"], imp["usd_per_1000"], 1e-5)):
            bad.append(f"{name}: overall score, interval or cost differs")
        for su, v in imp["suites"].items():
            pv = e["suites"].get(SITE_SUITE.get(su, su)) or {}
            if not (close(pv.get("task_score"), v.get("task_score")) and close(pv.get("usd_per_1000"), v.get("usd_per_1000"), 1e-6)):
                bad.append(f"{name}/{su}: category value differs")
        costs = [v["usd_per_1000"] for v in imp["suites"].values()]
        if not close(sum(costs) / len(costs), imp["usd_per_1000"], 1e-6):
            bad.append(f"{name}: overall cost is not the mean of the six category costs")
        wf = imp["suites"]["word_filters"]
        parts = [next(a for a in lb["arms"] if a["arm_id"] == arm_id) for arm_id in (wf.get("subtask_arms") or {}).values()]
        # three values each stored to 6 places: rounding alone can separate them by 1.5e-6
        if len(parts) != 2 or not close(sum(p["cost"]["usd_per_1000"] for p in parts), wf["usd_per_1000"], 2e-6):
            bad.append(f"{name}: word-filters cost is not the sum of its two checks")
        if len(parts) == 2 and not close(sum(p["suite_score"]["value"] for p in parts) / 2, wf["task_score"]):
            bad.append(f"{name}: word-filters score is not the mean of its two checks")
    page_order = [i for _, i in sorted(ranked, reverse=True)]
    frozen_order = [page_id(r["implementation"]) for r in lb["overall"]["ranking"]]
    check("overall matches the frozen overall block (score, interval, cost, categories, composition)", not bad,
          "; ".join(bad) or f"{len(ranked)} ranked implementations")
    check("overall ranking order matches", page_order == frozen_order, f"page {page_order} / frozen {frozen_order}")
    check("overall has no pooled latency (compared on cost only)",
          all(e.get("latency") is None for e in site["entries"] if e["suite"] == "overall"))

    # 5. The five core categories are the corrected five-category view, unchanged (the first run only). A later run
    #    instead checks its account of what changed since the first run against both leaderboards and the ledgers.
    if not CTX.is_first:
        run_checks(site, lb)
    cm = {(a["system"], a["question_set"]): a for a in (corrected or {"arms": []})["arms"]}
    bad, n = [], 0
    for a in lb["arms"]:
        c = cm.get((a["system"], a["question_set"]))
        if a["suite"] not in CORE or c is None or (v12 and a["suite"] == "sensitive_info"):
            continue
        n += 1
        for sub, v in a["subtasks"].items():
            if v["status"] != "evaluated":
                continue
            w = c["subtasks"].get(sub) or {}
            if v.get("task_score") != w.get("task_score") or v.get("n") != w.get("n"):
                bad.append(f"{a['arm_id']}/{sub}")
        if a["cost"].get("usd_per_1000") != c["cost"].get("usd_per_1000"):
            bad.append(f"{a['arm_id']}: cost")
    want_n = len([a for a in corrected["arms"] if not (v12 and a["suite"] == "sensitive_info")]) if corrected else 0
    if corrected: check("core categories identical to the corrected five-category view" + (" (PII excepted: replaced in v1.2)" if v12 else ""),
          not bad and n == want_n, "; ".join(bad) or f"{n} of {want_n} corrected arms")

    # 6. Provisional marking: the AI-labelled categories and the overall, and their label basis on the page.
    prov = set((site.get("provisional") or {}).get("suites") or [])
    ai = ("denied_topics",) if v13 else ("denied_topics", "profanity")   # v1.3: profanity has human rater labels
    rev = site.get("label_review")
    dq = {q["suite"]: q for q in site.get("data_quality") or []}
    if rev:   # 6a. a recorded owner review for this exact release manifest; nothing current still calls labels provisional
        sub = load(REPO / "benchmark/subsets" / site["benchmark"]["dataset_version"].split()[-1] / "manifest.json")
        rel = REPO / "dataset/release" / sub["release"]
        rec = load(REPO / rev["record"])
        ok = (rec["release_manifest_sha256"] == hashlib.sha256((rel / "manifest.json").read_bytes()).hexdigest()
              and rec["independent_two_reviewer_adjudication"] is False and not rev["independent_two_reviewer_adjudication"]
              and not git("status", "--porcelain", rev["record"]))
        check("owner label review is recorded for this release manifest, committed, and not called independent", ok,
              f"{rev['record']} ({rec['reviewer']}, {rec['role']}, {rec['recorded_at'][:10]})")
        check("no suite is marked provisional once the review is recorded", not prov and site.get("provisional") is None,
              ", ".join(sorted(prov)) or "none")
        current = [site.get("notice", "")] + site.get("disclosures", []) + site.get("blockers", []) + \
            [q.get("supports", "") + " " + q.get("limits", "") for q in dq.values()] + \
            [e.get("status_note") or "" for e in site["entries"]]
        stale = [t[:90] for t in current if re.search(r"provisional|await(s|ing)? (independent )?(human )?review|"
                                                       r"single-AI reference labels", t, re.I)]
        check("current page text (corrections aside) has no provisional or awaiting-review statement", not stale,
              "; ".join(stale) or f"{len(current)} strings")
        page = (REPO / "site/leaderboard/index.html").read_text(encoding="utf-8")
        check("the page renders review status from results.json, with no text-rewriting layer",
              "reviewText" not in page and ".replace(/Provisional" not in page, "index.html")
        origin = all(x.get("review") == "project owner" for q in dq.values() for x in q["sources"]) and \
            all(x["label_basis"] == "llm" for k in ai for x in dq[k]["sources"])
        check("label origins are kept beside the owner review (denied topics stays label basis llm)", origin,
              f"denied topics {dq.get('denied_topics', {}).get('test_cases')} rows")
    else:
        want = set(ai) | {"overall"}
        check(", ".join(ai) + " and overall are marked provisional" + (", profanity is not" if v13 else ""),
              prov == want if v13 else want <= prov, ", ".join(sorted(prov)))
        llm = all(s["label_basis"] == "llm" for k in ai for s in dq.get(k, {}).get("sources", [])) \
            and all(dq.get(k, {}).get("test_cases") for k in ai)
        check("data scope shows the AI-labelled rows with label basis llm", llm,
              f"denied topics {dq.get('denied_topics', {}).get('test_cases')}, profanity {dq.get('profanity', {}).get('test_cases')}")
    if v13:
        src = dq.get("profanity", {}).get("sources", [])
        n = sum(x["n"] for x in src)
        check("profanity scope is the 160 Civil Comments rows with human rater labels, lexicon rows outside it",
              n == 160 and all(x["source"] == "civil_comments_obscene" and x["label_basis"] == "human" for x in src),
              ", ".join(f"{x['source']} {x['label_basis']} {x['role']} {x['n']}" for x in src))

    # 6b. Verdicts: every paired comparison on the page is the evaluator's paired interval, Jev minus Bedrock.
    if site.get("comparisons") is not None:
        by_id = {a["arm_id"]: a for a in lb["arms"]}
        want = {}
        for su, block in lb["suites"].items():
            for p in block["paired_differences"]:
                A, B = by_id[p["a"]], by_id[p["b"]]
                ids = (page_id(A["system"]), page_id(B["system"]))
                if set(ids) == {"jev", "bedrock"} and p.get("ci") and A["question_set"] in B["question_set"] + A["question_set"] \
                        and (A["question_set"] == B["question_set"] or su != "word_filters"):
                    sign = 1 if ids[0] == "jev" else -1
                    want.setdefault(su, []).append((sign * p["difference"], sorted((sign * p["ci"]["low"], sign * p["ci"]["high"])), p["separated"]))
        for p in lb["overall"]["paired_differences"]:
            if {p["a"], p["b"]} == {"jev-1.13.0", "bedrock-guardrails"}:
                sign = 1 if p["a"] == "jev-1.13.0" else -1
                want["overall"] = [(sign * p["difference"], sorted((sign * p["ci"]["low"], sign * p["ci"]["high"])), p["separated"])]
        got = site["comparisons"]
        flat = [w for ws in want.values() for w in ws]
        bad = [c["suite"] for c in got if c["suite"] != "word_filters_category" and not any(
            close(c["difference"], d) and close(c["ci"]["low"], ci[0]) and close(c["ci"]["high"], ci[1]) and c["separated"] == sep
            for d, ci, sep in flat)]
        rows = {"content", "prompt_attacks", "denied_topics", "word_filters", "profanity", "sensitive_information", "grounding", "overall"}
        missing = rows - {c["suite"] for c in got}
        check("every verdict row has the evaluator's paired Jev-minus-Bedrock interval", not bad and not missing,
              "; ".join(bad + sorted(missing)) or f"{len(got)} comparisons")
        wfc = next((c for c in got if c["suite"] == "word_filters_category"), None)
        if wfc:   # derived: half the profanity interval, valid only because the custom-word difference is 0 in every replicate
            prof = next(c for c in got if c["suite"] == "profanity")
            ov = {page_id(i["implementation"]): i["suites"]["word_filters"]["task_score"] for i in lb["overall"]["implementations"]}
            words = [a for a in lb["arms"] if a["question_set"] == "v1-f4-words" and page_id(a["system"]) in ("jev", "bedrock")]
            ok = (all(a["suite_score"]["value"] == 100.0 for a in words) and len(words) == 2
                  and close(wfc["difference"], ov["jev"] - ov["bedrock"]) and close(wfc["ci"]["low"], prof["ci"]["low"] / 2)
                  and close(wfc["ci"]["high"], prof["ci"]["high"] / 2))
            check("word-filter category interval is half the profanity interval, with both perfect on custom words", ok,
                  f"{wfc['difference']:+.2f} [{wfc['ci']['low']:.2f}, {wfc['ci']['high']:.2f}]")

    # 6c. Claims, costs and the word-filter aggregate say what was measured.
    scope = site.get("scope") or {}
    text = json.dumps(site)
    check("claim is scoped to configured detectors, with untested capabilities listed and no causal vocabulary claim",
          "configured guardrail detectors across six selected task suites" in scope.get("compares", "").lower()
          and len(scope.get("not_tested") or []) >= 5 and "Complete guardrail implementations" not in
          (REPO / "site/leaderboard/index.html").read_text(encoding="utf-8")
          and not re.search(r"vocabular(y|ies) differ", text), f"{len(scope.get('not_tested') or [])} untested capabilities")
    cb = site.get("cost_basis", {})
    selfhosted = [e for e in site["entries"] if site_impl.get(e["implementation"], {}).get("type") == "self_hosted"
                  and e["suite"] not in ("overall", "bias") and (e.get("cost") or {}).get("usd_per_1000") is not None]
    check("self-hosted costs are labelled normalized estimates, with each pass's actual zone recorded apart from pricing",
          cb.get("self_hosted_cost") == "normalized estimate"
          and ({r["zone"] for r in cb.get("run_locations", [])} >= {"us-east4-a", "us-central1-a"} if CTX.is_first
               else {r["zone"] for r in cb.get("run_locations", [])} == {CTX.vm_zone()}
               and all(CTX.vm_zone() in e["cost"].get("estimate", "") for e in selfhosted))
          and all("normalized" in e["cost"].get("estimate", "") for e in selfhosted),
          f"{len(selfhosted)} entries; zones {sorted({r['zone'] for r in cb.get('run_locations', [])})}")
    wf = [e for e in site["entries"] if e["suite"] == "overall"]
    check("word filters is described as a component average wherever the composed value is carried",
          all("component average" in ((e.get("suites") or {}).get("word_filters") or {}).get("score_basis", "") for e in wf)
          and any("component average" in d for d in site.get("disclosures", [])), f"{len(wf)} overall entries")

    # 7. Bias is outside the score and matches bias.json, B2 with its pair count.
    bad = []
    for s in bias["guardrail_fairness"]["systems"]:
        e = next((x for x in site["entries"] if x["suite"] == "bias" and x.get("track") == "guardrail_fairness"
                  and x["implementation"] == page_id(s["system"])), None)
        if e is None:
            bad.append(f"{s['system']}: no B1 entry"); continue
        if not close(e["quality"]["score"], 100 * s["B1"]["quality"]["balanced_accuracy"], 0.01):
            bad.append(f"{s['system']}: B1")
        b2 = (s.get("B2") or {}).get("counts") or {}
        if e["bias"]["pairs"] != (b2.get("evaluable") or None) or not close(e["bias"]["pair_flip_rate"], s["B2"].get("flip_rate")):
            bad.append(f"{s['system']}: B2")
    in_overall = any("bias" in (e.get("suites") or {}) for e in site["entries"] if e["suite"] == "overall")
    check("bias matches bias.json and stays outside the overall", not bad and not in_overall, "; ".join(bad) or "B1 and B2 per system")

    # 8. Corrections on the page are in the corrections log, with their commits.
    log = (RC.RESULTS / RC.FIRST / "CORRECTIONS.md").read_text(encoding="utf-8")   # the only corrections log so far
    # a later run's page keeps the first run's corrections as history, titled "First run: ", and adds its own entries,
    # whose commits must exist and be in this run's history
    hist = [c for c in site.get("corrections") or [] if CTX.is_first or c["title"].startswith("First run: ")]
    own = [c for c in site.get("corrections") or [] if c not in hist]
    bad = [c["title"] for c in hist if c.get("code_commit") and c["code_commit"] not in log]
    bad += [c["title"] for c in own if not c.get("code_commit")
            or not H.in_history(c["code_commit"])]
    commits = set(re.findall(r"\b[0-9a-f]{7}\b", log))
    missing = [c for c in commits if not H.commit_exists(c)]
    check("every page correction's commit is in CORRECTIONS.md" + ("" if CTX.is_first else
          " (first-run history), and this run's own entries name a commit in its history"), not bad,
          ", ".join(bad) or f"{len(site.get('corrections') or [])} corrections" + ("" if CTX.is_first else f", {len(own)} of this run")
          + H.note(commits=[c["code_commit"] for c in own if c.get("code_commit")]))
    check("every commit named in CORRECTIONS.md exists", not missing,
          ", ".join(missing) or f"{len(commits)} commits" + H.note(commits=commits))

    # 9. Post-hoc views match their computed file, and their rules were committed before the views.
    sens_p = RES / "sensitivity-2026-09-24.json"
    if sens_p.exists():
        sens = load(sens_p)
        page = {v["id"]: v for v in (site.get("sensitivity_views") or {}).get("views", [])}
        bad = [n for n, v in sens["views"].items() if not (v12 and n.startswith("pii-"))
               if n not in page or any(not close(page[n]["scores"].get(k), x["score"], 0.01) for k, x in v["suite"].items())]
        dated = ["benchmark/subsets/first-benchmark/sensitivity-rules-2026-09-24.json",
                 "benchmark/results/first-benchmark/sensitivity-2026-09-24.json"]
        rules_t = H.log(dated[0], fmt="%ct", added=True)
        views_t = H.log(dated[1], fmt="%ct", added=True)
        ordered = bool(rules_t) and (not views_t or int(rules_t.split()[-1]) < int(views_t.split()[-1]))
        bad += [f"changed since the private history record: {p}" for p in H.stale(dated)]
        check("post-hoc views on the page match sensitivity-2026-09-24.json, with rules committed first", not bad and ordered,
              "; ".join(bad) or f"{len(sens['views'])} views" + H.note(dated))

    elif not CTX.is_first:
        claims = [q["suite"] for q in site.get("data_quality") or [] if "shown under the chart" in q.get("limits", "")]
        check("no post-hoc views on file for this run, and no text says one is shown", site.get("sensitivity_views") is None
              and not claims, ", ".join(claims) or "none claimed")

    # 10. Nothing on the page claims publication: blockers present, notice says not for publication.
    blocked = bool(lb["publication_blockers"])
    acc = site.get("accepted_blockers") or []
    acc_ok = True
    for x in acc:   # each accepted line is named in a committed, confirmed approval this result used
        rec = SUB / x["record"]
        a = load(rec)
        acc_ok &= (x["blocker"] in (a.get("accepted_blockers") or []) and bool((a.get("confirmation") or {}).get("statement"))
                   and not git("status", "--porcelain", str(rec.relative_to(REPO)))
                   and any(Path(v["approval_path"]).name == x["record"] for v in lb.get("analysis_versions") or []))
    open_ = [b for b in lb["publication_blockers"] if b not in {x["blocker"] for x in acc}]
    check("page carries every open evaluator blocker, owner-accepted ones only with a confirmed approval, and says not "
          "for publication while any stay open",
          site.get("blockers") == open_ and acc_ok and (("Not for publication" in site.get("notice", "")) == bool(open_)),
          f"open: {'; '.join(open_) or 'none'}; accepted: {len(acc)}")

    # 11. Bias in three parts (docs/benchmark/bias-distinction-developer-handoff.md, developer actions 2, 4 and 5).
    bias_parts_checks(site, lb, bias)

    out = {"checked_at_commit": git("rev-parse", "--short", "HEAD"), "results": str(SITE.relative_to(REPO)),
           "frozen": str(pick.relative_to(REPO)),
           "passed": sum(c["ok"] for c in checks), "failed": sum(not c["ok"] for c in checks), "checks": checks}
    (RES / "page-check.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + (f"  [{c['detail']}]" if c["detail"] else ""))
    return 0 if out["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
