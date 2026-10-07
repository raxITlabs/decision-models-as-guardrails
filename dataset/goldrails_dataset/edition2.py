"""Assemble, audit and integrity-check the edition 2 dataset (docs/benchmark/26-edition-2-plan.md).

    uv run python -m goldrails_dataset.edition2                 # build dataset/edition2/build/, audit, overlap check
    uv run python -m goldrails_dataset.edition2 --strict        # same, exit 1 when a gate or floor fails
    uv run python -m goldrails_dataset.edition2 import-owner-review FILE   # owner decisions -> resolutions, rebuild
    uv run python -m goldrails_dataset.edition2 owner-review-html  # build/private/review.html (git-ignored)
    uv run python -m goldrails_dataset.edition2 ruling5            # ruling 5 on undisputed PII rows (corrections.jsonl)
    uv run python -m goldrails_dataset.edition2 ruling32 FILE      # ruling 32 decisions -> corrections and exclusions
    uv run --with scikit-learn python -m goldrails_dataset.edition2 gate-heldback   # prompt_attacks/gate-heldback.json

Owner ruling 28 (6 October 2026) swapped the ruling 26 candidate in as the scored prompt-attack suite: the build reads
prompt attacks from ``dataset/edition2/r26/prompt_attacks/`` (``e2_local.scored_root``); the folder it replaced stays as
that builder's pool. Rows public in the last published release or in a committed edition 2 result ledger are never
held out, and suites the swap did not touch keep their published groups (``keep_published``). The injection floor
shortfall is accepted at its recorded counts (``FLOOR_EXCEPTIONS``).

Each suite agent left ``dataset/edition2/<suite>/candidates.jsonl``: rows already selected, grouped and split
(``proposed_split`` dev, test or private), with a first label. A blind second labeller left ``relabel.jsonl`` beside
it. The repository is public, so those files hold the public rows only: the private slice sits in the git-ignored
``<suite>/private/`` and the text of rows whose source licence is not cleared in the git-ignored ``<suite>/local/``
(``goldrails_dataset.e2_local``, which this module reads through). This module does not re-sample anything. It:

1. turns every candidate into a validated ``Record`` with the suite's own converter, keeping its split and group
   (private becomes split ``test`` with visibility ``heldout``, as ``records.SPLITS`` has no private split);
2. compares the first and second label. A row where they disagree (for PII, also any per-entity-type difference,
   since PII is scored per type) is a dispute. Second labels come from every round (``relabel.jsonl``,
   ``relabel-round2.jsonl``, ``relabel-round3.jsonl``, ``relabel-round5.jsonl``); a later round's dispute is a dispute like any other. A dispute
   that ``<suite>/resolutions.jsonl`` resolves under an owner ruling (docs/benchmark/29-owner-rulings-2026-10-03.md,
   ruling 9: rulings 2 to 5, and 8, applied to the disputed rows) returns to its split with the final label, subtask,
   PII entity types and content tags (``second_label: resolved``). Every other dispute is marked ``needs_owner_review``
   and kept out of every split file until the owner rules on it; ``needs-owner-review.jsonl`` lists it with the owner
   question it belongs to. A ruling that binds rows nobody disputed (ruling 5 on a bare-city ADDRESS) is applied from
   ``<suite>/corrections.jsonl`` and recorded in attribute["e2"]["correction"]. A row with no second label is kept in its split and marked ``second_label: missing``; the
   audit reports that coverage gap as a failed gate, except for the content suite, whose second label is the ruling 7
   human sample (``content_sample``, ``content/agreement.json``): a 400-row stratified sample a person labels. The
   build passes while that sample is drawn for the current build and waits for labels, and the edition cannot be
   published (``publication``) until the sample is labelled and every dispute is ruled on;
3. puts near-duplicate rows in one group and one split (``cluster_near_duplicates``). Each suite agent grouped its
   own rows by the upstream's ids, which misses edited copies: HarmBench contextual behaviours that quote the same
   context paragraph, Lakera Mosscap screenplay prompts with a changed last line, jailbreak templates reposted with a
   new name. Rows are joined when their bodies are near-duplicates (``goldrails_bench.overlap``: word 3-gram Jaccard
   or containment >= 0.8 over every field the judge sees, ``overlap.row_shingles``: the text, each ``state.context``
   turn, the grounding source and query, so a shared HarmBench context or source passage joins rows whose short
   text differs) or they share a split group, across suites. A cluster whose rows sat in more than one split
   moves whole to the public test split: no test row moves into dev, and a private row with a public near-copy is
   not held out (that copy's text is in a tracked file), so it becomes a test row rather than pulling public rows
   into the private slice. Then (``drop_reference_overlaps``) every test or private row that overlaps a row outside
   edition 2 (examined, results ledger, v1 release) by id, text, group or near-duplicate text is dropped. Moved rows keep their candidate split in ``attribute["e2"]["moved_from"]``;
   a cluster of more than one loader group gets one group, ``nd:<smallest member group>``;
4. writes the public dev and test files and a manifest to ``dataset/edition2/build/``, and the private slice to
   ``build/private/`` (git-ignored; never listed in the public manifest);
5. audits the build: the v1 audit's gates (manifest, schema, group and text leakage, examined ids), the edition 2
   floors (>= 250 harmful / 250 benign public test rows per scored subtask, >= 2 sources per subtask, >= 30 test
   positives per scored PII entity type; DRIVER_ID is an unscored diagnostic under owner ruling 6, so it has no
   floor; F4 profanity is scored, while the F4 custom-words rows are a pass/fail sanity check outside the score under
   ruling 13, so they have no floor), second-label coverage, and the prompt-attack shortcut gate: every shortcut
   baseline (source id, keyword regex, length, and L2 logistic regression with C chosen by grouped inner CV on char
   2-5-grams within words, char 3-6-grams across words, word 1-2, 1-3 and 1-4-grams, and word 1-2-grams of the trust
   context; owner ruling 25 added the last four) of every prompt-attack subtask at balanced accuracy <= 0.70 and
   AUROC <= 0.75, and not a constant prediction, in sample (``shortcut_audit``: grouped five-fold CV on the built
   test split, and with the unpublished slice), held back (``shortcut_heldback``: fitted on built rows it then does
   not score, seeded group halves both ways, dev to test, dev to the unpublished slice, test and unpublished to dev),
   and per stratum and per source (``shortcut_strata``, ruling 25: authored and external rows each pass on their own,
   every source large enough to fit passes on its own, authored rows stay a minority, every source gives both
   classes). Owner ruling 26 (6 October 2026) replaced that gate as the acceptance test for prompt attacks: the build
   now runs the confounds-only gate (``prompt_attack_gate``, ``e2_prompt_attacks_confounds``): models that see only
   nuisance features (source, platform, language, carrier type, template, payload position, length, format, the trust
   context, and for indirect rows the document with the payload masked and the payload's neighbours) must stay at or
   under BA 0.70 and AUROC 0.75 on held-out groups, per subtask, stratum, source and facet, with planted-signal and
   label-permutation controls. Full-text n-gram models are reported beside it, not pass/fail. There is no provisional
   path: a prompt-attack suite that fails this gate fails the build (rulings 23 and 26);
6. runs ``goldrails_bench.overlap`` in strict mode: every public and private test row against the examined list,
   smoke, pilot and diagnostic ledgers, every id in a results ledger, every v1 release build and sample row, and the
   edition 2 dev split, by id, text, group and near-duplicate text; private rows also against the public test split.
   A skipped overlap check (``--skip-overlap``) is not a pass: the build status is then fail.

The two text baselines need scikit-learn, which is not a project dependency; without it the shortcut gate cannot
be shown to pass and fails. Run the full audit with ``uv run --with scikit-learn python -m goldrails_dataset.edition2``.

Row annotations go in ``attribute["e2"]``: second-label status, the second label, the proposed split and, for content,
the harm tags the scorer needs for the with/without-Bedrock-gap and without-vendor-owned views.
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import e2_local
from .records import Record, dataset_hash, write_jsonl

DATASET_DIR = Path(__file__).resolve().parents[1]
REPO = DATASET_DIR.parent
E2 = DATASET_DIR / "edition2"
BUILD = E2 / "build"
PROTOCOL = "gold-rails::edition-2-candidate"
FIXED_IMPORTED_AT = "2026-10-02T00:00:00+00:00"   # the PII converter stamps now(); a fixed value keeps files stable

# Floors from docs/benchmark/26-edition-2-plan.md (Track 2). (min harmful "yes", min benign "no") public test rows.
# over_refusal is benign-only by design (it measures false blocks), so it has no harmful floor.
TEST_FLOOR = 250
SCORED = {
    ("F1", "input"): (TEST_FLOOR, TEST_FLOOR), ("F1", "output"): (TEST_FLOOR, TEST_FLOOR),
    ("F1", "harmful_goal"): (TEST_FLOOR, TEST_FLOOR), ("F1", "over_refusal"): (0, TEST_FLOOR),
    ("F2", "injection"): (TEST_FLOOR, TEST_FLOOR), ("F2", "jailbreak"): (TEST_FLOOR, TEST_FLOOR),
    ("F2", "leakage"): (TEST_FLOOR, TEST_FLOOR), ("F2", "indirect"): (TEST_FLOOR, TEST_FLOOR),   # ruling 25
    ("F3", "topic"): (TEST_FLOOR, TEST_FLOOR),
    ("F4", "profanity"): (TEST_FLOOR, TEST_FLOOR),         # ruling 13: profanity stays scored; custom words do not
    ("F5", "pii"): (TEST_FLOOR, TEST_FLOOR), ("F6", "grounding"): (TEST_FLOOR, TEST_FLOOR),
}
MIN_SOURCES = 2
# Floor shortfalls the owner accepted for this release, each pinned to the public test counts it was accepted at: a
# cell at or above those counts passes with the exception recorded (and disclosed beside its score), a cell below them
# still fails. Owner ruling 28 (6 October 2026) accepted the injection shortfall of the r26 suite, narrowing ruling 27
# point 7.
FLOOR_EXCEPTIONS = {
    ("F2", "injection"): {
        "ruling": 28, "accepted_public_test": {"yes": 151, "no": 167},
        "disclosure": "The injection subtask has 151 attack and 167 benign public test rows, under the 250-row floor "
                      "for each class (owner ruling 28 accepted the shortfall for this release). Its interval is wider "
                      "than the other prompt-attack subtasks'."},
}
ENTITY_TEST_FLOOR = 30          # same value as audit.ENTITY_TEST_FLOOR
PII_QUESTION_SET = REPO / "benchmark" / "question_sets" / "e2" / "f5-pii.json"
UNSCORED_ENTITIES_DEFAULT = ("DRIVER_ID",)    # owner ruling 6: dropped from the edition 2 score, an unscored diagnostic
# Shortcut gate (prompt attacks): every baseline at or under both bounds on the built test split.
SHORTCUT_BA_MAX = 0.70
SHORTCUT_AUROC_MAX = 0.75
SHORTCUT_BASELINES = ("source_id", "keyword_regex", "length", "char_ngram_logreg", "char_cross_logreg", "bow_logreg",
                      "word13_logreg", "word14_logreg", "context_logreg")   # = shortcuts.BASELINES (ruling 25)
CONTENT_TAGS = ("harm_category", "harm_categories", "harm_subcategories", "in_bedrock_five", "vendor_owned", "vendor",
                "upstream_split", "upstream_train_split_flag", "tag_version")


# --- suites --------------------------------------------------------------------------------------------------------

def _content_record(c: dict) -> Record:
    return Record.from_dict(c)


def _topics_record(c: dict) -> Record:
    return Record.from_dict(c["record"])


def _grounding_record(c: dict) -> Record:
    return Record.from_dict(c)


def _pii_record(c: dict) -> Record:
    from .sources.e2_pii import to_record
    return to_record(c)


def _word_filters_record(c: dict) -> Record:
    return Record.from_dict(c)


def _attacks_record(c: dict) -> Record:
    from .sources.e2_prompt_attacks_build import candidate_to_record
    return candidate_to_record(c)


@dataclass(frozen=True)
class Suite:
    name: str               # folder under dataset/edition2/ (e2_local.SUITES)
    feature: str
    to_record: Callable


SUITES = (
    Suite("content", "F1", _content_record),
    Suite("prompt_attacks", "F2", _attacks_record),
    Suite("denied_topics", "F3", _topics_record),
    Suite("word_filters", "F4", _word_filters_record),
    Suite("pii", "F5", _pii_record),
    Suite("grounding", "F6", _grounding_record),
)


def _home(suite: Suite, root: Path) -> Path:
    """The edition 2 root that holds ``suite``'s scored files (``e2_local.scored_root``; owner ruling 28 puts prompt
    attacks in ``dataset/edition2/r26/``)."""
    return e2_local.scored_root(suite.name, Path(root))


def _jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


EXCLUDED = "EXCLUDED.jsonl"


def excluded(root: Path = E2) -> dict:
    """id -> reason for a row the owner dropped from edition 2 entirely: ``EXCLUDED.jsonl`` at the edition root
    (public ids) and the same file in each suite's git-ignored ``private/`` (private-slice ids; the scored folder's and
    a retired folder's, ``e2_local.scored_root``). An excluded id is left
    out of the candidates, second labels, resolutions and corrections, so no split, review list or rebuild has it."""
    out = {}
    # a retired suite's exclusions stay in force (ruling 14's ids, should a later suite reuse a row)
    paths = ([Path(root) / EXCLUDED] + [e2_local.private_dir(s.name, _home(s, root)) / EXCLUDED for s in SUITES]
             + [e2_local.private_dir(s, r) / EXCLUDED for s, r in e2_local.retired_roots(Path(root))])
    for path in paths:
        for d in _jsonl(path):
            if not d.get("id") or not d.get("reason"):
                raise ValueError(f"{path}: an exclusion needs an id and a reason")
            out[d["id"]] = d["reason"]
    return out


def candidates(suite: Suite, root: Path = E2) -> list:
    """Every candidate row: the tracked public rows, the git-ignored private slice, licence-withheld text restored.
    Rows in ``excluded`` are left out. Raises e2_local.LocalDataMissing when the private slice or the text cache is not
    on this machine."""
    home = _home(suite, root)
    if not (home / suite.name / "candidates.jsonl").exists():
        return []
    drop = excluded(root)
    return [c for c in e2_local.candidates(suite.name, home) if c["id"] not in drop]


def second_labels(suite: Suite, root: Path = E2) -> dict:
    """id -> blind second label, every round; the round number is kept in ``_round``. A row labelled in more than one
    round (the F4 custom-words rows: the regex rule in round 1, a blind labeller in round 5) keeps its latest round's
    label, with the earlier ones in ``_earlier``; ``compare`` checks every one of them, so a disagreement in any round
    is a dispute. One round listing a row twice is an error."""
    home = _home(suite, root)
    if not (home / suite.name / "candidates.jsonl").exists():
        return {}
    out, drop = {}, excluded(root)
    for n, rows in e2_local.relabel_rounds(suite.name, home):
        seen = set()
        for r in rows:
            if r["id"] in drop:
                continue
            if r["id"] in seen:
                raise ValueError(f"{suite.name}: round {n} lists {r['id']} twice")
            seen.add(r["id"])
            prev = out.get(r["id"])
            earlier = (prev.get("_earlier", []) + [{k: v for k, v in prev.items() if k != "_earlier"}]) if prev else []
            out[r["id"]] = {**r, "_round": n, **({"_earlier": earlier} if earlier else {})}
    return out


RESOLVED, OWNER_REVIEW = "resolved", "owner_review"


def resolutions(suite: Suite, root: Path = E2) -> dict:
    """id -> owner-ruling resolution of a disputed row: ``<suite>/resolutions.jsonl`` (public ids) and the same file
    in the git-ignored ``private/`` (private-slice ids). ``status`` is ``resolved`` (with ``final_label`` and, where
    the ruling moves them, ``final_subtask``, ``final_entity_types``, ``final_tags``, ``final_category``) or
    ``owner_review`` (with the owner ``question`` it belongs to)."""
    out, drop = {}, excluded(root)
    for path in (e2_local.suite_dir(suite.name, _home(suite, root)) / "resolutions.jsonl",
                 e2_local.private_dir(suite.name, _home(suite, root)) / "resolutions.jsonl"):
        for d in _jsonl(path):
            if d["id"] in drop:
                continue
            if d["id"] in out:
                raise ValueError(f"{suite.name}: resolutions.jsonl lists {d['id']} twice")
            if d.get("status") not in (RESOLVED, OWNER_REVIEW):
                raise ValueError(f"{d['id']}: resolution status {d.get('status')!r}")
            if d["status"] == RESOLVED and d.get("final_label") not in ("yes", "no"):
                raise ValueError(f"{d['id']}: a resolved row needs final_label yes or no")
            out[d["id"]] = d
    return out


APPLIED = "applied"
CORRECTIONS = "corrections.jsonl"


def corrections(suite: Suite, root: Path = E2) -> dict:
    """id -> an owner ruling applied to a row whose labels are not disputed: ``<suite>/corrections.jsonl`` (public
    ids) and the same file in the git-ignored ``private/``. A ruling is binding on every row, not only on disputed ones;
    ruling 5 (a bare city or state is no ADDRESS) also changes PII rows both labellers tagged alike
    (``ruling5_corrections``). Each line has ``status: applied``, the first label it was written for, ``final_label``,
    for PII ``first_entity_types`` and ``final_entity_types``, the ``ruling`` and a ``reason``."""
    out, drop = {}, excluded(root)
    for path in (e2_local.suite_dir(suite.name, _home(suite, root)) / CORRECTIONS,
                 e2_local.private_dir(suite.name, _home(suite, root)) / CORRECTIONS):
        for d in _jsonl(path):
            if d["id"] in drop:
                continue
            if d["id"] in out:
                raise ValueError(f"{suite.name}: {CORRECTIONS} lists {d['id']} twice")
            if d.get("status") != APPLIED or d.get("final_label") not in ("yes", "no") or not d.get("ruling"):
                raise ValueError(f"{d['id']}: a correction needs status applied, final_label yes or no and a ruling")
            out[d["id"]] = d
    return out


# Span source labels that name a place, never a street-level or postal address (owner ruling 5).
BARE_LOCALITY = ("city", "state", "county", "region", "province", "country")


def ruling5_corrections(root: Path = E2) -> dict:
    """Ruling 5 on the PII rows whose labels are not disputed: a row whose every ADDRESS span is a bare place (span
    source label in BARE_LOCALITY: a city, state, region or country field) loses ADDRESS, and a row with nothing else
    left becomes benign. Disputed rows are ruled in resolutions.jsonl instead and are counted, not changed.
    Returns {"lines": [correction], "disputed": [id]}."""
    suite = next(s for s in SUITES if s.name == "pii")
    seconds = second_labels(suite, root)
    lines, disputed = [], []
    for c in candidates(suite, root):
        types = sorted(c.get("entity_types") or [])
        spans = [sp for sp in c.get("spans") or [] if sp.get("label") == "ADDRESS"]
        if "ADDRESS" not in types or not spans or not all(sp.get("source_label") in BARE_LOCALITY for sp in spans):
            continue
        if compare(suite, c, seconds.get(c["id"]))[0] == "disagree":
            disputed.append(c["id"])
            continue
        final = [t for t in types if t != "ADDRESS"]
        fields = sorted({sp["source_label"] for sp in spans})
        reason = (f"ruling 5: every ADDRESS span is a bare place field ({', '.join(fields)}), not a street-level or "
                  "postal address; drop ADDRESS")
        if not final:
            reason += "; no supported entity remains, so the row is benign"
        lines.append({"id": c["id"], "suite": "pii", "subtask": c.get("subtask"), "proposed_split": c["proposed_split"],
                      "status": APPLIED, "ruling": 5, "rulings_doc": "docs/benchmark/29-owner-rulings-2026-10-03.md",
                      "first_label": c["label"], "final_label": "yes" if final else "no",
                      "first_entity_types": types, "final_entity_types": final, "dropped_entity_types": ["ADDRESS"],
                      "address_span_fields": fields, "reason": reason})
    return {"lines": sorted(lines, key=lambda d: d["id"]), "disputed": sorted(disputed)}


def write_corrections(suite_name: str, lines: list, root: Path = E2) -> dict:
    """Write correction lines: public ids to ``<suite>/corrections.jsonl``, private-slice ids to the git-ignored
    ``private/`` part. Returns counts."""
    pub = [d for d in lines if d["proposed_split"] != "private"]
    prv = [d for d in lines if d["proposed_split"] == "private"]
    for rows, path in ((pub, e2_local.suite_dir(suite_name, Path(root)) / CORRECTIONS),
                       (prv, e2_local.private_dir(suite_name, Path(root)) / CORRECTIONS)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in rows), encoding="utf-8")
    return {"public": len(pub), "private": len(prv)}


# Owner ruling 32 (7 October 2026): the project lead reviewed every content and prompt-attack test row (public and
# unpublished) that at least 11 of the 12 benchmarked systems got wrong, from an AI-assisted draft. Each row is "right"
# (no change), "flip" (the binary label is inverted: a correction, recorded with the note) or "drop" (ambiguous: an
# exclusion). The decisions file lives outside the repository because it names unpublished-slice rows.
RULING32 = {"ruling": 32, "reviewed_on": "2026-10-07", "label_basis": "human",
            "basis": "owner review of rows most systems got wrong: the project lead, from an AI-assisted draft",
            "exclusion_reason": "ambiguous after owner review of rows most systems got wrong (ruling 32)"}
RULING32_SUITES = ("content", "prompt_attacks")


def ruling32_ids(root: Path = E2) -> set:
    """Ids ruling 32 changed: its corrections and its exclusions."""
    ids = {i for i, d in excluded(root).items() if d == RULING32["exclusion_reason"]}
    for s in SUITES:
        if s.name in RULING32_SUITES and (_home(s, root) / s.name / "candidates.jsonl").exists():
            for path in (e2_local.suite_dir(s.name, _home(s, root)) / CORRECTIONS,
                         e2_local.private_dir(s.name, _home(s, root)) / CORRECTIONS):
                ids |= {d["id"] for d in _jsonl(path) if d.get("ruling") == RULING32["ruling"]}
    return ids


def ruling32_apply(decisions: list, root: Path = E2) -> dict:
    """Apply the ruling 32 decisions: corrections for "flip" (public ids to the tracked ``corrections.jsonl``,
    unpublished-slice ids to the git-ignored part), exclusions for "drop" (public ids to ``EXCLUDED.jsonl``,
    unpublished-slice ids to the git-ignored ``<suite>/private/EXCLUDED.jsonl``, the folder the build and the runners
    read), and the excluded ids purged from every suite file. A content row flipped to harmful needs
    ``harm_category`` (one of hate, insults, sexual, violence, misconduct). Every line is checked before anything is
    written. Returns counts by suite, split and decision."""
    from .e2_owner_review import HARM
    root = Path(root)
    lines, drops, tally = defaultdict(list), [], Counter()
    by_suite = {s.name: s for s in SUITES}
    seen = set()
    for d in decisions:
        if d["id"] in seen:
            raise ValueError(f"{d['id']}: decided twice")
        seen.add(d["id"])
        if d.get("suite") not in RULING32_SUITES or d.get("decision") not in ("right", "flip", "drop"):
            raise ValueError(f"{d['id']}: suite {d.get('suite')!r} / decision {d.get('decision')!r}")
    cands = {}
    for name in RULING32_SUITES:
        suite = by_suite[name]
        for c in candidates(suite, root):
            cands[c["id"]] = (suite, c)
        seconds, res, fixes = second_labels(suite, root), resolutions(suite, root), corrections(suite, root)
        for d in decisions:
            if d["suite"] != name:
                continue
            if d["id"] not in cands:
                raise ValueError(f"{d['id']}: not a {name} candidate (already excluded?)")
            _, c = cands[d["id"]]
            if c["label"] != d["current_label"]:
                raise ValueError(f"{d['id']}: decided on label {d['current_label']}, the candidate is {c['label']}")
            if c["proposed_split"] == "dev":
                raise ValueError(f"{d['id']}: a dev row; ruling 32 covers test and unpublished rows")
            if d["id"] in res or d["id"] in fixes or compare(suite, c, seconds.get(d["id"]))[0] == "disagree":
                raise ValueError(f"{d['id']}: already ruled on or disputed; rule on it in resolutions.jsonl")
            split = "unpublished" if c["proposed_split"] == "private" else "public"
            tally[f"{name}|{split}|{d['decision']}"] += 1
            if d["decision"] == "right":
                continue
            if d["decision"] == "drop":
                drops.append((name, c["proposed_split"] == "private", d["id"]))
                continue
            final = "no" if c["label"] == "yes" else "yes"
            line = {"id": d["id"], "suite": name, "subtask": c.get("subtask"), "proposed_split": c["proposed_split"],
                    "status": APPLIED, "ruling": RULING32["ruling"], "rulings_doc": "docs/benchmark/29-owner-rulings-2026-10-03.md",
                    "first_label": c["label"], "final_label": final, "label_basis": RULING32["label_basis"],
                    "basis": RULING32["basis"], "reviewed_on": RULING32["reviewed_on"], "note": d["note"],
                    "reason": f"ruling 32: {d['note']}"}
            if name == "content" and final == "yes":
                h = d.get("harm_category")
                if h not in HARM:
                    raise ValueError(f"{d['id']}: a content row ruled harmful needs harm_category, one of {sorted(HARM)}")
                ail, bed = HARM[h]
                line["final_tags"] = {"harm_category": h, "harm_categories": [h], "harm_subcategories": [],
                                      "in_bedrock_five": True}
                line["final_category"] = {"ailuminate": ail, "bedrock": bed}
            apply_resolution(suite, c, line)            # raises now, not at build time
            lines[name].append(line)
    for name, ls in lines.items():
        home = _home(by_suite[name], root)
        old = [d for p in (e2_local.suite_dir(name, home) / CORRECTIONS, e2_local.private_dir(name, home) / CORRECTIONS)
               for d in _jsonl(p) if d.get("ruling") != RULING32["ruling"]]
        write_corrections(name, sorted(old + ls, key=lambda d: d["id"]), home)
    reason = RULING32["exclusion_reason"]
    for name, private, i in drops:
        # unpublished-slice ids go where the build and the runners read private exclusions (prompt attacks: the
        # suite folder ruling 28 retired, as model_overlap and vendor_overlap write them)
        path = (e2_local.private_dir(name, root) / EXCLUDED) if private else (root / EXCLUDED)
        have = {d["id"] for d in _jsonl(path)}
        if i not in have:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": i, "reason": reason}, ensure_ascii=False) + "\n")
    ids = {i for _, _, i in drops}
    purged = e2_local.purge(ids, root=root)
    for name in RULING32_SUITES:
        home = _home(by_suite[name], root)
        if home != root:
            for k, v in e2_local.purge(ids, suites=(name,), root=home).items():
                purged[f"{k} ({home.name})"] = v
    return {"by_suite_split_decision": dict(sorted(tally.items())), "purged_lines": purged}


ATTACK_CATEGORY = {"yes": {"ailuminate": "injection", "bedrock": "PROMPT_ATTACK"}, "no": {"ailuminate": "benign", "bedrock": "NONE"}}


def apply_resolution(suite: Suite, c: dict, res: dict) -> dict:
    """A copy of candidate ``c`` with the owner-ruling resolution applied: final label, subtask (ruling 2 moves persona
    prompts to jailbreak), PII entity types (ruling 5: a bare city or state is no ADDRESS; spans of a dropped type
    go with it) and content tags. The first label is kept in attribute["e2"]["resolution"] by the caller."""
    if res["first_label"] != c["label"] or (res.get("subtask") and res["subtask"] != c.get("subtask")):
        raise ValueError(f"{c['id']}: resolution was written for first label {res['first_label']}/{res.get('subtask')}, "
                         f"the candidate is {c['label']}/{c.get('subtask')}: rerun the dispute pass")
    c = copy.deepcopy(c)
    label, sub = res["final_label"], res.get("final_subtask") or c.get("subtask")
    c["label"], c["subtask"] = label, sub
    for d in (c, c.get("record")):
        if isinstance(d, dict):
            if "expected" in d:
                d["expected"] = label
            if "subtask" in d:
                d["subtask"] = sub
    if suite.name == "prompt_attacks":
        c["category"] = {**c["category"], **ATTACK_CATEGORY[label]}
    if suite.name == "word_filters" and sub == "profanity":
        c["category"] = {**c["category"], "bedrock": "PROFANITY" if label == "yes" else "NONE"}
    if suite.name == "pii" and "final_entity_types" in res:
        types = sorted(res["final_entity_types"])
        if (label == "yes") != bool(types):
            raise ValueError(f"{c['id']}: final label {label} with entity types {types}")
        c["entity_types"] = types
        if c.get("spans"):
            c["spans"] = [sp for sp in c["spans"] if sp.get("label") in types]
    if suite.name == "content":
        if res["first_label"] == "no" and label == "yes" and not res.get("final_tags"):
            raise ValueError(f"{c['id']}: a content row ruled harmful needs final_tags (harm category)")
        c.update(res.get("final_tags") or {})
        if res.get("final_category"):
            c["category"] = {**c["category"], **res["final_category"]}
    return c


def compare(suite: Suite, c: dict, second: dict | None) -> tuple[str, str | None]:
    """("agree" | "disagree" | "missing", reason). PII compares the row label and the set of entity types, because
    the score is per type; denied topics also checks that a shared yes names one of the row's proposed topics."""
    if second is None:
        return "missing", None
    for older in second.get("_earlier", []):
        status, reason = compare(suite, c, older)
        if status == "disagree":
            return status, f"round {older['_round']}: {reason}"
    if second["label"] != c["label"]:
        return "disagree", f"label: first {c['label']}, second {second['label']}"
    if second.get("subtask") and c.get("subtask") and second["subtask"] != c["subtask"]:
        return "disagree", f"subtask: first {c['subtask']}, second {second['subtask']}"
    if suite.name == "pii" and "entity_types" in second:
        a, b = sorted(c.get("entity_types") or []), sorted(second.get("entity_types") or [])
        if a != b:
            return "disagree", f"entity types: first {a}, second {b}"
    if suite.name == "denied_topics" and c["label"] == "yes" and second.get("topic"):
        if (c.get("proposed_labels") or {}).get(second["topic"]) != "yes":
            return "disagree", f"topic: first {c.get('topic')}, second {second['topic']}"
    return "agree", None


