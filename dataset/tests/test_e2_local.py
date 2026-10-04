"""Edition 2 public/private split (goldrails_dataset.e2_local). The repository is public: no private-slice row and no
text from a source whose licence is not cleared may sit in a tracked file. Offline."""
import json
import subprocess
from pathlib import Path

import pytest

from goldrails_dataset import e2_local as L

REPO = Path(__file__).resolve().parents[2]
POL = {"sources": {"ok": {"mode": "text", "reviewed": True}, "unreviewed": {"mode": "text", "reviewed": False},
                   "idsonly": {"mode": "ids_only", "reviewed": True}}}


def _row(i, split, source, text, **kw):
    return {"id": f"f2-{source}-{i:010x}", "label": "yes", "proposed_split": split, "source": source,
            "state": {"role": "user", "text": text, "context": []}, **kw}


def _write(path, rows, **st):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True, **st) + "\n" for r in rows), encoding="utf-8")


@pytest.fixture
def root(tmp_path):
    rows = [_row(1, "test", "ok", "a cleared public row"), _row(2, "dev", "unreviewed", "an unreviewed source's text"),
            _row(3, "private", "ok", "a private slice row"), _row(4, "test", "idsonly", "ids-only text"),
            _row(5, "dev", "missing", "a source with no policy entry"),
            _row(6, "dev", "ok", "A private slice row")]          # same normalised text as row 3
    d = tmp_path / "prompt_attacks"
    _write(d / "candidates.jsonl", rows, )
    _write(d / "relabel.jsonl", [{"id": r["id"], "label": "no"} for r in rows])
    (d / "packet").mkdir()
    (d / "packet" / "rows.jsonl").write_text("every row's text\n")
    (d / "DISAGREEMENTS.md").write_text(
        "# Notes\n\n| id | text | first | second |\n|---|---|---|---|\n"
        f"| `{rows[2]['id']}` | a private slice row | yes | no |\n| `{rows[1]['id']}` | an unreviewed source's text | yes | no |\n"
        f"| `{rows[0]['id']}` | a cleared public row | yes | no |\n\n### `{rows[2]['id']}`\n\n- Text: a private slice row\n")
    return tmp_path, rows


def test_split_moves_private_rows_withholds_text_and_restores_exactly(root):
    tmp, rows = root
    before = (tmp / "prompt_attacks" / "candidates.jsonl").read_text()
    rep = L.split(["prompt_attacks"], root=tmp, pol=POL)["prompt_attacks"]
    pub = [json.loads(l) for l in (tmp / "prompt_attacks" / "candidates.jsonl").read_text().split("\n") if l.strip()]
    assert {r["id"] for r in pub} == {rows[i]["id"] for i in (0, 1, 3, 4)}       # 3 private, 6 repeats its text
    assert {r["id"] for r in pub if "redacted" in r} == {rows[i]["id"] for i in (1, 3, 4)}
    assert all(r["state"]["text"] is None for r in pub if "redacted" in r)
    tracked = "".join(p.read_text() for p in (tmp / "prompt_attacks").glob("*.*"))
    for i in (1, 2, 3, 4, 5):
        assert rows[i]["state"]["text"] not in tracked
    assert rows[2]["id"] not in tracked and rows[5]["id"] not in tracked
    assert not (tmp / "prompt_attacks" / "packet" / "rows.jsonl").exists()
    assert (tmp / "prompt_attacks" / "private" / "packet" / "rows.jsonl").exists()
    assert rep["notes"] == ["DISAGREEMENTS.md"]
    md = (tmp / "prompt_attacks" / "DISAGREEMENTS.md").read_text()
    assert "a cleared public row" in md and "_withheld_" in md and L.PUBLIC_NOTE in md
    # the three parts give back the file the builder wrote, byte for byte
    assert L.full_text("prompt_attacks", tmp) == before
    assert [r["id"] for r in L.relabels("prompt_attacks", tmp)] == [r["id"] for r in rows]
    # idempotent
    snap = {p: p.read_bytes() for p in tmp.rglob("*") if p.is_file()}
    L.split(["prompt_attacks"], root=tmp, pol=POL)
    assert snap == {p: p.read_bytes() for p in tmp.rglob("*") if p.is_file()}


