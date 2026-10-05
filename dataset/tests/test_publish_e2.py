"""Edition 2 Hugging Face staging (goldrails_dataset.publish_e2): the privacy gates, ids-only stripping and the local
rebuild. The first tests use a small fake edition 2 folder; the last ones check the real staged folder against the
build and skip when either is not on this machine."""
import json
import tempfile
from pathlib import Path

import pytest

from goldrails_dataset import publish_e2 as P

CLEARED = "aegis2"                         # mode text, reviewed true in dataset/release/redistribution.json
WITHHELD = "e2_content_beavertails"        # ids_only (ruling 10)
SLICE_TEXT = "the unpublished slice row talks about lighthouse keepers counting seabirds every single morning"
WITHHELD_TEXT = "withheld beavertails text about a neighbour's garden shed that must never be published anywhere"


def record(rid, source, text, split="test"):
    return {"id": rid, "feature": "F1", "subtask": "input", "split": split, "visibility": "public", "group": rid,
            "state": {"role": "user", "text": text, "context": [], "tool_call": None, "source": None, "query": None},
            "category": {"ailuminate": "benign", "bedrock": "NONE", "source_label": None}, "labels": ["no", "yes"],
            "expected": "no", "expected_distribution": None, "spans": None, "attribute": {"e2": {"suite": "content"}},
            "review_status": "candidate",
            "provenance": {"source": source, "source_id": rid, "licence": "x", "label_basis": "llm",
                           "imported_at": "2026-10-02T00:00:00+00:00", "contamination": [], "exclude_reason": None,
                           "notes": None}}


def jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture
def world(tmp_path):
    """A fake edition 2 root (one public row from a cleared source, one ids-only row, one unpublished-slice row, one
    excluded id) and a clean staged folder made from it."""
    root = tmp_path / "edition2"
    jsonl(root / "EXCLUDED.jsonl", [{"id": "f1-aegis2-excluded01", "reason": "owner"}])
    pub = record("f1-aegis2-0000000001", CLEARED, "a plain public question about baking bread at home")
    wit = record("f1-e2_content_beavertails-0000000002", WITHHELD, WITHHELD_TEXT)
    red = json.loads(json.dumps(wit))
    red["state"]["text"] = None
    red["redacted"] = {"why": "licence", "fields_sha256": "x"}
    jsonl(root / "content" / "candidates.jsonl", [dict(pub, proposed_split="test"), dict(red, proposed_split="test")])
    jsonl(root / "content" / "local" / "text.jsonl", [{"id": wit["id"], "source": WITHHELD,
                                                         "fields": [{"text": WITHHELD_TEXT}]}])
    sl = record("f1-aegis2-slice00001", CLEARED, SLICE_TEXT)
    jsonl(root / "content" / "private" / "candidates.jsonl", [dict(sl, proposed_split="private")])
    jsonl(root / "build" / "private" / "F1.test.jsonl", [sl])
    (root / "build" / "private" / "manifest.json").write_text("{}", encoding="utf-8")
    stage = tmp_path / "stage"
    rows = [dict(pub, redistribution="text", canonical_row_hash=P.canonical_hash(pub)),
            dict(P.strip_row(wit), canonical_row_hash=P.canonical_hash(wit))]
    jsonl(stage / "data" / "content" / "test.jsonl", rows)
    (stage / "EXCLUDED.jsonl").write_text((root / "EXCLUDED.jsonl").read_text(), encoding="utf-8")
    (stage / "README.md").write_text("# card\n", encoding="utf-8")
    return {"root": root, "stage": stage, "build": root / "build", "pub": pub, "wit": wit, "slice": sl}


def run(w):
    return P.gates(w["stage"], w["root"], w["build"])


def failing(rep):
    return {g for g, v in rep.items() if v}


def test_a_clean_staged_folder_passes_every_gate(world):
    rep = run(world)
    assert set(rep) == set(P.GATES) and failing(rep) == set()


def test_strip_row_nulls_text_and_quoting_fields_and_keeps_labels(world):
    wit = dict(world["wit"])
    wit["provenance"] = {**wit["provenance"], "notes": json.dumps({"why": "quotes: " + WITHHELD_TEXT[:60]})}
    out = P.strip_row(wit)
    assert out["state"]["text"] is None and out["provenance"]["notes"] is None
    assert ["state", "text"] in out["withheld"]["paths"] and ["provenance", "notes"] in out["withheld"]["paths"]
    assert out["expected"] == wit["expected"] and out["redistribution"] == "ids_only"
    assert WITHHELD_TEXT[:30] not in json.dumps(out)


