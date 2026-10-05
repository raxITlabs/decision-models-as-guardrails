"""Build the rebuilt prompt-attack suite (owner ruling 23) as a candidate beside the current one.

The current suite stays in ``dataset/edition2/prompt_attacks/`` untouched. The candidate goes to
``dataset/edition2/r23/prompt_attacks/`` with the same layout (``e2_local``): tracked public rows in
``candidates.jsonl`` (licence-withheld text redacted), the unpublished slice and owner files in the git-ignored
``private/``, withheld text in the git-ignored ``local/``. The design is in ``dataset/edition2/r23/prompt_attacks/
DESIGN.md``.

Rows:

- authored role-swap pairs from ``e2_prompt_attacks_r23`` (source ``e2_attack_controls``, CC-BY-4.0). A pair goes to
  dev, test or the unpublished slice whole, by a salted draw (shares 0.15 / 0.60 / 0.25). A pair is dropped when
  either row fails a screen: same text as a v1 row or pool row, word 5-gram near-duplicate (Jaccard >= 0.7) of a v1 F2
  pool row, text in a benchmarked model's training or development data (``model_overlap``), a shared 8-word run with
  a benchmarked vendor's file (``vendor_overlap``), or the same text as a row of another edition 2 suite or of the
  current prompt-attack suite.
- real rows, taken from the current suite as the build would hold them (``e2_prompt_attacks_build.projected``: owner
  rulings applied, rows awaiting the owner left out, owner exclusions gone). So every real row already passed the
  overlap, vendor and model-training screens, keeps its split, its group and its second label. Selection is
  same-source and length-matched: inside each (subtask, source, split, length bin) the attack and benign counts are
  made equal, taking rows in salted order. A source that gives only one class in a cell gives nothing there. The
  earlier authored rows (rounds of 2 to 4 October) are not carried over: their twins differ in wording, which is the
  shortcut this rebuild removes.

Commands (from ``dataset/``; the gate needs scikit-learn):

    uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_r23_build build
    uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_r23_build gate
    uv run python -m goldrails_dataset.sources.e2_prompt_attacks_r23_build packet

``build`` writes the files and runs ``gate`` and ``packet``. ``gate`` assembles a scratch edition 2 root whose
prompt-attack folder is this candidate and every other suite is the current one, runs the edition 2 build's own
assembly (second labels, rulings, cross-suite text, near-duplicate clustering, reference-overlap drops) and its
shortcut gate (``edition2.shortcut_gate``: every baseline, in sample and held back, both bounds), and writes
``gate.json`` (metrics and counts only). ``packet`` writes the owner review page and a blind second-label packet into
``private/``.
"""
from __future__ import annotations

import argparse
import html
import json
import random
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from .. import e2_local
from . import e2_prompt_attacks_build as build
from . import e2_prompt_attacks_r23 as gen
from .e2_prompt_attacks_common import SUITE, normalise

ROOT = e2_local.E2 / "r23"                 # an edition 2 root holding only the candidate prompt-attack folder
OUT = ROOT / SUITE
SHARES = (("dev", 0.15), ("private", 0.25), ("test", 0.60))
SELECTION = "r23-same-source-length-matched-2026-10-06"
ROW_FILES = e2_local.ROW_FILES[SUITE]
GATE = OUT / "gate.json"
COUNTS = OUT / "counts.json"
REVIEW = OUT / "private" / "review.html"
PACKET = OUT / "private" / "packet"


# --- real rows -------------------------------------------------------------------------------------------------------

def current_rows() -> tuple[list, dict, dict]:
    """The current suite as the edition 2 build would hold it, plus its second labels and resolutions."""
    cands = e2_local.candidates(SUITE)
    seconds = {d["id"]: d for d in e2_local.relabels(SUITE)}
    res = build.resolutions()
    return build.projected(cands, seconds, res), {c["id"]: c for c in cands}, res


