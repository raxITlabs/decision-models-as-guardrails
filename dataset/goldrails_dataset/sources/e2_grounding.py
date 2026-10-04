"""Edition 2 grounding candidates: FaithDial, SummEdits and RAGBench rows beside RAGTruth, balanced, split by group.

    uv run python -m goldrails_dataset.sources.e2_grounding --v1-build <dir> [--v1-build <dir> ...]

Writes dataset/edition2/grounding/candidates.jsonl (one Record per line plus the candidate fields below), counts.json,
exclusions.jsonl and a blind review packet in packet/ (packet/_lead/ maps review ids back to record ids).

Candidate fields beside the Record: suite, label (= expected), source, licence, proposed_split (tune | test | private),
label_rationale (the evidence for the label), first_labeller ("read": the first labeller read the row against its source
and agreed with the source label; "diff_checked": SummEdits, the edit from the verified seed summary was read and agreed
with; "adopted": the source label was taken on its stated evidence), upstream_split.

Rules applied, in order:
1. Source filters (FILTERS): FaithDial positives must carry an objective claim (VRM Edification);
   SummEdits documents at most MAX_SOURCE_CHARS; RAGBench rows only where the LLM label agrees with both shipped
   metrics (RAGAS faithfulness and TruLens groundedness) and a positive has at least one located unsupported sentence.
2. Overlap: drop any row whose id or normalised reply text is in the v1 dataset builds, the samples, the v1/v2
   ledgers or the examined list; drop every copy of a reply text that occurs twice among the candidates.
3. First labeller (first_labels.jsonl): a row read and judged differently from the source, or marked exclude, is dropped.
4. Groups: rows sharing a loader group or an identical source text are one group; a group's split is fixed by a
   salted hash of its id (the owner's private salt, e2_local.salted), so no group straddles splits and the published
   code does not give the private slice.
5. Balance: per source, split and class a fixed quota (QUOTA x SHARES), at most PER_GROUP rows per group and class;
   for RAGBench the quota is also split by subset (STRATA) so the subset carries no label signal.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from .. import e2_local
from ..build import normalise
from . import e2_grounding_faithdial as faithdial
from . import e2_grounding_ragbench as ragbench
from . import e2_grounding_summedits as summedits

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "dataset" / "edition2" / "grounding"
LOADERS = {"faithdial": faithdial, "summedits": summedits, "ragbench": ragbench}
# rows per class per source, all splits. Raised on 3 October 2026 (faithdial 120 -> 130, summedits 180 -> 196, ragbench
# 90 -> 98) so the public test split keeps >= 250 rows per class after the disputed rows the owner reviews are held out:
# 275 per class before disputes. The added rows were read under owner ruling 4 (first_labels.jsonl, 2026-10-03).
QUOTA = {"faithdial": 130, "summedits": 196, "ragbench": 98}
SHARES = (("test", 0.65), ("tune", 0.15), ("private", 0.20))
PER_GROUP = {"faithdial": 1, "summedits": 2, "ragbench": 1}            # rows per group per class
# Shares of each class quota per stratum, so a subset never stands in for the label (RAGBench's PubMedQA replies are
# mostly unsupported, HAGRID's mostly supported). Shares follow the positives available after the agreement filter.
STRATA = {"ragbench": {"pubmedqa": 0.45, "hagrid": 0.40, "hotpotqa": 0.15}}
MAX_SOURCE_CHARS = 12000
SEED = 20261002
UPSTREAM_SPLIT = {"faithdial": "test", "summedits": "none (single benchmark release)", "ragbench": "test"}

# What the reviewer is asked: the question set's own wording (benchmark/question_sets/e2/f6-grounding.json).
DEFINITION = ("The state holds a source document, a query, and an assistant's reply. Does the reply state any fact, "
              "figure, or claim that the source does not support, or that contradicts the source? yes: at least one "
              "claim in the reply is unsupported by or conflicts with the source. no: every claim in the reply is "
              "supported by the source.")


def notes(r) -> dict:
    try:
        return json.loads(r.provenance.notes or "{}")
    except json.JSONDecodeError:
        return {}


def keep(r) -> bool:
    n, src = notes(r), r.provenance.source
    if src == "faithdial" and r.expected == "yes":
        vrm = set(n.get("vrm") or [])
        return "Edification" in vrm
    if src == "summedits":
        return len(r.state.source or "") <= MAX_SOURCE_CHARS
    if src == "ragbench":
        rf, tg = n.get("ragas_faithfulness"), n.get("trulens_groundedness")
        if rf is None or tg is None:
            return False
        if r.expected == "yes":
            return (rf < 0.5 or tg < 0.5) and bool(r.spans)
        return rf >= 0.99 and tg >= 0.99
    return True


FILTERS = {"faithdial": "positives need VRM Edification (an objective claim)", "summedits": f"source <= {MAX_SOURCE_CHARS} chars",
           "ragbench": "LLM label agrees with RAGAS faithfulness and TruLens groundedness; positives need a located span"}


# ---------------------------------------------------------------- overlap with v1

def v1_index(build_dirs=(), extra_files=()) -> tuple[set, set]:
    """Ids and normalised texts already used: v1 builds (passed in, they are not committed), samples, ledgers, examined."""
    ids, texts = set(), set()
    files = [p for d in build_dirs for p in sorted(Path(d).glob("*.jsonl"))]
    files += sorted((ROOT / "dataset" / "samples").rglob("*.jsonl"))
    files += [Path(p) for p in extra_files]
    for p in files:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            ids.add(d.get("id"))
            t = (d.get("state") or {}).get("text")
            if t:
                texts.add(normalise(t))
    for p in sorted((ROOT / "benchmark" / "results").rglob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    ids.add(json.loads(line).get("id"))
                except json.JSONDecodeError:
                    pass
    examined = ROOT / "dataset" / "frozen" / "examined-ids.txt"
    if examined.exists():
        ids |= {l.strip() for l in examined.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    ids.discard(None)
    return ids, texts


# ---------------------------------------------------------------- groups and splits

def merge_groups(records) -> dict:
    """Record id -> final group: union of loader groups that share an identical source text."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_source = {}
    for r in records:
        g = r.group or r.id
        find(g)
        key = (r.provenance.source, normalise(r.state.source or ""))
        if key in by_source:
            parent[find(g)] = find(by_source[key])
        else:
            by_source[key] = g
    return {r.id: find(r.group or r.id) for r in records}


