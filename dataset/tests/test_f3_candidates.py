"""F3 test candidates (sources/f3_test_candidates.py) and their blind review packet. Offline: no model or network."""
import json
import re
from collections import Counter
from pathlib import Path

import pytest

from goldrails_dataset.records import Record
from goldrails_dataset.sources import f3_controls
from goldrails_dataset.sources import f3_test_candidates as C

PACKETS = Path(__file__).resolve().parents[1] / "frozen" / "review-packets"
PDIR = PACKETS / C.PACKET
KEY = PACKETS / "_lead" / f"{C.PACKET}.key.json"
CITE = re.compile(r'Definition: "(.+)"\.$')


@pytest.fixture(scope="module")
def recs():
    return C.load()


@pytest.fixture(scope="module")
def defs():
    return {t["name"]: t for t in C.topics()}


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower())).strip()


def _words(s):
    return set(_norm(s).split())


def _ngrams(s, n=5):
    w = _norm(s).split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def test_all_rows_validate_and_round_trip(recs):
    assert len(recs) == len(C.CASES) == 90
    assert len({r.id for r in recs}) == len(recs)
    assert len({r.group for r in recs}) == len(recs)            # one group per case
    for r in recs:
        r.validate()
        assert Record.from_dict(json.loads(r.to_json())).to_dict() == r.to_dict()
        assert (r.feature, r.subtask, r.labels) == ("F3", "topic", ["no", "yes"])
        assert r.provenance.label_basis == "llm"
        assert r.provenance.notes.startswith("AI-drafted 2026-09-23; label proposed, pending independent human validation")
        if C.HAS_REVIEW_STATUS:
            assert r.review_status == "candidate"
        else:
            assert "review_status=candidate" in r.provenance.notes


def test_attributes_and_rationales_cite_the_definition(recs, defs):
    for r in recs:
        a = r.attribute
        assert a["kind"] in C.KINDS and a["topic_set"] == "v1"
        assert (a["topic"] is None) == (a["kind"] == "confuser")
        assert a["topic"] is None or a["topic"] in defs
        assert r.expected == ("yes" if a["kind"] == "in_topic" else "no")
        assert r.category.bedrock == ("TOPIC" if r.expected == "yes" else "NONE")
        m = CITE.search(a["rationale"])
        assert m, a["rationale"]
        cited_in = a["topic"] or (a["vocabulary"] if a["vocabulary"] in defs else None)
        if cited_in:
            assert m.group(1) in defs[cited_in]["definition"], (r.provenance.source_id, m.group(1))
        else:
            assert any(m.group(1) in d["definition"] for d in defs.values())
        assert "\n" not in a["rationale"] and len(a["rationale"]) < 300


def test_counts_by_topic_and_kind(recs):
    c = Counter((r.attribute["topic"], r.attribute["kind"]) for r in recs)
    for t in C.topic_names():
        assert c[(t, "in_topic")] == 12 and c[(t, "hard_negative")] == 12
    assert c[(None, "confuser")] == 18


def test_classes_balanced_within_ten_percent_per_topic(recs):
    for t in C.topic_names():
        lab = Counter(r.expected for r in recs if r.attribute["topic"] == t)
        assert abs(lab["yes"] - lab["no"]) <= 0.10 * max(lab["yes"], lab["no"]), (t, lab)


def test_no_text_overlaps_existing_controls_or_topic_examples(recs, defs):
    old = [text for _, _, text in f3_controls.CASES] + [e for d in defs.values() for e in d["examples"]]
    new = [r.state.text for r in recs]
    assert len({_norm(t) for t in new}) == len(new)            # no duplicates within the set
    for t in new:
        for o in old:
            assert _norm(t) != _norm(o), t
            assert not (_ngrams(t) & _ngrams(o)), (t, o)        # no shared five-word run
            a, b = _words(t), _words(o)
            assert len(a & b) / len(a | b) < 0.4, (t, o)        # no close paraphrase by word overlap


def test_ambiguous_ids_exist():
    sids = {c[0] for c in C.CASES}
    assert set(C.AMBIGUOUS) <= sids and C.AMBIGUOUS


