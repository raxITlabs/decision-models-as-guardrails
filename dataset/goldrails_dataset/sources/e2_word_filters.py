"""Edition 2 word filters: the profanity rows (a scored subtask) and the build of dataset/edition2/word_filters/.

Policy. ``benchmark/policies/word_filters/profanity.md``: semantic profanity, the reviewed ``DEFINITION`` in
``civil_comments_profanity`` (imported here unchanged). A message is yes when it holds at least one swear word or
vulgar term, quoted, reported, friendly or aimed at nobody; no when the letters only sit inside a longer ordinary word,
when the word is used in its ordinary literal or religious sense, or when an insult, threat or sexual content uses no
vulgar word. Masked spellings (f*ck) belong to the diagnostic subtask ``profanity_obfuscated``; a row whose only
candidate term is masked is not selected.

Sources (owner ruling 13 keeps profanity scored at >= 250/250 public test rows from >= 2 sources; Civil Comments was
used in v1 profanity and in Strands Decider's training, so two other redistributable sources are added, and every row
names its source):

- ``e2_profanity_civil_comments``: ``google/civil_comments`` (CC0-1.0, revision f2970eb3), validation and test splits,
  every v1 row and text left out. Tagged ``strands-decider-train`` in provenance.contamination.
- ``e2_profanity_rtp``: ``allenai/real-toxicity-prompts`` (Apache-2.0, revision f2162971): one web sentence, the
  prompt and its continuation joined back together. Group: the source document.
- ``e2_profanity_oasst2``: ``OpenAssistant/oasst2`` (Apache-2.0, revision 179dd21f), English chat messages (user and
  assistant turns), not deleted, not rejected in review. Group: the conversation tree. Messages the denied-topics
  suite already uses are left out.

Selection (``select``, run once; it writes the frozen pool to ``word_filters/private/pool.jsonl``, git-ignored
because two of the three sources are not cleared for text in ``dataset/release/redistribution.json``). The upstream
scores (Civil Comments rater fractions, Perspective scores in RTP, Detoxify scores in OASST2) and the term list below
pick candidates only; they are never the label. Buckets per source:

- ``strong``: a term from ``STRONG`` as a whole word;
- ``ambiguous``: only terms from ``AMBIGUOUS`` as whole words (hell, ass, cock, dick, bloody...): the literal and
  religious senses live here, so the label is read, not inferred;
- ``confuser``: no listed term as a whole word, but a listed term's letters inside a longer ordinary word
  (Scunthorpe, cocktail, assess, Dickens), capped per containing word so one word cannot dominate;
- ``insult``: no listed term and no confuser, a high upstream insult or toxicity score: rude without a vulgar word;
- ``meta``: no listed term, the message talks about swearing or profanity;
- ``clean``: no listed term, no confuser, low upstream toxicity.

No model output is used to select or retire a row (no adversarial filtering).

Labels. First labeller: Claude (AI), 4 October 2026, every row read against ``DEFINITION``; ``label_basis`` "llm",
``review_status`` "candidate". A row the definition does not settle is excluded with a reason
(``private/first-labels.jsonl``, ``exclude``), never forced. The second label comes from a blind second labeller
(``relabel.jsonl``), not from this module.

Splits: per group, stratified by (source, label): about 70% test, 15% tune, 15% private (test rows held out).

    uv run python -m goldrails_dataset.sources.e2_word_filters select      # network or HF cache: frozen pool
    uv run python -m goldrails_dataset.sources.e2_word_filters packet      # private/ labelling sheet for the pool
    uv run python -m goldrails_dataset.sources.e2_word_filters build       # pool + labels + custom words -> files
    uv run python -m goldrails_dataset.sources.e2_word_filters counts      # counts per split, class and source
"""
from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from ..records import Category, Provenance, Record, State, make_id
from .civil_comments_profanity import DEFINITION, MASKED