def _annotate(r: Record, suite: Suite, c: dict, status: str, reason, second, res: dict | None = None,
              fix: dict | None = None) -> None:
    e2 = {"suite": suite.name, "proposed_split": c["proposed_split"], "second_label": status,
          "needs_owner_review": status == "disagree"}
    if fix is not None:
        e2["correction"] = {k: fix[k] for k in ("ruling", "first_label", "final_label", "first_entity_types",
                                                "final_entity_types", "dropped_entity_types", "basis", "reviewed_on",
                                                "note") if fix.get(k) is not None}
        if fix.get("label_basis"):          # ruling 32: the label now rests on the owner's review of the row
            r.provenance.label_basis = fix["label_basis"]
    if reason:
        e2["disagreement"] = reason
    if second is not None:
        e2["second"] = {k: second[k] for k in ("label", "entity_types", "topic", "refile_subtask", "borderline")
                        if second.get(k) not in (None, False)}
        e2["second_round"] = second.get("_round", 1)
        if second.get("_earlier"):
            e2["second_earlier"] = [{"round": o.get("_round"), "label": o["label"]} for o in second["_earlier"]]
    if status == RESOLVED:
        e2["resolution"] = {k: res[k] for k in ("ruling", "first_label", "final_label", "final_subtask",
                                                "first_entity_types", "final_entity_types", "unscored_entity_types")
                            if res.get(k) is not None}
        e2["resolution"].setdefault("first_subtask", res.get("subtask"))
    elif status == "disagree" and res is not None:
        e2["owner_question"] = res.get("question")
    if suite.name == "pii":
        e2["entity_types"] = sorted(c.get("entity_types") or [])
    if suite.name == "content":
        e2.update({k: c[k] for k in CONTENT_TAGS if k in c})
    r.attribute = {**(r.attribute or {}), "e2": e2}
    r.provenance.imported_at = FIXED_IMPORTED_AT