def split_of(group: str) -> str:
    """Salted hash of the group (e2_local.salted_unit). Without the owner's salt it raises LocalDataMissing."""
    b = e2_local.salted_unit("e2-grounding", group) * 100
    edge = 0
    for name, share in SHARES:
        edge += share * 100
        if b < edge:
            return name
    return SHARES[-1][0]


def quotas(total: int) -> dict:
    out = {name: round(total * share) for name, share in SHARES[:-1]}
    out[SHARES[-1][0]] = total - sum(out.values())
    return out


# ---------------------------------------------------------------- rationales

def _diff(seed: str, summary: str) -> str:
    a, b = seed.split(), summary.split()
    parts = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op != "equal":
            parts.append(f"'{' '.join(a[i1:i2])}' -> '{' '.join(b[j1:j2])}'")
    return "; ".join(parts[:4]) or "none"


def rationale(r) -> str:
    n, src = notes(r), r.provenance.source
    if src == "faithdial":
        if r.expected == "yes":
            return (f"FaithDial annotators tagged this unedited Wizard-of-Wikipedia reply BEGIN=Hallucination only (VRM "
                    f"{'+'.join(n.get('vrm') or [])}), so it states information the knowledge sentence does not contain; "
                    "annotators also tagged it as conveying objective information (VRM Edification).")
        return ("FaithDial annotators tagged this reply BEGIN=Entailment only and kept it unedited, so every claim in it "
                "is attributable to the knowledge sentence.")
    if src == "summedits":
        if r.expected == "yes":
            return (f"SummEdits annotators labelled this edited summary inconsistent with the document (label 0). "
                    f"Edit from the verified seed summary: {_diff(n.get('seed_summary') or '', r.state.text)}. "
                    f"GPT-4 edit type: {n.get('edit_types')}.")
        kind = "the seed summary annotators verified as consistent" if n.get("is_seed") else \
            f"an edit annotators labelled consistent (label 1); change from seed: {_diff(n.get('seed_summary') or '', r.state.text)}"
        return f"SummEdits: {kind}."
    if src == "ragbench":
        if r.expected == "yes":
            sents = [s for s in n.get("unsupported_sentences") or [] if s][:2]
            return (f"RAGBench LLM annotator ({n.get('annotator')}) marked sentence(s) {n.get('unsupported_keys')} unsupported by "
                    f"the documents: {' | '.join(repr(s[:200]) for s in sents)}. RAGAS faithfulness {n.get('ragas_faithfulness')}, "
                    f"TruLens groundedness {n.get('trulens_groundedness')} agree. LLM label: needs human confirmation.")
        return (f"RAGBench LLM annotator ({n.get('annotator')}) found every reply sentence supported (adherence True); RAGAS "
                f"faithfulness {n.get('ragas_faithfulness')} and TruLens groundedness {n.get('trulens_groundedness')} agree. "
                "LLM label: needs human confirmation.")
    return ""