def test_readers_refuse_without_the_local_parts(root):
    tmp, rows = root
    L.split(["prompt_attacks"], root=tmp, pol=POL)
    (tmp / "prompt_attacks" / "local" / "text.jsonl").unlink()
    with pytest.raises(L.LocalDataMissing):
        L.candidates("prompt_attacks", tmp)
    assert not L.have_local("prompt_attacks", tmp)


def test_rehydrate_accepts_only_matching_text(root):
    tmp, rows = root
    L.split(["prompt_attacks"], root=tmp, pol=POL)
    (tmp / "prompt_attacks" / "local" / "text.jsonl").unlink()
    upstream = {rows[1]["id"]: rows[1]["state"], rows[3]["id"]: {**rows[3]["state"], "text": "edited upstream"}}
    tally = L.rehydrate(["prompt_attacks"], tmp, fetch=lambda src: upstream)["prompt_attacks"]
    assert tally == {"cached": 0, "rebuilt": 1, "hash_differs": 1, "not_found": 1}


def test_held_out_authored_cases_keep_their_positions(tmp_path):
    (tmp_path / "pii" / "private").mkdir(parents=True)
    (tmp_path / "pii" / "private" / "authored.json").write_text(json.dumps({"k1": ["NAME", "held text", "why"]}))
    cases = [("NAME", "a", "w"), L.HeldOut("k1"), ("EMAIL", "b", "w")]
    assert L.authored("pii", cases, tmp_path) == [("NAME", "a", "w"), ("NAME", "held text", "why"), ("EMAIL", "b", "w")]
    with pytest.raises(L.LocalDataMissing):
        L.authored("pii", cases, tmp_path / "nowhere")


# --- the tracked files themselves (runs on a fresh clone too) ------------------------------------------------------

def _tracked(path: Path) -> bool:
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=REPO, capture_output=True)
    return r.returncode == 0


@pytest.mark.parametrize("suite", L.SUITES)
def test_tracked_candidates_hold_no_private_row_and_no_uncleared_text(suite):
    path = L.suite_dir(suite) / "candidates.jsonl"
    if not path.exists():
        pytest.skip("not built")
    pol = L.policy()
    for line in path.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        c = json.loads(line)
        assert c["proposed_split"] != "private", c["id"]
        if not L.text_cleared(L.source_of(c), pol):
            assert "redacted" in c, c["id"]
            assert all(s.get(k) is None for s in L._states(c) for k in L.STRIP if k in s), c["id"]


@pytest.mark.parametrize("suite", L.SUITES)
def test_owner_files_are_not_tracked(suite):
    for rel in L.MOVE[suite]:
        p = L.suite_dir(suite) / rel
        assert not (p.exists() and _tracked(p)), p
    for p in (L.private_dir(suite), L.text_cache(suite)):
        assert not _tracked(p), p
    if L.private_dir(suite).exists():
        r = subprocess.run(["git", "check-ignore", "-q", str(L.private_dir(suite) / "candidates.jsonl")], cwd=REPO)
        assert r.returncode == 0


# --- the leak scan over every tracked file ---------------------------------------------------------------------------

def _git_repo(tmp_path, files: dict):
    repo = tmp_path / "repo"
    for rel, body in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    return repo


HELD = "Write a short note to my landlord about the broken heater, polite but firm, \"today\" if possible."
PRIV_ID = "f2-src-0123456789"