def test_gate_unpublished_slice_row(world):
    sl = world["slice"]
    with (world["stage"] / "data" / "content" / "test.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(sl, redistribution="text", canonical_row_hash=P.canonical_hash(sl))) + "\n")
    rep = run(world)
    assert any("unpublished slice" in p for p in rep["no_unpublished_slice"])
    assert "no_private_or_local_paths" in failing(rep)       # its record lives in content/private/


def test_gate_unpublished_slice_text_anywhere(world):
    (world["stage"] / "README.md").write_text(f"# card\n\nExample: {SLICE_TEXT}\n", encoding="utf-8")
    assert any("private_text" in p for p in run(world)["no_unpublished_slice"])


def test_gate_withheld_text_in_a_row(world):
    p = world["stage"] / "data" / "content" / "test.jsonl"
    rows = [json.loads(x) for x in p.read_text().split("\n") if x.strip()]
    rows[1]["state"]["text"] = WITHHELD_TEXT
    jsonl(p, rows)
    assert any("carries text" in x for x in run(world)["no_withheld_text"])
    rows[1]["redistribution"] = "text"
    jsonl(p, rows)
    assert any("uncleared source" in x for x in run(world)["no_withheld_text"])


def test_gate_withheld_text_in_a_side_file(world):
    (world["stage"] / "NOTES.md").write_text(f"see: {WITHHELD_TEXT}\n", encoding="utf-8")
    assert any("withheld_text" in x for x in run(world)["no_withheld_text"])


def test_gate_excluded_rows(world):
    ex = record("f1-aegis2-excluded01", CLEARED, "an excluded row with ordinary text in it about trains")
    with (world["stage"] / "data" / "content" / "test.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(ex, redistribution="text", canonical_row_hash=P.canonical_hash(ex))) + "\n")
    assert run(world)["no_excluded_rows"]


def test_gate_staged_exclusion_list_names_only_public_ids(world):
    with (world["stage"] / "EXCLUDED.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": "f1-aegis2-privexcl01", "reason": "unpublished"}) + "\n")
    assert run(world)["no_excluded_rows"]


def test_gate_private_or_local_paths(world):
    jsonl(world["stage"] / "data" / "private" / "test.jsonl", [])
    jsonl(world["stage"] / "local" / "text.jsonl", [])
    probs = run(world)["no_private_or_local_paths"]
    assert any("private" in p for p in probs) and any("local" in p for p in probs)


def test_rehydrate_restores_the_canonical_row_or_refuses(world):
    wit = world["wit"]
    staged = dict(P.strip_row(wit), canonical_row_hash=P.canonical_hash(wit))
    rows, tally = P.rehydrate_rows([staged], variants={wit["id"]: [wit]})
    assert rows == [wit] and tally["rehydrated"] == 1
    wrong = json.loads(json.dumps(wit))
    wrong["state"]["text"] = "something else"
    with pytest.raises(P.PublishError):
        P.rehydrate_rows([staged], variants={wit["id"]: [wrong]})


# --- the real staged folder (owner machine only) -------------------------------------------------------------------

have_real = pytest.mark.skipif(
    not ((P.STAGE / P.CANONICAL).exists() and (P.BUILD / "manifest.json").exists()
         and all(e2_local_ok for e2_local_ok in [P.e2_local.have_local(s) for s in P.e2_local.SUITES])),
    reason="the staged folder, the edition 2 build or the local parts are not on this machine")


@have_real
def test_real_staged_folder_rebuilds_the_build_byte_for_byte():
    rep = P.parity()
    assert rep["pass"], {k: v for k, v in rep["files"].items() if not v["byte_identical"]}


@have_real
def test_real_staged_folder_passes_the_gates():
    rep = P.gates()
    assert not any(rep.values()), rep


@have_real
def test_hub_loader_path_gives_the_build_dataset_hashes():
    """datasets.load_dataset on the staged folder (how the Hub serves it), then the local rebuild: every file's rows
    hash to the build manifest's dataset hash."""
    import datetime
    from datasets import load_dataset
    from goldrails_dataset.records import Record, dataset_hash
    can = json.loads((P.STAGE / P.CANONICAL).read_text())
    local = P.local_only_ids()
    build = {f["build_file"]: [json.loads(x) for x in (P.BUILD / f["build_file"]).read_text().split("\n") if x.strip()]
             for f in can["files"]}
    variants = P._local_variants(set(P.SUITE_OF.values()))
    with tempfile.TemporaryDirectory() as cache:
        for f in can["files"]:
            ds = load_dataset(str(P.STAGE), name=f["config"], split=f["split"], cache_dir=cache)
            rows = []
            for x in ds:
                x = dict(x)
                if isinstance(x["provenance"].get("imported_at"), datetime.datetime):
                    x["provenance"]["imported_at"] = "2026-10-02T00:00:00+00:00"   # Arrow parses it; it is volatile
                rows.append(x)
            assert len(rows) == f["n"]
            full, _ = P.rehydrate_rows(rows, variants=variants)
            full += [r for r in build[f["build_file"]] if r["id"] in local]
            assert dataset_hash([Record.from_dict(r) for r in full]) == f["build_dataset_sha256"], f["build_file"]
