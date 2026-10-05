"""The ruling 23 prompt-attack candidate (dataset/edition2/r23/prompt_attacks/): the role-swap generator's
construction rules, and the invariants of the committed files (privacy, floors, the recorded shortcut gate)."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
R23 = REPO / "dataset" / "edition2" / "r23" / "prompt_attacks"
MAIN = REPO / "dataset" / "edition2" / "prompt_attacks"
TEST_SALT = "0" * 64
WORD = re.compile(r"(?u)\b\w+\b")


def _jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").split("\n") if l.strip()] if p.exists() else []


# --- the generator ---------------------------------------------------------------------------------------------------

def test_every_noun_phrase_starts_with_the_and_every_connector_holds_a_word():
    from goldrails_dataset.sources import e2_prompt_attacks_r23 as g
    for fams in g.FAMILIES.values():
        for _, spec, _ in fams:
            for np_ in spec["P"] + spec["Q"]:
                assert np_.startswith("the "), np_
            for sep, _ in spec.get("conn", g.CONN):
                assert WORD.search(sep), f"connector without a word: {sep!r}"
            assert set(spec["P"]).isdisjoint(spec["Q"])


def test_twins_hold_the_same_words_and_the_label_follows_the_role():
    from goldrails_dataset.sources import e2_prompt_attacks_r23 as g
    pairs = g.generate(salt=TEST_SALT)
    assert len(pairs) == sum(n for fams in g.FAMILIES.values() for _, _, n in fams)
    for sub, fam, k, attack, benign, parts in pairs:
        assert attack != benign
        assert sorted(WORD.findall(attack.lower())) == sorted(WORD.findall(benign.lower())), (sub, fam, k)
        assert len(attack) == len(benign)
        assert f"{parts['act']} {parts['P']}".lower() in attack.lower()
        assert f"{parts['counter']} {parts['Q']}".lower() in attack.lower()
        assert f"{parts['act']} {parts['Q']}".lower() in benign.lower()
        assert f"{parts['counter']} {parts['P']}".lower() in benign.lower()


def test_word_counts_are_balanced_and_clause_order_is_drawn_both_ways():
    from goldrails_dataset.sources import e2_prompt_attacks_r23 as g
    rows = g.records(salt=TEST_SALT)
    bal = g.balance_check(rows)
    for sub, b in bal.items():
        uni = Counter(), Counter()
        for r in rows:
            if r.subtask == sub:
                uni[r.expected == "yes"].update(WORD.findall(r.state.text.lower()))
        assert uni[0] == uni[1], sub                          # single words: exactly equal, by construction
        assert b["max_abs_gap"] <= 25, (sub, b["largest"])    # word pairs: equal in expectation (clause order drawn)
    order = Counter(p[5]["act_first"] for p in g.generate(salt=TEST_SALT))
    assert min(order.values()) > 0.4 * sum(order.values())


def test_generation_is_fixed_by_the_salt():
    from goldrails_dataset.sources import e2_prompt_attacks_r23 as g
    a = [p[3] for p in g.generate(salt=TEST_SALT)]
    assert a == [p[3] for p in g.generate(salt=TEST_SALT)]
    assert a != [p[3] for p in g.generate(salt="1" * 64)]
    ids = {r.id for r in g.records(salt=TEST_SALT)}
    assert ids.isdisjoint({r.id for r in g.records(salt="1" * 64)})


def test_records_are_valid_authored_rows():
    from goldrails_dataset.sources import e2_prompt_attacks_r23 as g
    rows = g.records(salt=TEST_SALT)
    by = defaultdict(list)
    for r in rows:
        r.validate()
        n = json.loads(r.provenance.notes)
        assert r.provenance.source == "e2_attack_controls" and r.provenance.licence == "cc-by-4.0"
        assert r.provenance.label_basis == "deterministic" and n["revision"] == g.REVISION
        assert n["labeller"] == g.LABELLER and n["family"]
        by[r.group].append(r.expected)
    assert all(sorted(v) == ["no", "yes"] for v in by.values())


# --- the committed candidate -----------------------------------------------------------------------------------------

def _public():
    rows = _jsonl(R23 / "candidates.jsonl")
    if not rows:
        pytest.skip("the ruling 23 candidate is not built")
    return rows


def test_public_file_holds_no_unpublished_row_and_no_uncleared_text():
    from goldrails_dataset import e2_local
    pol = e2_local.policy()
    for c in _public():
        assert c["proposed_split"] in ("dev", "test")
        if not e2_local.text_cleared(c["source"], pol):
            assert "redacted" in c and c["state"]["text"] is None, c["id"]
        else:
            assert c["state"]["text"], c["id"]


def test_public_authored_pairs_are_whole_and_in_one_split():
    pairs = defaultdict(list)
    for c in _public():
        if c["source"] == "e2_attack_controls":
            pairs[c["group"]].append((c["label"], c["proposed_split"]))
    assert pairs
    for g, v in pairs.items():
        assert sorted(l for l, _ in v) == ["no", "yes"], g
        assert len({s for _, s in v}) == 1, g


def test_counts_meet_the_floors_and_the_recorded_gate_passes():
    _public()
    counts = json.loads((R23 / "counts.json").read_text(encoding="utf-8"))
    for sub in ("injection", "jailbreak", "leakage"):
        for lab in ("yes", "no"):
            assert counts["by_split"][f"{sub}/{lab}"]["test"] >= 250
    gate = json.loads((R23 / "gate.json").read_text(encoding="utf-8"))
    assert gate["pass"] and gate["in_sample_pass"] and gate["heldback_pass"] and not gate["failures"]
    assert len(gate["table"]) == 120
    for t in gate["table"]:
        assert t["ba"] <= 0.70 and t["auroc"] <= 0.75 and not t["constant_prediction"] and t["pass"], t
    for f in gate["floors"]:
        assert f["pass"] and min(f["public_test"].values()) >= 250
        assert len(f["sources_by_class"]["yes"]) >= 2 and len(f["sources_by_class"]["no"]) >= 2


def test_tracked_candidate_files_hold_no_unpublished_id_or_text():
    priv = _jsonl(R23 / "private" / "candidates.jsonl")
    main_priv = _jsonl(MAIN / "private" / "candidates.jsonl")
    if not priv or not main_priv:
        pytest.skip("the unpublished slice is owner-only and not on this machine")
    tracked = "".join(p.read_text(encoding="utf-8") for p in R23.iterdir() if p.is_file())
    for c in priv + main_priv:
        assert c["id"] not in tracked, c["id"]
        t = (c.get("state") or {}).get("text")
        if t and c["source"] == "e2_attack_controls":
            assert json.dumps(t)[1:-1] not in tracked, c["id"]