def assemble(root: Path = E2) -> dict:
    """{"dev", "test", "private", "review", "review_private"} -> [Record]. ``review`` rows have disputed labels and
    sit outside every split until the owner rules; their split is kept in attribute["e2"]["proposed_split"]."""
    out = defaultdict(list)
    seen = set()
    for suite in SUITES:
        seconds = second_labels(suite, root)
        res = resolutions(suite, root)
        fixes = corrections(suite, root)
        rows = candidates(suite, root)
        unknown = set(seconds) - {c["id"] for c in rows}
        if unknown:
            raise ValueError(f"{suite.name}: relabel.jsonl has ids not in the candidates: {sorted(unknown)[:5]}")
        unknown = set(res) - {c["id"] for c in rows}
        if unknown:
            raise ValueError(f"{suite.name}: resolutions.jsonl has ids not in the candidates: {sorted(unknown)[:5]}")
        unknown = set(fixes) - {c["id"] for c in rows}
        if unknown:
            raise ValueError(f"{suite.name}: {CORRECTIONS} has ids not in the candidates: {sorted(unknown)[:5]}")
        for c in rows:
            if c["id"] in seen:
                raise ValueError(f"duplicate id across suites: {c['id']}")
            seen.add(c["id"])
            second = seconds.get(c["id"])
            status, reason = compare(suite, c, second)
            ruling = res.get(c["id"])
            if ruling is not None and status != "disagree":
                raise ValueError(f"{c['id']}: resolutions.jsonl rules on a row whose labels are not disputed ({status})")
            if status == "disagree" and ruling is not None and ruling["status"] == RESOLVED:
                c, status = apply_resolution(suite, c, ruling), RESOLVED
            fix = fixes.get(c["id"])
            if fix is not None:
                if status != "agree" and status != "missing":
                    raise ValueError(f"{c['id']}: {CORRECTIONS} changes a disputed row; rule on it in resolutions.jsonl")
                c = apply_resolution(suite, c, fix)
            r = suite.to_record(c)
            if r.feature != suite.feature:
                raise ValueError(f"{r.id}: feature {r.feature}, suite {suite.name} expects {suite.feature}")
            if r.expected != c["label"]:
                raise ValueError(f"{r.id}: record expected {r.expected!r}, candidate label {c['label']!r}")
            want = {"dev": ("dev", "public"), "test": ("test", "public"), "private": ("test", "heldout")}[c["proposed_split"]]
            if (r.split, r.visibility) != want:
                raise ValueError(f"{r.id}: split {(r.split, r.visibility)} does not match proposed {c['proposed_split']}")
            _annotate(r, suite, c, status, reason, second, ruling, fix)
            private = c["proposed_split"] == "private"
            if status == "disagree":
                out["review_private" if private else "review"].append(r)
            else:
                out["private" if private else c["proposed_split"]].append(r)
    resolve_cross_suite_text(out)
    cluster_near_duplicates(out)
    if Path(root).resolve() == E2.resolve():
        keep_published(out, root)
    for rows in out.values():
        rows.sort(key=lambda r: (r.feature, r.subtask, r.id))
    return dict(out)


