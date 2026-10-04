"""Edition 2 denied topics: authored cases for eight topics, plus the build of the edition 2 candidate file.

Topic set: dataset/edition2/denied_topics/topics-e2.json (the three v1 topics and the four v2 candidates verbatim, plus
TaxAdvice). A row is labelled yes when it falls within at least one of the eight definitions, no otherwise.

Sources:
- ``e2_denied_topics`` (this module, offline): 45 matched pairs per topic from e2_denied_topics_cases_v1/_v2, an
  in-topic request (yes) and a hard negative that shares its subject and vocabulary but falls outside every
  definition (no), sharing a group; plus 40 plain or mixed-vocabulary confusers (no), one group each.
- ``e2_oasst2`` (e2_denied_topics_oasst, network): real OASST2 user prompts, Apache-2.0, labelled by us.

Labels: AI-drafted by Claude on 2 October 2026 as the FIRST labeller. label_basis "llm", review_status "candidate"
until a blind second labeller (AI, then the owner, per docs/benchmark/26-edition-2-plan.md) confirms them. Every row
carries a one-line rationale. Rows a labeller could read either way are flagged in AMBIGUOUS (authored) or
e2_denied_topics_oasst.AMBIGUOUS; the flag goes in the lead key, never in the blind packet.

Splits: proposed per group, stratified by (source, topic): about 70% test, 15% tune and 15% private, so tune and
private are each about a fifth of test. Private rows are test rows with visibility "heldout". In-topic and
hard-negative rows of a pair share a group, so a pair never straddles splits. Which groups are private is not in
this file: a held-out authored case is a HeldOut placeholder in the case lists (its text in the git-ignored
private/authored.json, its source id salted, e2_local.held_out_sid), and the OASST2 prompts in the private slice are
listed in the git-ignored private config. The published order (SPLIT_SEED) only divides the other groups between
tune and test.

    uv run python -m goldrails_dataset.sources.e2_denied_topics            # rewrite dataset/edition2/denied_topics/
    uv run python -m goldrails_dataset.sources.e2_denied_topics --offline  # authored rows only, no network
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from ..records import Category, Provenance, Record, State, make_id
from .base import now
from .. import e2_local
from ..e2_local import authored, authored_keys, held_out_sid
from . import e2_denied_topics_cases_v1 as V1
from . import e2_denied_topics_cases_v2 as V2

NAME, LICENCE = "e2_denied_topics", "cc-by-4.0"
TOPIC_SET = "e2"
DRAFTED = "2026-10-02"
LABELLER = "claude (first labeller, AI)"
REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "dataset" / "edition2" / "denied_topics"
SUITE_DIR = "denied_topics"           # e2_local suite name: held-out authored cases live in its private/
TOPICS = OUT / "topics-e2.json"
SPLIT_SEED = "gold-rails-e2-denied-topics"
PACKET_SEED = "gold-rails-e2-review"
SHARES = (("test", 0.70), ("tune", 0.15), ("private", 0.15))
NOTES = f"AI-drafted {DRAFTED} by the first labeller; label proposed, pending blind second labelling"
LANG = {"In Spanish": "es", "In German": "de", "In French": "fr"}

BY_TOPIC = {
    "InvestmentAdvice": ("IA", V1.INVESTMENT), "MedicalDiagnosis": ("MD", V1.MEDICAL), "LegalAdvice": ("LA", V1.LEGAL),
    "ElectionPersuasion": ("EP", V2.ELECTION), "GamblingTips": ("GT", V2.GAMBLING),
    "EmploymentDecisions": ("ED", V2.EMPLOYMENT), "AcademicDishonesty": ("AD", V2.ACADEMIC), "TaxAdvice": ("TX", V2.TAX),
}

# In-topic rows that also fall within a second topic. The row stays yes; the key records both.
ALSO_IN = {
    "TX:in:21": ["InvestmentAdvice"], "LA:in:22": ["EmploymentDecisions"],
}

# Rows whose proposed label could reasonably go the other way under the definition as written.
AMBIGUOUS = {
    "IA:in:25": "A nonprofit's endowment rather than the user's own funds; the definition does not limit whose funds.",
    "IA:in:29": "A family office's funds; the definition does not limit whose funds.",
    "IA:hn:32": "A CD-ladder explainer may be read as an inquiry regarding allocation of funds under the broad v1 wording.",
    "LA:in:29": "A family member's case, not the user's own legal situation.",
    "LA:hn:12": "General child-support rules; a reviewer may read an implied situation of the user's own.",
    "EP:in:37": "The user's own candidacy for a club post; the definition names candidates without limiting the election.",
    "EP:in:44": "An internal party leadership vote rather than a public election.",
    "GT:in:23": "Choosing which lottery has better odds can read as odds maths, an allowed near miss.",
    "ED:hn:19": "General age-discrimination rules; LegalAdvice does not apply without the user's own situation.",
    "AD:in:07": "A personal statement is assessed but not graded coursework.",
    "AD:in:34": "A scholarship essay is judged but not graded coursework.",
    "AD:in:41": "A driving theory test is an exam but not academic work.",
    "AD:hn:33": "Same question as its in-topic pair without the exam context; a cautious reader may still flag it.",
    "TX:in:40": "Choosing between buying and leasing for a credit may read as consumer advice rather than tax advice.",
}
# Entries for held-out cases are keyed by their salted source ids and sit in the git-ignored private config.
ALSO_IN.update(e2_local.private_part(SUITE_DIR, "e2_denied_topics.ALSO_IN", {}))
AMBIGUOUS.update(e2_local.private_part(SUITE_DIR, "e2_denied_topics.AMBIGUOUS", {}))


def topics() -> list:
    return json.loads(TOPICS.read_text(encoding="utf-8"))["topics"]


def topic_names() -> list:
    return [t["name"] for t in topics()]


def lang_of(rationale: str) -> str:
    for prefix, code in LANG.items():
        if rationale.startswith(prefix):
            return code
    return "en"


def proposed_labels(topic, expected: str, also=()) -> dict:
    hit = {topic, *also} if expected == "yes" else set()
    return {n: ("yes" if n in hit else "no") for n in topic_names()}


def make_record(*, source, licence, sid, text, topic, kind, expected, group, rationale, ambiguous, lang="en",
                also=(), revision=None, upstream_split=None) -> Record:
    attribute = {"topic": topic, "kind": kind, "topic_set": TOPIC_SET, "rationale": rationale,
                 "proposed_labels": proposed_labels(topic, expected, also), "ambiguous": ambiguous, "lang": lang,
                 "labeller": LABELLER}
    if revision:
        attribute["revision"] = revision
    if upstream_split:
        attribute["upstream_split"] = upstream_split
    return Record(
        id=make_id("F3", source, sid), feature="F3", subtask="topic",
        state=State(role="user", text=text),
        category=Category(ailuminate="benign", bedrock="TOPIC" if expected == "yes" else "NONE",
                          source_label=f"{topic or 'none'}:{kind}"),
        labels=["no", "yes"], expected=expected, split="test", group=group, attribute=attribute,
        provenance=Provenance(source=source, source_id=sid, licence=licence, label_basis="llm", imported_at=now(),
                              notes=NOTES + (f"; upstream {upstream_split} split" if upstream_split else "")),
        review_status="candidate",
    )


HELD_OUT_SIDS: set = set()      # source ids of the held-out (private-slice) authored cases, filled by authored_cases()
ORDER_NAME: dict = {}           # held-out group -> the group name its pair number gives, its place in the published order


def authored_cases() -> list:
    """[(sid, topic or None, kind, text, rationale)] for every authored row, in a fixed order. A held-out case (a
    HeldOut placeholder in the tracked list) gets a salted pair token in place of its pair number, so its id does not
    follow from the tracked lists; its sid goes in HELD_OUT_SIDS."""
    out = []
    for topic, (code, rows) in BY_TOPIC.items():
        held = authored_keys(rows)
        for i, (pair, kind, text, why) in enumerate(authored(SUITE_DIR, rows)):
            n = held_out_sid(SUITE_DIR, code, pair) if i in held else f"{pair:02d}"
            out.append((f"{code}:{kind}:{n}", topic, "in_topic" if kind == "in" else "hard_negative", text, why))
            if i in held:
                HELD_OUT_SIDS.add(out[-1][0])
                ORDER_NAME[group_of_authored(out[-1][0])] = group_of_authored(f"{code}:{kind}:{pair:02d}")
    held = authored_keys(V2.CONFUSERS)
    for i, (sid, vocab, text, why) in enumerate(authored(SUITE_DIR, V2.CONFUSERS)):
        if i in held:
            ORDER_NAME[group_of_authored("cf:" + held_out_sid(held[i]))] = group_of_authored(sid)
            sid = "cf:" + held_out_sid(held[i])
            HELD_OUT_SIDS.add(sid)
        out.append((sid, None, "confuser", text, why))
    return out


def group_of_authored(sid: str) -> str:
    code, kind, n = sid.split(":") if sid.count(":") == 2 else (None, None, None)
    return f"{NAME}-{code}-{n}" if code else f"{NAME}-{sid}"


def load(limit=None) -> list:
    names = set(topic_names())
    out = []
    for sid, topic, kind, text, why in authored_cases():
        if topic is not None and topic not in names:
            raise ValueError(f"{NAME}: topic {topic!r} not in {TOPICS.name}")
        expected = "yes" if kind == "in_topic" else "no"
        out.append(make_record(source=NAME, licence=LICENCE, sid=sid, text=text, topic=topic, kind=kind, expected=expected,
                               group=group_of_authored(sid), rationale=why, ambiguous=AMBIGUOUS.get(sid),
                               lang=lang_of(why), also=ALSO_IN.get(sid, ())))
    assign_splits(out, {r.group for r in out if r.provenance.source_id in HELD_OUT_SIDS})
    return out[:limit] if limit else out


def load_oasst(fetched: dict | None = None) -> list:
    """OASST2 rows as Records. ``fetched`` is e2_denied_topics_oasst.load()'s output; None fetches (network)."""
    from . import e2_denied_topics_oasst as O
    if fetched is None:
        e2_local.require_private_config(SUITE_DIR)        # the private-slice prompts are listed there
    fetched = fetched if fetched is not None else O.load()
    out = []
    for mid, upstream, topic, kind, why in O.CASES:
        f = fetched[mid]
        if f["upstream_split"] != upstream:
            raise ValueError(f"{O.NAME}: {mid} is in {f['upstream_split']}, table says {upstream}")
        expected = "yes" if kind == "in" else "no"
        out.append(make_record(source=O.NAME, licence=O.LICENCE, sid=mid, text=f["text"], topic=topic,
                               kind="in_topic" if kind == "in" else "natural_negative", expected=expected,
                               group=f"{O.NAME}-{f['message_tree_id']}", rationale=why, ambiguous=O.AMBIGUOUS.get(mid),
                               revision=O.REVISION, upstream_split=upstream))
    assign_splits(out, {r.group for r in out if r.provenance.source_id in O.PRIVATE})
    return out


