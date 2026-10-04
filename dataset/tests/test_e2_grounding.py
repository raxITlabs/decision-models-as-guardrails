"""Edition 2 grounding candidates (sources/e2_grounding*.py, dataset/edition2/grounding/). Offline: no model or network."""
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from goldrails_dataset.build import normalise
from goldrails_dataset.records import Record
from goldrails_dataset import e2_local
from goldrails_dataset.sources import e2_grounding as E
from goldrails_dataset.sources import e2_grounding_faithdial as F
from goldrails_dataset.sources import e2_grounding_ragbench as R
from goldrails_dataset.sources import e2_grounding_summedits as S

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "dataset" / "edition2" / "grounding"
SPLITS = ("dev", "test", "private")


# ---------------------------------------------------------------- loaders on fake upstream rows

def test_faithdial_keeps_clear_cut_turns_with_history_as_context(monkeypatch):
    conv = {"dialog_idx": 7, "utterances": [
        {"history": ["Do you like jazz?"], "knowledge": "Jazz originated in New Orleans.", "original_response": "Jazz began in Chicago in 1950.",
         "response": "Jazz originated in New Orleans.", "BEGIN": ["Hallucination"], "VRM": ["Edification"]},
        {"history": ["Do you like jazz?", "Jazz originated in New Orleans.", "Where exactly?"], "knowledge": "Jazz originated in New Orleans.",
         "original_response": None, "response": "In New Orleans.", "BEGIN": ["Entailment"], "VRM": ["Edification"]},
        {"history": ["Hi"], "knowledge": "k", "original_response": "x", "response": "y", "BEGIN": ["Hallucination", "Entailment"], "VRM": []}]}
    monkeypatch.setattr(F, "fetch", lambda split="test": [conv])
    out = F.load()
    assert [r.expected for r in out] == ["yes", "no"]                              # mixed BEGIN tags are skipped
    assert out[0].state.text == "Jazz began in Chicago in 1950." and out[1].state.text == "In New Orleans."
    assert out[1].state.query == "Where exactly?"
    assert out[1].state.context == [{"role": "user", "text": "Do you like jazz?"}, {"role": "assistant", "text": "Jazz originated in New Orleans."}]
    assert out[0].group == out[1].group == "faithdial-test-7" and all(r.provenance.label_basis == "human" for r in out)
    for r in out:
        r.validate()


def test_summedits_maps_labels_and_drops_non_redistributable_domains(monkeypatch):
    rows = [{"domain": "billsum", "id": "a_og", "doc": "Doc A", "summary": "Seed.", "label": "1", "seed_summary": "Seed.", "edit_types": "[]"},
            {"domain": "billsum", "id": "a_1", "doc": "Doc A", "summary": "Edited.", "label": 0, "seed_summary": "Seed.", "edit_types": "['entity']"},
            {"domain": "samsum", "id": "b_1", "doc": "Doc B", "summary": "Other.", "label": 1, "seed_summary": "Other.", "edit_types": "[]"}]
    monkeypatch.setattr(S, "fetch", lambda: rows)
    out = S.load()
    assert [r.expected for r in out] == ["no", "yes"]                              # samsum (CC-BY-NC-ND) is not loaded
    assert out[0].group == out[1].group and out[0].state.source == "Doc A" and out[0].state.query == S.QUERY
    assert json.loads(out[0].provenance.notes)["upstream_split"] == "none"


def test_ragbench_rows_are_llm_labelled_candidates_with_spans(monkeypatch):
    resp = "Paris is the capital. It has 90 million people."
    rows = [{"id": "q1_0", "question": "Capital of France?", "documents": ["Paris is the capital of France."], "response": resp,
             "generation_model_name": "m", "annotating_model_name": "gpt-4", "adherence_score": False,
             "response_sentences": [["a", "Paris is the capital."], ["b", "It has 90 million people."]],
             "unsupported_response_sentence_keys": ["b"], "ragas_faithfulness": 0.2, "trulens_groundedness": 0.5}]
    monkeypatch.setattr(R, "fetch", lambda subset, split="test": rows)
    out = R.load(subsets=("hagrid",))
    r = out[0]
    assert r.expected == "yes" and r.provenance.label_basis == "llm" and r.review_status == "candidate"
    assert r.spans == [{"start": 22, "end": len(resp), "label": "unsupported", "source_label": "ragbench:b"}]
    assert r.state.text[r.spans[0]["start"]:r.spans[0]["end"]] == "It has 90 million people."
    r.validate()


