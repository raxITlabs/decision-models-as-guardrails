"""Edition 2 data that never goes into git: the private slice, owner-only files and licence-restricted text.

The repository is public. Each suite folder ``dataset/edition2/<suite>/`` holds three kinds of file:

- tracked: public rows only (proposed split dev or test) in ``candidates.jsonl``, ``relabel.jsonl`` and the
  other row files. A row whose source's text is not cleared in ``dataset/release/redistribution.json`` (mode
  ``text`` and ``reviewed: true``) keeps its id, labels, spans and group, but its text fields (``STRIP``) are null and
  ``redacted`` records why and the sha256 of the removed fields.
- ``private/`` (git-ignored, owner only): the private-slice rows and every file that names them or carries row text
  in bulk: their second labels, the review packets, the ``_lead`` answer keys, the full disagreement notes,
  ``order.txt`` (the full row order, so the original files can be rebuilt). A public row whose normalised text is
  also a private-slice row's text lives here too, so no tracked file carries a private-slice text.
- ``local/text.jsonl`` (git-ignored): the removed text fields of the redacted public rows. ``rehydrate`` rebuilds it
  from the pinned upstream loaders (network), checking every row against its recorded sha256.

Readers (the edition 2 build, the PII loaders, the tests) use ``candidates()`` and ``relabels()``, which put the
three parts back together. They raise ``LocalDataMissing`` when a part is not on this machine.

Private-slice membership cannot be derived from tracked files. Three things keep it that way:

- the salt: ``dataset/edition2/.private-salt`` (git-ignored, owner only; ``salt --init`` writes it once). Every split
  draw that can put a row in the private slice, and every selection order that decides which rows a builder takes,
  is keyed with it (``salted``, ``salted_random``), so the published seeds and hashes do not give the slice.
- private config: a selection list or override entry keyed to a private-slice row (an upstream message id, a
  behaviour id, an authored case's key) sits in ``<suite>/private/selection.json``, not in the tracked builder code;
  ``private_part`` merges it back in. Tracked code holds public-row selections only.
- held-out authored ids: an authored case in the private slice gets a salted source id (``held_out_sid``), so its id
  does not follow from its position in the tracked case list.

``derivable_private_ids`` checks all three from the tracked files alone.

    uv run python -m goldrails_dataset.e2_local status
    uv run python -m goldrails_dataset.e2_local split [suite ...]      # after a builder rewrote a suite's files
    uv run python -m goldrails_dataset.e2_local rehydrate [suite ...]  # refill local/text.jsonl (network)
    uv run python -m goldrails_dataset.e2_local salt [--init]          # is the salt here (fingerprint only)
    uv run python -m goldrails_dataset.e2_local redraw [--apply] [suite ...]   # salted re-draw of the private slice
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[1]
E2 = DATASET_DIR / "edition2"
POLICY = DATASET_DIR / "release" / "redistribution.json"
SUITES = ("content", "prompt_attacks", "denied_topics", "pii", "grounding", "word_filters")
STRIP = ("text", "context", "source", "query", "tool_call")      # same fields release.STRIP removes
STYLE = {"prompt_attacks": {"ensure_ascii": True, "sort_keys": True}}   # how each suite's builder serialises rows
DEFAULT_STYLE = {"ensure_ascii": False, "sort_keys": True}

# Row files split by id: the row goes where its candidate lives.
# resolutions.jsonl: the owner-ruling resolution of each disputed row (docs/benchmark/29-owner-rulings-2026-10-03.md).
ROW_FILES = {"content": ("relabel.jsonl", "resolutions.jsonl"),
             "prompt_attacks": ("relabel.jsonl", "relabel-round2.jsonl", "relabel-round3.jsonl", "relabel-round5.jsonl",
                                "relabel-round6.jsonl", "resolutions.jsonl"),
             "denied_topics": ("relabel.jsonl", "resolutions.jsonl"),
             "pii": ("relabel.jsonl", "resolutions.jsonl", "corrections.jsonl"),
             "grounding": ("relabel.jsonl", "relabel-round3.jsonl", "first_labels.jsonl", "resolutions.jsonl"),
             "word_filters": ("relabel.jsonl", "relabel-round5.jsonl", "relabel-round6.jsonl", "resolutions.jsonl")}
# Second-label rounds in order. The number is in the name (round 4 was an owner review, not a labelling round), so a
# round keeps its own number whatever files a suite has.
RELABEL_ROUNDS = ("relabel.jsonl", "relabel-round2.jsonl", "relabel-round3.jsonl", "relabel-round5.jsonl",
                  "relabel-round6.jsonl")


def round_number(name: str) -> int:
    """1 for ``relabel.jsonl``, n for ``relabel-round<n>.jsonl``."""
    m = re.fullmatch(r"relabel(?:-round(\d+))?\.jsonl", name)
    if not m:
        raise ValueError(f"not a second-label file: {name}")
    return int(m.group(1) or 1)
# Files and folders that carry every row's text, private ids or answer keys: moved whole into private/.
MOVE = {
    "content": {"review-packet/01-rows.md": "review-packet-dev-test/01-rows.md",
                "review-packet/labels.template.jsonl": "review-packet-dev-test/labels.template.jsonl"},
    "prompt_attacks": {"packet/rows.jsonl": "packet/rows.jsonl",
                       "packet/labels.template.jsonl": "packet/labels.template.jsonl",
                       "label-disputes.jsonl": "label-disputes.jsonl"},
    "denied_topics": {"review-packet/packet.md": "review-packet/packet.md",
                      "review-packet/labels.template.jsonl": "review-packet/labels.template.jsonl",
                      "_lead": "_lead"},
    "pii": {"packet/packet.md": "packet/packet.md", "packet/labels.template.jsonl": "packet/labels.template.jsonl",
            "packet/_lead": "packet/_lead"},
    "grounding": {"packet/packet.md": "packet/packet.md", "packet/labels.template.jsonl": "packet/labels.template.jsonl",
                  "packet/_lead": "packet/_lead"},
    "word_filters": {},             # its builder writes the labelling packet straight into private/packet/
}


class LocalDataMissing(FileNotFoundError):
    """A git-ignored part of edition 2 (private slice or licence cache) is not on this machine."""


def suite_dir(suite: str, root: Path = E2) -> Path:
    return Path(root) / suite


def private_dir(suite: str, root: Path = E2) -> Path:
    return suite_dir(suite, root) / "private"


def text_cache(suite: str, root: Path = E2) -> Path:
    return suite_dir(suite, root) / "local" / "text.jsonl"


# --- licence ---------------------------------------------------------------------------------------------------------

def policy(path: Path = POLICY) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def text_cleared(source: str, pol: dict) -> bool:
    """True only for a source listed with mode text and reviewed true. Missing, ids_only or unreviewed: False."""
    e = pol["sources"].get(source)
    return bool(e and e.get("mode") == "text" and e.get("reviewed") is True)


def source_of(c: dict) -> str:
    return c.get("source") or (c.get("provenance") or {}).get("source") or \
        ((c.get("record") or {}).get("provenance") or {}).get("source")


def _states(c: dict) -> list:
    """The state dicts of a candidate row: ``state`` and, for denied topics, ``record.state``."""
    out = [c["state"]] if isinstance(c.get("state"), dict) else []
    if isinstance(c.get("record"), dict) and isinstance(c["record"].get("state"), dict):
        out.append(c["record"]["state"])
    return out


def _fields(c: dict) -> list:
    return [{k: s[k] for k in STRIP if k in s} for s in _states(c)]


def fields_sha256(fields: list) -> str:
    return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


QUOTE_WINDOW = 50       # a field quoting this many characters of a withheld text is withheld with it


def _quote_windows(texts) -> tuple[set, set]:
    """(50-character windows, whole short texts) of whitespace-normalised texts, to spot a field that quotes one."""
    wins, short = set(), set()
    for t in texts:
        n = re.sub(r"\s+", " ", t or "").strip()
        if not n:
            continue
        if len(n) < QUOTE_WINDOW:
            short.add(n)
        else:
            wins |= {n[i:i + QUOTE_WINDOW] for i in range(0, len(n) - QUOTE_WINDOW + 1, QUOTE_WINDOW // 2)}
            wins.add(n[-QUOTE_WINDOW:])
    return wins, short


def _quotes(value: str, wins: set, short: set) -> bool:
    n = re.sub(r"\s+", " ", value).strip()
    if n in short or any(len(t) >= 16 and t in n for t in short):
        return True
    return any(n[i:i + QUOTE_WINDOW] in wins for i in range(0, len(n) - QUOTE_WINDOW + 1))


def _quoting_paths(c: dict, texts: list, also: tuple = ((), ())) -> list:
    """Paths (lists of keys and indices) of string fields outside the states that quote one of ``texts`` (or the
    precomputed windows ``also``): a copy of the text, a quoted sentence in a rationale, upstream metadata that carries
    spans of it or of a sibling row."""
    wins, short = _quote_windows(texts)
    wins, short = wins | set(also[0]), short | set(also[1])
    skip = {id(s) for s in _states(c)}
    out = []

    def walk(x, path):
        if id(x) in skip:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                if path == [] and k in ("id", "redacted"):
                    continue
                walk(v, path + [k])
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, path + [i])
        elif isinstance(x, str) and _quotes(x, wins, short):
            out.append(path)
    walk(c, [])
    return out


def _get(d, path):
    for k in path:
        d = d[k]
    return d


def _set(d, path, value):
    for k in path[:-1]:
        d = d[k]
    d[path[-1]] = value


def redact(c: dict, why: str, also: tuple = ((), ())) -> tuple[dict, dict]:
    """(tracked copy without text, cache entry). The tracked copy keeps every other field and the key order. Besides
    the state's text fields, any other field that quotes the text, or another withheld text (``also``: windows from
    _quote_windows), is withheld too (``extra``)."""
    fields = _fields(c)
    extra = [[p, _get(c, p)] for p in _quoting_paths(c, _field_texts(*fields), also)]
    d = json.loads(json.dumps(c))
    for s in _states(d):
        for k in STRIP:
            if k in s:
                s[k] = None
    for p, _ in extra:
        _set(d, p, None)
    d["redacted"] = {"why": why, "fields_sha256": fields_sha256(fields),
                     "restore": "uv run python -m goldrails_dataset.e2_local rehydrate"}
    if extra:
        d["redacted"]["also_withheld"] = [p for p, _ in extra]
        d["redacted"]["also_withheld_sha256"] = fields_sha256([v for _, v in extra])
    entry = {"id": c["id"], "source": source_of(c), "fields": fields}
    if extra:
        entry["extra"] = extra
    return d, entry


def restore(d: dict, entry: dict) -> dict:
    red = d["redacted"]
    if fields_sha256(entry["fields"]) != red["fields_sha256"]:
        raise ValueError(f"{d['id']}: cached text does not match the recorded sha256")
    extra = entry.get("extra", [])
    if [p for p, _ in extra] != red.get("also_withheld", []) or \
            (extra and fields_sha256([v for _, v in extra]) != red["also_withheld_sha256"]):
        raise ValueError(f"{d['id']}: cached withheld fields do not match the recorded sha256")
    out = json.loads(json.dumps(d))
    del out["redacted"]
    for st, f in zip(_states(out), entry["fields"]):
        st.update(f)
    for p, v in extra:
        _set(out, p, v)
    return out


# --- authored cases in the private slice ------------------------------------------------------------------------------

class HeldOut:
    """Stands in an authored case list for a case whose row is in the private slice. The case itself (text and
    rationale) is in ``private/authored.json`` under ``key``; ``authored()`` puts it back. The placeholder keeps the
    list positions, so ids built from a case's index do not move."""

    def __init__(self, key: str):
        self.key = key

    def __repr__(self) -> str:
        return f"HeldOut({self.key!r})"


