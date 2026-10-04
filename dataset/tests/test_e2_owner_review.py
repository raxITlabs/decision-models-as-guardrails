"""The owner review page and its importer (goldrails_dataset.e2_owner_review). Offline, on a synthetic edition 2 folder."""
import json

import pytest

from goldrails_dataset import e2_owner_review as R


def _w(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture
def root(tmp_path):
    pii = [{"id": "f5-src-0000000001", "label": "yes", "subtask": "pii", "proposed_split": "test", "source": "src",
            "entity_types": ["NAME", "PASSWORD"], "spans": [{"start": 0, "end": 3, "label": "NAME"}],
            "state": {"role": "user", "text": "Ann's password </script> is hunter2"}}]
    _w(tmp_path / "pii" / "candidates.jsonl", pii)
    _w(tmp_path / "pii" / "private" / "candidates.jsonl", [])
    _w(tmp_path / "pii" / "relabel.jsonl", [{"id": "f5-src-0000000001", "label": "yes", "entity_types": ["NAME"]}])
    _w(tmp_path / "pii" / "resolutions.jsonl", [{"id": "f5-src-0000000001", "status": "owner_review", "suite": "pii",
                                                 "first_label": "yes", "subtask": "pii", "question": "P-Q9",
                                                 "question_text": "Is it a password?"}])
    content = [{"id": "f1-src-0000000002", "label": "no", "subtask": "input", "proposed_split": "test", "source": "src",
                "state": {"role": "user", "text": "you absolute clown"}}]
    _w(tmp_path / "content" / "candidates.jsonl", content)
    _w(tmp_path / "content" / "private" / "candidates.jsonl", [])
    _w(tmp_path / "content" / "resolutions.jsonl", [{
        "id": "f1-src-0000000002", "status": "owner_review", "suite": "content", "first_label": "no", "subtask": "input",
        "question": "C-R8", "question_text": "confirm?", "needs_owner_confirmation": True,
        "proposed": {"final_label": "yes", "ruling": 8, "reason": "ruling 8 (C3)",
                     "final_tags": {"harm_category": "insults"}, "final_category": {"bedrock": "INSULTS"}}}])
    return tmp_path


def test_page_lists_waiting_rows_with_text_and_is_only_written_privately(root, tmp_path):
    items = R.review_items(root)
    assert [i["id"] for i in items] == ["f1-src-0000000002", "f5-src-0000000001"]
    assert items[1]["text"].startswith("Ann") and items[1]["second"]["entity_types"] == ["NAME"]
    assert items[0]["proposed"]["final_label"] == "yes"
    with pytest.raises(ValueError, match="private"):
        R.write_html(tmp_path / "review.html", root)
    rep = R.write_html(tmp_path / "build" / "private" / "review.html", root)
    page = (tmp_path / "build" / "private" / "review.html").read_text()
    assert rep["rows"] == 2 and "localStorage" in page and "Export JSONL" in page
    assert "</script> is hunter2" not in page          # a row's text cannot close the data script


def test_import_applies_decisions_and_confirms_ruling_8(root, tmp_path):
    dec = tmp_path / "d.jsonl"
    _w(dec, [{"id": "f5-src-0000000001", "suite": "pii", "final_label": "yes", "final_entity_types": ["NAME"],
              "note": "not a real password field"},
             {"id": "f1-src-0000000002", "suite": "content", "final_label": "yes"},
             {"id": "f1-src-0000000009", "final_label": ""}])
    rep = R.import_decisions(dec, root)
    assert rep["applied"] == 2 and rep["undecided_lines"] == 1
    p = json.loads((root / "pii" / "resolutions.jsonl").read_text())
    assert p["status"] == "resolved" and p["ruling"] == 9 and p["final_entity_types"] == ["NAME"]
    assert p["ruled_by"] == "owner" and p["owner_note"] == "not a real password field"
    c = json.loads((root / "content" / "resolutions.jsonl").read_text())
    assert c["status"] == "resolved" and c["ruling"] == 8 and c["final_tags"]["harm_category"] == "insults"
    assert "confirmed by the owner" in c["reason"]
    # a second import of the same rows is refused: they are no longer waiting
    with pytest.raises(ValueError, match="already resolved"):
        R.import_decisions(dec, root)


def test_import_checks_every_line_before_writing(root, tmp_path):
    before = (root / "pii" / "resolutions.jsonl").read_text()
    dec = tmp_path / "d.jsonl"
    _w(dec, [{"id": "f1-src-0000000002", "final_label": "no"},
             {"id": "f5-src-0000000001", "final_label": "yes", "final_entity_types": []}])   # yes with no type
    with pytest.raises(ValueError, match="needs some entity types"):
        R.import_decisions(dec, root)
    assert (root / "pii" / "resolutions.jsonl").read_text() == before
    _w(dec, [{"id": "f9-none-0000000000", "final_label": "no"}])
    with pytest.raises(ValueError, match="no owner_review line"):
        R.import_decisions(dec, root)
    _w(dec, [{"id": "f1-src-0000000002", "final_label": "yes", "harm_category": "nonsense"}])
    with pytest.raises(ValueError, match="harm_category"):
        R.import_decisions(dec, root)