# ---------------------------------------------------------------- selection rules

def _rec(i, src, expected, group, text=None, source="src", notes=None):
    from goldrails_dataset.records import Category, Provenance, State
    return Record(id=f"f6-{src}-{i:010d}", feature="F6", subtask="grounding",
                  state=State(role="assistant", text=text or f"reply {src} {i}", source=source, query="q"),
                  category=Category("benign", "NONE", None), labels=["no", "yes"], expected=expected, group=group,
                  provenance=Provenance(source=src, source_id=str(i), licence="mit", label_basis="human", imported_at="2026-10-02T00:00:00+00:00",
                                        notes=json.dumps(notes or {"vrm": ["Edification"]})))


def test_select_balances_classes_and_never_splits_a_group(monkeypatch):
    monkeypatch.setattr(E, "QUOTA", {"faithdial": 20})
    recs = [_rec(i, "faithdial", "yes" if i % 2 else "no", f"g{i // 2}", source=f"s{i // 2}") for i in range(400)]
    rows, _ = E.select(recs)
    c = Counter((d["proposed_split"], d["label"]) for d in rows)
    for split, want in E.quotas(20).items():
        assert c[(split, "yes")] == c[(split, "no")] == want
    where = defaultdict(set)
    for d in rows:
        where[d["group"]].add(d["proposed_split"])
    assert all(len(s) == 1 for s in where.values())


def test_select_drops_overlap_duplicates_and_first_labeller_disagreements(monkeypatch):
    monkeypatch.setattr(E, "QUOTA", {"faithdial": 200})
    recs = [_rec(1, "faithdial", "yes", "a", text="seen in v1"), _rec(2, "faithdial", "yes", "b", text="dup"),
            _rec(3, "faithdial", "no", "c", text="dup"), _rec(4, "faithdial", "yes", "d"), _rec(5, "faithdial", "no", "e")]
    first = {recs[3].id: {"id": recs[3].id, "label": "no", "note": "supported"}}
    rows, excluded = E.select(recs, v1_texts={normalise("seen in v1")}, first_labels=first)
    reasons = {e["id"]: e["reason"] for e in excluded}
    assert reasons[recs[0].id].startswith("overlap") and reasons[recs[1].id].startswith("duplicate") and reasons[recs[2].id].startswith("duplicate")
    assert reasons[recs[3].id].startswith("first labeller disagrees")
    assert [d["id"] for d in rows] == [recs[4].id]


def test_same_source_text_merges_groups():
    recs = [_rec(1, "faithdial", "yes", "a", source="same knowledge"), _rec(2, "faithdial", "no", "b", source="Same  knowledge")]
    g = E.merge_groups(recs)
    assert g[recs[0].id] == g[recs[1].id]


def test_strata_split_each_class_quota_by_subset():
    rows = {f"g{i}": [_rec(i, "ragbench", "yes", f"g{i}", notes={"subset": "pubmedqa" if i < 50 else "hagrid"})] for i in range(100)}
    import random
    got = E.pick(rows, 10, 1, random.Random(1), {}, {"pubmedqa": 0.5, "hagrid": 0.5})
    assert Counter(E.stratum_of(r) for r in got) == {"pubmedqa": 5, "hagrid": 5}


# ---------------------------------------------------------------- the committed candidate file

@pytest.fixture(scope="module")
def cands():
    try:
        return e2_local.candidates("grounding")
    except e2_local.LocalDataMissing as e:          # private slice and licence-withheld text are git-ignored
        pytest.skip(str(e))


def test_candidates_meet_the_edition_2_targets(cands):
    assert len(cands) >= 400
    sources = {d["source"] for d in cands}
    assert len(sources - {"ragtruth"}) >= 2
    c = Counter((d["proposed_split"], d["label"]) for d in cands)
    for split in SPLITS:
        assert c[(split, "yes")] == c[(split, "no")] > 0, split
    per_source = Counter((d["source"], d["proposed_split"], d["label"]) for d in cands)
    for (src, split, label), n in per_source.items():
        assert per_source[(src, split, "no" if label == "yes" else "yes")] == n, (src, split)