def select_real(projected: list) -> list:
    """Same-source, length-matched real rows: ids, in salted order, with equal attack and benign counts inside every
    (subtask, source, split, length bin). Authored rows of earlier rounds are left out."""
    cells = defaultdict(lambda: {"yes": [], "no": []})
    for r in projected:
        if r["source"] == gen.SOURCE:
            continue
        key = (r["subtask"], r["source"], r["proposed_split"], build.length_bin(r["state"]["text"]))
        cells[key][r["label"]].append(r)
    out = []
    for key in sorted(cells):
        v = cells[key]
        n = min(len(v["yes"]), len(v["no"]))
        for lab in ("yes", "no"):
            out += sorted(v[lab], key=lambda r: e2_local.salted("pa-r23-real", r["id"]))[:n]
    return out


# --- authored rows ---------------------------------------------------------------------------------------------------

def split_of(group: str) -> str:
    u = e2_local.salted_unit("pa-r23-split", group)
    acc = 0.0
    for name, share in SHARES:
        acc += share
        if u < acc:
            return name
    return SHARES[-1][0]


def screens(fetch_pools: bool = True) -> dict:
    """The reference sets a new authored row is checked against."""
    from .. import model_overlap, vendor_overlap
    try:
        ref = build.v1_reference(fetch_pools=fetch_pools)
        pools = fetch_pools
    except Exception as e:      # the v1 pools need the network or a Hugging Face cache
        ref, pools = build.v1_reference(fetch_pools=False), f"not loaded ({type(e).__name__})"
    current = {normalise(c["state"]["text"]) for c in e2_local.candidates(SUITE)}
    return {"ref": ref, "v1_pools": pools, "vendor": vendor_overlap.vendor_index(),
            "model": model_overlap.index(), "other": build.other_suite_texts(), "current": current}


def screen_reason(c: dict, s: dict) -> str | None:
    from .. import model_overlap, vendor_overlap
    t = c["state"]["text"]
    if c["id"] in s["ref"]["ids"]:
        return "id in a v1 build, sample, examined list or ledger"
    if normalise(t) in s["ref"]["texts"]:
        return "same text as a v1 row or v1 pool row"
    if s["ref"]["near"].match(t):
        return "near-duplicate of a v1 F2 pool row (word 5-gram Jaccard >= 0.7)"
    if model_overlap.seen_by_model([t], s["model"]):
        return build.MODEL_SCREEN
    if vendor_overlap.match_row(c, s["vendor"]):
        return "text shares an 8-word run with a benchmarked vendor's file (vendor_overlap)"
    if build.loose(t) in s["other"]:
        return build.CROSS_SUITE_SCREEN
    if normalise(t) in s["current"]:
        return "same text as a row of the current prompt-attack suite"
    return None


def authored(s: dict | None) -> tuple[list, Counter]:
    """Candidate dicts of the authored pairs that pass every screen (a pair leaves whole)."""
    rows = gen.records()
    by_pair = defaultdict(list)
    for r in rows:
        by_pair[r.group].append(r)
    out, dropped = [], Counter()
    for group in sorted(by_pair, key=lambda g: e2_local.salted("pa-r23-order", g)):
        split = split_of(group)
        cs = [build.candidate(r, group, split) for r in by_pair[group]]
        reasons = [x for x in (screen_reason(c, s) for c in cs) if x] if s is not None else []
        if reasons:
            dropped[reasons[0]] += len(cs)
            continue
        out += cs
    return out, dropped


# --- writing ---------------------------------------------------------------------------------------------------------

def _write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    st = e2_local.STYLE.get(SUITE, e2_local.DEFAULT_STYLE)
    path.write_text("".join(json.dumps(r, **st) + "\n" for r in rows), encoding="utf-8")