def _h(*parts) -> str:
    return hashlib.sha256(":".join([SPLIT_SEED, *map(str, parts)]).encode("utf-8")).hexdigest()


def assign_splits(records: list, private_groups=frozenset()) -> None:
    """Proposed split per group, stratified by (source, topic of the group). Sets attribute["proposed_split"], and
    split/visibility on the Record: private = test + heldout. ``private_groups`` (git-ignored: held-out authored cases,
    the private config's OASST2 prompts) are the private slice; the published order divides the rest, a group in a
    private slot of that order going to test. The order is the one the first draw used (a held-out group sits where its
    pair number put it, ORDER_NAME), so the tune split does not move."""
    groups = defaultdict(list)
    for r in records:
        groups[r.group].append(r)
    strata = defaultdict(list)
    for g, rs in groups.items():
        topic = next((r.attribute["topic"] for r in rs if r.attribute["topic"]), None)
        strata[(rs[0].provenance.source, topic)].append(g)
    for (source, topic), gs in strata.items():
        gs.sort(key=lambda g: _h(source, topic, ORDER_NAME.get(g, g)))
        n = len(gs)
        n_test = round(SHARES[0][1] * n + 1e-9)
        n_tune = round(SHARES[1][1] * n + 1e-9)
        for i, g in enumerate(gs):
            split = "private" if g in private_groups else "tune" if n_test <= i < n_test + n_tune else "test"
            for r in groups[g]:
                r.attribute["proposed_split"] = split
                r.split = "tune" if split == "tune" else "test"
                r.visibility = "heldout" if split == "private" else "public"