def authored(suite: str, cases, root: Path = E2) -> list:
    """``cases`` with every HeldOut replaced by its stored tuple. Raises LocalDataMissing without the private file."""
    cases = list(cases)
    if not any(isinstance(c, HeldOut) for c in cases):
        return cases
    p = private_dir(suite, root) / "authored.json"
    if not p.exists():
        raise LocalDataMissing(f"{p} is not on this machine: held-out authored cases are owner-only")
    store = json.loads(p.read_text(encoding="utf-8"))
    return [tuple(store[c.key]) if isinstance(c, HeldOut) else c for c in cases]


# Where the row text sits in a held-out case tuple, by the key's case list (``<module>:<LIST>``).
HELD_OUT_TEXT_AT = {
    "e2_prompt_attacks_controls:CASES": 2,          # (subtask, kind, text, rationale)
    "e2_prompt_attacks_controls_v2:CASES_V2": 4,    # (subtask, label, kind, pair, text, rationale)
    "e2_pii_controls:NEGATIVES": 1,                 # (tempted type, text, rationale)
    "e2_pii_controls:DRIVER_POSITIVES": 0,          # (text, values, rationale)
}
HELD_OUT_TEXT_DEFAULT = 2                           # denied topics: (pair, kind, text, rationale)


def authored_keys(cases) -> dict:
    """{list position: HeldOut key} of an authored case list: which positions hold a private-slice case."""
    return {i: c.key for i, c in enumerate(cases) if isinstance(c, HeldOut)}


def held_out_sid(*parts, salt: str | None = None) -> str:
    """The salted token that stands in a held-out authored case's source id, in place of its list position (or pair
    number). ``parts`` name the case (its HeldOut key, or a pair). Raises LocalDataMissing without the salt."""
    return "h" + salted("held-out", *parts, salt=salt)[:12]


# --- the private salt ------------------------------------------------------------------------------------------------

SALT_FILE = E2 / ".private-salt"
_SALT = re.compile(r"[0-9a-f]{64}")


def private_salt(path: Path | None = None) -> str:
    """The owner's secret salt (64 hex characters). Raises LocalDataMissing when the file is not on this machine.
    ``GOLDRAILS_E2_SALT_FILE`` points at another file (a test, or the owner's backup)."""
    p = Path(path or os.environ.get("GOLDRAILS_E2_SALT_FILE") or SALT_FILE)
    if not p.exists():
        raise LocalDataMissing(f"{p} is not on this machine: the private-slice salt is git-ignored and owner only "
                               "(restore it from the owner's backup; a new salt would draw a different slice)")
    s = p.read_text(encoding="utf-8").strip()
    if not _SALT.fullmatch(s):
        raise ValueError(f"{p}: expected 64 lowercase hex characters")
    return s


def init_salt(path: Path | None = None) -> bool:
    """Write a new salt (secrets.token_hex(32), mode 600) when none exists. Never overwrites. True when written."""
    p = Path(path or SALT_FILE)
    if p.exists():
        private_salt(p)
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(secrets.token_hex(32) + "\n")
    return True


def salt_fingerprint(salt: str | None = None) -> str:
    """A short fingerprint that says which salt drew a slice without giving it away (safe to print)."""
    return hashlib.sha256(("fingerprint:" + (salt or private_salt())).encode()).hexdigest()[:12]


def salted(*parts, salt: str | None = None) -> str:
    """HMAC-SHA256 (hex) of ``parts`` under the private salt: an order or a split that nobody without the salt can
    recompute from the published code, seeds and upstream data."""
    key = (salt or private_salt()).encode("utf-8")
    return hmac.new(key, ":".join(str(p) for p in parts).encode("utf-8"), hashlib.sha256).hexdigest()


def salted_random(*parts, salt: str | None = None) -> random.Random:
    """A random.Random seeded from ``salted(parts)``."""
    return random.Random(salted(*parts, salt=salt))


def salted_unit(*parts, salt: str | None = None) -> float:
    """A number in [0, 1) from ``salted(parts)``: a salted split by threshold."""
    return int(salted(*parts, salt=salt)[:13], 16) / float(1 << 52)