SUITE = "word_filters"
REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "dataset" / "edition2" / SUITE
PRIVATE = OUT / "private"
POOL = PRIVATE / "pool.jsonl"
FIRST_LABELS = PRIVATE / "first-labels.jsonl"
IMPORTED_AT = "2026-10-04T00:00:00+00:00"
LABELLER = "claude (first labeller, AI)"
DRAFTED = "2026-10-04"
SEED = 20261004
SPLIT_SEED = "gold-rails-e2-word-filters"
SHARES = (("test", 0.70), ("tune", 0.15), ("private", 0.15))
LENGTH = (40, 600)

CC = {"name": "e2_profanity_civil_comments", "licence": "cc0-1.0", "repo": "google/civil_comments",
      "revision": "f2970eb3a55777454c94069077cc8d9b5866312d",
      "files": ("data/validation-00000-of-00001.parquet", "data/test-00000-of-00001.parquet"),
      "contamination": ["jigsaw-unintended-bias-2019-public", "strands-decider-train"]}
RTP = {"name": "e2_profanity_rtp", "licence": "apache-2.0", "repo": "allenai/real-toxicity-prompts",
       "revision": "f21629712ffd6a3d13a54fd2807ccd521c55ef74", "files": ("prompts.jsonl",),
       "contamination": ["realtoxicityprompts-public", "openwebtext"]}
OASST = {"name": "e2_profanity_oasst2", "licence": "apache-2.0", "repo": "OpenAssistant/oasst2",
         "revision": "179dd21fc55192153d94adb0e0ce8f69e222bf75", "files": ("2023-11-05_oasst2_all.messages.jsonl.gz",),
         "contamination": ["oasst2-public-train"]}
SOURCES = {s["name"]: s for s in (CC, RTP, OASST)}

# Candidate finders, not labels. STRONG: swear words with no common clean sense. AMBIGUOUS: words with an ordinary
# literal or religious sense (a rooster, a donkey, a place, a name), or a mild expletive whose use must be read.
STRONG = (r"\w*fuck\w*", r"\w*shit\w*", r"cunts?", r"twats?", r"\w*ass(?:hole|holes|hat|hats|wipe|clown)",
          r"arseholes?", r"(?:dumb|jack|smart|kick|bad|lard|fat)ass(?:es)?", r"bitch\w*", r"bastards?",
          r"dickheads?", r"cocksuck\w*", r"wank\w*", r"bollocks", r"tits", r"titt(?:y|ies)", r"jizz",
          r"goddam\w*", r"god damn\w*", r"damn\w*", r"dammit", r"crap\w*", r"piss\w*", r"bullcrap", r"douchebag\w*")
AMBIGUOUS = (r"hell", r"ass", r"asses", r"arse", r"bloody", r"dicks?", r"cocks?", r"puss(?:y|ies)", r"pricks?",
             r"bugger\w*", r"balls", r"sod")
# Letters of a listed term inside a longer ordinary word (the Scunthorpe problem).
STEMS = ("ass", "cock", "dick", "cum", "tit", "anal", "arse", "shit", "cunt", "piss", "hell", "crap", "damn", "twat",
         "wank", "fuck", "bitch", "prick", "puss", "sex", "rape")
META = re.compile(r"\b(?:swear(?:ing|s)?|curse words?|cuss(?:ing|words?)?|profan\w+|obscen\w+|f-word|four[- ]letter "
                  r"words?|expletives?|bad language|foul language|vulgar\w*)\b", re.I)


def _whole(alts) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(alts) + r")(?![a-z0-9])", re.I)


STRONG_RE, AMBIGUOUS_RE = _whole(STRONG), _whole(AMBIGUOUS)
WORD_RE = re.compile(r"[a-z]+", re.I)
BUCKETS = ("strong", "ambiguous", "confuser", "insult", "meta", "clean")
TARGETS = {
    CC["name"]: {"strong": 125, "ambiguous": 110, "confuser": 70, "insult": 50, "meta": 15, "clean": 45},
    RTP["name"]: {"strong": 110, "ambiguous": 85, "confuser": 60, "insult": 35, "meta": 10, "clean": 40},
    OASST["name"]: {"strong": 65, "ambiguous": 45, "confuser": 35, "insult": 15, "meta": 15, "clean": 30},
}
CONFUSER_CAP = 3        # rows per containing word in the confuser bucket