# --------------------------------------------------------------------------------------------------------------------
# Overlap with v1: ids and normalised texts in the v1 loaders, topic examples, samples, frozen packets and ledgers.
# --------------------------------------------------------------------------------------------------------------------

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]", " ", s.lower())).strip()


def _walk(obj, ids: set, texts: set) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("id", "record_id") and isinstance(v, str):
                ids.add(v)
            elif k in ("text", "prompt", "example") and isinstance(v, str):
                texts.add(norm(v))
            else:
                _walk(v, ids, texts)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, str) and len(v) > 25:
                texts.add(norm(v))
            else:
                _walk(v, ids, texts)


def v1_texts_from_loaders() -> set:
    from . import f3_controls, f3_controls_v2, f3_test_candidates
    out = set()
    for mod in (f3_controls, f3_controls_v2, f3_test_candidates):
        out |= {norm(r.state.text) for r in mod.load()}
    for f in ("topics.json", "topics-v2-candidates.json"):
        for t in json.loads((REPO / "benchmark" / "suites" / "denied_topics" / f).read_text(encoding="utf-8"))["topics"]:
            out |= {norm(e) for e in t["examples"]}
    return out


def v1_index(include_ledgers: bool = True) -> tuple:
    """(ids, normalised texts) found in the v1 dataset files, samples, frozen packets and (optionally) result ledgers."""
    ids, texts = set(), v1_texts_from_loaders()
    roots = [REPO / "dataset" / "samples", REPO / "dataset" / "frozen", REPO / "benchmark" / "subsets"]
    if include_ledgers:
        roots.append(REPO / "benchmark" / "results")
    for root in roots:
        for p in sorted(root.rglob("*")):
            if p.suffix == ".jsonl":
                for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.strip():
                        try:
                            _walk(json.loads(line), ids, texts)
                        except json.JSONDecodeError:
                            pass
            elif p.suffix == ".json" and p.stat().st_size < 50_000_000:
                try:
                    _walk(json.loads(p.read_text(encoding="utf-8", errors="replace")), ids, texts)
                except json.JSONDecodeError:
                    pass
    for line in (REPO / "dataset" / "frozen" / "examined-ids.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(line.strip())
    return ids, texts


def overlap(records: list, include_ledgers: bool = True) -> dict:
    ids, texts = v1_index(include_ledgers)
    seen_text, internal = {}, []
    for r in records:
        k = norm(r.state.text)
        if k in seen_text:
            internal.append([seen_text[k], r.id])
        seen_text[k] = r.id
    return {"v1_ids_indexed": len(ids), "v1_texts_indexed": len(texts),
            "id_hits": sorted(r.id for r in records if r.id in ids),
            "text_hits": sorted(r.id for r in records if norm(r.state.text) in texts),
            "internal_duplicates": internal}


# --------------------------------------------------------------------------------------------------------------------
# Candidate file, blind packet, lead key.
# --------------------------------------------------------------------------------------------------------------------

def candidate_row(r: Record) -> dict:
    a = r.attribute
    return {"id": r.id, "suite": "denied_topics", "feature": r.feature, "subtask": r.subtask, "text": r.state.text,
            "state": dataclasses.asdict(r.state), "label": r.expected, "topic": a["topic"], "kind": a["kind"],
            "proposed_labels": a["proposed_labels"], "entity_types": None, "lang": a["lang"],
            "source": r.provenance.source, "source_id": r.provenance.source_id, "licence": r.provenance.licence,
            "revision": a.get("revision"), "upstream_split": a.get("upstream_split"), "group": r.group,
            "proposed_split": a["proposed_split"], "label_rationale": a["rationale"], "ambiguous": a["ambiguous"],
            "label_basis": r.provenance.label_basis, "review_status": r.review_status, "labeller": a["labeller"],
            "topic_set": TOPIC_SET, "record": r.to_dict()}


PACKET_TASK = ("Each case is a single user message. The application denies the eight topics defined below, and only as "
               "defined. For each case, list every topic the message falls within, or write none. Sharing vocabulary "
               "with a topic is not enough. Answer unclear, with a note, when the definition does not settle the case.")

PACKET_RULES = """## How to label

You are the second, blind labeller. Another labeller has already labelled these cases; those labels are not in this packet, and you will not see them until you submit.

1. Read all eight definitions before the first case. Judge each case against the definitions as written, even where you would draw the line elsewhere; say so in the note.
2. For each case, fill `topics` with the topic names the message falls within (one or more), or `none`, or `unclear`.
3. Write a note whenever you answer unclear, and whenever the case is borderline.
4. Judge the text as it stands. Do not paste it into a chatbot or a guardrail, and do not look it up.
5. Put your name in `reviewer` and the date in `submitted_at` on every line of `labels.template.jsonl`."""


def render_packet(records: list) -> dict:
    ts = topics()
    order = sorted(records, key=lambda r: r.id)
    random.Random(PACKET_SEED).shuffle(order)
    defs = "\n".join(f"- **{t['name']}.** {t['definition']} Examples: " + "; ".join(f"\"{e}\"" for e in t["examples"]) + "."
                     + (f" Allowed near misses: {t['allowed_near_misses']}" if t.get("allowed_near_misses") else "")
                     for t in ts)
    md = ["# Review packet: Denied topics, edition 2 candidates", "", PACKET_RULES, "", "## Task", "", PACKET_TASK, "",
          defs, "", "## Cases", ""]
    template, key = [], {}
    for i, r in enumerate(order, 1):
        rid = f"e2t-r{i:04d}"
        key[rid] = r.id
        text = r.state.text.replace("\n", "\n> ")
        md += [f"### Case {i} of {len(order)}: `{rid}`", "", f"> {text}", "", "topics: ", "", "note: ", ""]
        template.append({"review_id": rid, "packet": "e2-denied-topics", "reviewer": "", "submitted_at": "",
                         "labels": {"topics": None}, "note": None})
    lead = {
        "_warning": "Lead only. Do not send this file to the second labeller.",
        "packet": "e2-denied-topics", "n_cases": len(order), "seed": PACKET_SEED,
        "first_labeller": LABELLER, "drafted": DRAFTED,
        "topics_sha256": hashlib.sha256(TOPICS.read_bytes()).hexdigest(),
        "case_text_sha256": hashlib.sha256("\n".join(sorted(r.state.text for r in records)).encode("utf-8")).hexdigest(),
        "review_id_to_record_id": key,
        "proposed": {rid: {"record_id": r.id, "label": r.expected, "proposed_labels": r.attribute["proposed_labels"],
                           "ambiguous": r.attribute["ambiguous"]} for rid, r in zip(key, order)},
        "second_look": [rid for rid, r in zip(key, order) if r.attribute["ambiguous"]],
    }
    return {"packet.md": "\n".join(md).rstrip() + "\n",
            "labels.template.jsonl": "".join(json.dumps(t, ensure_ascii=False) + "\n" for t in template), "key": lead}


def counts(records: list) -> dict:
    c = defaultdict(Counter)
    for r in records:
        a = r.attribute
        c["label"][r.expected] += 1
        c["split_label"][f"{a['proposed_split']}:{r.expected}"] += 1
        c["source_label"][f"{r.provenance.source}:{r.expected}"] += 1
        c["source_split_label"][f"{r.provenance.source}:{a['proposed_split']}:{r.expected}"] += 1
        c["topic_label"][f"{a['topic'] or 'none'}:{r.expected}"] += 1
        c["topic_split_label"][f"{a['topic'] or 'none'}:{a['proposed_split']}:{r.expected}"] += 1
        c["kind"][a["kind"]] += 1
        c["lang"][a["lang"]] += 1
        c["ambiguous_split"][f"{a['proposed_split']}:{r.expected}"] += bool(a["ambiguous"])
    return {k: dict(sorted(v.items())) for k, v in c.items()}


def write_all(offline: bool = False, include_ledgers: bool = True) -> dict:
    recs = load() + ([] if offline else load_oasst())
    for r in recs:
        r.validate()
    ov = overlap(recs, include_ledgers)
    if ov["id_hits"] or ov["text_hits"] or ov["internal_duplicates"]:
        raise SystemExit(f"overlap with v1 or within edition 2: {json.dumps(ov)[:2000]}")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = sorted((candidate_row(r) for r in recs), key=lambda d: d["id"])
    (OUT / "candidates.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in rows),
                                         encoding="utf-8")
    p = render_packet(recs)
    (OUT / "review-packet").mkdir(exist_ok=True)
    (OUT / "review-packet" / "packet.md").write_text(p["packet.md"], encoding="utf-8")
    (OUT / "review-packet" / "labels.template.jsonl").write_text(p["labels.template.jsonl"], encoding="utf-8")
    (OUT / "_lead").mkdir(exist_ok=True)
    (OUT / "_lead" / "e2-denied-topics.key.json").write_text(json.dumps(p["key"], indent=1, ensure_ascii=False) + "\n",
                                                            encoding="utf-8")
    summary = {"n": len(recs), "overlap": {k: (v if isinstance(v, int) else len(v)) for k, v in ov.items()},
               "counts": counts(recs)}
    (OUT / "counts.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    from ..e2_local import split
    split()         # the repository is public: private rows, packets, answer keys and withheld text leave tracked files
    return summary


if __name__ == "__main__":
    s = write_all(offline="--offline" in sys.argv, include_ledgers="--no-ledgers" not in sys.argv)
    print(json.dumps({"n": s["n"], "overlap": s["overlap"], "split_label": s["counts"]["split_label"]}, indent=1))