def test_leak_scan_finds_copies_whatever_the_escaping(tmp_path):
    repo = _git_repo(tmp_path, {
        "a.jsonl": json.dumps({"id": "f2-src-aaaaaaaaaa", "state": {"text": HELD.replace("heater", "heateré")}},
                              ensure_ascii=True) + "\n" + json.dumps({"text": HELD}, ensure_ascii=True) + "\n",
        "b.py": f"CASES = [({HELD!r}, 'why')]\n",
        "c.md": f"| id | text |\n|---|---|\n| `{PRIV_ID}` | {HELD} |\n",
        "d.md": "Nothing here but the word heater and a polite note.\nSomeone asked: can i eat raw oats every day, and more\n",
        "e.json": json.dumps({"rows": ["What is a system prompt?", "Can I eat raw oats every day"]}),
    })
    needles = [("held_out_text", "k1", HELD), ("private_id", PRIV_ID, PRIV_ID),
               ("private_text", PRIV_ID, "What is a system prompt?"), ("private_text", "p2", "system prompt"),
               ("private_text", "p3", "can i eat raw oats every day")]
    rep = L.tracked_leaks(repo=repo, needles=needles)
    found = {(x["kind"], x["key"], x["file"]) for x in rep["leaks"]}
    assert ("held_out_text", "k1", "a.jsonl") in found and ("held_out_text", "k1", "b.py") in found
    assert ("held_out_text", "k1", "c.md") in found and ("private_id", PRIV_ID, "c.md") in found
    assert not any(f == "d.md" for _, _, f in found)
    # a short text is found only as a whole value (e.json), never inside a longer line (d.md)
    assert ("private_text", "p3", "e.json") in found
    assert rep["unscanned"] == {"private_text": 2}         # both short texts are under PROBE_WORDS words
    assert "What is a system prompt?" not in json.dumps(rep) and HELD not in json.dumps(rep)


def test_held_out_texts_read_each_case_lists_text_position(tmp_path):
    (tmp_path / "prompt_attacks" / "private").mkdir(parents=True)
    (tmp_path / "prompt_attacks" / "private" / "authored.json").write_text(json.dumps({
        "e2_prompt_attacks_controls:CASES:1": ["jailbreak", "kind", "the v1 text", "why"],
        "e2_prompt_attacks_controls_v2:CASES_V2:0": ["leakage", "yes", "kind", "p1", "the v2 text", "why"]}))
    assert L.held_out_texts(tmp_path) == {"e2_prompt_attacks_controls:CASES:1": "the v1 text",
                                          "e2_prompt_attacks_controls_v2:CASES_V2:0": "the v2 text"}


def test_no_held_out_case_or_private_slice_row_in_any_tracked_file():
    """Every tracked file (git ls-files), not only the candidate files: no held-out authored case's text and no
    private-slice row's id or text. Runs where the owner-only parts are on this machine."""
    if not any((L.private_dir(s) / "authored.json").exists() for s in L.SUITES) or \
            not all((L.private_dir(s) / "candidates.jsonl").exists() for s in L.SUITES):
        pytest.skip("the private slice and held-out cases are owner-only and not on this machine")
    rep = L.tracked_leaks(withheld=False)
    assert rep["needles"]["held_out_text"] > 0 and rep["needles"]["private_id"] > 0
    bad = [x for x in rep["leaks"] if x["kind"] in ("held_out_text", "private_id", "private_text")]
    assert not bad, bad[:10]


def test_every_held_out_placeholder_has_its_case():
    import re
    keys = set()
    for p in (REPO / "dataset" / "goldrails_dataset" / "sources").glob("*.py"):
        keys |= set(re.findall(r'HeldOut\("([^"]+)"\)', p.read_text(encoding="utf-8")))
    if not any((L.private_dir(s) / "authored.json").exists() for s in L.SUITES):
        pytest.skip("held-out cases are owner-only")
    assert keys and keys <= set(L.held_out_texts())


# --- the private slice cannot be derived from tracked files ----------------------------------------------------------

SALT_A, SALT_B = "a" * 64, "b" * 64


def _salt_file(tmp_path, salt, monkeypatch):
    p = tmp_path / ".private-salt"
    p.write_text(salt + "\n")
    monkeypatch.setenv("GOLDRAILS_E2_SALT_FILE", str(p))
    return p