def norm(text) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def terms_in(text: str) -> dict:
    """{"strong": [...], "ambiguous": [...], "masked": [...], "confusers": [...]} found in a text (lower case)."""
    low = text.lower()
    strong = sorted({m.group(0).lower() for m in STRONG_RE.finditer(low)})
    amb = sorted({m.group(0).lower() for m in AMBIGUOUS_RE.finditer(low)})
    masked = sorted({m.group(0).lower() for m in MASKED.finditer(text)} - set(strong) - set(amb))
    listed = set(strong) | set(amb)
    conf = sorted({w for w in (x.lower() for x in WORD_RE.findall(text)) if w not in listed and len(w) > 3
                   and any(s in w and s != w for s in STEMS) and not STRONG_RE.fullmatch(w)
                   and not AMBIGUOUS_RE.fullmatch(w)})
    return {"strong": strong, "ambiguous": amb, "masked": masked, "confusers": conf}


def english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) >= 0.97


def bucket_of(text: str, insult: float, toxicity: float) -> tuple[str | None, dict]:
    t = terms_in(text)
    if t["masked"]:
        return None, t                          # masked spelling: the diagnostic subtask, not this one
    if t["strong"]:
        return "strong", t
    if t["ambiguous"]:
        return "ambiguous", t
    if t["confusers"]:
        return "confuser", t
    if META.search(text):
        return "meta", t
    if max(insult, toxicity) >= 0.6:
        return "insult", t
    if toxicity < 0.1:
        return "clean", t
    return None, t


# --- upstream readers (network or the Hugging Face cache) --------------------------------------------------------------

def _hf(src: dict, f: str) -> str:
    from huggingface_hub import hf_hub_download
    return hf_hub_download(src["repo"], f, repo_type="dataset", revision=src["revision"])


def read_civil_comments():
    import pyarrow.parquet as pq
    for f in CC["files"]:
        split = f.split("/")[-1].split("-")[0]
        cols = ["text", "toxicity", "obscene", "insult"]
        for i, r in enumerate(pq.read_table(_hf(CC, f), columns=cols).to_pylist()):
            yield {"source": CC["name"], "source_id": f"{split}:{i}", "group": f"cc:{split}:{i}", "role": "user",
                   "text": (r["text"] or "").strip(), "upstream_split": split,
                   "scores": {"toxicity": r["toxicity"], "obscene": r["obscene"], "insult": r["insult"]},
                   "insult": float(r["insult"] or 0), "toxicity": float(r["toxicity"] or 0)}