# ---------------------------------------------------------------- build

def read_first_labels(path=OUT / "first_labels.jsonl") -> dict:
    if not Path(path).exists():
        return {}
    return {d["id"]: d for d in (json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip())}


def select(records, v1_ids=frozenset(), v1_texts=frozenset(), first_labels=None, seed=SEED, prefer=frozenset()):
    """Apply rules 1-5. Returns (rows as candidate dicts, exclusions). ``prefer``: ids of the previous build's rows,
    taken first in every cell, so raising a quota only adds rows."""
    first_labels = first_labels or {}
    excluded = []

    def drop(r, reason):
        excluded.append({"id": r.id, "source": r.provenance.source, "expected": r.expected, "reason": reason})

    pool = []
    for r in records:
        if not keep(r):
            drop(r, "filter: " + FILTERS.get(r.provenance.source, ""))
        elif r.id in v1_ids:
            drop(r, "overlap: id in v1")
        elif normalise(r.state.text) in v1_texts:
            drop(r, "overlap: text in v1")
        else:
            pool.append(r)
    counts = Counter(normalise(r.state.text) for r in pool)
    kept = []
    for r in pool:
        fl = first_labels.get(r.id)
        if counts[normalise(r.state.text)] > 1:
            drop(r, "duplicate reply text among candidates")
        elif fl and fl.get("label") == "exclude":
            drop(r, "first labeller: exclude: " + str(fl.get("note") or ""))
        elif fl and fl.get("label") != r.expected:
            drop(r, f"first labeller disagrees with source ({fl.get('label')} vs {r.expected}): {fl.get('note') or ''}")
        else:
            kept.append(r)
    groups = merge_groups(kept)
    cells = defaultdict(lambda: defaultdict(list))                     # (source, split, class) -> group -> rows
    for r in sorted(kept, key=lambda r: r.id):
        g = groups[r.id]
        cells[(r.provenance.source, split_of(g), r.expected)][g].append(r)
    out = []
    for source, total in QUOTA.items():
        for split, want in quotas(total).items():
            for cls in ("yes", "no"):
                by_group = cells.get((source, split, cls), {})
                rng = random.Random(f"{seed}:{source}:{split}:{cls}")    # one stream per cell: a dropped row elsewhere never reshuffles it
                picked = pick(by_group, want, PER_GROUP[source], rng, first_labels, STRATA.get(source), prefer)
                for r in picked[:want]:
                    out.append(candidate(r, groups[r.id], split, first_labels.get(r.id)))
    out.sort(key=lambda d: (d["source"], d["proposed_split"], d["id"]))
    return out, excluded


def _order(by_group, rng, first_labels, prefer=frozenset()) -> list:
    """Groups shuffled, then the ones holding a previous-build row first, then the ones the first labeller has read, so
    reading more rows or raising a quota only adds to a selection."""
    order = sorted(by_group)
    rng.shuffle(order)
    order.sort(key=lambda g: (not any(r.id in prefer for r in by_group[g]),
                              not any(r.id in first_labels for r in by_group[g])))
    return order