def test_candidates_are_valid_records_with_the_candidate_fields(cands):
    for d in cands:
        r = Record.from_dict(d)                                                   # validates
        assert d["suite"] == "grounding" and r.feature == "F6" and r.subtask == "grounding"
        assert d["label"] == r.expected in ("yes", "no")
        assert d["source"] == r.provenance.source and d["licence"] == r.provenance.licence and d["licence"]
        assert d["proposed_split"] in SPLITS and d["label_rationale"].strip()
        assert d["first_labeller"] in ("read", "diff_checked", "adopted")
        assert json.loads(r.provenance.notes)["revision"]                         # pinned upstream revision
        assert (r.split, r.visibility) == {"dev": ("dev", "public"), "test": ("test", "public"), "private": ("test", "heldout")}[d["proposed_split"]]
        assert r.state.source and r.state.query


def test_candidates_are_unique_and_groups_never_straddle_splits(cands):
    assert len({d["id"] for d in cands}) == len(cands)
    assert len({normalise(d["state"]["text"]) for d in cands}) == len(cands)
    where = defaultdict(set)
    for d in cands:
        where[d["group"]].add(d["proposed_split"])
    assert all(len(s) == 1 for s in where.values())
    by_source_text = defaultdict(set)
    for d in cands:
        by_source_text[normalise(d["state"]["source"])].add(d["proposed_split"])
    assert all(len(s) == 1 for s in by_source_text.values())


def test_candidates_do_not_overlap_v1_rows_ledgers_or_examined_ids(cands):
    builds = sorted((ROOT / "dataset" / "release").glob("*/build"))
    ids, texts = E.v1_index(builds)
    assert ids and texts                                                         # samples and ledgers are committed
    assert not {d["id"] for d in cands} & ids
    assert not {normalise(d["state"]["text"]) for d in cands} & texts


def test_every_candidate_was_checked_by_the_first_labeller(cands):
    first = {d["id"]: d for d in e2_local.row_file("grounding", "first_labels.jsonl")}
    for d in cands:
        fl = first.get(d["id"])
        assert fl and fl["label"] == d["label"], d["id"]


def test_blind_packet_covers_every_candidate_without_labels(cands):
    pdir = e2_local.packet_dir("grounding")                       # git-ignored: it holds every row's text
    if not (pdir / "packet.md").exists():
        pytest.skip("packet not on this machine")
    key = json.loads((pdir / "_lead" / "e2-grounding.key.json").read_text(encoding="utf-8"))["review_id_to_record_id"]
    assert sorted(key.values()) == sorted(d["id"] for d in cands)
    tmpl = [json.loads(l) for l in (pdir / "labels.template.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert [t["review_id"] for t in tmpl] == list(key) and all(t["labels"] == {"unsupported": None} for t in tmpl)
    md = (pdir / "packet.md").read_text(encoding="utf-8")
    for leak in ("faithdial", "summedits", "ragbench", "label_rationale", "BEGIN:", "first_labeller"):
        assert leak not in md.lower() if leak.islower() else leak not in md


def test_would_be_built_test_split_meets_the_floor(cands):
    """>= 250 unsupported and 250 supported public test rows once the build holds disputed rows out: a row whose second
    label disagrees counts only when an owner ruling resolved it (resolutions.jsonl, ruling 4), with its final label."""
    seconds = {d["id"]: d for d in e2_local.relabels("grounding")}
    res = {}
    for path in (e2_local.suite_dir("grounding") / "resolutions.jsonl", e2_local.private_dir("grounding") / "resolutions.jsonl"):
        if path.exists():
            res.update({d["id"]: d for d in (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip())})
    built = Counter()
    for d in cands:
        if d["proposed_split"] != "test":
            continue
        s = seconds.get(d["id"])
        if s is None or s["label"] == d["label"]:
            built[d["label"]] += 1
        elif res.get(d["id"], {}).get("status") == "resolved":
            built[res[d["id"]]["final_label"]] += 1
    assert built["yes"] >= 250 and built["no"] >= 250, built
    assert len({d["source"] for d in cands if d["proposed_split"] == "test"} - {"ragtruth"}) >= 2


def test_rows_added_on_3_october_were_read_under_ruling_4(cands):
    """The quota raise of 3 October added rows only after the first labeller read them under owner ruling 4 (hedged
    unsupported claims count, omissions do not); the earlier rows are unchanged."""
    first = {d["id"]: d for d in e2_local.row_file("grounding", "first_labels.jsonl")}
    added = [d for d in cands if "2026-10-03" in first[d["id"]]["labeller"]]
    assert added and all("ruling 4" in first[d["id"]]["labeller"] for d in added)
    assert E.QUOTA == {"faithdial": 130, "summedits": 196, "ragbench": 98}