# --- private config: selection lists and overrides keyed to private-slice rows ----------------------------------------

SELECTION = "selection.json"


def private_config(suite: str, root: Path = E2) -> dict | None:
    """``<suite>/private/selection.json``: {"<module>.<NAME>": value} for the entries of tracked selection lists and
    overrides that name private-slice rows. None when not on this machine."""
    p = private_dir(suite, root) / SELECTION
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def private_part(suite: str, name: str, default, root: Path = E2):
    """The private entries of a tracked list or dict called ``name`` (``<module>.<NAME>``), or ``default`` when this
    machine has no private config. A module merges them in at import, so the owner sees the whole list; a builder
    that writes files calls ``require_private_config`` first, so it never builds from the public half alone."""
    cfg = private_config(suite, root)
    return default if cfg is None else cfg.get(name, default)


def require_private_config(suite: str, root: Path = E2) -> dict:
    cfg = private_config(suite, root)
    if cfg is None:
        raise LocalDataMissing(f"{private_dir(suite, root) / SELECTION} is not on this machine: selection entries "
                               "keyed to private-slice rows are git-ignored and owner only")
    return cfg


def write_private_config(suite: str, cfg: dict, root: Path = E2) -> None:
    p = private_dir(suite, root) / SELECTION
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(sorted(cfg.items())), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def held_out_texts(root: Path = E2) -> dict:
    """{key: row text} of every held-out authored case on this machine (each suite's ``private/authored.json``)."""
    out = {}
    for s in SUITES:
        p = private_dir(s, root) / "authored.json"
        if not p.exists():
            continue
        for key, case in json.loads(p.read_text(encoding="utf-8")).items():
            at = HELD_OUT_TEXT_AT.get(key.rsplit(":", 1)[0], HELD_OUT_TEXT_DEFAULT)
            if not isinstance(case[at], str):
                raise ValueError(f"{key}: held-out case has no text at position {at}")
            out[key] = case[at]
    return out


# --- reading ---------------------------------------------------------------------------------------------------------

def _jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def _cache(suite: str, root: Path) -> dict:
    return {e["id"]: e for e in _jsonl(text_cache(suite, root))}


def have_local(suite: str, root: Path = E2) -> bool:
    """True when this machine holds the private slice and every redacted row's text for the suite."""
    sd = suite_dir(suite, root)
    if not (sd / "candidates.jsonl").exists() or not (private_dir(suite, root) / "candidates.jsonl").exists():
        return False
    cache = _cache(suite, root)
    return all(c["id"] in cache for c in _jsonl(sd / "candidates.jsonl") if "redacted" in c)


def _ordered(suite: str, rows: list, root: Path) -> list:
    order = private_dir(suite, root) / "order.txt"
    if not order.exists():
        return rows
    pos = {i: n for n, i in enumerate(order.read_text(encoding="utf-8").split())}
    return sorted(rows, key=lambda c: pos.get(c["id"], len(pos)))


def candidates(suite: str, root: Path = E2, private: bool = True, text: bool = True) -> list:
    """Every candidate row of a suite in its original order, private slice included and redacted text restored.
    ``private=False`` leaves the private file out; ``text=False`` leaves redacted rows redacted."""
    rows = _jsonl(suite_dir(suite, root) / "candidates.jsonl")
    if private:
        p = private_dir(suite, root) / "candidates.jsonl"
        if not p.exists():
            raise LocalDataMissing(f"{p} is not on this machine: the private slice is git-ignored and owner-only")
        rows += _jsonl(p)
    if text and any("redacted" in c for c in rows):
        cache = _cache(suite, root)
        missing = [c["id"] for c in rows if "redacted" in c and c["id"] not in cache]
        if missing:
            raise LocalDataMissing(f"{suite}: {len(missing)} redacted rows have no text in {text_cache(suite, root)}; "
                                   f"run: uv run python -m goldrails_dataset.e2_local rehydrate {suite}")
        rows = [restore(c, cache[c["id"]]) if "redacted" in c else c for c in rows]
    return _ordered(suite, rows, root)


def row_file(suite: str, name: str, root: Path = E2, private: bool = True) -> list:
    """A per-row file (relabel.jsonl, first_labels.jsonl): the tracked part plus the private part."""
    rows = _jsonl(suite_dir(suite, root) / name)
    if private:
        if not (private_dir(suite, root) / "candidates.jsonl").exists():
            raise LocalDataMissing(f"{private_dir(suite, root)} is not on this machine: the private slice is git-ignored")
        rows += _jsonl(private_dir(suite, root) / name)
    return _ordered(suite, rows, root)


def relabel_rounds(suite: str, root: Path = E2, private: bool = True) -> list:
    """[(round number, rows)] of a suite's blind second labels: round 1 (``relabel.jsonl``) and each later round
    (``relabel-round2.jsonl``, ``relabel-round3.jsonl``, ``relabel-round5.jsonl``: rows added after the earlier
    rounds), tracked and private parts together. A round with no file on this machine is left out."""
    out = []
    for name in RELABEL_ROUNDS:
        n = round_number(name)
        if n == 1 or (suite_dir(suite, root) / name).exists() or (private_dir(suite, root) / name).exists():
            out.append((n, row_file(suite, name, root, private)))
    return out


def relabels(suite: str, root: Path = E2, private: bool = True) -> list:
    """Every blind second label of a suite, every round (``relabel_rounds``) in one list."""
    return [r for _, rows in relabel_rounds(suite, root, private) for r in rows]


def full_text(suite: str, root: Path = E2) -> str:
    """The suite's candidates.jsonl as its builder wrote it (private rows and text included)."""
    st = STYLE.get(suite, DEFAULT_STYLE)
    return "".join(json.dumps(c, **st) + "\n" for c in candidates(suite, root))


def packet_dir(suite: str, root: Path = E2) -> Path:
    """Where a suite's moved review packet lives (private/)."""
    return private_dir(suite, root) / {"content": "review-packet-dev-test", "denied_topics": "review-packet"}.get(suite, "packet")


# --- splitting -------------------------------------------------------------------------------------------------------

def _norm(text) -> str:
    from .audit import normalise
    return normalise(text or "")


def _texts(c: dict) -> set:
    return {_norm(s.get("text")) for s in _states(c) if s.get("text")}


def _field_texts(*fields) -> list:
    """Every string a row's text fields hold: text, source passage, query and each context turn."""
    out = []
    for f in fields:
        out += [f[k] for k in ("text", "source", "query") if isinstance(f.get(k), str)]
        out += [t.get("text") if isinstance(t, dict) else t for t in (f.get("context") or [])
                if isinstance(t, str) or (isinstance(t, dict) and isinstance(t.get("text"), str))]
    return out


def _write_lines(path: Path, lines: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(l + "\n" for l in lines), encoding="utf-8")


def _raw_rows(path: Path) -> list:
    if not path.exists():
        return []
    return [(l, json.loads(l)) for l in path.read_text(encoding="utf-8").split("\n") if l.strip()]