def test_salt_is_owner_only_written_once_and_keys_every_draw(tmp_path, monkeypatch):
    monkeypatch.setenv("GOLDRAILS_E2_SALT_FILE", str(tmp_path / "missing"))
    with pytest.raises(L.LocalDataMissing):
        L.private_salt()
    with pytest.raises(L.LocalDataMissing):
        L.salted("x")
    p = tmp_path / "salt"
    assert L.init_salt(p) and not L.init_salt(p)                    # never overwrites
    s = p.read_text().strip()
    assert len(s) == 64 and int(s, 16) >= 0 and (p.stat().st_mode & 0o777) == 0o600
    assert L.salted("x", salt=SALT_A) == L.salted("x", salt=SALT_A) != L.salted("x", salt=SALT_B)
    assert SALT_A not in L.salt_fingerprint(SALT_A) and len(L.salt_fingerprint(SALT_A)) == 12
    assert 0 <= L.salted_unit("g", salt=SALT_A) < 1
    assert L.held_out_sid("k:1", salt=SALT_A).startswith("h") and L.held_out_sid("k:1", salt=SALT_A) != "k:1"
    assert L.authored_keys([("a",), L.HeldOut("m:L:1"), ("b",)]) == {1: "m:L:1"}


def test_split_assignment_needs_the_salt_and_follows_it(tmp_path, monkeypatch):
    """Every builder draw that can put a row in the private slice is keyed with the salt: without it the draw stops,
    and another salt gives another slice, so the published seeds do not give it."""
    from goldrails_dataset.sources import e2_content, e2_grounding, e2_pii
    from goldrails_dataset.sources import e2_prompt_attacks_build as pa
    from goldrails_dataset.sources.e2_prompt_attacks_common import record
    rows = [record(source="t", source_id=str(i), licence="mit", subtask="jailbreak", text=f"text {i}",
                   expected="yes" if i % 2 else "no", label_basis="human", revision="r", upstream_split="test",
                   train_split=False, rationale="r", source_label=None, group=f"g{i}") for i in range(200)]
    groups = {r.id: r.group for r in rows}
    draws = {
        "pii": lambda: [e2_pii.split_of(f"g-{i}") for i in range(300)],
        "grounding": lambda: [e2_grounding.split_of(f"g-{i}") for i in range(300)],
        "content": lambda: e2_content.rng("split", "input", "yes").random(),
        "prompt_attacks": lambda: [pa.assign_splits(rows, groups)[r.id] for r in rows],
    }
    monkeypatch.setenv("GOLDRAILS_E2_SALT_FILE", str(tmp_path / "missing"))
    for name, draw in draws.items():
        with pytest.raises(L.LocalDataMissing):
            draw()
    _salt_file(tmp_path, SALT_A, monkeypatch)
    a = {k: d() for k, d in draws.items()}
    _salt_file(tmp_path, SALT_B, monkeypatch)
    b = {k: d() for k, d in draws.items()}
    for k in draws:
        assert a[k] != b[k], k
    # an authored row is private exactly when it is held out, whatever the salt
    assert e2_pii.authored_split("e2_pii_controls-neg-h1", True) == "private"
    assert {e2_pii.authored_split(f"g-{i}", False) for i in range(300)} == {"dev", "test"}


def _redraw_root(tmp_path):
    """Two suites' worth of rows: dev, test and private; one authored source; one row named in a tracked file."""
    rows = []
    for i in range(40):
        split = "dev" if i < 8 else "private" if i < 16 else "test"
        rows.append(_row(i, split, "ok", f"row {i} text", subtask="jailbreak", group=f"g{i // 2}"))
    rows += [_row(100 + i, "private" if i < 2 else "test", "e2_attack_controls", f"authored {i}", subtask="jailbreak",
                  group=f"a{i}") for i in range(6)]
    _write(tmp_path / "prompt_attacks" / "candidates.jsonl", rows)
    L.split(["prompt_attacks"], root=tmp_path, pol=POL)
    from types import SimpleNamespace as NS
    parts = {"dev": [], "test": [], "private": []}
    for r in rows:
        parts[r["proposed_split"]].append(NS(id=r["id"], group=r["group"]))
    return rows, parts