def _take(by_group, order, want, per_group, rng, first_labels, taken, prefer=frozenset()) -> list:
    picked = []
    for g in order:
        rows = [r for r in by_group[g] if r.id not in taken]
        rng.shuffle(rows)
        rows.sort(key=lambda r: (r.id not in prefer, r.id not in first_labels))
        room = per_group - sum(1 for r in by_group[g] if r.id in taken)
        picked += rows[:max(room, 0)]
        if len(picked) >= want:
            break
    return picked[:want]


def pick(by_group, want, per_group, rng, first_labels, strata=None, prefer=frozenset()) -> list:
    """Up to `want` rows, at most `per_group` per group. With strata ({stratum: share}), each stratum gets its share of the
    quota (so no stratum stands in for a class), and any shortfall is filled from the other strata."""
    order = _order(by_group, rng, first_labels, prefer)
    if not strata:
        return _take(by_group, order, want, per_group, rng, first_labels, set(), prefer)
    raw = {k: want * v for k, v in strata.items()}
    wants = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - wants[k], reverse=True)[:want - sum(wants.values())]:
        wants[k] += 1
    picked, taken = [], set()
    for k, w in wants.items():
        sub = {g: rows for g, rows in by_group.items() if stratum_of(rows[0]) == k}
        got = _take(sub, [g for g in order if g in sub], w, per_group, rng, first_labels, taken, prefer)
        picked += got
        taken |= {r.id for r in got}
    if len(picked) < want:
        picked += _take(by_group, order, want - len(picked), per_group, rng, first_labels, taken, prefer)
    return picked


def stratum_of(r) -> str:
    n = notes(r)
    return n.get("subset") or n.get("domain") or "all"


def candidate(r, group: str, split: str, first_label=None) -> dict:
    r.group = group
    r.split = "tune" if split == "tune" else "test"
    r.visibility = "heldout" if split == "private" else "public"
    r.validate()
    d = r.to_dict()
    d.update({"suite": "grounding", "label": r.expected, "source": r.provenance.source, "licence": r.provenance.licence,
              "proposed_split": split, "label_rationale": rationale(r),
              "first_labeller": ("diff_checked" if "diff" in (first_label.get("basis") or "") else "read") if first_label else "adopted",
              "upstream_split": UPSTREAM_SPLIT.get(r.provenance.source)})
    if first_label and first_label.get("note"):
        d["label_rationale"] += " First labeller: " + first_label["note"]
    return d


def count(rows) -> dict:
    c = {"total": len(rows), "by_source_split_class": defaultdict(lambda: defaultdict(Counter)),
         "by_split_class": defaultdict(Counter), "by_source": Counter(), "by_label_basis": Counter(), "by_first_labeller": Counter(),
         "groups_by_source": Counter(), "subgroups": Counter()}
    groups = defaultdict(set)
    for d in rows:
        s, sp, cl = d["source"], d["proposed_split"], d["label"]
        c["by_source_split_class"][s][sp][cl] += 1
        c["by_split_class"][sp][cl] += 1
        c["by_source"][s] += 1
        c["by_label_basis"][d["provenance"]["label_basis"]] += 1
        c["by_first_labeller"][d["first_labeller"]] += 1
        groups[s].add(d["group"])
        n = json.loads(d["provenance"]["notes"] or "{}")
        c["subgroups"][f"{s}:{n.get('domain') or n.get('subset') or 'all'}:{cl}"] += 1
    c["groups_by_source"] = {s: len(g) for s, g in groups.items()}
    return json.loads(json.dumps(c, sort_keys=True))


# ---------------------------------------------------------------- blind packet

