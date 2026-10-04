"""Edition 2 sensitive-information rows: the committed candidate file and the loader rules, offline."""
import json
from pathlib import Path
from collections import Counter, defaultdict

import pytest

from goldrails_dataset.sources import e2_pii as E
from goldrails_dataset.sources import e2_pii_controls, e2_pii_gretel, e2_pii_gretel_finance, e2_pii_nemotron

from goldrails_dataset import e2_local

ROWS = E.read_candidates() if e2_local.have_local("pii") else []
needs_file = pytest.mark.skipif(not ROWS, reason="pii candidates, private slice or text cache not on this machine")


# --- the committed candidate file ----------------------------------------------------------------------------------

@needs_file
def test_candidate_file_holds_its_invariants():
    assert E.check(ROWS) == []


@needs_file
def test_no_row_repeats_an_id_text_or_group_v1_used():
    refs = E.reference_index(use_hf_cache=False)          # repo files only: ledgers, subsets, examined list, reviews
    assert len(refs["ids"]) > 1000
    # the edition 2 smoke test (benchmark/results/edition2-smoke) sent 20 public dev rows per subtask through the
    # adapters after the rows were selected, and the dev-split sample (edition2-dev-sample) sent every public dev
    # row; those dev rows may be named in their ledgers, no test or private row may
    smoke = _smoke_row_ids()
    assert all(c["proposed_split"] == "dev" for c in ROWS if c["id"] in smoke)
    hits = [c["id"] for c in ROWS if (c["id"] in refs["ids"] or c["group"] in refs["groups"]
            or E.text_hash(c["state"]["text"]) in refs["texts"]) and c["id"] not in smoke]
    assert hits == []


def _smoke_row_ids() -> set:
    """Rows the edition 2 smoke run and the dev-split sample (benchmark/runs/e2_sample.py, every public dev row)
    sent through the adapters. Both send dev rows only."""
    res = Path(__file__).resolve().parents[2] / "benchmark" / "results"
    out = set()
    p = res / "edition2-smoke" / "summary.json"
    if p.exists():
        ids = json.loads(p.read_text(encoding="utf-8"))["row_ids"]
        out |= {i for v in ids.values() for i in v} if isinstance(ids, dict) else set(ids)
    for f in (res / "edition2-dev-sample").glob("*.jsonl"):
        out |= {json.loads(x)["row_id"] for x in f.open(encoding="utf-8") if x.strip()}
    return out


@needs_file
def test_class_targets_per_split():
    n = Counter((c["proposed_split"], c["label"]) for c in ROWS)
    assert n[("test", "yes")] >= 250 and n[("test", "no")] >= 250
    for split in ("dev", "private"):
        assert n[(split, "yes")] >= 50 and n[(split, "no")] >= 50


@needs_file
def test_every_supported_type_reaches_the_test_floor_and_has_dev_and_private_rows():
    ent = defaultdict(Counter)
    for c in ROWS:
        for t in c["entity_types"]:
            ent[t][c["proposed_split"]] += 1
    for t in E.SUPPORTED:
        assert ent[t]["test"] >= 50, (t, ent[t])
        assert ent[t]["dev"] >= 10 and ent[t]["private"] >= 10, (t, ent[t])


@needs_file
def test_at_least_two_sources_per_class_and_for_every_type():
    for label in ("yes", "no"):
        assert len({c["source"] for c in ROWS if c["label"] == label and c["proposed_split"] == "test"}) >= 2
    for t in E.SUPPORTED:
        assert len({c["source"] for c in ROWS if t in c["entity_types"] and c["proposed_split"] == "test"}) >= 2, t


@needs_file
def test_driver_rows_keep_a_yes_label_without_driver_id():
    for c in ROWS:
        if "DRIVER_ID" in c["entity_types"]:
            assert set(c["entity_types"]) - {"DRIVER_ID"}, c["id"]


@needs_file
def test_one_row_per_group_and_loaders_turn_private_into_heldout_test():
    assert len({c["group"] for c in ROWS}) == len(ROWS)
    recs = []
    for mod in (e2_pii_nemotron, e2_pii_gretel, e2_pii_gretel_finance, e2_pii_controls):
        got = mod.load()
        assert got, mod.NAME
        recs += got
    assert len(recs) == len(ROWS)
    by_id = {c["id"]: c for c in ROWS}
    for r in recs:
        r.validate()
        c = by_id[r.id]
        assert r.expected == c["label"] and r.subtask == "pii" and r.feature == "F5"
        assert (r.split, r.visibility) == (("test", "heldout") if c["proposed_split"] == "private" else (c["proposed_split"], "public"))
        assert json.loads(r.provenance.notes)["label_rationale"]


@needs_file
def test_nemotron_rows_use_the_v1_id_namespace():
    from goldrails_dataset.records import make_id
    for c in ROWS:
        if c["source"] == "nemotron_pii":
            assert c["id"] == make_id("F5", "nemotron_pii", c["source_id"])
            assert c["revision"] == "b70ffaf5ff39e079776134c5bf4381f00a9fd1ed" and c["upstream_split"] == "test"


