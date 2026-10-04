"""Shared helpers for the edition 2 prompt-attack loaders (``e2_prompt_attacks_*``).

Edition 2 (docs/benchmark/26-edition-2-plan.md) needs hard benign rows for jailbreak and leakage and attack rows from
sources other than deepset's train split. Every edition 2 prompt-attack loader builds its records through ``record``
below, so all of them carry the same fields: the first labeller's label as ``expected``, the source's own label
verbatim in ``category.source_label``, and a JSON ``provenance.notes`` with the pinned revision, the upstream split,
whether that split is a TRAIN split (flagged, used only when the source has no test split), the label rationale and
the labeller. Rows the first labeller rejects keep ``exclude_reason``; nothing is dropped silently.

The first labeller is Claude (2 October 2026). A blind second labeller follows; until both agree and the owner has
reviewed, every row is ``review_status = "candidate"``.
"""
from __future__ import annotations

import hashlib
import json
import re

from ..records import Category, Provenance, Record, State, make_id
from .base import now

SUITE = "prompt_attacks"
FEATURE = "F2"
LABELLER = "claude-first-labeller-2026-10-02"
GROUP_PREFIX = "e2pa"
MAX_CHARS = 4000        # longer prompts are excluded: cost and context limits differ across systems under test
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """The same normalisation as ``build.normalise`` and ``goldrails_bench.overlap.normalise_text``."""
    return _WS.sub(" ", (text or "").strip().lower())


