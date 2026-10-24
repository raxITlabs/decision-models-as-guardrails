"""Version progress for the lineages on the board (``goldrails_bench.versions``): offline, no API calls, no keys.

    uv run python benchmark/runs/e2_versions.py score      # benchmark/results/versions/versions.json and versions-site.json
    uv run python benchmark/runs/e2_versions.py tables     # Markdown tables from versions.json, for docs/benchmark/

It reads the raw ledgers (the published results folder and its git-ignored ``private/`` copies, which hold the
unpublished slice), so it runs only on the maintainers' machine, like the rescore. Nothing is written to the
results folder or the ledgers: the records are built in memory with the rescore's own functions (label amendment,
latest record per row, scorer record) and scored by ``leaderboard_v2.evaluate`` in diagnostic mode over the lineage
systems alone, against the frozen row list. Every arm covers the full frozen row list, so the group draws are the
board's and every point and interval equals the published ``leaderboard.json``; the script checks that before it
writes anything.

Examples of fixed and broken rows come from public rows only. A row's text is quoted only when the released Hugging
Face copy ships it (``redistribution: text``) and the suite is not content (harmful text). Both outputs are scanned
for unpublished ids before they are kept.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_smoke as smoke  # noqa: E402
import e2_full as full  # noqa: E402
import e2_sample as sample  # noqa: E402
import e2_attacks_rerun as ar  # noqa: E402

from goldrails_bench import leaderboard_v2 as lv2  # noqa: E402
from goldrails_bench import versions as V  # noqa: E402

REPO = full.REPO
LEDGERS = full.FINAL / "ledgers"
PUBLISHED = full.FINAL / "leaderboard.json"
OUT = REPO / "benchmark" / "results" / "versions" / "versions.json"
SITE_OUT = OUT.parent / "versions-site.json"     # site/scripts/build-data.ts copies it to site/data/versions.json
SITE_DATA = REPO / "site" / "data" / "versions.json"
RELEASES = REPO / "dataset" / "publish"
QUOTE_SUITES = {"denied_topics", "prompt_attacks"}
EXCERPT_CHARS = 160
CLASS_NAMES = {"content": ("harmful", "benign"), "prompt_attacks": ("attack", "benign"),
               "denied_topics": ("denied topic", "allowed"), "word_filters": ("profane", "clean"),
               "grounding": ("unsupported claim", "supported")}
SUITE_FOLDER = {"content": "content", "prompt_attacks": "prompt_attacks", "denied_topics": "denied_topics",
                "word_filters": "word_filters", "sensitive_info": "sensitive_information", "grounding": "grounding"}
# (ledger folder under LEDGERS, suites to take from it); the full run's prompt attacks were replaced by the rerun
SOURCES = (("main-run", lambda s: s != "prompt_attacks"), ("prompt-attacks", lambda s: s == "prompt_attacks"),
           ("jev-1.14.0", lambda s: True), ("strands-deciders", lambda s: True))


def systems() -> list[str]:
    return [v for L in V.LINEAGES.values() for v in L["versions"] if len(L["versions"]) > 1]


def load(names: set) -> tuple[list, list, "full.TestRows"]:
    """(scorer records, latest raw ledger records) for ``names``, built as the rescore builds them."""
    tr = full.TestRows()
    raw = []
    for folder, keep in SOURCES:
        raw += [d for d in sample.load_ledgers(LEDGERS / folder / "private") if d["system"] in names and keep(d["suite"])]
    final = sample.latest(full.amend_ledgers(raw, tr))
    records = [x for d in final if (x := full.scorer_record(d, tr))]
    return records, final, tr


def evaluate(records: list, tr) -> tuple[dict, dict, dict]:
    contract = lv2.load_contract()
    cap = {}
    doc = lv2.evaluate([dict(r) for r in records], contract, ar.implementations(records), None, "test", None, None,
                       None, None, [], {}, {}, frozen=full.frozen_rows(tr), diagnostic=True, capture=cap)
    return doc, cap, contract


def check_against_board(sc: V.Scored, pub: dict, names: list[str]) -> dict:
    """Every overall, suite and subtask point and the overall interval equal the published board, or stop."""
    checked = 0
    rank = {r["name"]: r for r in pub["overall"]["ranking"]}
    for n in names:
        s = V.system_stats(sc, n)
        want = rank[n]
        if abs(s["overall"]["point"]["balanced_accuracy"] - want["balanced_accuracy"]) > 1e-5:
            raise SystemExit(f"{n}: overall {s['overall']['point']['balanced_accuracy']} != board {want['balanced_accuracy']}")
        ci = lv2.lb.ci_of(s["overall"]["reps"]["balanced_accuracy"], sc.level)
        if (ci["low"], ci["high"]) != (want["ci"]["low"], want["ci"]["high"]):
            raise SystemExit(f"{n}: overall interval {ci} != board {want['ci']}")
        checked += 2
        for suite, e in s["suites"].items():
            row = next(r for r in pub["suites"][suite]["ranking"] if r["name"] == n)
            if abs(e["point"]["balanced_accuracy"] - row["balanced_accuracy"]) > 1e-5:
                raise SystemExit(f"{n} {suite}: {e['point']['balanced_accuracy']} != board {row['balanced_accuracy']}")
            checked += 1
        for key, e in s["subtasks"].items():
            row = next(r for r in pub["subtasks"][key]["ranking"] if r["name"] == n)
            if abs(e["point"]["balanced_accuracy"] - row["balanced_accuracy"]) > 1e-5:
                raise SystemExit(f"{n} {key}: {e['point']['balanced_accuracy']} != board {row['balanced_accuracy']}")
            checked += 1
    return {"values_checked": checked, "equal_to": full._rel(PUBLISHED)}


def board_pair(pub: dict, a: str, b: str) -> dict | None:
    for p in pub["overall"]["paired_differences"]:
        if {p["a"], p["b"]} == {a, b}:
            sign = 1 if p["a"] == b else -1          # report new - old
            return {"difference": round(sign * p["difference"], 6), "p_holm_board": p["p_holm"],
                    "separated_on_board": p["separated"], "pairs_in_board_family": len(pub["overall"]["paired_differences"])}
    return None


def tiers(pub: dict) -> dict:
    return {r["name"]: {"rank": r["rank"], "tier": r["tier"], "rank_interval": r["rank_interval"]}
            for r in pub["overall"]["ranking"]}


def serving_of(final: list) -> dict:
    out = {}
    for d in final:
        s = d.get("serving") or {}
        ident = s.get("identity") or {}
        e = out.setdefault(d["system"], {"model": ident.get("ref") or ident.get("model") or s.get("model_id"),
                                         "revision": ident.get("revision") or s.get("revision"),
                                         "max_length": s.get("max_length"), "dates": set(),
                                         "provider": ident.get("provider") or ("self-hosted" if ident.get("kind") else None)})
        if s.get("date"):
            e["dates"].add(s["date"])
    return {k: {**v, "dates": sorted(v["dates"])} for k, v in out.items()}


def tokens_of(final: list) -> tuple[dict, dict]:
    """({system: {check key: reported input tokens}}, {system: counts of window flags})."""
    tok, flags = {}, {}
    for d in final:
        k = (d["suite"], d["subtask"], d["row_id"])
        u = d.get("usage_input_tokens")
        if u is None:
            u = (d.get("usage") or {}).get("input_tokens")
        tok.setdefault(d["system"], {})[k] = u
        c = flags.setdefault(d["system"], Counter())
        c["checks"] += 1
        c["at_cap"] += bool(d.get("at_cap"))
        c["near_limit"] += bool(d.get("near_limit"))
        c["truncated"] += bool(d.get("truncated"))
    return tok, {k: dict(v) for k, v in flags.items()}


def released_text() -> dict:
    """{row id: state text} for rows the released copy ships with text, newest release folder first."""
    out = {}
    for rel in sorted(RELEASES.glob("release-*"), reverse=True):
        for f in (rel / "data").glob("*/test.jsonl"):
            for line in f.open(encoding="utf-8"):
                r = json.loads(line)
                if r.get("redistribution") == "text" and r["id"] not in out:
                    st = r.get("state") or {}
                    out[r["id"]] = st.get("text") or st.get("source") or ""
    return out


def describe_examples(ex: dict, tr, text: dict) -> dict:
    out = {}
    for key, kinds in ex.items():
        suite = key.split("/")[0]
        for kind, items in kinds.items():
            for e in items:
                r = tr.rows[e["id"]]
                e["source"] = (r.get("provenance") or {}).get("source")
                if suite == "sensitive_info":
                    e["label"] = f"{'contains' if e['positive'] else 'does not contain'} {e['unit']}"
                else:
                    e["label"] = CLASS_NAMES[suite][0 if e["positive"] else 1]
                t = text.get(e["id"])
                if t and suite in QUOTE_SUITES:
                    t = " ".join(t.split())
                    e["excerpt"] = t[:EXCERPT_CHARS] + ("..." if len(t) > EXCERPT_CHARS else "")
        out[key] = kinds
    return out


def site_view(doc: dict) -> dict:
    """The compact shape the site reads: no rows, no ids."""
    lin = []
    for key, L in doc["lineages"].items():
        comps = []
        for c in L["comparisons"]:
            comps.append({
                "from": c["from"], "to": c["to"], "kind": c["kind"],
                "overall": {m: {"old": c["overall"]["old"][m], "new": c["overall"]["new"][m], **c["overall"]["delta"][m]}
                            for m in V.METRICS},
                "board": c.get("board"),
                "suites": {s: {"old": b["old"]["balanced_accuracy"], "new": b["new"]["balanced_accuracy"],
                               **b["delta"]["balanced_accuracy"],
                               "false_block_rate": b["delta"]["false_block_rate"]}
                           for s, b in c["suites"].items()},
                "subtasks": {s: {"old": b["old"]["balanced_accuracy"], "new": b["new"]["balanced_accuracy"],
                                 **b["delta"]["balanced_accuracy"], "fixed": b["flips"]["fixed"],
                                 "broke": b["flips"]["broke"]}
                             for s, b in c["subtasks"].items()},
                "flips": {k: c["flips"][k] for k in ("fixed", "broke", "catches_gained", "catches_lost",
                                                      "false_blocks_cleared", "false_blocks_added", "judgments")},
                "mcnemar_p": c["mcnemar"]["p"],
                "calibration": {s: {"old_ece": b["calibration"]["old"]["ece"], "new_ece": b["calibration"]["new"]["ece"],
                                    **b["calibration"]["delta_ece"]}
                                for s, b in c["subtasks"].items() if "calibration" in b},
                "cost": c.get("cost"), "tokens": c.get("tokens")})
        lin.append({"key": key, "label": L["label"], "vendor": L["vendor"], "versions": L["versions"],
                    "planned": L.get("planned", []), "board": L["board"], "comparisons": comps})
    return {"schema": "goldrails-versions-site/1", "method": doc["method"]["short"], "lineages": lin}


def privacy(paths: list[Path], tr) -> None:
    bad = []
    for p in paths:
        s = p.read_text(encoding="utf-8")
        bad += [i for i in tr.unpublished if i in s]
    if bad:
        for p in paths:
            p.unlink()
        raise SystemExit(f"privacy check failed: {len(bad)} unpublished ids in the output; files removed")


METHOD = {
    "short": "Paired on identical rows (9,975 checks). Intervals and tests are the leaderboard's: 2,000 group-bootstrap "
             "draws shared by both versions, 95% percentile interval of the difference, Wald test. A change is better "
             "or worse only when its Holm-adjusted p is below 0.05; otherwise it is within noise.",
    "families": {"overall": "per metric, every comparison of the lineage",
                 "suites": "per comparison and metric, the six suites",
                 "subtasks": "per comparison and metric, the eight scored subtasks",
                 "calibration": "per comparison, the calibrated subtasks"},
    "board": "p_holm_board is the board's adjustment over every pair of the full board; a version step can be "
             "better here and share a tier on the board",
    "mcnemar": "exact McNemar on per-judgment correctness; a cross-check, never the verdict",
}


def score() -> Path:
    names = systems()
    records, final, tr = load(set(names))
    doc_eval, cap, contract = evaluate(records, tr)
    sc = V.Scored(cap, contract)
    pub = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    check = check_against_board(sc, pub, names)
    pub_ids, tok, flags, serving, tr_board = tr.public_ids(), *tokens_of(final), serving_of(final), tiers(pub)
    text = released_text()
    out = {"schema": "goldrails-versions/1", "method": METHOD, "check": check,
           "rows": {"public": len(pub_ids), "unpublished": len(tr.unpublished)}, "lineages": {}}
    for key, L in V.LINEAGES.items():
        vs = L["versions"]
        entry = {"label": L["label"], "vendor": L["vendor"], "versions": vs, "planned": L.get("planned", []),
                 "board": {v: tr_board.get(v) for v in vs}, "serving": {v: serving.get(v) for v in vs},
                 "window_flags": {v: flags.get(v) for v in vs}, "comparisons": []}
        if len(vs) > 1:
            for c in V.lineage(sc, vs, pub_ids):
                c["board"] = board_pair(pub, c["from"], c["to"])
                c["cost"] = V.cost_summary(pub["run"]["cost"].get(c["from"]), pub["run"]["cost"].get(c["to"]))
                c["tokens"] = V.token_summary(tok[c["from"]], tok[c["to"]])
                c["examples"] = describe_examples(c["examples"], tr, text)
                entry["comparisons"].append(c)
        out["lineages"][key] = entry
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    SITE_OUT.write_text(json.dumps(site_view(out), indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    privacy([OUT, SITE_OUT], tr)
    if SITE_DATA.parent.is_dir():
        SITE_DATA.write_text(SITE_OUT.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {full._rel(OUT)} and {full._rel(SITE_OUT)}; {check['values_checked']} values equal the board")
    return OUT


# --- Markdown tables for the write-up ----------------------------------------------------------------------------

SUITE_NAME = {"content": "Content", "prompt_attacks": "Prompt attacks", "denied_topics": "Denied topics",
              "word_filters": "Profanity", "sensitive_info": "Sensitive info", "grounding": "Grounding"}
SUB_NAME = {"content/request": "Content, requests", "content/reply": "Content, replies",
            "prompt_attacks/direct": "Prompt attacks, direct", "prompt_attacks/indirect": "Prompt attacks, indirect",
            "denied_topics/topic": "Denied topics", "word_filters/profanity": "Profanity",
            "sensitive_info/entity_detection": "Sensitive info", "grounding/grounding": "Grounding"}


def _pp(d: dict, scale: float = 1.0, nd: int = 2) -> str:
    lo, hi = d["ci"]["low"] * scale, d["ci"]["high"] * scale
    return f"{d['point'] * scale:+.{nd}f} [{lo:+.{nd}f}, {hi:+.{nd}f}]"


def _p(p) -> str:
    return "n/a" if p is None else ("<0.001" if p < 0.001 else f"{p:.3f}")


def tables(path: Path = OUT) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    lines = []
    for key, L in doc["lineages"].items():
        for c in L["comparisons"]:
            o = c["overall"]
            lines += [f"### {c['from']} -> {c['to']} ({c['kind']})", "",
                      "| Metric | Old | New | Change [95% CI] | p | p (Holm) | Verdict |", "|---|---|---|---|---|---|---|"]
            for m, sc_, unit in (("balanced_accuracy", 1, ""), ("catch_rate", 100, " pp"), ("false_block_rate", 100, " pp")):
                d = o["delta"][m]
                lines.append(f"| {m.replace('_', ' ')} | {o['old'][m] * sc_:.2f} | {o['new'][m] * sc_:.2f} | "
                             f"{_pp(d, sc_)}{unit} | {_p(d['p'])} | {_p(d['p_holm'])} | {d['verdict']} |")
            b = c["board"]
            lines += ["", f"Board: Holm-adjusted p {_p(b['p_holm_board'])} over {b['pairs_in_board_family']} pairs, "
                          f"separated {b['separated_on_board']}.", ""]
            lines += ["| Suite | Old | New | Change [95% CI] | p (Holm) | Verdict | False-block change, pp |",
                      "|---|---|---|---|---|---|---|"]
            for s, x in c["suites"].items():
                d = x["delta"]["balanced_accuracy"]
                lines.append(f"| {SUITE_NAME[s]} | {x['old']['balanced_accuracy']:.2f} | {x['new']['balanced_accuracy']:.2f}"
                             f" | {_pp(d)} | {_p(d['p_holm'])} | {d['verdict']} | {_pp(x['delta']['false_block_rate'], 100)} |")
            lines += ["", "| Subtask | Old | New | Change [95% CI] | p (Holm) | Verdict | Fixed | Broke | McNemar p |",
                      "|---|---|---|---|---|---|---|---|---|"]
            for s, x in c["subtasks"].items():
                d = x["delta"]["balanced_accuracy"]
                lines.append(f"| {SUB_NAME[s]} | {x['old']['balanced_accuracy']:.2f} | {x['new']['balanced_accuracy']:.2f}"
                             f" | {_pp(d)} | {_p(d['p_holm'])} | {d['verdict']} | {x['flips']['fixed']} | "
                             f"{x['flips']['broke']} | {_p(x['mcnemar']['p'])} |")
            f = c["flips"]
            lines += ["", f"Flips over {f['judgments']:,} judgments: {f['catches_gained']} catches gained, "
                          f"{f['catches_lost']} lost; {f['false_blocks_cleared']} false blocks cleared, "
                          f"{f['false_blocks_added']} added. McNemar p {_p(c['mcnemar']['p'])}.", ""]
            cal = {s: x["calibration"] for s, x in c["subtasks"].items() if "calibration" in x}
            if cal:
                lines += ["| Calibrated subtask | ECE old | ECE new | Change [95% CI] | p (Holm) | Verdict |",
                          "|---|---|---|---|---|---|"]
                for s, x in cal.items():
                    d = x["delta_ece"]
                    lines.append(f"| {SUB_NAME[s]} | {x['old']['ece']:.3f} | {x['new']['ece']:.3f} | {_pp(d, 1, 3)} | "
                                 f"{_p(d['p_holm'])} | {d['verdict']} |")
                lines.append("")
            co, tk = c["cost"], c["tokens"]
            if co:
                lines.append(f"Cost per 1,000 checks: USD {co['old_usd_per_1000']:.4f} -> {co['new_usd_per_1000']:.4f} "
                             f"({co['delta_pct']:+.1f}%), {'comparable' if co['comparable'] else 'not comparable: ' + co['why_not_comparable']}.")
            if tk.get("checks"):
                lines.append(f"Reported input tokens per check: {tk['old_mean']:.0f} -> {tk['new_mean']:.0f} "
                             f"({tk['delta_pct']:+.1f}%) over {tk['checks']:,} checks.")
            lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["score", "tables"])
    a = ap.parse_args(argv)
    smoke.use_source("local")
    if a.stage == "score":
        score()
    else:
        print(tables())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