def split(suites=SUITES, root: Path = E2, pol: dict | None = None) -> dict:
    """Bring each suite's folder to the layout above. Idempotent. A builder that rewrote ``candidates.jsonl`` with
    every row (and text) in it, or wrote packets and answer keys into the suite folder, is split again: private
    rows and owner files into private/, restricted text into local/text.jsonl. Returns counts per suite."""
    pol = pol or policy()
    root = Path(root)
    # every suite's rows, so a public row that repeats a private-slice text in another suite is caught too
    full = {}
    for s in SUITES:
        sd = suite_dir(s, root)
        if not (sd / "candidates.jsonl").exists():
            continue
        pub = _raw_rows(sd / "candidates.jsonl")
        prv = _raw_rows(private_dir(s, root) / "candidates.jsonl")
        if any(c["proposed_split"] == "private" for _, c in pub):
            prv = []                                 # a builder rewrote the whole file: the old private part is stale
        seen = {c["id"] for _, c in pub}
        full[s] = (pub, [(l, c) for l, c in prv if c["id"] not in seen])
    private_texts = set()
    for s, (pub, prv) in full.items():
        for _, c in pub + prv:
            if c["proposed_split"] == "private":
                private_texts |= _texts(c)
    report = {}
    private_ids = {c["id"] for s in full for _, c in full[s][0] + full[s][1] if c["proposed_split"] == "private"}
    for s in suites:
        if s not in full:
            continue
        sd, pd = suite_dir(s, root), private_dir(s, root)
        st = STYLE.get(s, DEFAULT_STYLE)
        pub, prv = full[s]
        cache = _cache(s, root)
        order_file = pd / "order.txt"
        old_order = order_file.read_text(encoding="utf-8").split() if order_file.exists() else []
        keep_pub, keep_prv, n_red = [], [], 0
        # every text this suite withholds (private rows, uncleared sources): a withheld row's other fields that quote
        # any of them (say upstream notes carrying a sibling summary) are withheld too
        also = _quote_windows([t for _, c in pub + prv if "redacted" not in c and (
            c["proposed_split"] == "private" or not text_cleared(source_of(c), pol)) for t in _field_texts(*_fields(c))])
        for line, c in pub + prv:
            if "redacted" in c:                      # already split
                keep_pub.append(line)
                continue
            if c["proposed_split"] == "private" or _texts(c) & private_texts:
                keep_prv.append((line, c))
                continue
            src = source_of(c)
            if text_cleared(src, pol):
                keep_pub.append(line)
            else:
                d, entry = redact(c, f"licence: text of source {src} is not cleared in dataset/release/redistribution.json",
                                  also)
                cache[c["id"]] = entry
                keep_pub.append(json.dumps(d, **st))
                n_red += 1
        ids_prv = {c["id"] for _, c in keep_prv}
        # full order: the order the rows arrived in, unless already recorded
        arrived = [c["id"] for _, c in pub + prv]
        order = old_order if set(old_order) == set(arrived) else arrived
        _write_lines(sd / "candidates.jsonl", keep_pub)
        _write_lines(pd / "candidates.jsonl", [l for l, _ in keep_prv])
        _write_lines(order_file, order)
        live = {json.loads(l)["id"] for l in keep_pub}
        cache_lines = [json.dumps(cache[i], ensure_ascii=False, sort_keys=True) for i in order if i in cache and i in live]
        _write_lines(text_cache(s, root), cache_lines)
        for name in ROW_FILES.get(s, ()):
            rows, seen = [], set()
            for l, r in _raw_rows(sd / name) + _raw_rows(pd / name):
                if r["id"] not in seen:                  # a rewritten tracked file wins over a stale private part
                    seen.add(r["id"])
                    rows.append((l, r))
            if not rows:
                continue
            _write_lines(sd / name, [l for l, r in rows if r["id"] not in ids_prv])
            _write_lines(pd / name, [l for l, r in rows if r["id"] in ids_prv])
        moved = []
        for src_rel, dst_rel in MOVE.get(s, {}).items():
            src, dst = sd / src_rel, pd / dst_rel
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
                shutil.move(str(src), str(dst))
                moved.append(src_rel)
        report[s] = {"public": len(keep_pub), "private_file": len(keep_prv), "redacted_now": n_red,
                     "redacted_total": sum(1 for l in keep_pub if '"redacted"' in l), "moved": moved}
    # notes last, against every suite's private and withheld rows (a note can quote another suite's row)
    withheld, texts = set(private_ids), []
    for s in full:
        withheld |= {c["id"] for c in _jsonl(private_dir(s, root) / "candidates.jsonl")}
        for e in _jsonl(text_cache(s, root)):
            withheld.add(e["id"])
            texts += [t for f in e["fields"] for t in _field_texts(f)]
        texts += [t for c in _jsonl(private_dir(s, root) / "candidates.jsonl") for t in _field_texts(*_fields(c))]
    for s in suites:
        if s in report:
            report[s]["notes"] = publish_notes(s, private_ids, withheld, texts, root)
    return report


def purge(ids: set, suites=SUITES, root: Path = E2) -> dict:
    """Take rows out of every per-suite file: candidates, the per-row files (second labels, resolutions,
    corrections), order.txt and the text cache, tracked and private parts alike. For rows an owner exclusion
    (EXCLUDED.jsonl) has taken out of edition 2, so no candidate or label file still names them. Returns lines removed
    per suite."""
    out = {}
    for s in suites:
        n = 0
        for d in (suite_dir(s, root), private_dir(s, root)):
            for name in ("candidates.jsonl",) + tuple(ROW_FILES.get(s, ())):
                p = d / name
                if not p.exists():
                    continue
                lines = [l for l in p.read_text(encoding="utf-8").split("\n") if l.strip()]
                keep = [l for l in lines if json.loads(l)["id"] not in ids]
                if len(keep) != len(lines):
                    _write_lines(p, keep)
                    n += len(lines) - len(keep)
        order = private_dir(s, root) / "order.txt"
        if order.exists():
            o = order.read_text(encoding="utf-8").split()
            if set(o) & ids:
                _write_lines(order, [i for i in o if i not in ids])
        cache = text_cache(s, root)
        if cache.exists():
            lines = [l for l in cache.read_text(encoding="utf-8").split("\n") if l.strip()]
            keep = [l for l in lines if json.loads(l)["id"] not in ids]
            if len(keep) != len(lines):
                _write_lines(cache, keep)
        if n:
            out[s] = n
    return out


# --- notes ----------------------------------------------------------------------------------------------------------

NOTES = ("DISAGREEMENTS.md",)
ID_RE = re.compile(r"\bf\d-[A-Za-z0-9_]+-[0-9a-f]{10}\b")
LABEL_COLUMNS = {"id", "subtask", "source", "first", "second", "mine", "agree", "first only", "mine only",
                 "first label", "second label", "label", "split", "proposed split", "#"}
KEEP_BULLETS = ("- subtask / source:", "- owner decision:")
LABEL_BULLET = re.compile(r"^(\s*- (?:first|mine|second|first label|second label): \*\*[^*]+\*\*(?: \[[^\]]*\])?)", re.I)
PUBLIC_NOTE = ("> Public copy. Rows of the private slice are left out. For rows whose source licence is not cleared "
               "(`dataset/release/redistribution.json`), only the id, source and labels are shown. The full notes are "
               "in `private/DISAGREEMENTS.md` (git-ignored, owner only).")
W = 50


def _mdnorm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("`", " ").replace("\\|", "|")).strip()