def write(fetch_pools: bool = True) -> dict:
    projected, originals, _ = current_rows()
    real_ids = [r["id"] for r in select_real(projected)]
    real = [originals[i] for i in real_ids]
    s = screens(fetch_pools)
    auth, dropped = authored(s)
    rows = auth + real
    rows.sort(key=lambda c: (c["subtask"], c["source"] != gen.SOURCE, c["id"]))
    if OUT.exists():                       # a rebuild starts clean; private/ and local/ are rebuilt by split()
        for p in OUT.iterdir():
            if p.name in ("DESIGN.md",):
                continue
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(parents=True, exist_ok=True)
    _write_jsonl(OUT / "candidates.jsonl", rows)
    keep = set(real_ids)
    for name in ROW_FILES:
        try:
            lines = e2_local.row_file(SUITE, name)
        except e2_local.LocalDataMissing:
            raise
        lines = [d for d in lines if d["id"] in keep]
        if lines:
            _write_jsonl(OUT / name, lines)
    rep = e2_local.split((SUITE,), ROOT)
    held = hold_back_shared()
    return {"authored": len(auth), "real": len(real), "dropped_authored": dict(dropped),
            "v1_pools": s["v1_pools"], "split": rep.get(SUITE), "held_back_shared": held}


def edition_private() -> tuple[set, set]:
    """Ids in any current suite's private/ file, and the normalised texts of every unpublished-slice row of edition 2.
    e2_local.split on this root only sees this folder, so it cannot know that a public row repeats another suite's
    unpublished text; the current edition already holds such rows in private/."""
    ids, texts = set(), set()
    for s in e2_local.SUITES:
        for c in e2_local._jsonl(e2_local.private_dir(s) / "candidates.jsonl"):
            ids.add(c["id"])
            if c["proposed_split"] == "private":
                texts |= e2_local._texts(c)
    return ids, texts


def hold_back_shared() -> int:
    """Move every public row of this candidate that the current edition keeps in a private/ file, or whose text is an
    unpublished row's text, into this candidate's private/ (candidates, row files, text cache). Returns rows moved."""
    ids, texts = edition_private()
    pub = e2_local._raw_rows(OUT / "candidates.jsonl")
    cache = {e["id"]: e for e in e2_local._jsonl(e2_local.text_cache(SUITE, ROOT))}
    move = set()
    for _, c in pub:
        full = e2_local.restore(c, cache[c["id"]]) if "redacted" in c else c
        if c["id"] in ids or e2_local._texts(full) & texts:
            move.add(c["id"])
    if not move:
        return 0
    prv = e2_local._raw_rows(OUT / "private" / "candidates.jsonl")
    full_lines = {c["id"]: json.dumps(e2_local.restore(c, cache[c["id"]]) if "redacted" in c else c,
                                      **e2_local.STYLE.get(SUITE, e2_local.DEFAULT_STYLE)) for _, c in pub}
    e2_local._write_lines(OUT / "candidates.jsonl", [l for l, c in pub if c["id"] not in move])
    e2_local._write_lines(OUT / "private" / "candidates.jsonl", [l for l, _ in prv] + [full_lines[i] for i in sorted(move)])
    e2_local._write_lines(e2_local.text_cache(SUITE, ROOT),
                          [json.dumps(e, ensure_ascii=False, sort_keys=True) for i, e in cache.items() if i not in move])
    for name in ROW_FILES:
        a, b = e2_local._raw_rows(OUT / name), e2_local._raw_rows(OUT / "private" / name)
        if not a and not b:
            continue
        e2_local._write_lines(OUT / name, [l for l, r in a if r["id"] not in move])
        e2_local._write_lines(OUT / "private" / name, [l for l, _ in b] + [l for l, r in a if r["id"] in move])
    return len(move)


# --- the gate on the built rows --------------------------------------------------------------------------------------

def scratch_root() -> Path:
    """A temporary edition 2 root: every suite folder links to the current one except prompt_attacks, which links to
    this candidate. Root files the build reads (EXCLUDED.jsonl) link to the current ones."""
    tmp = Path(tempfile.mkdtemp(prefix="pa-r23-gate-"))
    for s in e2_local.SUITES:
        (tmp / s).symlink_to(OUT if s == SUITE else e2_local.E2 / s, target_is_directory=True)
    for f in ("EXCLUDED.jsonl",):
        if (e2_local.E2 / f).exists():
            (tmp / f).symlink_to(e2_local.E2 / f)
    return tmp