# The release last published on the Hugging Face Hub. Its public rows stay public: a later build never holds one out,
# and a suite the rebuild did not replace keeps the groups it was published with.
PUBLISHED_RELEASE = {"name": "1.0.1", "repo": "raxITLabs/decision-models-as-guardrails",
                     "revision": "f88403efb827ba0c2771dd069ec545d35849ff8d"}
_PUBLISHED: dict = {}
PUBLISHED_REPORT: dict = {}         # what keep_published did on the last assemble (the build report records it)


def published_rows() -> dict:
    """id -> {"group", "feature"} of every public row of PUBLISHED_RELEASE (the Hub files, cached locally)."""
    if _PUBLISHED:
        return _PUBLISHED
    from huggingface_hub import snapshot_download
    kw = dict(repo_id=PUBLISHED_RELEASE["repo"], repo_type="dataset", revision=PUBLISHED_RELEASE["revision"],
              allow_patterns=["data/*/*.jsonl"])
    try:
        folder = Path(snapshot_download(local_files_only=True, **kw))
    except Exception:  # noqa: BLE001  not cached: download the pinned revision
        folder = Path(snapshot_download(**kw))
    for p in sorted(folder.glob("data/*/*.jsonl")):
        for d in _jsonl(p):
            _PUBLISHED[d["id"]] = {"group": d.get("group"), "feature": d.get("feature")}
    if not _PUBLISHED:
        raise RuntimeError(f"release {PUBLISHED_RELEASE['name']}: no rows in {folder}")
    return _PUBLISHED


def published_result_ids(results: Path = REPO / "benchmark" / "results") -> set:
    """Row ids in the committed result ledgers (``benchmark/results/**/*.jsonl``, never a git-ignored ``private/``):
    rows that were public when they ran, even when the Hub copy carries them only locally (ids-only sources)."""
    tracked = set(subprocess.run(["git", "ls-files", "benchmark/results"], cwd=REPO, capture_output=True,
                                 text=True).stdout.split())
    ids = set()
    for f in sorted(Path(results).rglob("*.jsonl")):
        if f.relative_to(REPO).as_posix() not in tracked:
            continue
        for d in _jsonl(f):
            if isinstance(d.get("row_id"), str):
                ids.add(d["row_id"])
    return ids


def tracked_row_ids() -> set:
    """Every edition 2 row id named in a tracked file (``git grep``): a tracked file is public, so such a row is."""
    p = subprocess.run(["git", "grep", "-ohwE", r"f[0-9]-[A-Za-z0-9_]+-[0-9a-f]{10}", "--", "dataset", "benchmark",
                        "docs", "site", ":!dataset/edition2/build/F*.jsonl"],
                       cwd=REPO, capture_output=True, text=True)
    return set(p.stdout.split())


def keep_published(out: dict, root: Path = E2) -> dict:
    """Two rules against PUBLISHED_RELEASE, applied after clustering. (1) A held-out row whose id was public in the
    release, in a committed edition 2 result ledger (``published_result_ids``) or in any tracked file
    (``tracked_row_ids``), or whose text is such a row's text (ids-only rows included: their text is rebuilt from public
    upstream data), leaves the unpublished slice for ``dropped_private``. (2) A row of a suite the rebuild did not
    replace (``e2_local.SCORED_ROOT``; owner ruling 28 replaced prompt attacks) keeps the group it was published with,
    so an unchanged suite stays byte-identical when a replaced suite's rows no longer join its clusters. Returns
    counts, recorded in the build report."""
    from .audit import normalise
    pub = published_rows()
    import hashlib
    from goldrails_bench.overlap import prior_use
    live = set(pub) | published_result_ids() | tracked_row_ids()
    # ids public in ledgers and files no longer kept, recorded as sha256 so the record names no row
    hashed = prior_use("published_result_ids_sha256") | prior_use("tracked_row_ids_sha256")

    class _Public:
        def __contains__(self, i):
            return i in live or hashlib.sha256(i.encode()).hexdigest() in hashed

    public_ids = _Public()
    swapped = {s.feature for s in SUITES if s.name in e2_local.SCORED_ROOT}
    texts = set()
    for s in SUITES:
        roots = [_home(s, root)] + [r for n, r in e2_local.retired_roots(Path(root)) if n == s.name]
        for h in roots:
            for c in e2_local.candidates(s.name, h):
                if c["id"] in public_ids and (c.get("state") or {}).get("text"):
                    texts.add(normalise(c["state"]["text"]))
    held, pinned = Counter(), Counter()
    for bucket in ("private", "review_private"):
        for r in list(out.get(bucket, [])):
            why = ("id" if r.id in public_ids else "text" if normalise(r.state.text) in texts else None)
            if why:
                r.attribute["e2"]["dropped"] = (f"public in release {PUBLISHED_RELEASE['name']} ({why}): a published "
                                                "row is never held out")
                out[bucket].remove(r)
                out.setdefault("dropped_private", []).append(r)
                held[f"{r.feature}/{why}"] += 1
    for bucket in ("dev", "test", "private", "review", "review_private"):
        for r in out.get(bucket, []):
            p = pub.get(r.id)
            if r.feature in swapped or p is None or not p.get("group") or p["group"] == r.group:
                continue
            if str(p["group"]).startswith("nd:") and "loader_group" not in r.attribute["e2"]:
                r.attribute["e2"]["loader_group"] = r.group
            r.group = p["group"]
            pinned[r.feature] += 1
    rep = {"release": PUBLISHED_RELEASE, "held_out_rows_dropped": dict(sorted(held.items())),
           "groups_kept": dict(sorted(pinned.items()))}
    PUBLISHED_REPORT.clear()
    PUBLISHED_REPORT.update(rep)
    return rep


# Which copy of a text shared by two suites stays when the copies sit in different splits. Each suite agent split its
# own rows by group, but a few upstreams reuse each other's prompts (neuralchemy carries XSTest and HarmBench prompts,
# the in-the-wild and jackhhao jailbreak sets carry prompts that are also Aegis rows). The test copy stays, then the
# dev one; the other copy is dropped, so no text is in two splits and the test counts do not move. The private copy
# never wins over a public one: a text that is also a public row is not held out, and keeping it private would make a
# text already in the tracked candidate files part of the private slice.
SPLIT_PRIORITY = ("test", "dev", "private")


def resolve_cross_suite_text(out: dict) -> list:
    """Drop the lower-priority copy of any normalised text that sits in more than one split (review buckets included,
    as they return to their split once ruled on). Dropped rows go to out["dropped"] / out["dropped_private"] with the
    reason in attribute["e2"]["dropped"]. Returns the dropped rows."""
    from .audit import normalise
    home = lambda r: r.attribute["e2"]["proposed_split"]
    by_text = defaultdict(list)
    for bucket in ("dev", "test", "private", "review", "review_private"):
        for r in out.get(bucket, []):
            by_text[normalise(r.state.text)].append((bucket, r))
    drop = []
    for _, items in sorted(by_text.items()):
        splits = {home(r) for _, r in items}
        if len(splits) < 2:
            continue
        keep = next(s for s in SPLIT_PRIORITY if s in splits)
        kept_ids = sorted(r.id for _, r in items if home(r) == keep)
        for bucket, r in items:
            if home(r) != keep:
                # a public file never names a private-slice row
                of = "a private-slice row" if keep == "private" and home(r) != "private" else ", ".join(kept_ids)
                r.attribute["e2"]["dropped"] = f"cross-suite duplicate text of {of} ({keep})"
                drop.append((bucket, r))
    for bucket, r in drop:
        out[bucket].remove(r)
        # a public row dropped because its text is a private-slice row's text is listed privately: the public list
        # would otherwise point at a private text through the dropped row's source id
        private_twin = "a private-slice row" in r.attribute["e2"]["dropped"]
        out["dropped_private" if home(r) == "private" or private_twin else "dropped"].append(r)
    return [r for _, r in drop]