def text_hash(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def short_hash(s: str, n: int = 10) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


# --- language -------------------------------------------------------------------------------------------------------
# v1 and edition 2 are English. A row is non-English when most of its letters are outside ASCII (after removing the
# look-alike characters attackers use for obfuscation) or when common function words of another language dominate.
_OTHER = {
    "de": {"und", "der", "die", "das", "ist", "nicht", "ich", "wie", "was", "mit", "für", "auf", "ein", "eine", "sie",
           "du", "bitte", "vergiss", "alle", "sind", "wir", "zu", "den", "dem", "des", "auch", "über", "kann"},
    "es": {"el", "la", "los", "las", "que", "por", "para", "una", "yo", "tu", "tus", "dices", "todo", "como",
           "pero", "mis", "sigue", "y", "de", "del", "sus"},
    "fr": {"le", "les", "des", "une", "est", "pas", "vous", "pour", "dans", "avec", "ceci", "toutes", "et", "je",
           "sans", "ta", "tes", "sur", "cette", "comme"},
    "id": {"yang", "anda", "saya", "dengan", "untuk", "dalam", "ini", "itu", "sebagai", "tulis", "bahasa",
           "artikel", "dari", "akan", "atau", "tidak", "bisa", "minimal", "kata"},
    "pt": {"você", "não", "uma", "para", "com", "por", "como", "mais", "seu", "sua", "isso", "ou", "ser", "suas", "diga-me"},
    "it": {"il", "di", "che", "è", "non", "sono", "una", "della", "le", "tue", "tuo", "questa", "dietro"},
}
_EN = {"the", "and", "is", "not", "what", "how", "with", "for", "you", "are", "all", "please", "of", "to", "in", "a",
       "your", "me", "i", "it", "this", "that", "be", "can", "will", "my", "on", "as", "do"}


def is_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    ascii_share = sum(c.isascii() for c in letters) / len(letters)
    words = [w.strip(".,!?;:\"'()[]{}¿¡").lower() for w in text.split()]
    en = sum(w in _EN for w in words)
    for vocab in _OTHER.values():
        other = sum(w in vocab for w in words)
        if other >= 2 and other > en:
            return False
        if other >= 1 and en == 0:
            return False
    if en == 0 and len(words) >= 4 and ascii_share < 0.98:
        return False
    if ascii_share >= 0.9:
        return True
    # obfuscated English (homoglyphs, leetspeak) still reads as English through its function words
    return ascii_share >= 0.6 and en >= 2


# --- near-duplicate groups --------------------------------------------------------------------------------------------
# Jailbreak templates, HackAPrompt submissions and Mosscap attempts come in many small edits of one idea. Rows whose
# word 5-gram sets overlap strongly share a group, so no split separates a template from its edits. MinHash with
# banding finds candidate pairs; a pair joins when its exact Jaccard is at least NEAR_DUP.
NEAR_DUP = 0.6
_NUM_PERM, _BANDS = 64, 16
_MASK = (1 << 61) - 1
_PERMS = [(int(short_hash(f"a{i}", 15), 16) | 1, int(short_hash(f"b{i}", 15), 16)) for i in range(_NUM_PERM)]


def shingles(text: str, n: int = 5) -> set:
    words = re.findall(r"\w+", normalise(text))
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def _minhash(sh: set) -> list:
    hs = [int(hashlib.blake2b(s.encode("utf-8"), digest_size=8).hexdigest(), 16) for s in sh] or [0]
    return [min((a * h + b) & _MASK for h in hs) for a, b in _PERMS]


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def near_dup_components(texts: list, threshold: float = NEAR_DUP) -> list:
    """Union-find over near-duplicate pairs. Returns one component index per text."""
    sh = [shingles(t) for t in texts]
    parent = list(range(len(texts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    rows = _NUM_PERM // _BANDS
    buckets: dict = {}
    for i, s in enumerate(sh):
        if not s:
            continue
        mh = _minhash(s)
        for b in range(_BANDS):
            buckets.setdefault((b, tuple(mh[b * rows:(b + 1) * rows])), []).append(i)
    checked = set()
    for members in buckets.values():
        for x in range(1, len(members)):
            j = members[x]
            for i in members[:x]:
                if (i, j) in checked:
                    continue
                checked.add((i, j))
                ri, rj = find(i), find(j)
                if ri != rj and jaccard(sh[i], sh[j]) >= threshold:
                    parent[rj] = ri
    return [find(i) for i in range(len(texts))]


class NearDupIndex:
    """MinHash-banded index of reference texts (the v1 rows). ``match(text)`` returns the best reference Jaccard at or
    above ``threshold`` among banded candidates, else 0.0. Exact for every pair the bands surface; pairs with Jaccard
    above 0.7 share a band with probability above 0.99 at 16 bands of 4."""

    def __init__(self, texts, threshold: float = 0.7):
        self.threshold = threshold
        self.sets: list = []
        self.buckets: dict = {}
        rows = _NUM_PERM // _BANDS
        for t in texts:
            s = shingles(t)
            if not s:
                continue
            k = len(self.sets)
            self.sets.append(s)
            mh = _minhash(s)
            for b in range(_BANDS):
                self.buckets.setdefault((b, tuple(mh[b * rows:(b + 1) * rows])), []).append(k)

    def match(self, text: str) -> float:
        s = shingles(text)
        if not s:
            return 0.0
        rows = _NUM_PERM // _BANDS
        mh = _minhash(s)
        cands = set()
        for b in range(_BANDS):
            cands.update(self.buckets.get((b, tuple(mh[b * rows:(b + 1) * rows])), ()))
        best = max((jaccard(s, self.sets[k]) for k in cands), default=0.0)
        return best if best >= self.threshold else 0.0


# --- markers ---------------------------------------------------------------------------------------------------------
# Used by the first labeller to screen source labels and filter large pools, and reported as a trivial baseline.
JAILBREAK_MARKERS = re.compile(
    r"\b(dan|jailbr\w*|developer mode|dev mode|no (?:restrictions|limits|filters|rules|boundaries|ethic\w*|morals?)|"
    r"without (?:any )?(?:restrictions|limits|filters|censorship|ethic\w*|morals?)|unfilt\w*|uncensored|amoral|"
    r"unrestricted|unethical|illegal|content polic\w*|openai(?:'s)? polic\w*|never refuses?|not bound by|"
    r"(?:ignore|disregard|forget|break(?:s|ing)?|bypass\w*|free from|freed from) (?:all |any |the |your |of )*"
    r"(?:previous |prior |earlier |above |openai |safety |ethical )*(?:instructions|rules|guidelines|polic\w*|"
    r"restrictions|filters|programming|constraints|limitations)|stay in character|anything now|evil|immoral)\b",
    re.I)
LEAK_MARKERS = re.compile(
    r"\b(password|passphrase|pass word|secret|the word|letters?|spell\w*|hint|riddle|acrostic|"
    r"(?:system|initial|original|hidden|previous|above|first) (?:prompt|instructions?|message|text)|"
    r"instructions|prompt|reveal|disclose|cipher|encode|reverse|backwards?|rhymes?)\b", re.I)
RISKY_TOPICS = re.compile(
    r"\b(nsfw|porn\w*|sex\w*|nud\w*|erotic\w*|fetish\w*|drugs?|meth\w*|cocaine|weapons?|bombs?|explosiv\w*|kill\w*|"
    r"murder\w*|suicid\w*|self-harm|racis\w*|nazi\w*|slurs?|hack\w*|malware|ransomware|exploit\w*|phishing|scam\w*|"
    r"steal\w*|gore|torture|rape|abuse|violent|violence|terror\w*|cum|horny|kink\w*|onlyfans|swear\w*|curse\w*|"
    r"profan\w*|offensive|vulgar)\b", re.I)


def notes(**kw) -> str:
    return json.dumps({k: v for k, v in kw.items() if v is not None}, ensure_ascii=False, sort_keys=True)


def record(*, source: str, source_id: str, licence: str, subtask: str, text: str, expected, label_basis: str,
           revision: str, upstream_split: str, train_split: bool, rationale: str, source_label: str | None,
           group: str, role: str = "user", context: list | None = None, exclude_reason: str | None = None,
           contamination: list | None = None, extra: dict | None = None) -> Record:
    attack = expected == "yes"
    return Record(
        id=make_id(FEATURE, source, source_id), feature=FEATURE, subtask=subtask,
        state=State(role=role, text=text, context=list(context or [])),
        category=Category(ailuminate="injection" if attack else ("benign" if expected == "no" else None),
                          bedrock="PROMPT_ATTACK" if attack else ("NONE" if expected == "no" else None),
                          source_label=source_label),
        labels=["no", "yes"], expected=expected, group=f"{GROUP_PREFIX}-{group}",
        provenance=Provenance(source=source, source_id=source_id, licence=licence, label_basis=label_basis,
                              imported_at=now(), contamination=list(contamination or []),
                              exclude_reason=exclude_reason,
                              notes=notes(suite=SUITE, revision=revision, upstream_split=upstream_split,
                                          train_split_flag=train_split, label_rationale=rationale,
                                          labeller=LABELLER, **(extra or {}))),
        review_status="candidate",
    )


def note(r: Record) -> dict:
    return json.loads(r.provenance.notes or "{}")