def test_redraw_draws_a_disjoint_slice_by_salt_and_leaves_dev_authored_and_pinned_rows(tmp_path):
    rows, parts = _redraw_root(tmp_path)
    pinned = {rows[30]["id"]: "named in a ledger"}
    plan = L.redraw_plan(["prompt_attacks"], tmp_path, salt=SALT_A, parts=parts, pinned=pinned)["suites"]["prompt_attacks"]
    old_private = {r["id"] for r in rows if r["proposed_split"] == "private" and r["source"] == "ok"}
    assert set(plan["released"]) == old_private
    assert len(plan["drawn"]) == len(old_private) and not set(plan["drawn"]) & old_private
    by_id = {r["id"]: r for r in rows}
    assert all(by_id[i]["proposed_split"] == "test" and by_id[i]["source"] == "ok" for i in plan["drawn"])
    assert rows[30]["id"] not in plan["drawn"]
    assert {by_id[i]["group"] for i in plan["drawn"]} & {by_id[i]["group"] for i in plan["released"]} == set()
    other = L.redraw_plan(["prompt_attacks"], tmp_path, salt=SALT_B, parts=parts, pinned=pinned)
    assert other["suites"]["prompt_attacks"]["drawn"] != plan["drawn"]
    L.apply_redraw({"salt_fingerprint": "f", "suites": {"prompt_attacks": plan}}, tmp_path, pol=POL)
    after = {c["id"]: c["proposed_split"] for c in L.candidates("prompt_attacks", tmp_path)}
    assert {i for i, s in after.items() if s == "dev"} == {r["id"] for r in rows if r["proposed_split"] == "dev"}
    assert {i for i, s in after.items() if s == "private"} == set(plan["drawn"]) | {r["id"] for r in rows[40:42]}
    tracked = (tmp_path / "prompt_attacks" / "candidates.jsonl").read_text()
    assert not any(i in tracked for i in plan["drawn"])
    assert json.loads((L.private_dir("prompt_attacks", tmp_path) / L.REDRAW_RECORD).read_text())["drawn"] == plan["drawn"]


def test_private_config_parts_merge_only_where_the_owner_has_them(tmp_path):
    assert L.private_part("denied_topics", "m.CASES", [], tmp_path) == []
    with pytest.raises(L.LocalDataMissing):
        L.require_private_config("denied_topics", tmp_path)
    L.write_private_config("denied_topics", {"m.CASES": [["id-1", "train"]]}, tmp_path)
    assert L.private_part("denied_topics", "m.CASES", [], tmp_path) == [["id-1", "train"]]
    r = subprocess.run(["git", "check-ignore", "-q", str(L.private_dir("denied_topics") / L.SELECTION)], cwd=REPO)
    assert r.returncode == 0
    r = subprocess.run(["git", "check-ignore", "-q", str(L.SALT_FILE)], cwd=REPO)
    assert r.returncode == 0


def test_derivable_scan_finds_a_private_handle_in_builder_code_and_a_positional_id(tmp_path):
    rows = [_row(1, "test", "ok", "public", source_id="pub-0001", group="grp-public"),
            _row(2, "private", "ok", "private", source_id="9366a8d8-5c4e-412f-826f-924df3d2b307", group="grp-secret-0002")]
    _write(tmp_path / "e2" / "prompt_attacks" / "candidates.jsonl", rows)
    L.split(["prompt_attacks"], root=tmp_path / "e2", pol=POL)
    repo = _git_repo(tmp_path, {
        "dataset/goldrails_dataset/sources/e2_x.py": "CASES = [('9366a8d8-5c4e-412f-826f-924df3d2b307', 'train')]\n",
        "notes.md": "the group grp-secret-0002 was held out\n", "ok.md": "pub-0001 grp-public\n"})
    rep = L.derivable_private_ids(tmp_path / "e2", repo, build_private=tmp_path / "nowhere")
    assert rep["selection_entries"] == [{"file": "dataset/goldrails_dataset/sources/e2_x.py", "n": 1}]
    assert rep["handles_elsewhere"] == [{"file": "notes.md", "n": 1}]
    assert "9366a8d8" not in json.dumps(rep)