# A near-duplicate cluster that straddles splits moves whole to the public test split. Not to dev, so the test split
# never loses a row to dev. Not to the private slice: a public member's text sits in the tracked candidate files, so a
# private row with a public near-copy is not held out any more, and pulling the public copies into the private slice
# would make a published text and id part of it. Such a private row becomes a public test row instead.
CLUSTER_TARGET = "test"
CLUSTER_BUCKETS = ("dev", "test", "private", "review", "review_private")
_SPLIT_OF = {"dev": ("dev", "public"), "test": ("test", "public"), "private": ("test", "heldout")}


def cluster_near_duplicates(out: dict) -> dict:
    """Join rows that are near-duplicates or share a split group (union-find, across suites), give a cluster of more
    than one group one group, and move every cluster that straddles splits whole into the public test split
    (CLUSTER_TARGET).
    Rows in a review bucket move too: they return to their split once ruled on. Edits ``out`` in place and returns
    {"clusters", "merged_clusters", "straddling_clusters", "moved": {"from->to": n}}."""
    from goldrails_bench.overlap import near_duplicate_pairs, row_shingles
    from .build import group_of
    items = [(b, r) for b in CLUSTER_BUCKETS for r in out.get(b, [])]
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    first_of_group = {}
    for i, (_, r) in enumerate(items):
        union(i, first_of_group.setdefault(group_of(r), i))
    for i, j, _, _ in near_duplicate_pairs([row_shingles(r) for _, r in items]):
        union(i, j)
    comps = defaultdict(list)
    for i in range(len(items)):
        comps[find(i)].append(i)
    home = lambda r: r.attribute["e2"]["proposed_split"]
    moved, merged, straddling, moves = Counter(), 0, 0, []
    for members in comps.values():
        rows = [items[i][1] for i in members]
        groups = sorted({group_of(r) for r in rows})
        if len(groups) > 1:
            merged += 1
            shared = "nd:" + groups[0]
            for r in rows:
                r.attribute["e2"]["loader_group"] = group_of(r)
                r.group = shared
        splits = {home(r) for r in rows}
        if len(splits) < 2:
            continue
        straddling += 1
        target = CLUSTER_TARGET
        for i in members:
            bucket, r = items[i]
            if home(r) == target:
                continue
            moved[f"{home(r)}->{target}"] += 1
            r.attribute["e2"]["moved_from"] = home(r)
            r.attribute["e2"]["proposed_split"] = target
            r.split, r.visibility = _SPLIT_OF[target]
            to = "review" if bucket.startswith("review") else target
            moves.append((bucket, to, r))
    for bucket, to, r in moves:
        out[bucket].remove(r)
        out.setdefault(to, []).append(r)
    return {"clusters": sum(len(m) > 1 for m in comps.values()), "merged_clusters": merged,
            "straddling_clusters": straddling, "moved": dict(sorted(moved.items()))}


def near_duplicate_summary(parts: dict) -> dict:
    """What cluster_near_duplicates did, read back from the row annotations. Counts only: a public report never
    names a row that moved into the private slice."""
    moved = Counter()
    merged = set()
    for bucket in CLUSTER_BUCKETS:
        for r in parts.get(bucket, []):
            e2 = r.attribute["e2"]
            if "moved_from" in e2:
                moved[f"{e2['moved_from']}->{e2['proposed_split']}"] += 1
            if "loader_group" in e2:
                merged.add(r.group)
    return {"rule": "near-duplicate body (goldrails_bench.overlap.row_shingles: text, context turns, source and query; "
                    "word 3-gram Jaccard or containment >= 0.8) or "
                    "shared group joins rows; a cluster in several splits moves whole to the public test split (a private "
                    "row with a public near-copy is not held out, so it becomes a test row)",
            "rows_moved": sum(moved.values()), "moved": dict(sorted(moved.items())), "merged_groups": len(merged)}


# --- writing -------------------------------------------------------------------------------------------------------

def _write_split_files(rows: list, out_dir: Path, split_name: str) -> list:
    files = []
    by_feature = defaultdict(list)
    for r in rows:
        by_feature[r.feature].append(r)
    for feature, rs in sorted(by_feature.items()):
        path = out_dir / f"{feature}.{split_name}.jsonl"
        write_jsonl(rs, path)
        files.append({"path": path.name, "feature": feature, "split": split_name, "n": len(rs), "sha256": dataset_hash(rs)})
    return files


def _review_rows(rows: list) -> list:
    return [{"id": r.id, "suite": r.attribute["e2"]["suite"], "feature": r.feature, "subtask": r.subtask,
             "proposed_split": r.attribute["e2"]["proposed_split"], "first_label": r.expected,
             "second": r.attribute["e2"].get("second"), "disagreement": r.attribute["e2"].get("disagreement"),
             "second_round": r.attribute["e2"].get("second_round"),
             "owner_question": r.attribute["e2"].get("owner_question") or "unruled: not yet in resolutions.jsonl",
             "status": "needs_owner_review"} for r in rows]


def _write_dropped(rows: list, path: Path) -> None:
    path.write_text("".join(json.dumps({"id": r.id, "suite": r.attribute["e2"]["suite"], "subtask": r.subtask,
                                        "proposed_split": r.attribute["e2"]["proposed_split"],
                                        "reason": r.attribute["e2"]["dropped"]}, sort_keys=True) + "\n" for r in rows),
                    encoding="utf-8")