@needs_file
def test_every_negative_authored_and_rare_type_row_gets_a_full_second_label():
    for c in ROWS:
        if c["label"] == "no" or c["label_basis"] == "llm" or set(c["entity_types"]) & E.RARE:
            assert c["second_label"] == "required", c["id"]
        assert c["review_status"] in ("candidate", "source_label")
        if c["label"] == "no":
            assert c["review_status"] == "candidate"


@needs_file
def test_packet_is_blind():
    pdir = e2_local.packet_dir("pii")                             # git-ignored: it holds every row's text
    if not (pdir / "packet.md").exists():
        pytest.skip("packet not on this machine")
    tmpl = [json.loads(l) for l in (pdir / "labels.template.jsonl").read_text().splitlines()]
    key = json.loads((pdir / "_lead" / "key.json").read_text())["review_id_to_record_id"]
    assert {t["review_id"] for t in tmpl} == set(key)
    required = {c["id"] for c in ROWS if c["second_label"] == "required"}
    assert required <= set(key.values())
    md = (pdir / "packet.md").read_text()
    for leak in ("nemotron", "gretel", "e2_pii_controls", "label_rationale", "proposed_split", "f5-"):
        assert leak not in md.lower()
    for t in tmpl:
        assert set(t["labels"]) == set(E.SUPPORTED) | {"other_personal_information"}
        assert all(v is None for v in t["labels"].values())


# --- rules ---------------------------------------------------------------------------------------------------------

def test_screen_finds_unlisted_supported_values():
    assert E.screen("mail a.b@c.org now", set(), False) == ["unlisted email-shaped value"]
    assert "unlisted IP address" in E.screen("host 10.2.3.4 is down", set(), False)
    assert "unlisted IP address" in E.screen("bind fe80::1ff:fe23:4567:890a", set(), False)
    assert E.screen("Release 3.12.4 and model 4.0 scored 0.83 at 12:30:45", set(), False) == []
    assert "unlisted SSN-shaped number" in E.screen("ssn 123-45-6789", set(), False)
    assert "unlisted phone-shaped number" in E.screen("call (555) 201-3344 today", set(), False)
    assert E.screen("ISBN 978-0-306-40615-7 and order 4417-2290-118", set(), False) == []
    assert "password key with a value" in E.screen("Password: hunter22", set(), False)
    assert "driver's licence mention without a verified number" in E.screen("Vehicle V52 - Driver ID: S-489142-V", set(), False)
    assert "username key or @handle" in E.screen("ping @dev_ops about it", set(), False)
    assert E.screen("email me at a.b@c.org", {"EMAIL"}, False) == []


def test_type_absent_screens():
    assert "street or state-and-ZIP pattern" in E.screen("Ship to 42 Elm Street by Friday, thanks a lot for the help.", set(), True)
    assert "street or state-and-ZIP pattern" in E.screen("Ship to 42 Elm Street by Friday, thanks.", {"NAME"}, False)
    assert E.screen("Ship to 42 Elm Street by Friday, thanks.", {"ADDRESS"}, False) == []
    assert E.name_hint("Reviewer Name: John Doe, Date 2015")
    assert not E.name_hint("Dear Valued Customer, thank you. Company Name: Velox Motors")
    assert "negative shorter than 60 characters" in E.screen("Date of Birth: 2020-09-19", set(), True)


def test_lexicon_screens_names_and_places_only_when_their_type_is_absent():
    lex = {"first_names": ["John", "Priya"], "places": ["Abu Dhabi", "St. Louis"]}
    assert E.lexicon_hit("Farmer: John Doe, corn", lex) == "a first name the sources label elsewhere"
    assert E.lexicon_hit("Farmer: John Doe, corn", lex, ["NAME"]) is None
    assert E.lexicon_hit("Shipped from Abu Dhabi on Monday", lex) == "a city or state the sources label elsewhere"
    assert E.lexicon_hit("Office in St. Louis", lex) is not None
    assert E.lexicon_hit("Abu is a word; Dhabi alone too", lex) is None
    assert E.lexicon_hit("Shipped from Abu Dhabi", lex, ["ADDRESS"]) is None


@needs_file
def test_committed_lexicon_drops_common_words():
    lex = E.read_lexicon()
    assert lex and "Two" not in lex["first_names"] and "Health" not in lex["first_names"]


def test_driver_context_needs_a_label_right_before_the_value():
    t = "**Driver License**\n\n**License Number:** TX-37218495"
    assert E.driver_context_ok(t, t.index("TX-"))
    t = "Bring a driver's license, passport, or national id 5501122689701"
    assert not E.driver_context_ok(t, t.index("5501"))
    t = "the license plate associated with this driver license is 8GJ325"
    assert E.driver_context_ok(t, t.index("8GJ"))       # label right before; nemotron maps only licence-number types
    t = "Your policy number is 34-438489-77"
    assert not E.driver_context_ok(t, t.index("34-"))