def _owner_data():
    if not all((L.private_dir(s) / "candidates.jsonl").exists() for s in L.SUITES) or not L.BUILD_PRIVATE.exists():
        pytest.skip("the private slice is owner-only and not on this machine")
    try:
        L.private_salt()
    except L.LocalDataMissing as e:
        pytest.skip(str(e))


def test_tracked_files_alone_do_not_give_the_private_slice():
    """From the tracked files, without the salt or any git-ignored file: no selection list or override names a
    private-slice row, no long handle of one (source id, group) sits in any tracked file, and no held-out authored
    case's id follows from its position in a tracked case list."""
    _owner_data()
    rep = L.derivable_private_ids()
    assert rep["private_ids"] > 1000
    assert rep["selection_entries"] == [], rep["selection_entries"]
    assert rep["handles_elsewhere"] == [], rep["handles_elsewhere"]
    assert rep["positional_ids"] == 0


def test_tracked_selection_lists_hold_public_rows_and_the_private_config_private_ones():
    _owner_data()
    from goldrails_dataset.sources import e2_content as C, e2_denied_topics as E, e2_denied_topics_oasst as O
    import ast
    cfg = L.private_config("denied_topics")
    priv = {c["source_id"] for c in L.candidates("denied_topics", text=False) if c["proposed_split"] == "private"}
    tree = ast.parse((REPO / "dataset/goldrails_dataset/sources/e2_denied_topics_oasst.py").read_text())
    tracked = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert O.PRIVATE and O.PRIVATE <= priv and not O.PRIVATE & tracked
    assert {c[0] for c in cfg["e2_denied_topics_oasst.CASES"]} == {c for c in priv if c in {x[0] for x in O.CASES}}
    for name in ("e2_denied_topics.ALSO_IN", "e2_denied_topics.AMBIGUOUS"):
        assert set(cfg[name]) <= priv, name
    hb = L.private_config("content")["e2_content.HARMBENCH_OVERRIDE"]
    assert set(hb) <= set(C.HARMBENCH_OVERRIDE)
    assert set(E.AMBIGUOUS) >= set(cfg["e2_denied_topics.AMBIGUOUS"])


def test_builders_give_the_committed_split_of_authored_and_listed_rows():
    """The authored rows and the OASST2 prompts come out of their builders with the ids and splits on record: held-out
    cases private under their salted ids, the rest in the dev or test split they had."""
    _owner_data()
    from goldrails_dataset.sources import e2_denied_topics as E, e2_pii_controls as PC
    from goldrails_dataset.sources import e2_prompt_attacks_controls as PA
    for suite, built in (("pii", [(c["id"], c["proposed_split"]) for c in PC.candidates()]),
                         ("denied_topics", [(r.id, r.attribute["proposed_split"]) for r in E.load()])):
        cands = {c["id"]: c["proposed_split"] for c in L.candidates(suite, text=False)}
        assert {i: s for i, s in built if i in cands} == {i: cands[i] for i, _ in built if i in cands}, suite
        assert sum(i in cands for i, _ in built) >= 0.9 * len(built), suite
    oasst = [c for c in L.candidates("denied_topics") if c["source"] == "e2_oasst2"]
    fetched = {c["source_id"]: {"text": c["text"], "message_tree_id": c["group"].removeprefix("e2_oasst2-"),
                                "upstream_split": c["upstream_split"]} for c in oasst}
    assert {r.id: r.attribute["proposed_split"] for r in E.load_oasst(fetched)} == \
        {c["id"]: c["proposed_split"] for c in oasst}
    cands = {c["id"] for c in L.candidates("prompt_attacks", text=False)}
    held = [r.id for r in PA.load() if PA.is_held_out(r.provenance.source_id)]
    assert held and {i for i in held if i in cands} <= {c["id"] for c in L._jsonl(L.private_dir("prompt_attacks") / "candidates.jsonl")}


def test_the_slice_on_record_was_drawn_with_this_salt():
    _owner_data()
    for s in ("prompt_attacks", "denied_topics", "pii", "grounding"):
        rec = json.loads((L.private_dir(s) / L.REDRAW_RECORD).read_text())
        assert rec["salt_fingerprint"] == L.salt_fingerprint(), s
