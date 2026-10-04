"""Edition 2 word filters (sources/e2_word_filters*.py, dataset/edition2/word_filters/). Offline: no model call and no
network. Tests that need the git-ignored private slice or text cache skip without them."""
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

import pytest

from goldrails_bench import overlap
from goldrails_bench.regex_words import RegexWordClient
from goldrails_dataset import e2_local
from goldrails_dataset.records import Record
from goldrails_dataset.sources import civil_comments_profanity as V1P
from goldrails_dataset.sources import e2_word_filters as W
from goldrails_dataset.sources import e2_word_filters_words as WW
from goldrails_dataset.sources import f4_words

OUT = W.OUT
SUITE = W.SUITE
PROFANITY_SOURCES = (W.CC["name"], W.RTP["name"], W.OASST["name"])


def _jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


@pytest.fixture(scope="module")
def tracked():
    return _jsonl(OUT / "candidates.jsonl")


@pytest.fixture(scope="module")
def full():
    try:
        return e2_local.candidates(SUITE)
    except e2_local.LocalDataMissing as e:
        pytest.skip(str(e))


# --- custom words: the sanity check ----------------------------------------------------------------------------------

def test_custom_words_follow_the_rule_and_the_regex_baseline_agrees():
    recs = WW.records()
    assert 100 <= len(recs) <= 130
    c = RegexWordClient()
    for r in recs:
        Record.from_dict(r.to_dict())
        assert (r.feature, r.subtask, r.provenance.label_basis) == ("F4", "word", "deterministic")
        hit = c.ask({"role": "user", "text": r.state.text}, {"any_word": {}}).answers["any_word"]["noul"]
        assert (hit == 1.0) == (r.expected == "yes"), (r.attribute["kind"], r.id)
    labels = Counter(r.expected for r in recs)
    assert labels["yes"] == labels["no"]
    test = Counter(r.expected for r in recs if r.split == "test")
    assert test["yes"] >= 45 and test["no"] >= 45


def test_custom_words_cover_case_punctuation_and_substring_traps():
    kinds = {r.attribute["kind"] for r in WW.records()}
    assert {"upper", "title", "mixed_case"} <= kinds                                    # case
    assert {"double_quoted", "parenthesised", "possessive", "trailing_punctuation"} <= kinds   # punctuation
    assert {"plural", "prefix_glued", "digit_glued", "run_together", "hyphenated"} <= kinds    # substring traps
    assert {"reversed", "word_inserted", "paraphrase"} <= kinds
    phrases = json.loads(WW.WORDS.read_text(encoding="utf-8"))["words"]
    per = Counter(r.attribute["word"] for r in WW.records())
    assert all(per[p] == len(WW.MATCH) + len(WW.NO_MATCH) for p in phrases)


def test_custom_word_frames_stay_in_one_split_and_are_new_for_edition_2():
    recs = WW.records()
    by_group = defaultdict(set)
    for r in recs:
        by_group[r.group].add(r.split)
    assert all(len(s) == 1 for s in by_group.values())
    v1 = [overlap.shingles(r.state.text) for r in f4_words.load()]
    mine = [overlap.shingles(r.state.text) for r in recs]
    assert overlap.near_duplicate_pairs(mine, v1) == []
    v1_texts = {W.norm(r.state.text) for r in f4_words.load()}
    assert not any(W.norm(r.state.text) in v1_texts for r in recs)


def test_custom_word_second_labels_are_the_regex_verdicts(tracked):
    words = [c for c in tracked if c["subtask"] == "word"]
    rel = {d["id"]: d for d in _jsonl(OUT / "relabel.jsonl")}
    assert len(words) == len(WW.records())
    for c in words:
        assert rel[c["id"]]["label"] == c["label"]
        assert "regex" in rel[c["id"]]["labeller"]


# --- profanity: the scored subtask ------------------------------------------------------------------------------------

def test_profanity_uses_the_reviewed_v1_definition():
    assert W.DEFINITION == V1P.DEFINITION


def test_profanity_floors_sources_and_splits(tracked):
    prof = [c for c in tracked if c["subtask"] == "profanity"]
    test = Counter(c["label"] for c in prof if c["proposed_split"] == "test")
    assert test["yes"] >= 250 and test["no"] >= 250
    for lab in ("yes", "no"):
        srcs = Counter(c["source"] for c in prof if c["proposed_split"] == "test" and c["label"] == lab)
        assert len(srcs) >= 2, (lab, srcs)
        assert sum(n for s, n in srcs.items() if s != W.CC["name"]) >= 100, srcs   # not mostly Civil Comments
    assert {c["source"] for c in prof} == set(PROFANITY_SOURCES)


