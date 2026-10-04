"""Edition 2 denied topics (sources/e2_denied_topics*.py, dataset/edition2/denied_topics/). Offline: no model or
network; the OASST2 rows are checked through the committed candidate file and a monkeypatched fetch."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from goldrails_dataset import e2_local
from goldrails_dataset.records import Record
from goldrails_dataset.sources import e2_denied_topics as E
from goldrails_dataset.sources import e2_denied_topics_oasst as O

OUT = Path(__file__).resolve().parents[1] / "edition2" / "denied_topics"
ROOT = Path(__file__).resolve().parents[2]
SUITES = ROOT / "benchmark" / "suites" / "denied_topics"


@pytest.fixture(scope="module")
def recs():
    try:
        return E.load()
    except e2_local.LocalDataMissing as e:          # held-out authored cases are git-ignored, owner only
        pytest.skip(str(e))


@pytest.fixture(scope="module")
def cands():
    try:
        return e2_local.candidates("denied_topics")
    except e2_local.LocalDataMissing as e:
        pytest.skip(str(e))


def _ngrams(s, n=5):
    w = E.norm(s).split()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def test_topic_file_reuses_v1_and_v2_definitions_verbatim_and_fits_bedrock():
    ts = {t["name"]: t for t in E.topics()}
    assert len(ts) >= 8
    for f in ("topics.json", "topics-v2-candidates.json"):
        for t in json.loads((SUITES / f).read_text(encoding="utf-8"))["topics"]:
            assert ts[t["name"]]["definition"] == t["definition"]
            assert ts[t["name"]]["examples"] == t["examples"]
    for t in ts.values():
        assert len(t["definition"]) <= 200 and 1 <= len(t["examples"]) <= 5
        assert all(len(e) <= 100 for e in t["examples"])


def test_authored_records_are_valid_candidates_with_rationale(recs):
    assert len(recs) == 8 * 90 + len(E.V2.CONFUSERS)
    for r in recs:
        Record.from_dict(r.to_dict())
        assert (r.feature, r.subtask) == ("F3", "topic")
        assert r.provenance.label_basis == "llm" and r.review_status == "candidate"
        assert r.attribute["rationale"].strip() and r.attribute["topic_set"] == "e2"
        assert r.expected == ("yes" if r.attribute["kind"] == "in_topic" else "no")
        assert (r.expected == "yes") == ("yes" in r.attribute["proposed_labels"].values())
        if r.expected == "yes":
            assert r.attribute["proposed_labels"][r.attribute["topic"]] == "yes"


def test_every_topic_has_balanced_pairs(recs):
    c = Counter((r.attribute["topic"], r.expected) for r in recs if r.attribute["topic"])
    for name in E.topic_names():
        assert c[(name, "yes")] == c[(name, "no")] >= 45


def test_pairs_share_a_group_and_groups_never_straddle_splits(recs, cands):
    for rows in (recs, cands):
        split_of = defaultdict(set)
        for r in rows:
            g = r.group if isinstance(r, Record) else r["group"]
            s = r.attribute["proposed_split"] if isinstance(r, Record) else r["proposed_split"]
            split_of[g].add(s)
        assert all(len(s) == 1 for s in split_of.values())
    by_group = defaultdict(list)
    for r in recs:
        by_group[r.group].append(r.expected)
    assert all(sorted(v) in (["no"], ["no", "yes"]) for v in by_group.values())


def test_private_rows_are_heldout_test_rows(recs):
    for r in recs:
        s = r.attribute["proposed_split"]
        assert (r.split, r.visibility) == {"test": ("test", "public"), "dev": ("dev", "public"),
                                           "private": ("test", "heldout")}[s]


def test_no_exact_or_near_duplicate_of_v1_denied_topic_texts(recs):
    v1 = E.v1_texts_from_loaders()
    v1_grams = [_ngrams(t) for t in v1]
    for r in recs:
        assert E.norm(r.state.text) not in v1
        g = _ngrams(r.state.text)
        for vg in v1_grams:
            if g and vg:
                assert len(g & vg) / min(len(g), len(vg)) < 0.5, r.provenance.source_id


def test_no_overlap_with_v1_samples_frozen_and_subsets_by_id_or_text(recs, cands):
    ids, texts = E.v1_index(include_ledgers=False)
    for c in cands:
        assert c["id"] not in ids
        assert E.norm(c["text"]) not in texts


def test_candidate_texts_unique(cands):
    norm = Counter(E.norm(c["text"]) for c in cands)
    assert max(norm.values()) == 1
    assert len({c["id"] for c in cands}) == len(cands)


def test_candidate_file_matches_the_loader(recs, cands):
    by_id = {c["id"]: c for c in cands}
    for r in recs:
        c = by_id[r.id]
        assert (c["text"], c["label"], c["group"], c["proposed_split"], c["label_rationale"]) == (
            r.state.text, r.expected, r.group, r.attribute["proposed_split"], r.attribute["rationale"])


def test_candidate_fields_and_records(cands):
    need = {"id", "suite", "subtask", "text", "state", "label", "source", "licence", "group", "proposed_split",
            "label_rationale", "topic", "proposed_labels"}
    for c in cands:
        assert need <= set(c)
        assert c["suite"] == "denied_topics" and c["label"] in ("yes", "no")
        assert c["proposed_split"] in ("test", "dev", "private")
        assert c["label_rationale"].strip()
        r = Record.from_dict(c["record"])
        assert r.id == c["id"] and r.expected == c["label"]
        assert "expected" not in c["state"] and "label" not in c["state"]


def test_targets_met(cands):
    c = Counter((x["proposed_split"], x["label"]) for x in cands)
    assert c[("test", "yes")] >= 250 and c[("test", "no")] >= 250
    for lab in ("yes", "no"):
        assert c[("dev", lab)] >= 0.15 * c[("test", lab)]
        assert c[("private", lab)] >= 0.15 * c[("test", lab)]
    assert len({x["topic"] for x in cands if x["label"] == "yes"}) >= 8
    assert {x["source"] for x in cands} == {E.NAME, O.NAME}
    for lab in ("yes", "no"):
        assert len({x["source"] for x in cands if x["label"] == lab and x["proposed_split"] == "test"}) == 2


def test_oasst_rows_record_licence_revision_and_train_flag(cands):
    rows = [c for c in cands if c["source"] == O.NAME]
    assert len(rows) == len(O.CASES)
    for c in rows:
        assert c["licence"] == "apache-2.0" and c["revision"] == O.REVISION
        assert c["upstream_split"] in ("train", "validation")
        if c["upstream_split"] == "train":
            assert "upstream train split" in c["record"]["provenance"]["notes"]


def test_oasst_loader_builds_records_from_fetch(monkeypatch):
    fake = {mid: {"text": f"prompt {i} about something", "message_tree_id": f"tree-{i}", "upstream_split": up}
            for i, (mid, up, *_rest) in enumerate(O.CASES)}
    recs = E.load_oasst(fake)
    assert len(recs) == len(O.CASES)
    assert {r.provenance.source for r in recs} == {O.NAME}
    assert all(r.attribute["revision"] == O.REVISION for r in recs)


def test_blind_packet_carries_no_labels_or_rationales(cands):
    pdir = e2_local.packet_dir("denied_topics")                   # git-ignored: it holds every row's text
    if not (pdir / "packet.md").exists():
        pytest.skip("packet not on this machine")
    md = (pdir / "packet.md").read_text(encoding="utf-8")
    tmpl = [json.loads(l) for l in (pdir / "labels.template.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(tmpl) == len(cands)
    for c in cands[:200]:
        assert c["id"] not in md and c["label_rationale"] not in md
    for word in ("in_topic", "hard_negative", "proposed", "rationale"):
        assert word not in md
    assert all(t["labels"] == {"topics": None} for t in tmpl)
    key = json.loads((e2_local.private_dir("denied_topics") / "_lead" / "e2-denied-topics.key.json").read_text(encoding="utf-8"))
    assert set(key["review_id_to_record_id"].values()) == {c["id"] for c in cands}


def test_ambiguous_flags_point_at_real_rows(recs):
    sids = {r.provenance.source_id for r in recs}
    assert set(E.AMBIGUOUS) <= sids
    assert set(E.ALSO_IN) <= sids
    assert set(O.AMBIGUOUS) <= {c[0] for c in O.CASES}