def read_rtp():
    with open(_hf(RTP, "prompts.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            p, c = d["prompt"], d["continuation"]
            text = ((p.get("text") or "") + (c.get("text") or "")).strip()
            sc = lambda k: max(float(p.get(k) or 0), float(c.get(k) or 0))
            yield {"source": RTP["name"], "source_id": f"{d['filename']}:{d['begin']}-{d['end']}",
                   "group": f"rtp:{d['filename']}", "role": "user", "text": text, "upstream_split": "all",
                   "scores": {k: round(sc(k), 4) for k in ("toxicity", "profanity", "insult")},
                   "challenging": d.get("challenging"), "insult": sc("insult"), "toxicity": sc("toxicity")}


def read_oasst(skip_ids: set):
    with gzip.open(_hf(OASST, OASST["files"][0]), "rt", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if d.get("lang") != "en" or d.get("deleted") or d.get("review_result") is False:
                continue
            if d["message_id"] in skip_ids:
                continue
            dx = d.get("detoxify") or {}
            yield {"source": OASST["name"], "source_id": d["message_id"], "group": f"oasst2:{d['message_tree_id']}",
                   "role": "user" if d["role"] == "prompter" else "assistant", "text": (d["text"] or "").strip(),
                   "upstream_split": "all",
                   "scores": {k: round(float(dx.get(k) or 0), 4) for k in ("toxicity", "obscene", "insult")},
                   "insult": float(dx.get("insult") or 0), "toxicity": float(dx.get("toxicity") or 0)}


# --- what must not be selected again ------------------------------------------------------------------------------------

def _walk_texts(x, out: set) -> None:
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "text" and isinstance(v, str):
                out.add(norm(v))
            else:
                _walk_texts(v, out)
    elif isinstance(x, list):
        for v in x:
            _walk_texts(v, out)


def reference_texts() -> tuple[set, list]:
    """(normalised texts, v1 profanity and word row texts) never to select: every v1 release build and sample (the
    main checkout's git-ignored builds included), the frozen dataset files, the result ledgers, and every other edition 2
    suite's candidates (text restored where this machine has it)."""
    from .. import e2_local
    from ..edition2 import v1_row_files
    texts, v1_f4 = set(), []
    files = list(v1_row_files())
    for root in (REPO / "dataset" / "frozen", REPO / "benchmark" / "results", REPO / "benchmark" / "subsets"):
        files += sorted(str(p) for p in root.rglob("*.jsonl"))
    for f in files:
        for line in Path(f).read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            _walk_texts(d, texts)
            if isinstance(d, dict) and d.get("feature") == "F4" and isinstance(d.get("state"), dict):
                v1_f4.append(d["state"].get("text") or "")
    for s in e2_local.SUITES:
        if s == SUITE:                  # this suite's own rows are what is being checked
            continue
        try:
            rows = e2_local.candidates(s)
        except e2_local.LocalDataMissing:
            rows = e2_local.candidates(s, private=False, text=False)
        for c in rows:
            _walk_texts(c.get("state"), texts)
    return texts, v1_f4


def denied_topics_oasst_ids() -> set:
    from . import e2_denied_topics_oasst as O
    return {c[0] for c in O.CASES}


# --- selection --------------------------------------------------------------------------------------------------------

def select(write: bool = True) -> list:
    """Draw the frozen pool. Deterministic for a given upstream revision."""
    from goldrails_bench import overlap
    seen, v1_f4 = reference_texts()
    v1_sh = [overlap.shingles(t) for t in v1_f4 if t]
    readers = ((CC["name"], read_civil_comments()), (RTP["name"], read_rtp()),
               (OASST["name"], read_oasst(denied_topics_oasst_ids())))
    pool = []
    for name, rows in readers:
        pools = defaultdict(list)
        taken_text = set()
        for r in rows:
            t = r["text"]
            if not LENGTH[0] <= len(t) <= LENGTH[1] or not english(t):
                continue
            n = norm(t)
            if n in seen or n in taken_text:
                continue
            b, terms = bucket_of(t, r["insult"], r["toxicity"])
            if b is None:
                continue
            taken_text.add(n)
            pools[b].append({**{k: v for k, v in r.items() if k not in ("insult", "toxicity")}, "bucket": b,
                             "terms": terms})
        rng = random.Random(f"{SEED}:{name}")
        groups_taken = set()
        for b in BUCKETS:
            cand = sorted(pools[b], key=lambda r: r["source_id"])
            rng.shuffle(cand)
            per_word, picked = Counter(), 0
            for r in cand:
                if picked >= TARGETS[name][b]:
                    break
                if r["group"] in groups_taken and name != CC["name"]:
                    continue                     # one row per document or conversation tree: groups stay small
                if b == "confuser":
                    key = r["terms"]["confusers"][0]
                    if per_word[key] >= CONFUSER_CAP:
                        continue
                    per_word[key] += 1
                sh = overlap.shingles(r["text"])
                if any(overlap.is_near_duplicate(sh, v) for v in v1_sh):
                    continue
                groups_taken.add(r["group"])
                pool.append(r)
                picked += 1
    for r in pool:
        r["key"] = make_id("F4", r["source"], r["source_id"])
    pool.sort(key=lambda r: r["key"])
    if write:
        POOL.parent.mkdir(parents=True, exist_ok=True)
        POOL.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in pool), encoding="utf-8")
    return pool


def read_pool() -> list:
    from .. import e2_local
    if not POOL.exists():
        raise e2_local.LocalDataMissing(f"{POOL} is not on this machine: the frozen pool is git-ignored")
    return [json.loads(l) for l in POOL.read_text(encoding="utf-8").splitlines() if l.strip()]


def read_first_labels() -> dict:
    from .. import e2_local
    if not FIRST_LABELS.exists():
        raise e2_local.LocalDataMissing(f"{FIRST_LABELS} is not on this machine: first labels of the pool are private")
    out = {}
    for line in FIRST_LABELS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d["id"] in out:
                raise ValueError(f"first-labels.jsonl lists {d['id']} twice")
            out[d["id"]] = d
    return out


# --- records, groups, splits --------------------------------------------------------------------------------------------

def profanity_record(r: dict, label: str, split: str, group: str) -> Record:
    src = SOURCES[r["source"]]
    notes = {"repo": src["repo"], "revision": src["revision"], "bucket": r["bucket"],
             "selection": "bucket from the term list and upstream scores; they pick candidates and are never the label",
             "upstream_scores": r["scores"], "upstream_split": r["upstream_split"]}
    if r.get("challenging") is not None:
        notes["rtp_challenging"] = r["challenging"]
    return Record(
        id=r["key"], feature="F4", subtask="profanity", state=State(role=r["role"], text=r["text"]),
        category=Category(ailuminate=None, bedrock="PROFANITY" if label == "yes" else "NONE", source_label=None),
        labels=["no", "yes"], expected=label, split="tune" if split == "tune" else "test",
        visibility="heldout" if split == "private" else "public", group=group,
        attribute={"bucket": r["bucket"], "upstream_split": r["upstream_split"]},
        provenance=Provenance(source=r["source"], source_id=r["source_id"], licence=src["licence"], label_basis="llm",
                              imported_at=IMPORTED_AT, contamination=list(src["contamination"]),
                              notes=json.dumps(notes, sort_keys=True)),
        review_status="candidate")


def near_duplicate_groups(rows: list) -> dict:
    """{upstream group: joined group}: rows whose texts are near-duplicates (goldrails_bench.overlap rule) share one
    group, named after the smallest member, so they always land in one split."""
    from goldrails_bench import overlap
    parent = {r["group"]: r["group"] for r in rows}

    def find(g):
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g
    sh = [overlap.shingles(r["text"]) for r in rows]
    for i, j, _, _ in overlap.near_duplicate_pairs(sh):
        a, b = find(rows[i]["group"]), find(rows[j]["group"])
        if a != b:
            parent[max(a, b)] = min(a, b)
    return {g: find(g) for g in parent}


def assign_splits(items: list) -> dict:
    """{group: split} for [(group, stratum)], about SHARES of the groups of each stratum, in a seeded hash order."""
    strata = defaultdict(set)
    for g, s in items:
        strata[s].add(g)
    out = {}
    for s, groups in sorted(strata.items()):
        order = sorted(groups, key=lambda g: hashlib.sha256(f"{SPLIT_SEED}:{g}".encode()).hexdigest())
        n = len(order)
        for k, g in enumerate(order):
            frac = k / n
            out[g] = "test" if frac < SHARES[0][1] else "tune" if frac < SHARES[0][1] + SHARES[1][1] else "private"
    return out


def profanity_candidates() -> tuple[list, list]:
    """(candidate rows, excluded rows) from the frozen pool and the first labels."""
    pool, labels = read_pool(), read_first_labels()
    missing = [r["key"] for r in pool if r["key"] not in labels]
    if missing or set(labels) - {r["key"] for r in pool}:
        raise ValueError(f"first labels and pool differ: {len(missing)} pool rows unlabelled")
    kept = [r for r in pool if labels[r["key"]]["label"] in ("yes", "no")]
    excluded = [{"id": r["key"], "source": r["source"], "bucket": r["bucket"], "exclude": labels[r["key"]]["exclude"]}
                for r in pool if labels[r["key"]]["label"] is None]
    joined = near_duplicate_groups(kept)
    by_group = defaultdict(list)
    for r in kept:
        by_group[joined[r["group"]]].append(r)
    # stratum: (source, label of the group's first row by key); a mixed group follows its first row
    items = [(g, (min(rs, key=lambda r: r["key"])["source"], labels[min(rs, key=lambda r: r["key"])["key"]]["label"]))
             for g, rs in by_group.items()]
    splits = assign_splits(items)
    out = []
    for r in kept:
        lab = labels[r["key"]]
        g = joined[r["group"]]
        rec = profanity_record(r, lab["label"], splits[g], g)
        out.append({**rec.to_dict(), "suite": SUITE, "label": lab["label"], "proposed_split": splits[g],
                    "source": r["source"], "licence": SOURCES[r["source"]]["licence"], "bucket": r["bucket"],
                    "labeller": lab["labeller"], "label_rationale": lab["rationale"], "label_basis": "llm",
                    "upstream_split": r["upstream_split"]})
    return out, excluded


def words_candidates() -> list:
    from . import e2_word_filters_words as W
    return [{**r.to_dict(), "suite": SUITE, "label": r.expected, "proposed_split": r.split, "source": W.NAME,
             "licence": W.LICENCE, "bucket": r.attribute["kind"], "labeller": "deterministic (words.json rule)",
             "label_rationale": f"{'matches' if r.expected == 'yes' else 'does not match'}: {r.attribute['kind']}",
             "label_basis": "deterministic", "upstream_split": None} for r in W.records()]


def words_second_labels(rows: list) -> list:
    """The regex baseline's verdict on every custom-words row: an independent implementation of the rule."""
    from goldrails_bench.regex_words import RegexWordClient
    c = RegexWordClient()
    out = []
    for row in rows:
        hit = c.ask({"role": "user", "text": row["state"]["text"]}, {"any_word": {}}).answers["any_word"]["noul"]
        out.append({"id": row["id"], "label": "yes" if hit == 1.0 else "no", "subtask": "word",
                    "labeller": "regex baseline (goldrails_bench.regex_words, words.json rule)",
                    "rationale": "exact phrase, case-insensitive, whole words"})
    return out


# --- e2_local: this suite is split and scanned like the five others ---------------------------------------------------

@contextlib.contextmanager
def registered():
    """e2_local with word_filters added to its suites, so ``split``, ``leak_needles`` and ``rehydrate`` treat this folder
    the way they treat the other five. Restores e2_local afterwards. Once the integration adds the suite to
    e2_local.SUITES, this is a no-op."""
    from .. import e2_local
    old = (e2_local.SUITES, dict(e2_local.ROW_FILES), dict(e2_local.MOVE))
    if SUITE not in e2_local.SUITES:
        e2_local.SUITES = tuple(e2_local.SUITES) + (SUITE,)
    e2_local.ROW_FILES.setdefault(SUITE, ("relabel.jsonl",))
    e2_local.MOVE.setdefault(SUITE, {})
    try:
        yield e2_local
    finally:
        e2_local.SUITES = old[0]
        e2_local.ROW_FILES.clear(); e2_local.ROW_FILES.update(old[1])
        e2_local.MOVE.clear(); e2_local.MOVE.update(old[2])


def upstream_fields(source: str) -> dict:
    """{id: {"state": ...}} for one source, read again from the pinned upstream: what ``rehydrate`` checks against the
    recorded sha256 of each redacted row."""
    from dataclasses import asdict
    if source == "e2_word_filters_words":
        from . import e2_word_filters_words as W
        return {r.id: {"state": asdict(r.state)} for r in W.records()}
    reader = {CC["name"]: read_civil_comments, RTP["name"]: read_rtp,
              OASST["name"]: lambda: read_oasst(set())}[source]
    out = {}
    for r in reader():
        out[make_id("F4", source, r["source_id"])] = {"state": asdict(State(role=r["role"], text=r["text"]))}
    return out


def rehydrate() -> dict:
    with registered() as e2_local:
        return e2_local.rehydrate([SUITE], fetch=upstream_fields)


def leaks() -> dict:
    """e2_local.tracked_leaks over every tracked file, with this suite's private rows and withheld text included."""
    with registered() as e2_local:
        return e2_local.tracked_leaks()


# --- blind packet for the second labeller -------------------------------------------------------------------------------

PACKET_SEED = "gold-rails-e2-word-filters-review"
PACKET_RULES = """## How to label

You are the second, blind labeller. Another labeller has labelled these messages; those labels are not in this packet.

1. Read the definition before the first case and return to it whenever you hesitate. Judge against it as written. If
   you think the definition is wrong for a case, say so in the note.
2. For each case answer `profanity_present`: yes, no or unclear. Use unclear, with a note, when the definition does not
   settle it.
3. This is about the words in the message, not about whether the writer is rude or harmful.
4. Masked spellings (f*ck) are out of scope: judge only the words written in full.
5. Set `exclude_case` to yes only when the case cannot be judged at all (not English, unreadable, empty).
6. Work alone. Do not run the text through a model or a filter and do not compare answers before submitting.

Some messages are offensive. They come from public datasets and are shown only so you can label them.
"""


def write_label_sheet() -> dict:
    """private/packet/: the blind packet (definition, shuffled messages, blank answers) and the lead key, for every
    profanity candidate. Nothing in it is tracked."""
    rows, _ = profanity_candidates()
    order = sorted(rows, key=lambda c: c["id"])
    random.Random(PACKET_SEED).shuffle(order)
    pdir = PRIVATE / "packet"
    (pdir / "_lead").mkdir(parents=True, exist_ok=True)
    lines = ["# Review packet: edition 2 profanity", "", PACKET_RULES, "## Definition", "", DEFINITION, ""]
    template, key = [], {}
    for n, c in enumerate(order, 1):
        rid = f"wf-r{n:04d}"
        key[rid] = c["id"]
        lines += [f"### {rid}", "", "```text", c["state"]["text"], "```", ""]
        template.append(json.dumps({"review_id": rid, "reviewer": "", "submitted_at": "",
                                    "labels": {"profanity_present": None}, "exclude_case": None, "note": None}))
    (pdir / "packet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (pdir / "labels.template.jsonl").write_text("\n".join(template) + "\n", encoding="utf-8")
    (pdir / "_lead" / "key.json").write_text(json.dumps(
        {"_warning": "Lead only. Maps review ids to row ids; never send to the reviewer.", "seed": PACKET_SEED,
         "review_id_to_row_id": key}, indent=1) + "\n", encoding="utf-8")
    return {"cases": len(order), "packet": str(pdir.relative_to(REPO))}


def import_second_labels(path: Path) -> dict:
    """A filled labels.template.jsonl -> relabel.jsonl rows (split into tracked and private by e2_local)."""
    key = json.loads((PRIVATE / "packet" / "_lead" / "key.json").read_text(encoding="utf-8"))["review_id_to_row_id"]
    out, unclear = [], 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        ans = (d.get("labels") or {}).get("profanity_present")
        if d.get("exclude_case") == "yes" or ans not in ("yes", "no"):
            unclear += 1
            ans = "unclear"
        out.append({"id": key[d["review_id"]], "label": ans, "subtask": "profanity", "note": d.get("note"),
                    "labeller": d.get("reviewer") or "second labeller", "submitted_at": d.get("submitted_at")})
    return {"rows": out, "unclear": unclear}


# --- build ------------------------------------------------------------------------------------------------------------

def _write(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def overlap_report(rows: list) -> dict:
    """Ids, normalised texts and near-duplicate texts of the candidates against v1 (release builds, samples, frozen
    files, ledgers) and the other edition 2 suites. Counts only."""
    from goldrails_bench import overlap
    seen, v1_f4 = reference_texts()
    from ..edition2 import v1_row_files
    ids = overlap.repo_examined_ids() | {r.get("id") for f in v1_row_files() for r in _jsonl_rows(Path(f))}
    v1_sh = [overlap.shingles(t) for t in v1_f4 if t]
    sh = [overlap.shingles(r["state"]["text"]) for r in rows]
    near = overlap.near_duplicate_pairs(sh, v1_sh)
    by_sub = Counter(r["subtask"] for r in rows)
    return {"rows": dict(by_sub), "v1_f4_rows_compared": len(v1_f4),
            "id_hits": sum(r["id"] in ids for r in rows),
            "text_hits": sum(norm(r["state"]["text"]) in seen for r in rows),
            "near_duplicate_hits_vs_v1_f4": len({i for i, _, _, _ in near}),
            "internal_text_duplicates": len(rows) - len({norm(r["state"]["text"]) for r in rows})}


def _jsonl_rows(p: Path) -> list:
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def counts(rows: list | None = None, excluded: list | None = None) -> dict:
    if rows is None:
        from .. import e2_local
        rows = e2_local.candidates(SUITE, private=(PRIVATE / "candidates.jsonl").exists(), text=False)
    c = lambda f: dict(sorted(Counter(f(r) for r in rows).items()))
    out = {"n": len(rows),
           "subtask_split_label": c(lambda r: f"{r['subtask']}:{r['proposed_split']}:{r['label']}"),
           "subtask_source_label": c(lambda r: f"{r['subtask']}:{r['source']}:{r['label']}"),
           "subtask_source_split_label": c(lambda r: f"{r['subtask']}:{r['source']}:{r['proposed_split']}:{r['label']}"),
           "profanity_bucket_label": dict(sorted(Counter(f"{r['source']}:{r['bucket']}:{r['label']}" for r in rows
                                                         if r["subtask"] == "profanity").items())),
           "words_kind_label": dict(sorted(Counter(f"{r['bucket']}:{r['label']}" for r in rows
                                                   if r["subtask"] == "word").items()))}
    if excluded is not None:
        out["excluded"] = {"n": len(excluded), "by_source": dict(sorted(Counter(e["source"] for e in excluded).items())),
                           "by_reason": dict(sorted(Counter(e["exclude"] for e in excluded).items()))}
    return out


def build() -> dict:
    """Write dataset/edition2/word_filters/ from the frozen pool, the first labels and the authored custom words, then
    split it with e2_local (private slice to private/, uncleared text to local/). Rerunning gives the same files."""
    prof, excluded = profanity_candidates()
    words = words_candidates()
    rows = sorted(prof, key=lambda r: r["id"]) + sorted(words, key=lambda r: r["id"])
    for r in rows:
        Record.from_dict(r)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate candidate ids")
    _write(OUT / "candidates.jsonl", rows)
    _write(OUT / "relabel.jsonl", words_second_labels(words))
    _write(PRIVATE / "exclusions.jsonl", excluded)
    for stale in (PRIVATE / "candidates.jsonl", PRIVATE / "relabel.jsonl"):
        if stale.exists():
            stale.unlink()
    with registered() as e2_local:
        rep = e2_local.split([SUITE])
    report = {"split": rep.get(SUITE), "counts": counts(rows, excluded), "overlap": overlap_report(rows)}
    (OUT / "counts.json").write_text(json.dumps({k: report[k] for k in ("counts", "overlap")}, indent=1) + "\n",
                                     encoding="utf-8")
    write_label_sheet()
    return report



def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "counts"
    if cmd == "select":
        pool = select()
        print(json.dumps({"rows": len(pool), "by_source_bucket": dict(sorted(Counter(
            f"{r['source']}:{r['bucket']}" for r in pool).items()))}, indent=1))
    elif cmd == "packet":
        print(json.dumps(write_label_sheet(), indent=1))
    elif cmd == "build":
        print(json.dumps(build(), indent=1))
    elif cmd == "counts":
        print(json.dumps(counts(), indent=1))
    else:
        raise SystemExit(f"unknown command {cmd!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