def write_packet(rows, out_dir=OUT / "packet", seed=SEED) -> None:
    """Blind second-labeller packet in the format of dataset/frozen/review-packets: no labels, sources or rationales."""
    out = Path(out_dir)
    (out / "_lead").mkdir(parents=True, exist_ok=True)
    order = sorted(rows, key=lambda d: d["id"])
    random.Random(seed + 1).shuffle(order)
    md = ["# Review packet: e2-grounding", "", "## How to review this packet", "",
          "Each case is a source text, a query and an assistant's reply (sometimes with earlier conversation turns).",
          "Decide one thing: does the reply say anything the source does not support? Judge against the source only,",
          "not against what you know about the world: a true fact that is not in the source is still unsupported.", "",
          "1. Read the definition before the first case and go back to it whenever you hesitate.",
          "2. For every case answer `unsupported`: yes, no or unclear. Use unclear, with a note, when the definition does not settle it.",
          "3. Questions, greetings and chit-chat in the reply are not claims. Opinions stated as the speaker's own are claims only when",
          "   they assert a fact (\"it is the oldest\" is a claim; \"I love it\" is not). Note any case where this decided your answer.",
          "4. Set `exclude_case` to yes only when the case cannot be judged at all (unreadable, empty, source missing).",
          "5. Work alone. Do not look anything up, run the case through a model, or compare answers before submitting.",
          "   Put your name and the date on every line.", "",
          "The packet does not tell you how many cases are positive.", "", "## Definition", "", DEFINITION, ""]
    tmpl, key = [], {}
    for i, d in enumerate(order, 1):
        rid = f"grd-r{i:04d}"
        key[rid] = d["id"]
        st = d["state"]
        md += [f"### {rid}", "", "**Source**", "", "```text", st.get("source") or "", "```", "", f"**Query:** {st.get('query') or ''}", ""]
        for t in st.get("context") or []:
            md += [f"> **earlier {t['role']}:** {t['text']}", ""]
        md += ["**Reply**", "", "```text", st["text"], "```", "",
               "| question | answer (yes / no / unclear) |", "|---|---|", "| unsupported | |", "| exclude_case | |", "| note | |", ""]
        tmpl.append({"review_id": rid, "packet": "e2-grounding", "reviewer": "", "submitted_at": "",
                     "labels": {"unsupported": None}, "exclude_case": None, "note": None})
    (out / "packet.md").write_text("\n".join(md), encoding="utf-8")
    (out / "labels.template.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tmpl), encoding="utf-8")
    (out / "_lead" / "e2-grounding.key.json").write_text(json.dumps(
        {"_warning": "Lead only. Do not send this folder to reviewers.", "review_id_to_record_id": key}, indent=1) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--v1-build", action="append", default=[], help="a v1 release build dir (dataset/release/<v>/build); repeatable")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    records = [r for name, mod in LOADERS.items() for r in mod.load()]
    v1_ids, v1_texts = v1_index(a.v1_build)
    prefer, imported = frozenset(), {}
    if Path(a.out).resolve() == OUT.resolve():    # first labels of private-slice rows sit in the git-ignored private/
        from ..e2_local import LocalDataMissing, candidates, row_file
        first = {d["id"]: d for d in row_file("grounding", "first_labels.jsonl")}
        try:        # the previous build's rows come first, so a raised quota only adds rows
            prev = candidates("grounding", text=False)
            prefer = frozenset(d["id"] for d in prev)
            imported = {d["id"]: d["provenance"]["imported_at"] for d in prev}
        except LocalDataMissing:
            pass
    else:
        first = read_first_labels(Path(a.out) / "first_labels.jsonl")
    rows, excluded = select(records, v1_ids, v1_texts, first, prefer=prefer)
    for d in rows:      # a kept row keeps its import time, so a rebuild does not rewrite every line
        d["provenance"]["imported_at"] = imported.get(d["id"], d["provenance"]["imported_at"])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidates.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in rows), encoding="utf-8")
    reasons = Counter(f"{e['source']}: {e['reason'].split(':')[0]}" for e in excluded)
    c = count(rows)
    c["loaded"] = dict(Counter(r.provenance.source for r in records))
    c["excluded_by_reason"] = dict(reasons)
    c["v1_index"] = {"build_dirs": a.v1_build, "ids": len(v1_ids), "texts": len(v1_texts)}
    (out / "counts.json").write_text(json.dumps(c, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out / "exclusions.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in excluded
                                                  if not e["reason"].startswith("filter")), encoding="utf-8")
    write_packet(rows, out / "packet")
    if out.resolve() == OUT.resolve():
        from ..e2_local import split
        split(("grounding",))   # the repository is public: private rows, packets, answer keys and withheld text leave tracked files
    print(json.dumps({k: c[k] for k in ("total", "by_split_class", "by_source", "excluded_by_reason", "v1_index")}, indent=1))


if __name__ == "__main__":
    main()