def test_profanity_rows_are_first_labelled_candidates(tracked):
    for c in tracked:
        assert c["label"] in ("yes", "no") and c["label"] == c["expected"]
        assert c["proposed_split"] in ("test", "dev")          # the private slice never sits in a tracked file
        if c["subtask"] == "profanity":
            assert c["provenance"]["label_basis"] == "llm" and c["review_status"] == "candidate"
            assert c["label_rationale"] and c["label_rationale"].startswith(c["label"] + ":")
            assert c["source"] in PROFANITY_SOURCES and c["provenance"]["source"] == c["source"]
            assert c["category"]["bedrock"] == ("PROFANITY" if c["label"] == "yes" else "NONE")
    cc = [c for c in tracked if c["source"] == W.CC["name"]]
    assert all("strands-decider-train" in c["provenance"]["contamination"] for c in cc)


def test_uncleared_text_is_withheld_from_the_tracked_file(tracked):
    pol = e2_local.policy()
    for c in tracked:
        if not e2_local.text_cleared(c["source"], pol):
            assert "redacted" in c and c["state"]["text"] is None, c["id"]


def test_full_rows_rebuild_and_keep_groups_in_one_split(full):
    prof = [c for c in full if c["subtask"] == "profanity"]
    assert any(c["proposed_split"] == "private" for c in prof)
    by_group = defaultdict(set)
    for c in full:
        Record.from_dict(c)
        by_group[c["group"]].add(c["proposed_split"])
    assert all(len(s) == 1 for s in by_group.values())
    texts = [W.norm(c["state"]["text"]) for c in full]
    assert len(texts) == len(set(texts))
    assert not any(W.terms_in(c["state"]["text"])["masked"] for c in prof)   # masked-only rows are diagnostic
    # each source contributes both classes to every split
    cells = Counter((c["source"], c["proposed_split"], c["label"]) for c in prof)
    for s in PROFANITY_SOURCES:
        for split in ("test", "dev", "private"):
            for lab in ("yes", "no"):
                assert cells[(s, split, lab)] > 0, (s, split, lab)


def test_build_is_reproducible_from_the_frozen_pool(full):
    try:
        prof, excluded = W.profanity_candidates()
    except e2_local.LocalDataMissing as e:
        pytest.skip(str(e))
    got = {c["id"]: (c["label"], c["proposed_split"], c["group"]) for c in full if c["subtask"] == "profanity"}
    assert {c["id"]: (c["label"], c["proposed_split"], c["group"]) for c in prof} == got
    assert all(e["exclude"] for e in excluded)
    counts = json.loads((OUT / "counts.json").read_text(encoding="utf-8"))
    assert counts["counts"] == W.counts(full, excluded)


def test_no_overlap_with_v1_word_filter_rows(full):
    from goldrails_dataset.edition2 import v1_row_files
    if not any("/release/" in f for f in v1_row_files()):
        pytest.skip("no v1 release build on this machine")
    rep = W.overlap_report(full)
    assert rep["v1_f4_rows_compared"] > 0
    assert (rep["id_hits"], rep["text_hits"], rep["near_duplicate_hits_vs_v1_f4"], rep["internal_text_duplicates"]) == \
        (0, 0, 0, 0)


def test_words_text_cache_matches_the_authored_module(full):
    up = W.upstream_fields(WW.NAME)
    for c in [c for c in _jsonl(OUT / "candidates.jsonl") if c["source"] == WW.NAME and "redacted" in c]:
        fields = [{k: up[c["id"]]["state"].get(k) for k in e2_local.STRIP if k in c["state"]}]
        assert e2_local.fields_sha256(fields) == c["redacted"]["fields_sha256"]


def test_no_private_row_or_withheld_profanity_text_in_any_tracked_file(full):
    """The suite's own needles (private ids and texts, withheld upstream text) against every tracked file and this
    suite's new files. Our authored custom words are the one expected exception while their source has no entry in
    redistribution.json: their text is in the tracked module that generates them."""
    with W.registered() as L:
        # without a build listing this suite's private slice, every private candidate counts as private
        needles = [n for n in L.leak_needles(build_private=OUT / "no-build") if n[1].startswith("f4-e2_")]
        files = sorted(set(L.tracked_files()) | {
            "dataset/edition2/word_filters/candidates.jsonl", "dataset/edition2/word_filters/relabel.jsonl",
            "dataset/edition2/word_filters/counts.json", "dataset/goldrails_dataset/sources/e2_word_filters.py",
            "dataset/goldrails_dataset/sources/e2_word_filters_words.py", "dataset/tests/test_e2_word_filters.py"})
        files = [f for f in files if (L.REPO / f).exists()]
        rep = L.tracked_leaks(needles=needles, files=files)
    assert any(n[0] == "private_id" for n in needles)
    words_cleared = e2_local.text_cleared(WW.NAME, e2_local.policy())
    bad = [l for l in rep["leaks"] if words_cleared or not (
        l["kind"] == "withheld_text" and l["key"].startswith(f"f4-{WW.NAME}-")
        and l["file"] == "dataset/goldrails_dataset/sources/e2_word_filters_words.py")]
    assert bad == []