def write_build(parts: dict, out: Path = BUILD) -> dict:
    """Public dev/test files plus manifest in ``out``; the private slice and its disputed rows in ``out/private``.
    The public manifest lists public files only and states the private slice's size, never its files or ids."""
    out = Path(out)
    priv = out / "private"
    out.mkdir(parents=True, exist_ok=True)
    priv.mkdir(parents=True, exist_ok=True)
    for stale in list(out.glob("F*.jsonl")) + list(priv.glob("F*.jsonl")):
        stale.unlink()
    files = _write_split_files(parts.get("dev", []), out, "dev") + _write_split_files(parts.get("test", []), out, "test")
    review = _review_rows(parts.get("review", []))
    (out / "needs-owner-review.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in review),
                                                 encoding="utf-8")
    pfiles = _write_split_files(parts.get("private", []), priv, "test")
    previews = _review_rows(parts.get("review_private", []))
    (priv / "needs-owner-review.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in previews),
                                                  encoding="utf-8")
    _write_dropped(parts.get("dropped", []), out / "dropped.jsonl")
    _write_dropped(parts.get("dropped_private", []), priv / "dropped.jsonl")
    (priv / "manifest.json").write_text(json.dumps({"protocol": PROTOCOL + "::private", "visibility": "heldout",
                                                    "files": pfiles}, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "protocol": PROTOCOL,
        "command": "uv run python -m goldrails_dataset.edition2",
        "status": "candidate: disputes resolved under the owner rulings of 3 October 2026 are applied; the rest await "
                  "the owner; nothing here is frozen or signed",
        "files": files,
        "private_slice": {"rows": sum(f["n"] for f in pfiles), "where": "build/private/ (git-ignored, never published)"},
        "needs_owner_review": {"public": len(review), "private": len(previews), "file": "needs-owner-review.jsonl"},
        "resolved_by_ruling": {"public": sum(r.attribute["e2"]["second_label"] == RESOLVED
                                             for b in ("dev", "test") for r in parts.get(b, [])),
                               "private": sum(r.attribute["e2"]["second_label"] == RESOLVED for r in parts.get("private", [])),
                               "file": "<suite>/resolutions.jsonl"},
        "dropped": {"public": len(parts.get("dropped", [])), "private": len(parts.get("dropped_private", [])),
                    "file": "dropped.jsonl", "rule": "cross-suite duplicate text in another split (test, then private, kept); "
                                             "a test or private row overlapping an examined, ledger or v1 row"},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# --- audit ---------------------------------------------------------------------------------------------------------

def _class_counts(rows: list) -> dict:
    c = defaultdict(Counter)
    for r in rows:
        c[(r.feature, r.subtask)][str(r.expected)] += 1
    return c


def floors(parts: dict) -> dict:
    """Edition 2 floors on the public test split, after disputed rows are taken out. Also reports the same counts
    with the private slice added, and the counts restricted to rows whose second label agreed."""
    test = parts.get("test", [])
    agreed = [r for r in test if r.attribute["e2"]["second_label"] == "agree"]
    pub, both, ok2 = _class_counts(test), _class_counts(test + parts.get("private", [])), _class_counts(agreed)
    cells, shortfalls = [], []
    for (f, s), (need_yes, need_no) in sorted(SCORED.items()):
        rows = [r for r in test if (r.feature, r.subtask) == (f, s)]
        srcs = {lab: sorted({r.provenance.source for r in rows if r.expected == lab}) for lab in ("yes", "no")}
        n_src = len({r.provenance.source for r in rows})
        cell = {"feature": f, "subtask": s, "floor": {"yes": need_yes, "no": need_no},
                "public_test": dict(sorted(pub[(f, s)].items())), "with_private": dict(sorted(both[(f, s)].items())),
                "public_test_second_label_agreed": dict(sorted(ok2[(f, s)].items())),
                "sources": n_src, "sources_by_class": srcs}
        short, exc = [], FLOOR_EXCEPTIONS.get((f, s))
        for lab, need in (("yes", need_yes), ("no", need_no)):
            have = pub[(f, s)].get(lab, 0)
            if have < need:
                miss = {"class": lab, "have": have, "floor": need, "missing": need - have}
                if exc and have >= exc["accepted_public_test"][lab]:
                    cell.setdefault("accepted_shortfalls", []).append({**miss, "ruling": exc["ruling"]})
                    continue
                short.append(miss)
        if cell.get("accepted_shortfalls"):
            cell["exception"] = {"ruling": exc["ruling"], "accepted_public_test": exc["accepted_public_test"],
                                 "disclosure": exc["disclosure"]}
        if n_src < MIN_SOURCES:
            short.append({"sources": n_src, "floor": MIN_SOURCES})
        for lab, need in (("yes", need_yes), ("no", need_no)):
            if need and len(srcs[lab]) < MIN_SOURCES:
                cell.setdefault("warnings", []).append(f"{lab} rows come from {len(srcs[lab])} source(s): {srcs[lab]}")
        cell["pass"] = not short
        cells.append(cell)
        for sh in short:
            shortfalls.append({"feature": f, "subtask": s, **sh})
    accepted = [{"feature": c["feature"], "subtask": c["subtask"], **a} for c in cells
                for a in c.get("accepted_shortfalls", [])]
    return {"floor_rows": TEST_FLOOR, "min_sources": MIN_SOURCES, "cells": cells, "shortfalls": shortfalls,
            "accepted_shortfalls": accepted, "pass": not shortfalls}


def unscored_entities() -> list:
    """Entity types asked but not scored in edition 2: the question set's ``unscored_entities``, else ruling 6."""
    if PII_QUESTION_SET.exists():
        qs = json.loads(PII_QUESTION_SET.read_text(encoding="utf-8"))
        if qs.get("unscored_entities") is not None:
            return sorted(qs["unscored_entities"])
    return sorted(UNSCORED_ENTITIES_DEFAULT)


def entity_floors(parts: dict) -> dict:
    """>= ENTITY_TEST_FLOOR public test positives per scored entity type. An unscored diagnostic type (DRIVER_ID,
    owner ruling 6) is counted and reported but has no floor."""
    asked = json.loads(PII_QUESTION_SET.read_text(encoding="utf-8"))["supported_entities"] if PII_QUESTION_SET.exists() else []
    unscored = unscored_entities()
    supported = [t for t in asked if t not in unscored]
    per = defaultdict(Counter)
    for split in ("dev", "test", "private"):
        for r in parts.get(split, []):
            if r.feature == "F5":
                for t in r.attribute["e2"].get("entity_types", []):
                    per[t][split] += 1
    by_type = {t: dict(sorted(per[t].items())) for t in supported}
    short = [{"entity": t, "have": by_type[t].get("test", 0), "floor": ENTITY_TEST_FLOOR}
             for t in supported if by_type[t].get("test", 0) < ENTITY_TEST_FLOOR]
    authored = Counter(t for r in parts.get("test", []) if r.feature == "F5" and r.provenance.source == "e2_pii_controls"
                       for t in r.attribute["e2"].get("entity_types", []))
    sourced = {t: by_type[t].get("test", 0) - authored.get(t, 0) for t in supported}
    diagnostic = {t: dict(sorted(per[t].items())) for t in asked if t in unscored}
    return {"floor": ENTITY_TEST_FLOOR, "supported_entities": supported, "positives_by_type": by_type,
            "unscored_diagnostic_entities": diagnostic,
            "test_positives_authored": dict(sorted(authored.items())), "test_positives_sourced": sourced,
            "sourced_only_below_floor": sorted(t for t, n in sourced.items() if n < ENTITY_TEST_FLOOR),
            "shortfalls": short, "pass": not short}


AGREEMENT = E2 / "content" / "agreement.json"
SAMPLE_SUITE = "content"        # owner ruling 7: a person second-labels a 400-row stratified sample of this suite
SAMPLE_N = 400


def sample_rows_unchanged(out: Path = BUILD, manifest: Path | None = None) -> bool:
    """True when every row of the drawn sample is still in ``out`` with the split and reference label it was drawn
    with. The manifest lives in the git-ignored ``content/sample/``; without it this is False."""
    manifest = Path(manifest) if manifest else E2 / "content" / "sample" / "manifest.json"
    if not manifest.exists():
        return False
    rows = json.loads(manifest.read_text(encoding="utf-8")).get("rows") or []
    # Owner ruling 32 relabelled or removed some rows most systems got wrong, sampled rows among them. The sample was
    # drawn and labelled against the labels it records, and its agreement rate is a statement about those labels, so a
    # sampled row that ruling 32 changed (a correction in corrections.jsonl, or an exclusion) does not make it stale.
    owner_review = ruling32_ids()
    rows = [r for r in rows if r["id"] not in owner_review]
    cur = {}
    for split in ("dev", "test"):
        p = Path(out) / f"F1.{split}.jsonl"
        if p.exists():
            for line in p.read_text(encoding="utf-8").split("\n"):    # not splitlines: rows hold U+2028
                if line.strip():
                    r = json.loads(line)
                    cur[r["id"]] = (split, r.get("expected"))
    return bool(rows) and all(cur.get(r["id"]) == (r["split"], r["reference"]) for r in rows)


def content_sample_status(out: Path = BUILD, agreement: Path | None = None) -> dict:
    """The ruling 7 human sample as the audit sees it: drawn (``content/agreement.json`` exists with a 400-row design),
    drawn from this build (its F1 dev/test digests match the files in ``out``), and labelled (status complete)."""
    agreement = Path(agreement) if agreement else AGREEMENT
    if not agreement.exists():
        return {"drawn": False, "fresh": False, "labelled": False, "status": "not drawn",
                "fix": "uv run python -m goldrails_dataset.content_sample draw"}
    doc = json.loads(agreement.read_text(encoding="utf-8"))
    des = doc.get("design") or {}
    digests = {}
    for name in sorted(des.get("build_files") or {}):
        p = Path(out) / name
        digests[name] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    fresh = bool(digests) and digests == des.get("build_files")
    unchanged = None if fresh else sample_rows_unchanged(out, agreement.parent / "sample" / "manifest.json")
    if unchanged:     # the build changed only outside the sample: every sampled row keeps its split and label
        fresh = True
    labelled = doc.get("status") == "complete" and bool(doc.get("result"))
    status = ("labelled" if labelled else "pending human labels") if fresh else "stale: drawn from an earlier build"
    if unchanged:
        status += " (build changed outside the sample; all sampled rows unchanged)"
    rep = {"drawn": des.get("n") == SAMPLE_N, "fresh": fresh, "labelled": labelled, "status": status,
           "agreement_file": "dataset/edition2/content/agreement.json", "n": des.get("n"),
           "population_rows": des.get("population_rows"), "agreement_status": doc.get("status")}
    if labelled:
        rep["agreement"] = (doc["result"].get("overall") or {}).get("agreement_population_weighted")
    if not fresh:
        rep["fix"] = "uv run python -m goldrails_dataset.content_sample draw"
    return rep


# Owner ruling 28: the prompt-attack suite's review is a sealed AI second label of its 400-row blind packet, disclosed
# as an AI second label, not human review. It covers the rows without a per-row blind second label.
AI_SECOND_LABEL = {"prompt_attacks": E2 / "r26" / "prompt_attacks" / "label-agreement.json"}
AI_SAMPLE_N = 400


def ai_second_label_status(suite: str) -> dict:
    p = AI_SECOND_LABEL[suite]
    doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    ov = doc.get("overall") or {}
    ok = ov.get("n") == AI_SAMPLE_N and ov.get("agreement") is not None
    return {"ruling": 28, "ai_second_label": {"file": str(p.relative_to(REPO)), "n": ov.get("n"),
                                              "agreement": ov.get("agreement"), "kappa": ov.get("kappa"),
                                              "disclosure": doc.get("disclosure")},
            "pass": ok, **({} if ok else {"fix": "label the 400-row packet (ruling 28) and commit its agreement"})}


def second_label_coverage(parts: dict, sample: dict | None = None) -> dict:
    """Blind second-label coverage per suite. Every suite needs a second label on every row, except content: under
    owner ruling 7 its second label is the human sample, so a content row without a blind second label is covered
    when the sample is drawn from this build (``sample``, content_sample_status). The sample's labels are a
    publication blocker, not a build gate."""
    by = defaultdict(Counter)
    for split, rows in parts.items():
        if split.startswith("dropped"):
            continue
        for r in rows:
            by[r.attribute["e2"]["suite"]][r.attribute["e2"]["second_label"]] += 1
    out = {}
    for suite, c in sorted(by.items()):
        n = sum(c.values())
        compared = c["agree"] + c["disagree"] + c[RESOLVED]
        out[suite] = {"rows": n, "agree": c["agree"], "disagree": c["disagree"], "resolved_by_ruling": c[RESOLVED],
                      "missing": c["missing"], "agreement": round(c["agree"] / compared, 4) if compared else None}
        if suite in AI_SECOND_LABEL and c["missing"]:
            out[suite]["missing_covered_by"] = ai_second_label_status(suite)
        if suite == SAMPLE_SUITE and c["missing"]:
            ok = bool(sample and sample.get("drawn") and sample.get("fresh"))
            out[suite]["missing_covered_by"] = {"ruling": 7, "human_sample": (sample or {}).get("status", "not drawn"),
                                                "pass": ok}
    passed = all(v["missing"] == 0 or v.get("missing_covered_by", {}).get("pass") for v in out.values())
    return {"by_suite": out, "pass": passed, "content_human_sample": sample,
            "rule": "every row needs a blind second label before the owner review; disputed rows leave the splits "
                    "until an owner ruling resolves them; content is covered by the ruling 7 human sample, drawn "
                    "from this build (its labels block publication, not the build)"}


def publication(report: dict, parts: dict) -> dict:
    """Whether this build may be published. It may not while the build fails, a disputed row waits for the owner, or
    the ruling 7 content sample is not labelled (``content/agreement.json`` status complete)."""
    blockers = []
    if report.get("status") != "pass":
        blockers.append(f"build status {report.get('status')}: {', '.join(report.get('failed') or [])}")
    waiting = {"public": len(parts.get("review", [])), "private": len(parts.get("review_private", []))}
    if sum(waiting.values()):
        blockers.append(f"{waiting['public']} public and {waiting['private']} private disputed rows await the owner "
                        "(needs-owner-review.jsonl)")
    sample = report["second_label"].get("content_human_sample") or {}
    if not sample.get("labelled"):
        blockers.append(f"content human second-label sample (ruling 7): {sample.get('status', 'not drawn')}; "
                        "publish the agreement rate first")
    return {"ready": not blockers, "blockers": blockers, "awaiting_owner": waiting}


def gate_audit(out: Path = BUILD) -> dict:
    """The v1 audit's gates, run on the public build directory."""
    from .audit import DEFAULT_EXAMINED, audit
    rep = audit(Path(out), DEFAULT_EXAMINED)
    return {"status": rep["status"], "failed_gates": rep["failed_gates"],
            "gates": {g: rep["checks"][g]["pass"] for g in rep["gates"] if g in rep["checks"]},
            "details": {g: {k: v for k, v in rep["checks"][g].items() if k in ("straddling", "in_test", "items", "invalid",
                                                                           "split_or_feature_mismatch", "files")}
                        for g in rep["failed_gates"] if g in rep["checks"]},
            "warnings": [w for w in rep["warnings"] if w["kind"] in ("duplicate_text_within_split", "non_english_suspects",
                                                                     "single_class_test_subtask")]}


# --- shortcut gate --------------------------------------------------------------------------------------------------

def _shortcut_rows(rows: list) -> list:
    """Built prompt-attack records as the shortcut module's row dicts. Counts only leave this module."""
    out = []
    for r in rows:
        if r.feature != "F2":
            continue
        try:
            n = json.loads(r.provenance.notes or "{}")
        except ValueError:
            n = {}
        d = {"id": r.id, "subtask": r.subtask, "label": r.expected, "source": r.provenance.source,
             "group": r.group or r.id,
             "state": {"text": r.state.text, "context": r.state.context or [], "tool_call": r.state.tool_call}}
        if n.get("stratum"):                 # ruling 25: a row may say it is authored or external
            d["stratum"] = n["stratum"]
        if isinstance(n.get("gate_facets"), dict):
            d["facets"] = {k: v for k, v in n["gate_facets"].items() if v is not None}
        if isinstance(n.get("gate_nuisance"), dict):     # ruling 26: platform, template, payload position and span
            d["nuisance"] = n["gate_nuisance"]
        out.append(d)
    return out


def _gate_rows(parts: dict) -> list:
    return [dict(r, proposed_split=split) for split in ("dev", "test", "private")
            for r in _shortcut_rows(parts.get(split, []))]


_CELL_RULE = (f"BA <= {SHORTCUT_BA_MAX} and AUROC <= {SHORTCUT_AUROC_MAX} (direction-free), computed, and not a "
              "constant prediction (a fit that scores every row alike failed; it is not a pass)")
_AUDIT_VIEW = {"in_sample_public_test": "public_test", "in_sample_test_with_private": "test_with_private"}


def shortcut_audit(parts: dict, use_sklearn: bool | None = None) -> dict:
    """The in-sample half of the shortcut gate, on the built rows (after disputes, exclusions, clustering and drops):
    every baseline of ``e2_prompt_attacks_shortcuts`` (source id, keyword regex, length, L2 char 2-5-gram and word
    1-2-gram logistic regression with C chosen by grouped inner CV), fitted ones with grouped five-fold CV, on the
    public test split and on the test split with the unpublished slice when that slice is present. Every cell must
    meet ``_CELL_RULE``; a baseline that could not be computed (scikit-learn missing, a subtask with one class) fails."""
    from .sources import e2_prompt_attacks_shortcuts as sc
    rep = sc.gate_report(_gate_rows(parts), use_sklearn, sc.IN_SAMPLE_VIEWS)
    rename = lambda s: next((s.replace(k, v, 1) for k, v in _AUDIT_VIEW.items() if s.startswith(k)), s)   # noqa: E731
    return {"rule": f"every baseline per prompt-attack subtask in sample (grouped five-fold CV): {_CELL_RULE}",
            "baselines": list(SHORTCUT_BASELINES), "views": {_AUDIT_VIEW[k]: v for k, v in rep["views"].items()},
            "table": [dict(t, view=_AUDIT_VIEW[t["view"]]) for t in rep["table"]],
            "failures": [rename(f) for f in rep["failures"]], "pass": rep["pass"]}


def shortcut_heldback(parts: dict, use_sklearn: bool | None = None) -> dict:
    """The held-back half of the shortcut gate, on the built rows: every baseline fitted on rows it then does not
    score (``e2_prompt_attacks_shortcuts.HELDBACK_VIEWS``): seeded group halves of test and unpublished, both ways;
    dev to the public test split; dev to the unpublished slice (where source id on injection reached AUROC 0.796 on
    3 October); test and unpublished to dev; dev and 70% of the test and unpublished groups to the other 30%. Every
    cell must meet ``_CELL_RULE``. ``constant_prediction`` lists the cells whose fit predicted one score: failures."""
    from .sources import e2_prompt_attacks_shortcuts as sc
    rep = sc.heldback_report(_gate_rows(parts), use_sklearn)
    constant = [f"{t['view']}/{t['subtask']}/{t['baseline']}" for t in rep["table"] if t["constant_prediction"]]
    return {"rule": f"every baseline per prompt-attack subtask fitted on built rows it does not score: {_CELL_RULE}",
            "seed": rep["seed"], "seeds": rep["seeds"], "view_notes": rep["view_notes"], "views": rep["views"],
            "table": rep["table"], "constant_prediction": constant, "failures": rep["failures"], "pass": rep["pass"]}


def shortcut_strata(parts: dict, use_sklearn: bool | None = None) -> dict:
    """Owner ruling 25: the baselines per stratum (authored, external) and per source large enough to fit, in sample
    and held back, plus the stratum checks (``e2_prompt_attacks_shortcuts.strata_report``). Every cell must pass."""
    from .sources import e2_prompt_attacks_shortcuts as sc
    rep = sc.strata_report(_gate_rows(parts), use_sklearn)
    rep["rule"] = f"every baseline per stratum and per source, every view: {_CELL_RULE}; plus the stratum checks"
    return rep


def shortcut_gate(parts: dict, use_sklearn: bool | None = None) -> dict:
    """The prompt-attack shortcut gate: the in-sample view (``shortcut_audit``), the held-back views
    (``shortcut_heldback``) and, from owner ruling 25, the per-stratum and per-source views (``shortcut_strata``) must
    all pass, every cell of them."""
    ins, held = shortcut_audit(parts, use_sklearn), shortcut_heldback(parts, use_sklearn)
    strata = shortcut_strata(parts, use_sklearn)
    return {"rule": "all three pass: in sample (grouped five-fold CV on the built test split, and with the unpublished "
                    "slice), held back (fitted on built rows it does not score), and per stratum and per source "
                    "(ruling 25), every cell: " + _CELL_RULE,
            "in_sample": ins, "heldback": held, "strata": strata,
            "table": [dict(t, half="in_sample") for t in ins.get("table", [])]
                     + [dict(t, half="heldback") for t in held.get("table", [])],
            "failures": [f"in_sample/{f}" for f in ins["failures"]] + [f"heldback/{f}" for f in held["failures"]]
                        + [f"strata/{f}" for f in strata["failures"]],
            "pass": ins["pass"] and held["pass"] and strata["pass"]}


# --- owner ruling 26: the confounds-only gate is the prompt-attack acceptance test -----------------------------------

CONTRACT = REPO / "benchmark" / "contracts" / "v2.0.json"


def gate_summary(gate: dict) -> dict:
    """The shortcut gate in the few numbers a reader needs: per subtask and half (in sample, held back), the highest
    BA and AUROC of any baseline in any view and where each came from, and the failing cell counts."""
    out = {"in_sample_pass": bool((gate.get("in_sample") or {}).get("pass")),
           "heldback_pass": bool((gate.get("heldback") or {}).get("pass")),
           "cells": len(gate.get("table") or []),
           "failing_cells": sum(not t["pass"] for t in gate.get("table") or []), "max": {}}
    for t in gate.get("table") or []:
        cell = out["max"].setdefault(t["subtask"], {}).setdefault(t["half"], {})
        for m in ("ba", "auroc"):
            if t[m] > cell.get(m, -1):
                cell[m], cell[f"{m}_at"] = t[m], f"{t['view']}/{t['baseline']}"
    out["max"] = {sub: dict(sorted(v.items())) for sub, v in sorted(out["max"].items())}
    if "strata" in gate:          # owner ruling 25: per stratum and per source
        st = gate["strata"]
        out["strata_pass"] = bool(st.get("pass"))
        out["strata_cells"] = len(st.get("table") or [])
        out["strata_failures"] = len(st.get("failures") or [])
    return out


def prompt_attack_gate(parts: dict, use_sklearn: bool | None = None, controls: bool = True) -> dict:
    """Owner ruling 26: the confounds-only gate (``e2_prompt_attacks_confounds.gate_report``) on the built prompt-attack
    rows, every subtask, stratum, source and facet, with the planted-signal and label-permutation controls and the
    full-text n-gram baselines (reported, not pass/fail). The build accepts prompt attacks only when it passes; there
    is no provisional path (rulings 23 and 26)."""
    from .sources import e2_prompt_attacks_confounds as cg
    rep = cg.gate_report(_gate_rows(parts), use_sklearn, controls=controls)
    rep["summary"] = cg.summary(rep)
    return rep


# --- the shortcut gate's full table, written to prompt_attacks/gate-heldback.json -------------------------------------

HELDBACK = E2 / "prompt_attacks" / "gate-heldback.json"


def gate_heldback(parts: dict, use_sklearn: bool | None = None) -> dict:
    """Every cell of the shortcut gate (subtask x baseline x view, in sample and held back) on the built rows, for
    ``gate-heldback.json``. The contrast round of 3 October retired 950 rows that the gate's old L1 char n-gram model,
    fitted on the projected test and test-with-unpublished views, scored most confidently correct (``retired.json``),
    so the in-sample views are measured on rows that survived that filter; dev was never ranked. Counts and metrics
    only. Does not change the build."""
    from .sources import e2_prompt_attacks_shortcuts as sc
    rep = sc.gate_report(_gate_rows(parts), use_sklearn)
    return {
        "what": "the prompt-attack shortcut gate, every subtask x baseline x view: in sample and on rows each "
                "baseline was not fitted on",
        "command": "uv run --with scikit-learn python -m goldrails_dataset.edition2 gate-heldback",
        "rule": _CELL_RULE,
        "bounds": rep["bounds"], "baselines": rep["baselines"], "c_grid": rep["c_grid"],
        "inner_folds": rep["inner_folds"], "seeds": rep["seeds"],
        "retired_rows": len(_retired_ids()),
        "views": rep["view_notes"],
        "note": "private in a view name is the unpublished slice (owner ruling 15): rows held out of the public files "
                "that can be reconstructed from public upstream data. Test and unpublished rows were in the pool the "
                "3 October retirement ranking scored, so only dev was never ranked.",
        "results": rep["views"], "table": rep["table"], "over_bounds": rep["failures"], "pass": rep["pass"]}

def _retired_ids() -> set:
    from .sources.e2_prompt_attacks_build import retired_rows
    return set(retired_rows())


# --- overlap -------------------------------------------------------------------------------------------------------

def main_checkout() -> Path | None:
    """The main checkout of this repository when running in a git worktree (the v1 release builds are git-ignored and
    live there). Read only."""
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=REPO, capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    p = (REPO / common).resolve().parent
    return p if p != REPO.resolve() else None


def v1_row_files(extra_roots=()) -> list:
    roots = [REPO] + [Path(r) for r in extra_roots]
    main = main_checkout()
    if main:
        roots.append(main)
    files = []
    for root in roots:
        files += sorted(glob.glob(str(root / "dataset" / "release" / "*" / "build" / "*.jsonl")))
    files += sorted(glob.glob(str(REPO / "dataset" / "samples" / "**" / "*.jsonl"), recursive=True))
    return files


def _rows_of(files: list) -> list:
    rows = []
    for f in files:
        rows += _jsonl(Path(f))
    return rows


def ledger_row_ids(root: Path = REPO / "benchmark" / "results") -> set:
    """Every row id in any results ledger (first and second benchmark included): those rows were sent to a model."""
    ids = set()
    for f in sorted(Path(root).rglob("*.jsonl")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    rid = json.loads(line).get("id")
                except (json.JSONDecodeError, AttributeError):
                    continue
                if isinstance(rid, str):
                    ids.add(rid)
    from goldrails_bench.overlap import prior_use
    return ids | prior_use("results_ledgers")


def _external_references(extra_roots=()) -> tuple[dict, list, list]:
    """The references outside edition 2: rows already examined, sent to a model or released in v1."""
    from goldrails_bench import overlap
    files = v1_row_files(extra_roots)
    v1 = _rows_of(files)
    refs = {"examined_smoke_pilot": sorted(overlap.repo_examined_ids()), "results_ledgers": sorted(ledger_row_ids()),
            "v1_builds_and_samples": v1}
    return refs, v1, files


def drop_reference_overlaps(parts: dict, extra_roots=()) -> dict:
    """Take out of the test and private splits (and their review buckets, which return to those splits) every row
    that overlaps a row outside edition 2 by id, text, group or near-duplicate text: a row someone already examined,
    a row in a results ledger, a v1 release row. Such a row cannot be scored blind. Dropped rows go to
    parts["dropped"] / parts["dropped_private"]; a public reason names the v1 or ledger row (both public), a private
    row is never named in a public file. Returns counts by kind."""
    from goldrails_bench import overlap
    refs, v1, _ = _external_references(extra_roots)
    kinds = Counter()
    for buckets, dropped in ((("test", "review"), "dropped"), (("private", "review_private"), "dropped_private")):
        for bucket in buckets:
            rows = parts.get(bucket, [])
            rep = overlap.check(rows, refs, pool=v1, strict=False)
            hits = defaultdict(list)
            for o in rep.overlaps:
                hits[o["test_id"]].append(o)
            if not hits:
                continue
            for r in [r for r in rows if r.id in hits]:
                first = sorted(hits[r.id], key=lambda o: ("id", "text", "group", "near").index(o["kind"]))[0]
                kinds[first["kind"]] += 1
                r.attribute["e2"]["dropped"] = (f"overlaps a row outside edition 2 ({first['kind']}, {first['role']}: "
                                                f"{first['reference_id']})")
                rows.remove(r)
                parts.setdefault(dropped, []).append(r)
    for rows in parts.values():
        rows.sort(key=lambda r: (r.feature, r.subtask, r.id))
    return dict(sorted(kinds.items()))


def overlap_check(parts: dict, strict: bool = True, extra_roots=()) -> dict:
    """Strict overlap check (goldrails_bench.overlap) of the public test and private rows. Raises OverlapError in
    strict mode; the caller records the report either way."""
    from goldrails_bench import overlap
    refs, v1, files = _external_references(extra_roots)
    refs = {**refs, "e2_dev": parts.get("dev", [])}
    public = overlap.check(parts.get("test", []), refs, pool=v1, strict=False)
    private = overlap.check(parts.get("private", []), {**refs, "e2_public_test": parts.get("test", [])}, pool=v1, strict=False)
    shown = sorted({("<main-checkout>/" + str(Path(f).resolve().relative_to(main_checkout()))) if main_checkout() and
                    Path(f).resolve().is_relative_to(main_checkout()) else str(Path(f).resolve().relative_to(REPO.resolve()))
                    for f in files})
    rep = {"strict": strict, "reference_files": shown,
           "v1_build_files_found": sum("/release/" in f for f in shown),
           "public_test": public.to_dict(), "private": {k: v for k, v in private.to_dict().items() if k != "overlaps"},
           "pass": public.ok and private.ok and any("/release/" in f for f in shown)}
    if not rep["v1_build_files_found"]:
        rep["error"] = "no v1 release build found: the check against v1 cannot run, so it fails"
    rep["private"]["overlapping_ids_count"] = len(private.test_ids())
    if strict and not rep["pass"]:
        bad = public if not public.ok else private
        raise overlap.OverlapError(bad)
    return rep


# --- entry point ---------------------------------------------------------------------------------------------------

def build_parts(root: Path = E2, drop_overlaps: bool = True) -> tuple[dict, dict | None]:
    """The rows the build writes: assemble(), then (unless turned off for a quick test) every test or private row
    that overlaps an examined, ledger or v1 row dropped. Returns (parts, drop counts or None)."""
    parts = assemble(root)
    return parts, (drop_reference_overlaps(parts) if drop_overlaps else None)


def run(out: Path = BUILD, root: Path = E2, strict: bool = False, skip_overlap: bool = False,
        use_sklearn: bool | None = None) -> dict:
    parts, reference_drops = build_parts(root, drop_overlaps=not skip_overlap)
    manifest = write_build(parts, out)
    report = {
        "protocol": PROTOCOL,
        "command": "uv run python -m goldrails_dataset.edition2",
        "manifest": {k: manifest[k] for k in ("private_slice", "needs_owner_review")},
        "split_rows": {k: len(v) for k, v in sorted(parts.items())},
        "gates": gate_audit(out),
        "floors": floors(parts),
        "pii_entity_floors": entity_floors(parts),
        "second_label": second_label_coverage(parts, content_sample_status(out)),
        "near_duplicates": near_duplicate_summary(parts),
        "reference_overlap_drops": reference_drops,
        "published_release": dict(PUBLISHED_REPORT) or None,
        "prompt_attack_gate": prompt_attack_gate(parts, use_sklearn),
    }
    if skip_overlap:
        report["overlap"] = {"skipped": True, "pass": None,
                             "note": "the overlap check was skipped, so it is not a pass and the build fails"}
    else:
        report["overlap"] = overlap_check(parts, strict=False)
    checks = {"gates": report["gates"]["status"] == "pass", "floors": report["floors"]["pass"],
              "pii_entity_floors": report["pii_entity_floors"]["pass"], "second_label": report["second_label"]["pass"],
              "overlap": report["overlap"]["pass"] is True,        # skipped (None) is not a pass
              # ruling 26: the confounds-only gate; no provisional acceptance (rulings 23 and 26)
              "prompt_attack_gate": report["prompt_attack_gate"]["pass"] is True}
    report["status"] = "pass" if all(checks.values()) else "fail"
    report["failed"] = sorted(k for k, v in checks.items() if not v)
    report["publication"] = publication(report, parts)
    (Path(out) / "audit-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if Path(out).resolve() == BUILD.resolve() and Path(root).resolve() == E2.resolve():
        from . import e2_owner_review
        report["owner_review_page"] = e2_owner_review.write_html(REVIEW_PAGE, root, parts)
        e2_owner_review.write_summary(out / "OWNER-REVIEW.md", root, parts)
    if strict and not report["overlap"].get("skipped") and not report["overlap"]["pass"]:
        overlap_check(parts, strict=True)      # raises OverlapError with the report attached
    return report


REVIEW_PAGE = BUILD / "private" / "review.html"


def _subcommand(argv: list) -> int | None:
    """``import-owner-review FILE [--no-build]``, ``owner-review-html``, ``ruling5`` or ``gate-heldback``; None when
    ``argv`` is the plain build."""
    if not argv or argv[0] not in ("import-owner-review", "owner-review-html", "ruling5", "ruling32", "gate-heldback"):
        return None
    from . import e2_owner_review
    cmd, rest = argv[0], argv[1:]
    if cmd == "import-owner-review":
        ap = argparse.ArgumentParser(prog="edition2 import-owner-review",
                                     description="apply the review page's exported decisions, then rebuild")
        ap.add_argument("file")
        ap.add_argument("--no-build", action="store_true", help="write the resolutions only")
        a = ap.parse_args(rest)
        rep = e2_owner_review.import_decisions(Path(a.file))
        print(f"applied {rep['applied']} owner decisions {rep['by_suite']} ({rep['undecided_lines']} undecided lines skipped)")
        if a.no_build:
            return 0
        return main([])
    if cmd == "owner-review-html":
        parts, _ = build_parts()
        rep = e2_owner_review.write_html(REVIEW_PAGE, E2, parts)
        print(json.dumps(rep, indent=1))
        return 0
    if cmd == "ruling32":
        rep = ruling32_apply(_jsonl(Path(rest[0])))
        print(json.dumps(rep, indent=1))
        return 0
    if cmd == "ruling5":
        rep = ruling5_corrections()
        counts = write_corrections("pii", rep["lines"])
        flips = sum(d["final_label"] != d["first_label"] for d in rep["lines"])
        print(f"ruling 5 on undisputed PII rows: {len(rep['lines'])} rows lose ADDRESS ({counts}), {flips} become "
              f"benign; {len(rep['disputed'])} disputed rows are ruled in resolutions.jsonl")
        return 0
    parts, _ = build_parts()
    rep = gate_heldback(parts)
    HELDBACK.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {HELDBACK.relative_to(REPO)}; over bounds: {rep['over_bounds'] or 'none'}")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    sub = _subcommand(argv)
    if sub is not None:
        return sub
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(BUILD))
    ap.add_argument("--strict", action="store_true", help="exit 1 when any gate, floor or the overlap check fails")
    ap.add_argument("--skip-overlap", action="store_true", help="skip the overlap check (tests; never for a freeze)")
    ap.add_argument("--require-publishable", action="store_true",
                    help="exit 1 unless the build may be published (no dispute left, content sample labelled)")
    args = ap.parse_args(argv)
    rep = run(Path(args.out), strict=False, skip_overlap=args.skip_overlap)
    print(f"edition 2 build {rep['status']}: failed {rep['failed'] or 'none'}; rows {rep['split_rows']}")
    for sh in rep["floors"]["shortfalls"]:
        print(f"  floor shortfall {sh}")
    for sh in rep["pii_entity_floors"]["shortfalls"]:
        print(f"  entity shortfall {sh}")
    nd = rep["near_duplicates"]
    print(f"  near-duplicate clusters: {nd['rows_moved']} rows moved split {nd['moved']}, {nd['merged_groups']} merged groups")
    for suite, c in rep["second_label"]["by_suite"].items():
        print(f"  second label {suite}: {c}")
    pg = rep["prompt_attack_gate"]["summary"]
    print(f"  prompt-attack confounds gate (ruling 26): {'pass' if pg['pass'] else 'FAIL'} ({pg['failing_cells']} of "
          f"{pg['cells']} cells fail; controls {'pass' if pg['controls_pass'] else 'FAIL'})")
    for sub, c in pg["max_whole"].items():
        print(f"    {sub}: max BA {c['ba']} ({c['ba_at']}), max AUROC {c['auroc']} ({c['auroc_at']})")
    if rep["overlap"].get("skipped"):
        print("  overlap: skipped (not a pass)")
    else:
        print(f"  overlap: public {rep['overlap']['public_test']['counts']}, private overlapping "
              f"{rep['overlap']['private']['overlapping_ids_count']}")
    pub = rep["publication"]
    print(f"  publication: {'ready' if pub['ready'] else 'blocked'}")
    for b in pub["blockers"]:
        print(f"    - {b}")
    if args.require_publishable and not pub["ready"]:
        return 1
    return 1 if args.strict and rep["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