class _TextIndex:
    """Finds a line that quotes any of a set of texts, whole (short texts) or by a 50-character window."""

    def __init__(self, texts):
        self.windows, self.short = set(), set()
        for t in texts:
            n = _mdnorm(t)
            if len(n) < 16:
                continue
            if len(n) < W:
                self.short.add(n)
                continue
            for i in list(range(0, len(n) - W + 1, W // 2)) + [len(n) - W]:
                w = n[i:i + W]
                if sum(ch.isalpha() for ch in w) >= 30 and len(set(w.lower())) >= 12:
                    self.windows.add(w)

    def hit(self, line: str) -> bool:
        n = _mdnorm(line)
        if any(n[i:i + W] in self.windows for i in range(0, max(0, len(n) - W + 1))):
            return True
        return any(t in n for t in self.short)


def public_notes(md: str, private_ids: set, withheld_ids: set, index: _TextIndex) -> str:
    """A public copy of a markdown note: sections, table rows and lines naming a private-slice row go; for a
    withheld row (licence not cleared) only the id, source and labels stay; any other line quoting withheld text
    goes."""
    out, header, skip, cur, dropped = [], None, None, False, False
    for line in md.split("\n"):
        if dropped and line.startswith((" ", "\t")) and not line.lstrip().startswith("- "):
            continue                              # continuation of a dropped list item
        dropped = False
        h = re.match(r"^(#+)\s", line)
        ids = set(ID_RE.findall(line))
        if h:
            level = len(h.group(1))
            if skip is not None and level > skip:
                continue
            skip, header = None, None
            if ids & private_ids:
                skip = level
                continue
            cur = bool(ids & withheld_ids)
            out.append(line)
            continue
        if skip is not None:
            continue
        if line.startswith("|"):
            cells = re.split(r"(?<!\\)\|", line)[1:-1]
            if all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in cells):
                out.append(line)
                continue
            if header is None and not ids:
                header = [c.strip().lower() for c in cells]
                out.append(line)
                continue
            if ids & private_ids:
                continue
            if ids & withheld_ids or index.hit(line):
                cells = [c if header and j < len(header) and header[j] in LABEL_COLUMNS and not index.hit(c)
                         else " _withheld_ " for j, c in enumerate(cells)]
                line = "|" + "|".join(cells) + "|"
            out.append(line)
            continue
        header = None
        if ids & private_ids:
            dropped = True
            continue
        low = line.strip().lower()
        if cur and low.startswith("- ") and not low.startswith(KEEP_BULLETS):
            m = LABEL_BULLET.match(line)
            line = m.group(1) if m else re.sub(r"^(\s*- [^:]{1,40}:).*$", r"\1 _withheld_", line)
        if index.hit(line):
            if low.startswith("- "):
                line = re.sub(r"^(\s*- [^:]{1,40}:).*$", r"\1 _withheld_", line)
                if index.hit(line):
                    dropped = True
                    continue
            else:
                dropped = True
                continue
        out.append(line)
    if out == md.split("\n"):
        return md
    if PUBLIC_NOTE not in out:
        at = 1 if out and out[0].startswith("# ") else 0
        out[at:at] = ["", PUBLIC_NOTE]
    return "\n".join(out)


def publish_notes(suite: str, private_ids: set, withheld_ids: set, texts, root: Path = E2) -> list:
    """For each note that names private rows or quotes withheld text: the full file goes to private/, a public copy
    stays. Returns the notes rewritten."""
    index = _TextIndex(texts)
    done = []
    for name in NOTES:
        p = suite_dir(suite, root) / name
        if not p.exists():
            continue
        md = p.read_text(encoding="utf-8")
        pub = public_notes(md, private_ids, withheld_ids, index)
        if pub == md:
            continue
        if PUBLIC_NOTE not in md:                 # an original, not an earlier public copy
            dst = private_dir(suite, root) / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(md, encoding="utf-8")
        p.write_text(pub, encoding="utf-8")
        done.append(name)
    return done


# --- leak scan over the tracked files ----------------------------------------------------------------------------------

REPO = DATASET_DIR.parent
BUILD_PRIVATE = E2 / "build" / "private"
PROBE_WORDS = 6         # a text is looked for by a run of this many of its words
SHORT_NEEDLE = 40       # a text under this many characters must match a whole string value, not a substring
BOILERPLATE_ROWS = 25   # a field value shared by this many rows (a fixed grounding query) names no row
_WORD = re.compile(rb"[a-z0-9]+")
_ESCAPE = re.compile(rb"\\(?:u[0-9a-fA-F]{4}|.)")     # JSON and Python escapes (\n, \", \u00e9) read as a space
_ID = re.compile(rb"\bf\d-[A-Za-z0-9_]+-[0-9a-f]{10}\b")


def _nws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _words(b: bytes) -> list:
    return _WORD.findall(_ESCAPE.sub(b" ", b.lower()))


def _probe(text: str) -> tuple | None:
    """PROBE_WORDS consecutive words of a text (from the middle, starting at a long word), which a file holds whatever
    its escaping; None when the text has fewer words."""
    w = [x.decode() for x in _WORD.findall((text or "").lower().encode("utf-8"))]
    if len(w) < PROBE_WORDS:
        return None
    lo = max(0, (len(w) - PROBE_WORDS) // 2 - 4)
    hi = min(len(w) - PROBE_WORDS, lo + 8)
    i = max(range(lo, hi + 1), key=lambda j: (len(w[j]), -abs(j - (lo + hi) // 2)))
    return tuple(w[i:i + PROBE_WORDS])


def _tracked_strings(path: Path) -> tuple[set, str]:
    """(normalised string values, whole normalised text) of a tracked file: parsed JSON strings, Python string
    constants, or the lines and table cells of any other text file."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    vals = []

    def walk(x):
        if isinstance(x, str):
            vals.append(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                vals.append(k)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    if path.suffix in (".json", ".jsonl", ".ipynb"):
        for line in ([raw] if path.suffix != ".jsonl" else raw.split("\n")):
            try:
                walk(json.loads(line))
            except json.JSONDecodeError:
                vals.append(line)
    elif path.suffix == ".py":
        import ast
        try:
            vals += [n.value for n in ast.walk(ast.parse(raw)) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        except SyntaxError:
            vals += raw.split("\n")
    else:
        raw = raw.replace("\\|", "|")
        vals += raw.split("\n") + [c for line in raw.split("\n") if line.startswith("|") for c in line.split("|")]
    return {_nws(v) for v in vals}, _nws(" \n ".join(vals) + " " + raw)


def tracked_files(repo: Path = REPO) -> list:
    import subprocess
    r = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, check=True)
    return [f for f in r.stdout.decode("utf-8").split("\0") if f]


def _scan(files: list, repo: Path, probes: dict, ids: set) -> dict:
    """{file: {"probes": {probe}, "ids": {id}}} for tracked text files holding a probe (a word run) or an id."""
    first = {p[0] for p in probes}
    out = {}
    for f in files:
        try:
            data = (Path(repo) / f).read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        hit_ids = {m.decode() for m in _ID.findall(data)} & ids
        w = [x.decode() for x in _words(data)]
        hit = set()
        for i, t in enumerate(w):
            if t in first:
                p = tuple(w[i:i + PROBE_WORDS])
                if p in probes:
                    hit.add(p)
        if hit or hit_ids:
            out[f] = {"probes": hit, "ids": hit_ids}
    return out


def private_slice_ids(root: Path = E2, build_private: Path = BUILD_PRIVATE) -> set:
    """Ids of the private slice: the rows the edition 2 build holds out (``build/private/F*.test.jsonl``) and the
    private disputed rows waiting for the owner. A private candidate the build released (its near-copy is public, so
    it became a public test row) or dropped (its text is another split's row, or a row outside edition 2) is not in
    the slice. Without a build on this machine, every private candidate."""
    bp = Path(build_private)
    if not (bp / "manifest.json").exists():
        return {c["id"] for s in SUITES for c in _jsonl(private_dir(s, root) / "candidates.jsonl")}
    ids = {r["id"] for f in sorted(bp.glob("F*.test.jsonl")) for r in _jsonl(f)}
    return ids | {r["id"] for r in _jsonl(bp / "needs-owner-review.jsonl")}


def leak_needles(root: Path = E2, withheld: bool = True, build_private: Path = BUILD_PRIVATE) -> list:
    """(kind, key, value) of everything that must never be in a tracked file: each held-out authored case's text
    (``held_out_text``), each private-slice row's id (``private_id``) and text fields (``private_text``) and, with
    ``withheld``, the text of every public row whose source licence is not cleared (``withheld_text``) unless a
    public row of a cleared source carries the same text. A field value that BOILERPLATE_ROWS or more rows share (the
    fixed SummEdits query) is not a row's text and is left out."""
    slice_ids = private_slice_ids(root, build_private)
    out = [("held_out_text", k, t) for k, t in sorted(held_out_texts(root).items())]
    shared, cleared, rows = {}, set(), []
    for s in SUITES:
        pub = _jsonl(suite_dir(s, root) / "candidates.jsonl")
        prv = _jsonl(private_dir(s, root) / "candidates.jsonl")
        for c in pub + prv:
            for t in {_nws(t) for t in _field_texts(*_fields(c)) if t}:
                shared[t] = shared.get(t, 0) + 1
        cleared |= {_nws(t) for c in pub if "redacted" not in c for t in _field_texts(*_fields(c)) if t}
        for c in prv:
            if c["id"] in slice_ids:
                out.append(("private_id", c["id"], c["id"]))
                rows += [("private_text", c["id"], t) for t in _field_texts(*_fields(c)) if t and t.strip()]
        if withheld:
            for e in _jsonl(text_cache(s, root)):
                rows += [("withheld_text", e["id"], t) for f in e["fields"] for t in _field_texts(f)
                         if t and t.strip() and _nws(t) not in cleared]
    for e in _jsonl(Path(build_private) / "needs-owner-review.jsonl"):
        if not any(k == "private_id" and key == e["id"] for k, key, _ in out):
            out.append(("private_id", e["id"], e["id"]))
    return out + [r for r in rows if shared.get(_nws(r[2]), 0) < BOILERPLATE_ROWS]


def tracked_leaks(root: Path = E2, repo: Path = REPO, withheld: bool = True, needles: list | None = None,
                  build_private: Path = BUILD_PRIVATE, files: list | None = None) -> dict:
    """Scan every tracked file (``git ls-files``) for the ``leak_needles``. An id is found as a whole id. A text is
    found when a run of PROBE_WORDS of its words is in a file and the whole text (whitespace and case normalised) is in
    that file too; a text under SHORT_NEEDLE characters only when it is a whole string value (a JSON string, a Python
    constant, a line or a table cell). Returns {"leaks": [{"kind", "key", "file"}], "unscanned": {kind: n} (texts too
    short for a probe), "needles": {kind: n}}, never the texts themselves."""
    needles = leak_needles(root, withheld, build_private) if needles is None else needles
    ids = {v: (k, key) for k, key, v in needles if k == "private_id"}
    texts, unscanned = {}, {}
    for k, key, v in needles:
        if k == "private_id":
            continue
        p = _probe(v)
        if p is None:
            unscanned[k] = unscanned.get(k, 0) + 1
            continue
        texts.setdefault(p, []).append((k, key, _nws(v)))
    leaks = set()
    for f, hit in _scan(tracked_files(repo) if files is None else files, repo, texts, set(ids)).items():
        leaks |= {(*ids[i], f) for i in hit["ids"]}
        if not hit["probes"]:
            continue
        vals, whole = _tracked_strings(Path(repo) / f)
        for p in hit["probes"]:
            for k, key, n in texts[p]:
                if (n in whole) if len(n) >= SHORT_NEEDLE else (n in vals):
                    leaks.add((k, key, f))
    return {"leaks": [{"kind": k, "key": key, "file": f} for k, key, f in sorted(leaks)], "unscanned": unscanned,
            "needles": {k: sum(1 for n in needles if n[0] == k) for k in sorted({n[0] for n in needles})}}


# --- rehydration -----------------------------------------------------------------------------------------------------

def _upstream_fields(source: str) -> dict:
    """{id: row dict (with "state")} for one source, from its pinned loader (network or the Hugging Face cache)."""
    from .sources import SOURCES
    if source in ("nemotron_pii", "gretel_pii_en", "gretel_pii_finance"):
        from .sources import e2_pii, e2_pii_gretel, e2_pii_gretel_finance, e2_pii_nemotron
        mod = {"nemotron_pii": e2_pii_nemotron, "gretel_pii_en": e2_pii_gretel, "gretel_pii_finance": e2_pii_gretel_finance}[source]
        rows, _ = mod.eligible(e2_pii.reference_index())
        return {c["id"]: c for c in rows}
    key = {"lakera_gandalf_summarization": "lakera_mosscap"}.get(source, source)    # one loader yields both
    return {r.id: r.to_dict() for r in SOURCES[key].load()}


def rehydrate(suites=SUITES, root: Path = E2, fetch=_upstream_fields) -> dict:
    """Fill local/text.jsonl for redacted rows that have no cached text. Only text whose sha256 matches is kept."""
    out = {}
    for s in suites:
        sd = suite_dir(s, root)
        rows = [c for c in _jsonl(sd / "candidates.jsonl") if "redacted" in c]
        cache = _cache(s, root)
        todo = [c for c in rows if c["id"] not in cache]
        tally = {"cached": len(rows) - len(todo), "rebuilt": 0, "hash_differs": 0, "not_found": 0}
        by_source = {}
        for c in todo:
            by_source.setdefault(source_of(c), []).append(c)
        for src, cs in sorted(by_source.items()):
            states = fetch(src)
            for c in cs:
                up = states.get(c["id"])
                if up is None:
                    tally["not_found"] += 1
                    continue
                state = up.get("state", up)
                fields = [{k: state.get(k) for k in STRIP if k in st} for st in _states(c)]
                if fields_sha256(fields) != c["redacted"]["fields_sha256"]:
                    tally["hash_differs"] += 1
                    continue
                entry = {"id": c["id"], "source": src, "fields": fields}
                paths = c["redacted"].get("also_withheld", [])
                if paths:
                    try:
                        extra = [[p, _get(up, p)] for p in paths]
                    except (KeyError, IndexError, TypeError):
                        extra = None
                    if extra is None or fields_sha256([v for _, v in extra]) != c["redacted"]["also_withheld_sha256"]:
                        tally["text_only_extra_fields_missing"] = tally.get("text_only_extra_fields_missing", 0) + 1
                        continue
                    entry["extra"] = extra
                cache[c["id"]] = entry
                tally["rebuilt"] += 1
        order = [c["id"] for c in _jsonl(sd / "candidates.jsonl") if c["id"] in cache]
        _write_lines(text_cache(s, root), [json.dumps(cache[i], ensure_ascii=False, sort_keys=True) for i in order])
        out[s] = tally
    return out


# --- the salted re-draw of the private slice ------------------------------------------------------------------------
#
# The first private slice was drawn with the builders' published seeds, so the published code gave it. ``redraw``
# draws it again, once, under the salt. Per suite and stratum (subtask, label, source) it releases every movable
# private unit to the public test split and draws the same number of rows from the units that were public test rows,
# in salted order. The new slice is disjoint from the old one: rerunning the old seeded code gives rows that are now
# public. A unit is a build cluster (``edition2.assemble``: shared group or near-duplicate body), so the build never
# releases a drawn row again. Left where they are: dev (the dev split stays as it was), authored sources (a
# held-out case's text is in private/authored.json and its id is salted, ``held_out_sid``), rows named or quoted in a
# tracked file the build does not regenerate (a ledger, a doc, needs-owner-review.jsonl), disputed rows waiting for the
# owner, rows the build dropped, clusters across suites, and the content human sample (ruling 7) while it is drawn.

AUTHORED_SOURCES = ("e2_denied_topics", "e2_attack_controls", "e2_pii_controls")
# tracked files the edition 2 build and e2_local.split regenerate from the candidates: a row they name may move
REGENERATED = re.compile(r"^dataset/edition2/(?:[a-z_]+/(?:candidates|relabel(?:-round\d+)?|first_labels|resolutions|"
                         r"corrections)\.jsonl|[a-z_]+/DISAGREEMENTS\.md|build/(?:manifest|audit-report)\.json|"
                         r"build/OWNER-REVIEW\.md)$")
SAMPLE_MANIFEST = E2 / "content" / "sample" / "manifest.json"
REDRAW_RECORD = "redraw.json"


def _stratum(c: dict) -> tuple:
    sub = c.get("subtask") or (c.get("record") or {}).get("subtask")
    return (sub, c["label"], source_of(c))


def set_split(c: dict, split: str) -> None:
    """Move a candidate row to ``split`` (dev, test or private) in every field that records it."""
    c["proposed_split"] = split
    vis = "heldout" if split == "private" else "public"
    rec_split = "dev" if split == "dev" else "test"
    for d in (c, c.get("record")):
        if not isinstance(d, dict):
            continue
        if "visibility" in d:
            d["visibility"] = vis
        if "split" in d:
            d["split"] = rec_split
        if isinstance(d.get("attribute"), dict) and "proposed_split" in d["attribute"]:
            d["attribute"]["proposed_split"] = split


def pinned_public(root: Path = E2, repo: Path = REPO, files: list | None = None) -> dict:
    """{id: why} of rows that may not move into the private slice: named in a tracked file the build does not
    regenerate, or in the drawn content human sample."""
    ids = {c["id"] for s in SUITES for c in _jsonl(suite_dir(s, root) / "candidates.jsonl")}
    out = {}
    for f in (tracked_files(repo) if files is None else files):
        if REGENERATED.match(f):
            continue
        try:
            data = (Path(repo) / f).read_bytes()
        except OSError:
            continue
        for m in set(_ID.findall(data)):
            i = m.decode()
            if i in ids:
                out.setdefault(i, f"named in {f}")
    if SAMPLE_MANIFEST.exists() and Path(root).resolve() == E2.resolve():
        for r in json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))["rows"]:
            out.setdefault(r["id"], "content human sample (ruling 7)")
    return out


def redraw_plan(suites=SUITES, root: Path = E2, salt: str | None = None, parts: dict | None = None,
                pinned: dict | None = None) -> dict:
    """The salted re-draw (see above), not applied. ``parts``: edition2.build_parts() output (computed when None)."""
    salt = salt or private_salt()
    if parts is None:
        from . import edition2
        parts, _ = edition2.build_parts(Path(root))
    pinned = pinned_public(root) if pinned is None else pinned
    bucket_of, unit_of = {}, {}
    for bucket, rows in parts.items():
        for r in rows:
            bucket_of[r.id] = bucket
            unit_of[r.id] = r.group
    rows = {s: candidates(s, root) for s in suites}
    units = defaultdict(list)
    for s, cs in rows.items():
        for c in cs:
            units[unit_of.get(c["id"], "row:" + c["id"])].append((s, c))
    # a unit that spans suites or reaches rows of a suite not being drawn stays put
    reach = Counter(unit_of[c["id"]] for s in SUITES if s not in suites for c in _jsonl(suite_dir(s, root) / "candidates.jsonl")
                    if c["id"] in unit_of) if set(suites) != set(SUITES) else Counter()
    plan = {"salt_fingerprint": salt_fingerprint(salt), "suites": {}}
    for s in suites:
        why_not, movable, pool = Counter(), [], []
        for u, members in units.items():
            if members[0][0] != s:
                continue
            cs = [c for _, c in members]
            splits = {c["proposed_split"] for c in cs}
            if len({m[0] for m in members}) > 1 or reach[u]:
                why = "cluster across suites"
            elif any(source_of(c) in AUTHORED_SOURCES for c in cs):
                why = "authored source"
            elif "dev" in splits:
                why = "dev"
            elif len(splits) > 1:
                why = "cluster across splits (the build releases it to test)"
            elif any(c["id"] not in bucket_of for c in cs):
                why = "not in the build"
            elif any(bucket_of[c["id"]].startswith(("review", "dropped")) for c in cs):
                why = "disputed (awaits the owner) or dropped by the build"
            elif any(c["id"] in pinned for c in cs):
                why = "pinned public: " + sorted(pinned[c["id"]] for c in cs if c["id"] in pinned)[0].split(" in ")[0]
            else:
                why = None
            if why:
                why_not[f"{why}|{splits.pop() if len(splits) == 1 else 'mixed'}"] += len(cs)
                continue
            (movable if splits == {"private"} else pool).append((u, cs))
        target = Counter(_stratum(c) for _, cs in movable for c in cs)
        got, picked = Counter(), []
        for u, cs in sorted(pool, key=lambda x: salted("redraw", s, x[0], salt=salt)):
            need = Counter(_stratum(c) for c in cs)
            if all(got[k] + n <= target[k] for k, n in need.items()):
                got.update(need)
                picked.append((u, cs))
        plan["suites"][s] = {
            "released": sorted(c["id"] for _, cs in movable for c in cs),
            "drawn": sorted(c["id"] for _, cs in picked for c in cs),
            "units": {"movable_private": len(movable), "pool": len(pool), "drawn": len(picked)},
            "kept_in_place_rows": dict(sorted(why_not.items())),
            "strata": {"|".join(map(str, k)): {"target": target[k], "drawn": got[k]} for k in sorted(target)},
            "shortfall": sum(target.values()) - sum(got.values()),
        }
    return plan


def _retag_split_line(line: str, row: dict, new: str) -> str:
    """A row-file line with its top-level proposed_split changed, keeping the rest of the line byte for byte."""
    old = row["proposed_split"]
    for sep in ('": "', '":"'):
        needle = f'"proposed_split{sep}{old}"'
        if line.count(needle) == 1:
            return line.replace(needle, f'"proposed_split{sep}{new}"')
    row = dict(row, proposed_split=new)
    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def apply_redraw(plan: dict, root: Path = E2, pol: dict | None = None) -> dict:
    """Write a redraw_plan: every suite file rewritten with the new splits, then ``split`` puts each row where it now
    belongs. The plan (it names private-slice ids) is kept in ``<suite>/private/redraw.json``."""
    root = Path(root)
    moved = {}
    for s, p in plan["suites"].items():
        moved.update({i: (s, "test") for i in p["released"]})
        moved.update({i: (s, "private") for i in p["drawn"]})
    for s in plan["suites"]:
        st = STYLE.get(s, DEFAULT_STYLE)
        rows = candidates(s, root)
        for c in rows:
            if c["id"] in moved:
                set_split(c, moved[c["id"]][1])
        _write_lines(suite_dir(s, root) / "candidates.jsonl", [json.dumps(c, **st) for c in rows])
        for name in ROW_FILES.get(s, ()):
            for path in (suite_dir(s, root) / name, private_dir(s, root) / name):
                lines = []
                for line, r in _raw_rows(path):
                    if r["id"] in moved and "proposed_split" in r and r["proposed_split"] != moved[r["id"]][1]:
                        line = _retag_split_line(line, r, moved[r["id"]][1])
                    lines.append(line)
                if path.exists():
                    _write_lines(path, lines)
        rec = dict(plan["suites"][s], salt_fingerprint=plan["salt_fingerprint"], rule="e2_local.redraw_plan")
        private_dir(s, root).mkdir(parents=True, exist_ok=True)
        (private_dir(s, root) / REDRAW_RECORD).write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    return split(SUITES, root, pol)


# --- held-out authored cases: salted ids ---------------------------------------------------------------------------

def _authored_rows(suite: str) -> list:
    """(id, source_id, group, text) of every authored row the suite's builder makes now (held-out ids salted)."""
    if suite == "denied_topics":
        from .sources import e2_denied_topics as M
        return [(r.id, r.provenance.source_id, r.group, r.state.text) for r in M.load()]
    if suite == "prompt_attacks":
        from .sources import e2_prompt_attacks_controls as M
        return [(r.id, r.provenance.source_id, r.group, r.state.text) for r in M.load()]
    if suite == "pii":
        from .sources import e2_pii_controls as M
        return [(c["id"], c["source_id"], c["group"], c["state"]["text"]) for c in M.candidates()]
    return []


def _replace_strings(x, table: dict):
    if isinstance(x, str):
        return table.get(x, x)
    if isinstance(x, list):
        return [_replace_strings(v, table) for v in x]
    if isinstance(x, dict):
        return {k: _replace_strings(v, table) for k, v in x.items()}
    return x


def rekey_held_out(root: Path = E2, apply: bool = False) -> dict:
    """Give every private-slice row of an authored source the id its builder now makes (``held_out_sid``), matched on
    the row's text. The id, source id and group change in the private candidate row, and the id in every other file
    under ``<suite>/private/`` and ``build/private/`` (second labels, rulings, packets, answer keys, notes). Returns
    {suite: {"rows": n, "renamed": n}}; ``apply=False`` only checks the match."""
    root = Path(root)
    report, ids = {}, {}
    for s in ("denied_topics", "prompt_attacks", "pii"):
        built = {}
        for i, sid, grp, text in _authored_rows(s):
            built.setdefault(_norm(text), []).append((i, sid, grp))
        prv = [c for c in _jsonl(private_dir(s, root) / "candidates.jsonl") if source_of(c) in AUTHORED_SOURCES]
        tables, renamed = {}, 0
        for c in prv:
            hits = built.get(_norm((c.get("state") or {}).get("text")), [])
            if len(hits) != 1:
                raise ValueError(f"{s}: a held-out authored row matches {len(hits)} built rows by text")
            new_id, new_sid, new_grp = hits[0]
            old_sid = c.get("source_id") or ((c.get("record") or {}).get("provenance") or {}).get("source_id")
            # the builder's own group (prompt attacks: loader_group; a merged near-duplicate group keeps its name)
            old_grp = c.get("loader_group") or c.get("group") or (c.get("record") or {}).get("group")
            if new_id == c["id"]:
                continue
            renamed += 1
            ids[c["id"]] = new_id
            tables[c["id"]] = {c["id"]: new_id, old_sid: new_sid, old_grp: new_grp}
        report[s] = {"rows": len(prv), "renamed": renamed}
        if apply and tables:
            path = private_dir(s, root) / "candidates.jsonl"
            st = STYLE.get(s, DEFAULT_STYLE)
            out = []
            for line, c in _raw_rows(path):
                out.append(json.dumps(_replace_strings(c, tables[c["id"]]), **st) if c["id"] in tables else line)
            _write_lines(path, out)
    if apply and ids:
        pat = re.compile("|".join(re.escape(i) for i in sorted(ids, key=len, reverse=True)))
        dirs = [private_dir(s, root) for s in SUITES] + [Path(root) / "build" / "private"]
        for d in dirs:
            for p in sorted(d.rglob("*")) if d.exists() else []:
                if not p.is_file() or p.suffix not in (".jsonl", ".json", ".md", ".txt", ".html", ".csv"):
                    continue
                if p.name == "candidates.jsonl" and p.parent.name == "private":
                    continue                          # rewritten above, field by field
                t = p.read_text(encoding="utf-8")
                n = pat.sub(lambda m: ids[m.group(0)], t)
                if n != t:
                    p.write_text(n, encoding="utf-8")
    return report


# --- can the private slice be derived from tracked files? ----------------------------------------------------------

def _row_handles(c: dict) -> set:
    """Strings that point at one row: its id, source id (and each ':' part), group and loader group."""
    rec = c.get("record") or {}
    sid = c.get("source_id") or (rec.get("provenance") or {}).get("source_id") or \
        (c.get("provenance") or {}).get("source_id") or ""
    out = {c["id"], sid, c.get("group"), rec.get("group"), c.get("loader_group")} | set(sid.split(":"))
    return {h for h in out if isinstance(h, str) and h.strip()}


def private_handles(root: Path = E2, ids: set | None = None) -> dict:
    """{handle: private row id} for every handle of a private candidate that no public candidate shares. ``ids``: only
    these private rows (the slice the build holds out: a private candidate the build released to test, because its
    near-copy is public, is not held out)."""
    public, out = set(), {}
    for s in SUITES:
        for c in _jsonl(suite_dir(s, root) / "candidates.jsonl"):
            public |= _row_handles(c)
        for c in _jsonl(private_dir(s, root) / "candidates.jsonl"):
            if ids is not None and c["id"] not in ids:
                public |= _row_handles(c) if c["proposed_split"] != "private" else set()
                continue
            for h in _row_handles(c):
                out.setdefault(h, c["id"])
    return {h: i for h, i in out.items() if h not in public}


BUILDER_CODE = re.compile(r"^dataset/goldrails_dataset/sources/e2_[a-z0-9_]+\.py$")
LONG_HANDLE = 12        # a handle this long is looked for in every tracked file, not only in the builder code


def _py_strings(path: Path) -> set:
    import ast
    return {n.value for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def positional_ids() -> set:
    """Every id an authored row would get if its source id still followed its position in the tracked case list (or
    its pair number): the ids someone could compute from the tracked code alone."""
    from .records import make_id
    from .sources import e2_denied_topics as DT, e2_pii_controls as PC, e2_prompt_attacks_controls as PA
    out = set()
    for n in range(1000):
        out |= {make_id("F5", PC.SOURCE, f"{k}-{n:03d}") for k in ("neg", "dl")}
        out |= {make_id("F2", PA.NAME, f"{a}:{n}") for a in (PA.AUTHORED, PA.V2.AUTHORED)}
    for code, _ in DT.BY_TOPIC.values():
        for kind in ("in", "hn"):
            out |= {make_id("F3", DT.NAME, f"{code}:{kind}:{n:02d}") for n in range(200)}
    out |= {make_id("F3", DT.NAME, f"cf:{n:02d}") for n in range(200)}
    return out


def derivable_private_ids(root: Path = E2, repo: Path = REPO, files: list | None = None,
                          build_private: Path = BUILD_PRIVATE) -> dict:
    """What the tracked files give away about the private slice, without the salt or any git-ignored file:
    {"selection_entries": [{"file", "kind"}]: a tracked builder string (a selection list or override entry) equal to a
    handle only a private row has (its source id, a part of it, its group); "handles_elsewhere": the same for long
    handles in any tracked file; "positional_ids": private ids that follow from a held-out case's position in a
    tracked case list; "private_ids": how many rows were checked (the private slice of the last build, as
    ``private_slice_ids``). Never the ids themselves."""
    priv = private_slice_ids(root, build_private)
    handles = private_handles(root, priv)
    files = tracked_files(repo) if files is None else files
    sel, other = Counter(), Counter()
    for f in files:
        p = Path(repo) / f
        if BUILDER_CODE.match(f):
            for v in _py_strings(p) & set(handles):
                sel[f] += 1
            continue
        long = {h for h in handles if len(h) >= LONG_HANDLE}
        try:
            data = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        toks = set(re.findall(r"[A-Za-z0-9_:\-]{%d,}" % LONG_HANDLE, data))
        if toks & long:
            other[f] += len(toks & long)
    pos = positional_ids() & priv
    return {"private_ids": len(priv), "selection_entries": [{"file": f, "n": n} for f, n in sorted(sel.items())],
            "handles_elsewhere": [{"file": f, "n": n} for f, n in sorted(other.items())],
            "positional_ids": len(pos)}


def status(root: Path = E2) -> dict:
    out = {}
    for s in SUITES:
        sd = suite_dir(s, root)
        pub = _jsonl(sd / "candidates.jsonl")
        out[s] = {"public_rows": len(pub), "redacted": sum("redacted" in c for c in pub),
                  "private_file": (private_dir(s, root) / "candidates.jsonl").exists(),
                  "text_cache_rows": len(_cache(s, root)), "complete": have_local(s, root)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("status", "split", "rehydrate", "salt", "redraw", "rekey", "derivable"))
    ap.add_argument("suites", nargs="*", default=list(SUITES))
    ap.add_argument("--init", action="store_true", help="salt: write a new salt if none exists (never overwrites)")
    ap.add_argument("--apply", action="store_true", help="redraw / rekey: write the result (default: report only)")
    a = ap.parse_args(argv)
    if a.command == "split":
        rep = split(a.suites)
    elif a.command == "rehydrate":
        rep = rehydrate(a.suites)
    elif a.command == "salt":
        written = init_salt() if a.init else False
        rep = {"file": str(SALT_FILE), "written_now": written, "fingerprint": salt_fingerprint()}
    elif a.command == "redraw":
        plan = redraw_plan(a.suites)
        # counts only: the plan names private-slice rows, it goes to the git-ignored private/redraw.json
        rep = {"salt_fingerprint": plan["salt_fingerprint"], "applied": a.apply,
               "suites": {s: {k: (len(v) if isinstance(v, list) else v) for k, v in p.items() if k != "strata"}
                          for s, p in plan["suites"].items()}}
        if a.apply:
            rep["split"] = apply_redraw(plan)
    elif a.command == "rekey":
        rep = rekey_held_out(apply=a.apply)
    elif a.command == "derivable":
        rep = derivable_private_ids()
    else:
        rep = status()
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
