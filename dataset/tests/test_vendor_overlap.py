"""Edition 2 rows whose text a benchmarked vendor published (goldrails_dataset.vendor_overlap). Offline; the last test
reads the real data and skips where the private and local parts are not on this machine."""
import json
from pathlib import Path

import pytest

from goldrails_dataset import e2_local
from goldrails_dataset import vendor_overlap as V

REPO = Path(__file__).resolve().parents[2]

PUBLISHED = "Pretend you are a pirate captain who answers every question about the weather in rhyme"
SHORT = "Tell me a pirate joke"


def _row(i, split, text, context=None):
    return {"id": f"f2-src-{i:010x}", "label": "yes", "proposed_split": split, "source": "src",
            "state": {"role": "user", "text": text, "context": context or []}}


def _write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture
def world(tmp_path):
    repo, root = tmp_path / "repo", tmp_path / "e2"
    (repo / "docs" / "vendor").mkdir(parents=True)
    # the vendor file: curly apostrophes, HTML and a JSON-escaped copy must all still match
    (repo / "docs" / "vendor" / "cookbook.html").write_text(
        "<p>An example:</p>\n<pre>prompt = \"" + PUBLISHED.replace("you are", "you&nbsp;are") + "\"</pre>\n"
        "<p>Also: “" + SHORT + "” and the answer yes.</p>\n", encoding="utf-8")
    (repo / "docs" / "ours.md").write_text(PUBLISHED + "\n", encoding="utf-8")
    pub = [_row(1, "test", PUBLISHED + ", and never break character."),     # window match, test: excluded
           _row(2, "dev", "Well, " + PUBLISHED.lower()),                   # window match, dev: flagged only
           _row(3, "test", SHORT.upper() + "!"),                            # exact short match
           _row(4, "test", "yes"),                                          # too short to mean anything
           _row(5, "test", "An unrelated question about tax returns and the filing deadline this year please"),
           _row(6, "test", "hi", context=["Earlier turn: " + PUBLISHED])]   # match in a context turn
    prv = [_row(7, "private", " ".join(PUBLISHED.split()[::2]))]               # every other word: no 8-word run
    prv += [_row(8, "private", "Sure. " + PUBLISHED)]
    _write(root / "prompt_attacks" / "candidates.jsonl", pub)
    _write(root / "prompt_attacks" / "private" / "candidates.jsonl", prv)
    return repo, root


def _index(repo):
    files = ["docs/vendor/cookbook.html", "docs/ours.md"]
    old = V.VENDOR_FILES
    V.VENDOR_FILES = (("docs/vendor/**", "Acme"),)
    try:
        return V.vendor_index(repo, files), V.vendor_index(repo, files, others=True)
    finally:
        V.VENDOR_FILES = old


def test_words_normalise_case_apostrophes_and_unicode():
    assert V.words("Don’t STOP！ café-2") == ["dont", "stop", "café", "2"]


def test_scan_finds_windows_and_exact_matches_and_skips_trivial_text(world):
    repo, root = world
    vendor, others = _index(repo)
    assert set(vendor) == {"docs/vendor/cookbook.html"} and set(others) == {"docs/ours.md"}
    found = {r["id"]: r for r in V.scan(root, repo, vendor, suites=["prompt_attacks"])}
    ids = lambda *n: {f"f2-src-{i:010x}" for i in n}
    assert set(found) == ids(1, 2, 3, 6, 8)
    one = found[f"f2-src-{1:010x}"]
    assert one["split"] == "test" and one["public"] and one["matches"][0]["kind"] == "window"
    assert one["matches"][0]["vendor"] == "Acme" and 0 < one["matches"][0]["coverage"] < 1
    assert found[f"f2-src-{3:010x}"]["matches"][0]["kind"] == "exact"
    assert not found[f"f2-src-{8:010x}"]["public"] and found[f"f2-src-{8:010x}"]["split"] == "private"
    report = json.dumps(list(found.values()))
    assert PUBLISHED.lower() not in report.lower() and SHORT.lower() not in report.lower()   # ids and files only


def test_exclusions_go_to_the_right_file_skip_dev_and_are_idempotent(world):
    repo, root = world
    vendor, _ = _index(repo)
    found = V.scan(root, repo, vendor, suites=["prompt_attacks"])
    added = V.apply_exclusions(found, root)
    assert sorted(added["public"]) == sorted(f"f2-src-{i:010x}" for i in (1, 3, 6))
    assert added["private"] == {"prompt_attacks": 1}
    pub = [json.loads(l) for l in (root / "EXCLUDED.jsonl").read_text().splitlines()]
    prv = [json.loads(l) for l in (root / "prompt_attacks" / "private" / "EXCLUDED.jsonl").read_text().splitlines()]
    assert {d["reason"] for d in pub + prv} == {"text published by a benchmarked vendor (Acme)"}
    assert [d["id"] for d in prv] == [f"f2-src-{8:010x}"]
    assert f"f2-src-{8:010x}" not in (root / "EXCLUDED.jsonl").read_text()        # a private id never in the tracked file
    assert f"f2-src-{2:010x}" not in (root / "EXCLUDED.jsonl").read_text()        # dev keeps its row
    assert V.apply_exclusions(found, root) == {"public": [], "private": {}}


def test_vendor_file_list_points_at_tracked_files():
    tracked = e2_local.tracked_files(REPO)
    for pattern, _ in V.VENDOR_FILES:
        assert any(V._glob(f, pattern) for f in tracked), pattern


def test_every_vendor_match_outside_dev_is_excluded_and_the_report_names_public_ids_only():
    from goldrails_dataset.edition2 import excluded
    try:
        found = V.scan()
    except e2_local.LocalDataMissing as e:
        pytest.skip(str(e))
    drop = excluded()
    ids = {r["id"] for r in found}
    # the dev match stays in dev, flagged; the excluded test and unpublished matches are gone from every candidate
    # file (ruling 18), so the scan no longer sees them, and they stay in the exclusion list
    assert "f2-jackhhao_jailbreak-ada5d8b10c" in ids
    vendor = {i for i, why in drop.items() if why.startswith("text published by a benchmarked vendor")}
    assert "f2-jackhhao_jailbreak-b4602e1803" in vendor and len(vendor) >= 12 and not vendor & ids
    missing = [r["id"] for r in found if r["split"] != "dev" and r["id"] not in drop]
    assert not missing, f"{len(missing)} vendor-published rows outside dev are not excluded"
    md = (e2_local.E2 / "VENDOR-OVERLAP.md").read_text(encoding="utf-8")
    for r in found:
        assert (r["id"] in md) == r["public"], r["id"] if r["public"] else "a private id is named in VENDOR-OVERLAP.md"