def built_parts() -> dict:
    from .. import edition2
    tmp = scratch_root()
    try:
        parts, _ = edition2.build_parts(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return parts


def _origin_rows(parts: dict, authored_only: bool) -> list:
    from .. import edition2
    rows = edition2._gate_rows(parts)
    return [r for r in rows if (r["source"] == gen.SOURCE) == authored_only]


def gate(parts: dict | None = None) -> dict:
    from .. import edition2
    from . import e2_prompt_attacks_shortcuts as sc
    parts = parts if parts is not None else built_parts()
    g = edition2.shortcut_gate(parts)
    fl = [c for c in edition2.floors(parts)["cells"] if c["feature"] == "F2"]
    diag = {}
    for name, flag in (("authored_rows_only", True), ("real_rows_only", False)):
        rep = sc.gate_report(_origin_rows(parts, flag))
        mx = defaultdict(dict)
        for t in rep["table"]:
            cell = mx[t["subtask"]]
            for m in ("ba", "auroc"):
                if t[m] > cell.get(m, -1):
                    cell[m], cell[f"{m}_at"] = t[m], f"{t['view']}/{t['baseline']}"
        diag[name] = {"pass": rep["pass"], "failing_cells": len(rep["failures"]), "cells": len(rep["table"]),
                      "max": dict(sorted(mx.items()))}
    out = {
        "what": "the edition 2 prompt-attack shortcut gate (edition2.shortcut_gate) on the ruling 23 candidate, built "
                "by the edition 2 assembly with every other suite as it is",
        "command": "uv run --with scikit-learn python -m goldrails_dataset.sources.e2_prompt_attacks_r23_build gate",
        "rule": g["rule"], "selection": SELECTION,
        "pass": g["pass"], "in_sample_pass": g["in_sample"]["pass"], "heldback_pass": g["heldback"]["pass"],
        "summary": edition2.gate_summary(g),
        "failures": g["failures"],
        "floors": [{"subtask": c["subtask"], "public_test": c["public_test"], "with_private": c["with_private"],
                    "sources_by_class": c["sources_by_class"], "pass": c["pass"]} for c in fl],
        "diagnostics": {"note": "not part of the gate: the same baselines on the authored role-swap rows alone and "
                                "on the real-source rows alone (every view)", **diag},
        "table": g["table"],
    }
    GATE.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    write_counts(parts)
    return out


def write_counts(parts: dict) -> dict:
    """Counts per subtask, label, source, family and split, from the built rows (public file: counts only)."""
    per = defaultdict(Counter)
    fam = defaultdict(Counter)
    for split in ("dev", "test", "private", "review", "review_private"):
        for r in parts.get(split, []):
            if r.feature != "F2":
                continue
            per[f"{r.subtask}/{r.expected}"][f"{split}:{r.provenance.source}"] += 1
            if r.provenance.source == gen.SOURCE:
                n = json.loads(r.provenance.notes or "{}")
                fam[r.subtask][f"{n.get('family')}/{r.expected}"] += 1
    totals = defaultdict(Counter)
    for k, c in per.items():
        for sk, n in c.items():
            totals[k][sk.split(":")[0]] += n
    out = {"selection": SELECTION, "generator_revision": gen.REVISION,
           "families": {k: dict(sorted(v.items())) for k, v in sorted(fam.items())},
           "by_split": {k: dict(sorted(v.items())) for k, v in sorted(totals.items())},
           "by_split_and_source": {k: dict(sorted(v.items())) for k, v in sorted(per.items())}}
    COUNTS.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


# --- owner review page and blind packet --------------------------------------------------------------------------------

_CSS = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--atk:#9b2c2c;--atkbg:#fbeeee;--ok:#2f6b3a;--okbg:#edf6ee;
--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--line:#33322f;--atk:#f2a6a6;
--atkbg:#2e1b1b;--ok:#9fd3a8;--okbg:#18261a;--card:#1e1e1c}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;margin:0;padding:0 16px}
main{max-width:1100px;margin:24px auto 64px}h1{font-size:24px;margin:0 0 4px}h2{margin-top:36px;font-size:19px}
h3{font-size:16px;margin:24px 0 8px}p,li{color:var(--fg)}.mut{color:var(--mut)}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:14px}th,td{border-bottom:1px solid var(--line);
padding:6px 8px;text-align:left;vertical-align:top}th{font-weight:600}td.n{text-align:right;font-variant-numeric:tabular-nums}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0;border:1px solid var(--line);border-radius:8px;
padding:10px;background:var(--card)}.pair .meta{grid-column:1/-1;font-size:12px;color:var(--mut)}
.row{border-radius:6px;padding:8px;white-space:pre-wrap;font-size:14px}.yes{background:var(--atkbg)}.no{background:var(--okbg)}
.tag{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase}.yes .tag{color:var(--atk)}
.no .tag{color:var(--ok)}details{margin:6px 0}summary{cursor:pointer;font-weight:600}
@media (max-width:700px){.pair{grid-template-columns:1fr}}
"""


def write_review(parts: dict | None = None) -> Path:
    """The owner review page for the authored rows: counts, the design rules, and every pair side by side (unpublished
    slice included, so the page stays in private/)."""
    cands = e2_local.candidates(SUITE, ROOT)
    auth = [c for c in cands if c["source"] == gen.SOURCE]
    real = [c for c in cands if c["source"] != gen.SOURCE]
    pairs = defaultdict(dict)
    for c in auth:
        pairs[c["group"]][c["label"]] = c
    g = json.loads(GATE.read_text(encoding="utf-8")) if GATE.exists() else None
    e = html.escape
    out = [f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,"
           f"initial-scale=1'><title>Prompt attack rebuild review</title><style>{_CSS}</style></head><body><main>",
           "<h1>Prompt-attack rebuild (ruling 23): owner review</h1>",
           "<p class=mut>Local and git-ignored. It shows every authored row, unpublished slice included. "
           "Design: <code>dataset/edition2/r23/prompt_attacks/DESIGN.md</code>.</p>"]
    if g:
        out.append(f"<h2>Shortcut gate</h2><p><b>{'Pass' if g['pass'] else 'Fail'}</b>: in sample "
                   f"{'pass' if g['in_sample_pass'] else 'fail'}, held back {'pass' if g['heldback_pass'] else 'fail'}; "
                   f"{g['summary']['failing_cells']} of {g['summary']['cells']} cells fail.</p>"
                   "<table><tr><th>Subtask</th><th>Half</th><th>Max BA (where)</th><th>Max AUROC (where)</th></tr>")
        for sub, halves in g["summary"]["max"].items():
            for half, m in halves.items():
                out.append(f"<tr><td>{sub}</td><td>{half}</td><td>{m['ba']} ({e(m['ba_at'])})</td>"
                           f"<td>{m['auroc']} ({e(m['auroc_at'])})</td></tr>")
        out.append("</table><h3>Diagnostics (not part of the gate)</h3><table><tr><th>Rows</th><th>Subtask</th>"
                   "<th>Max BA</th><th>Max AUROC</th></tr>")
        for name, d in g["diagnostics"].items():
            if name == "note":
                continue
            for sub, m in d["max"].items():
                out.append(f"<tr><td>{e(name)}</td><td>{sub}</td><td>{m['ba']}</td><td>{m['auroc']} "
                           f"({e(m['auroc_at'])})</td></tr>")
        out.append("</table>")
    split_n = Counter((c["subtask"], c["label"], c["proposed_split"]) for c in cands)
    out.append("<h2>Counts</h2><table><tr><th>Subtask</th><th>Class</th><th>Origin</th><th>dev</th><th>test</th>"
               "<th>unpublished</th></tr>")
    for sub in ("injection", "jailbreak", "leakage"):
        for lab in ("yes", "no"):
            for origin, rows in (("authored", auth), ("real", real)):
                c = Counter(x["proposed_split"] for x in rows if x["subtask"] == sub and x["label"] == lab)
                out.append(f"<tr><td>{sub}</td><td>{'attack' if lab == 'yes' else 'benign'}</td><td>{origin}</td>"
                           f"<td class=n>{c['dev']}</td><td class=n>{c['test']}</td><td class=n>{c['private']}</td></tr>")
    out.append("</table><h3>Real rows by source</h3><table><tr><th>Subtask</th><th>Source</th><th>Attack</th>"
               "<th>Benign</th></tr>")
    for sub, src in sorted({(x["subtask"], x["source"]) for x in real}):
        n = Counter(x["label"] for x in real if x["subtask"] == sub and x["source"] == src)
        out.append(f"<tr><td>{sub}</td><td>{e(src)}</td><td class=n>{n['yes']}</td><td class=n>{n['no']}</td></tr>")
    out.append("</table>")
    out.append("<h2>What to check</h2><ol><li>Each attack really is an attack of its subtask under the policy and "
               "rulings 2 and 3, and each benign twin really is benign.</li><li>The benign twins read as something a "
               "person could send. Flag pairs that are too odd to keep.</li><li>The family rules: P phrases "
               "(protected) and Q phrases (ordinary) in <code>e2_prompt_attacks_r23.py</code>. A wrong phrase "
               "affects every pair that uses it, so fix it there and rebuild.</li></ol>")
    by_fam = defaultdict(list)
    for gid, p in pairs.items():
        if "yes" in p and "no" in p:
            fam = p["yes"]["notes"].get("family")
            by_fam[(p["yes"]["subtask"], fam)].append((gid, p))
    out.append("<h2>Authored pairs</h2>")
    for (sub, fam), items in sorted(by_fam.items()):
        out.append(f"<details><summary>{sub} / {e(fam)}: {len(items)} pairs</summary>")
        for gid, p in sorted(items, key=lambda x: x[0]):
            out.append(f"<div class=pair><div class=meta>{e(gid)} &middot; {p['yes']['proposed_split']} &middot; "
                       f"P = {e(p['yes']['label_rationale'].split('(')[-1].rstrip(')'))}</div>"
                       f"<div class='row yes'><div class=tag>attack</div>{e(p['yes']['state']['text'])}</div>"
                       f"<div class='row no'><div class=tag>benign</div>{e(p['no']['state']['text'])}</div></div>")
        out.append("</details>")
    out.append("</main></body></html>")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text("\n".join(out), encoding="utf-8")
    return REVIEW


def write_packet() -> Path:
    """A blind second-label packet for the authored rows: opaque ids, shuffled, the policy, no labels."""
    cands = [c for c in e2_local.candidates(SUITE, ROOT) if c["source"] == gen.SOURCE]
    rng = random.Random(e2_local.salted("pa-r23-packet"))
    rng.shuffle(cands)
    PACKET.mkdir(parents=True, exist_ok=True)
    key, rows, tmpl = [], [], []
    for n, c in enumerate(cands):
        pid = f"r23-{n:05d}"
        rows.append({"packet_id": pid, "subtask": c["subtask"], "text": c["state"]["text"]})
        tmpl.append({"packet_id": pid, "label": None, "subtask": None, "note": None})
        key.append({"packet_id": pid, "id": c["id"]})
    _write_jsonl(PACKET / "rows.jsonl", rows)
    _write_jsonl(PACKET / "labels.template.jsonl", tmpl)
    _write_jsonl(PACKET.parent / "packet-key.jsonl", key)
    shutil.copy(build.OUT / "packet" / "00-policy.md", PACKET / "00-policy.md")
    return PACKET


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=("build", "gate", "packet"))
    ap.add_argument("--no-pools", action="store_true", help="skip the v1 F2 source pools in the authored-row screen")
    a = ap.parse_args(argv)
    if a.command == "build":
        rep = write(fetch_pools=not a.no_pools)
        print(json.dumps(rep, indent=2))
        a.command = "gate"
    if a.command == "gate":
        g = gate()
        print(json.dumps({k: g[k] for k in ("pass", "in_sample_pass", "heldback_pass", "summary", "floors",
                                            "diagnostics")}, indent=2))
    write_review()
    write_packet()
    print(f"review page: {REVIEW}\nblind packet: {PACKET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