def test_ambiguous_context():
    t = 'record "hash": "&#2GrRfWne9BoFYe"'
    assert E.ambiguous_context("PASSWORD", t, t.index("&#2"))
    t = "Password: River45#"
    assert not E.ambiguous_context("PASSWORD", t, t.index("River"))
    t = "SSID: ashley01, Channel 6"
    assert E.ambiguous_context("USERNAME", t, t.index("ashley"))


def test_split_is_a_fixed_function_of_the_group():
    assert E.split_of("g-1") == E.split_of("g-1")
    shares = Counter(E.split_of(f"g-{i}") for i in range(5000))
    assert 0.66 < shares["test"] / 5000 < 0.74 and 0.12 < shares["dev"] / 5000 < 0.18


def test_join_on_values_groups_shared_identifiers():
    root = E.join_on_values([("a", ["x@y.com"]), ("b", ["X@Y.COM", "555-0101"]), ("c", ["555-0101"]), ("d", ["zz"])])
    assert root["a"] == root["b"] == root["c"] != root["d"]


def test_nemotron_mapping_rules():
    text = "Driver License Number: TX-1472398. Name: Ann Lee. PIN 4471."
    row = {"text": text, "locale": "us", "spans": [
        {"start": text.index("TX-"), "end": text.index("TX-") + 10, "label": "certificate_license_number"},
        {"start": text.index("Ann"), "end": text.index("Ann") + 3, "label": "first_name"}]}
    spans, src, why = e2_pii_nemotron.map_spans(row)
    assert set(src) == {"DRIVER_ID", "NAME"} and why == []
    row["spans"].append({"start": text.index("4471"), "end": text.index("4471") + 4, "label": "pin"})
    assert "pin span: may be a passcode" in e2_pii_nemotron.map_spans(row)[2]
    other = {"text": "Certificate CPA-1 issued.", "locale": "us",
             "spans": [{"start": 12, "end": 17, "label": "certificate_license_number"}]}
    assert any("unknown kind" in w for w in e2_pii_nemotron.map_spans(other)[2])
    intl = {"text": "id 123-45-6789", "locale": "intl", "spans": [{"start": 3, "end": 14, "label": "ssn"}]}
    assert "ssn label on an international row" in e2_pii_nemotron.map_spans(intl)[2]


def test_gretel_mapping_rules():
    text = "User 'kim_7' set password 'Xy9!pq' and SSN 123-45-6789; hash: 'Ab#9zz'"
    ents = [{"entity": "kim_7", "types": ["user_name"]}, {"entity": "Xy9!pq", "types": ["password"]},
            {"entity": "123-45-6789", "types": ["ssn"]}]
    spans, src, why = e2_pii_gretel.map_entities(text, ents)
    assert set(src) == {"USERNAME", "PASSWORD", "US_SOCIAL_SECURITY_NUMBER"} and why == []
    assert all(text[s["start"]:s["end"]] in ("kim_7", "Xy9!pq", "123-45-6789") for s in spans)
    _, _, why = e2_pii_gretel.map_entities(text, ents + [{"entity": "Ab#9zz", "types": ["password"]}])
    assert any("doubtful context" in w for w in why)
    _, _, why = e2_pii_gretel.map_entities("ssn 12345678", [{"entity": "12345678", "types": ["ssn"]}])
    assert why == ["ssn value not in the US shape"]
    _, _, why = e2_pii_gretel.map_entities("hello", [{"entity": "absent", "types": ["email"]}])
    assert why == ["email value not found in the text"]


def test_gretel_finance_rejects_driver_labels_without_a_driver_label():
    text = "Your policy number is 34-438489-77 and your name is Ana Ruiz."
    raw = [{"start": text.index("34-"), "end": text.index("34-") + 12, "label": "driver_license_number"},
           {"start": text.index("Ana"), "end": text.index("Ana") + 8, "label": "name"}]
    spans, src, why = e2_pii_gretel_finance.map_spans(text, raw)
    assert "DRIVER_ID" not in src and why == ["driver_license_number span without a driver's-licence label"]


def test_authored_rows():
    try:
        rows = e2_pii_controls.candidates()
    except e2_local.LocalDataMissing as e:          # held-out authored cases are git-ignored, owner only
        pytest.skip(str(e))
    neg = [c for c in rows if c["label"] == "no"]
    pos = [c for c in rows if c["label"] == "yes"]
    assert len(neg) == len(e2_pii_controls.NEGATIVES) and len(pos) == len(e2_pii_controls.DRIVER_POSITIVES)
    assert {c["notes"]["tempts"] for c in neg} == set(E.SUPPORTED)
    for c in rows:
        assert c["label_basis"] == "llm" and c["review_status"] == "candidate" and c["label_rationale"]
    for c in pos:
        assert {"DRIVER_ID", "NAME"} <= set(c["entity_types"])
        for s in c["spans"]:
            assert s["label"] in c["entity_types"]
    # hard negatives hold no unlisted email, IP, SSN-shaped or phone-shaped value
    hard = ("unlisted email-shaped value", "unlisted IP address", "unlisted SSN-shaped number", "unlisted phone-shaped number")
    for c in neg:
        assert not set(E.screen(c["state"]["text"], set(), True)) & set(hard), c["state"]["text"]
