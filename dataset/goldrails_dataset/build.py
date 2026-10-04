"""Assemble a Gold Rails sample: load sources, drop excluded rows, dedup on
normalised text, stratify per (feature, subtask, expected), split tune/test,
write jsonl and a manifest with one hash per file.

    uv run python -m goldrails_dataset.build --out dataset/samples/pilot --per-cell 25 --seed 7
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from .records import dataset_hash, write_jsonl
from .sources import SOURCES

PILOT_PLAN = {
    # (feature, subtask): sources that feed it
    ("F1", "input"): ["ailuminate_demo", "aegis2", "openai_moderation"],
    ("F1", "output"): ["aegis2"],
    ("F1", "over_refusal"): ["orbench"],
    ("F1", "harmful_goal"): ["jailbreakbench"],     # plain harmful/benign requests, no attack technique
    ("F2", "injection"): ["deepset_injections", "f2_controls"],
    ("F2", "leakage"): ["gandalf", "f2_controls"],   # Gandalf is positives only; authored controls supply the negatives
    ("F2", "jailbreak"): ["jbb_artifacts", "f2_controls"],   # real attack prompts as positives; authored controls as negatives
    ("F5", "pii"): ["ai4privacy", "f5_controls"],       # positives from the source; PII-free negatives are authored controls
    ("F3", "topic"): ["f3_controls", "f3_test_candidates"],   # authored; scored only after independent human review
    ("F4", "word"): ["f4_words"],                       # deterministic, from words.json
    ("F4", "profanity"): ["civil_comments_profanity"],   # real comments; scored only after human review against the definition
    ("F4", "profanity_obfuscated"): ["civil_comments_profanity"],   # diagnostic: masked spellings, never in the suite score
    ("F6", "grounding"): ["ragtruth"],                  # human-annotated hallucination spans
    ("F7", "b1_disparate_fpr"): ["civil_comments_identity"],   # cutoffs per docs/21: toxic >= 0.5, benign < 0.2, mention >= 0.5
    ("F7", "b3_decision"): ["discrim_eval", "bbq"],            # decision-model bias; Bedrock not applicable (docs/21)
    ("F7", "b2_counterfactual"): ["bias_pairs_reviewed"],    # only pairs two reviewers kept with one shared action
    # LLMail indirect joins only if its readiness check passes
}


# Bounded reads for large sources at sample scale; the release build sets these from the size decision in docs/22.
LOAD_KWARGS = {"civil_comments_identity": {"row_groups": list(range(0, 40))}}


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def dedup(records):
    seen, out = set(), []
    for r in records:
        key = normalise(r.state.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


EXAMINED = Path(__file__).resolve().parents[1] / "frozen" / "examined-ids.txt"


CLEARANCES = EXAMINED.parent / "examined-clearances.jsonl"


def cleared_ids() -> set:
    """Examined ids later cleared for test, each with a written reason and evidence (examined-clearances.jsonl). A
    clearance covers rows that were only read to annotate or quality-check them, never sent to a model under test or
    used to write questions or fit thresholds. The examined list itself is never edited, so the history stays."""
    if not CLEARANCES.exists():
        return set()
    out = set()
    for line in CLEARANCES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d.get("cleared_for") == "test" and d.get("reason"):
                out.add(d["id"])
    return out


def examined_ids() -> set:
    """Rows a person or a pilot run has already looked at, less documented clearances. They may be tuning rows; they
    are never test rows again."""
    if not EXAMINED.exists():
        return set()
    seen = {l.strip() for l in EXAMINED.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    return seen - cleared_ids()


def group_of(r) -> str:
    """Rows that must land in the same split: an Aegis prompt and its response share the conversation id."""
    if r.provenance.source == "aegis2":
        return f"aegis2:{r.provenance.source_id.split(':')[0]}"
    return r.group or r.id      # keep the loader's group (RAGTruth document, JBB behaviour, LLMail team, bias pair)


AUTHORED = ("f2_controls", "f3_controls", "f5_controls", "f2_indirect_controls", "f3_controls_v2", "f3_test_candidates",
            # edition 2: written by an AI first labeller; scored only after the blind second label and the owner
            "e2_attack_controls", "e2_denied_topics", "e2_pii_controls")
# Sources whose rows are scored only on a final human label, which replaces the draft label when they differ.
# Edition 2 adds the sources whose labels came from a model or from a noisy tag the first labeller disputed:
# OASST2 topic labels (first labeller), RAGBench (GPT-4 labels), FaithDial (46% of Hallucination tags not clearly
# unsupported, dataset/edition2/grounding/SOURCES.md).
REVIEW_GATED = AUTHORED + ("civil_comments_profanity", "e2_oasst2", "ragbench", "faithdial")

# Edition 2 cells and the sources that feed them (docs/benchmark/26-edition-2-plan.md). Edition 2 does not go through
# build(): each suite's dataset/edition2/<suite>/candidates.jsonl is already selected, grouped and split, and
# goldrails_dataset.edition2 assembles them. Re-sampling with build() would undo the first labeller's drops and the
# length matching. Provenance source names, not registry keys (e2_pii_nemotron rows keep source nemotron_pii).
E2_PLAN = {
    ("F1", "input"): ["aegis2", "openai_moderation", "ailuminate_demo", "e2_content_aegis2_test"],
    # 5 October 2026: e2_content_aegis2_val left (pplx-decider-v1-27b tunes on the Aegis validation split)
    ("F1", "output"): ["e2_content_beavertails", "e2_content_harmbench_cls"],
    ("F1", "harmful_goal"): ["e2_content_harmbench", "e2_content_xstest", "e2_content_orbench80k"],
    ("F1", "over_refusal"): ["orbench", "e2_content_orbench80k"],
    ("F2", "injection"): ["deepset_injections_test", "yanis_prompt_injections", "neuralchemy_injection", "notinject",
                          "e2_attack_controls", "itw_jailbreak_prompts"],
    ("F2", "jailbreak"): ["jackhhao_jailbreak", "itw_jailbreak_prompts", "neuralchemy_injection",
                          "yanis_prompt_injections", "e2_attack_controls"],
    ("F2", "leakage"): ["lakera_mosscap", "lakera_gandalf_summarization", "yanis_prompt_injections",
                        "neuralchemy_injection", "e2_attack_controls", "itw_jailbreak_prompts"],
    ("F3", "topic"): ["e2_denied_topics", "e2_oasst2"],
    ("F4", "profanity"): ["e2_profanity_civil_comments", "e2_profanity_rtp", "e2_profanity_oasst2"],
    ("F5", "pii"): ["nemotron_pii", "gretel_pii_en", "gretel_pii_finance", "e2_pii_controls"],
    ("F6", "grounding"): ["faithdial", "summedits", "ragbench"],
}
# Tuning share per (feature, subtask) where the plan fixes one; 15% elsewhere. Profanity: 40 tuning, 160 test.
TUNE_SHARE = {("F4", "profanity"): 0.20}
REVIEWS = Path(__file__).resolve().parents[1] / "frozen" / "reviews.jsonl"


def reviewed_ids() -> set:
    """Rows a person validated independently of model outputs: dataset/frozen/reviews.jsonl, one JSON object per line
    with id, reviewer, label, and agreement or adjudication for ambiguous rows. Only rows whose final label equals the
    record's expected label count as reviewed; a disagreement leaves the row a candidate until it is fixed."""
    if not REVIEWS.exists():
        return set()
    out = set()
    for line in REVIEWS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d.get("final") is True:
                out.add((d["id"], str(d.get("label"))))
    return out


def final_reviews() -> dict:
    """Record id -> final review row (denied topics, profanity and other single-row packets; B2 pairs have their own
    loader)."""
    if not REVIEWS.exists():
        return {}
    out = {}
    for line in REVIEWS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d.get("final") is True and d.get("packet") != "b2":
                out[d["id"]] = d
    return out


def apply_reviews(records: list, finals: dict) -> dict:
    """Final human labels on review-gated rows: the label replaces the draft (the draft is kept in the notes); an
    agreed exclusion drops the row with its reason; anything unreviewed or unresolved stays a candidate. Returns
    counts for the release notes."""
    n = defaultdict(int)
    for r in records:
        if r.provenance.source not in REVIEW_GATED:
            continue
        f = finals.get(r.id)
        if f is None:
            r.review_status = "candidate"
            n["unreviewed_or_unresolved"] += 1
            continue
        if f.get("excluded"):
            r.provenance.exclude_reason = f"review: excluded ({f.get('basis')}; {json.dumps(f.get('notes'))})"
            r.review_status = "candidate"
            n["excluded_by_review"] += 1
            continue
        if f.get("label") not in r.labels:
            r.review_status = "candidate"
            n["unresolved"] += 1
            continue
        try:
            notes = json.loads(r.provenance.notes) if r.provenance.notes and r.provenance.notes.startswith("{") else {"notes": r.provenance.notes}
        except json.JSONDecodeError:
            notes = {"notes": r.provenance.notes}
        notes.update({"draft_expected": r.expected, "review": {k: f.get(k) for k in ("basis", "reviewers", "review_id")}})
        if f["label"] != r.expected:
            n["draft_label_replaced"] += 1
        r.expected = f["label"]
        r.provenance.label_basis = "human"
        r.provenance.notes = json.dumps(notes, sort_keys=True)
        r.review_status = "reviewed"
        n["reviewed"] += 1
    return dict(n)


def ai_reference(path) -> tuple[dict, dict]:
    """(record id -> AI review row, profanity reserve source row -> AI review row) from a single-AI review folder."""
    path = Path(path)
    rows = {}
    for line in (path / "mapped-ai-reference.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            rows[d["id"]] = d
    reserves = {}
    rf = path / "f4-profanity-reserve.jsonl"
    for line in rf.read_text(encoding="utf-8").splitlines() if rf.exists() else []:
        if line.strip():
            d = json.loads(line)
            if d.get("include_in_replenishment"):
                reserves[d["source_row"]] = d
    return rows, reserves


def apply_ai_reference(records: list, rows: dict, reserves: dict, authorization: str) -> dict:
    """Single-AI labels for a provisional build. An eligible label replaces the draft (kept in the notes) with label
    basis llm and status ai_reviewed; an unresolved one drops the row with its reason; a required diagnostic subtask
    (masked spelling only) moves the row there. Nothing becomes human-reviewed."""
    n = defaultdict(int)
    for r in records:
        if r.provenance.source not in REVIEW_GATED:
            continue
        d = rows.get(r.id)
        if d is None and r.provenance.source == "civil_comments_profanity" and r.provenance.source_id in reserves:
            q = reserves[r.provenance.source_id]
            lab = q["labels"].get("profanity_present")
            d = {"label": lab, "eligible_for_ai_reference": lab in ("yes", "no") and q.get("exclude_case") in ("no", False, None),
                 "note": q.get("note"), "review_id": q.get("review_id"), "reviewer": q.get("reviewer"), "required_subtask": None}
        if d is None:
            r.review_status = "candidate"
            n["not_in_ai_reference"] += 1
            continue
        if not d.get("eligible_for_ai_reference") or d.get("label") not in r.labels:
            r.provenance.exclude_reason = f"ai review: unresolved ({d.get('review_id')}: {d.get('note')})"
            r.review_status = "candidate"
            n["excluded_unresolved"] += 1
            continue
        try:
            notes = json.loads(r.provenance.notes) if r.provenance.notes and r.provenance.notes.startswith("{") else {"notes": r.provenance.notes}
        except json.JSONDecodeError:
            notes = {"notes": r.provenance.notes}
        notes.update({"draft_expected": r.expected, "ai_review": {"reviewer": d.get("reviewer"), "review_id": d.get("review_id"),
                                                                  "note": d.get("note"), "authorization": authorization}})
        if d.get("required_subtask") and d["required_subtask"] != r.subtask:
            notes["subtask_moved_from"] = r.subtask
            r.subtask = d["required_subtask"]
            n["moved_to_diagnostic"] += 1
        if d["label"] != r.expected:
            n["draft_label_replaced"] += 1
        r.expected = d["label"]
        r.provenance.label_basis = "llm"
        r.provenance.notes = json.dumps(notes, sort_keys=True)
        r.review_status = "ai_reviewed"
        n["ai_reviewed"] += 1
    return dict(n)


def review_status_of(r, reviewed: set) -> str:
    if r.review_status:
        return r.review_status
    if r.provenance.source in AUTHORED or r.provenance.source.startswith("bias_pairs"):
        return "reviewed" if (r.id, str(r.expected)) in reviewed else "candidate"
    if r.provenance.label_basis == "deterministic":
        return "deterministic"
    return "source_label"


def cell_rng(seed: int, *parts) -> random.Random:
    """One generator per (feature, subtask, expected) cell, seeded from the cell's name: adding or changing another
    feature's sources never changes which rows this cell picks. Before this, one global generator made every rebuild
    reshuffle every feature (22 September 2026)."""
    return random.Random(f"{seed}:" + ":".join(str(p) for p in parts))


def pii_parent_group(source_id: str) -> str:
    """AI4Privacy ids such as 50846A and 50846B are fragments of one source document (the data-quality review of 24
    September 2026 found text running on from one to the next). Group by the numeric parent so fragments never
    straddle tuning and test. Conservative: some numerically related ids may be unrelated documents."""
    m = re.match(r"(\d+)[A-Z]*$", str(source_id))
    return f"ai4privacy-{m.group(1)}" if m else f"ai4privacy-{source_id}"


def build(per_cell: int, seed: int, sources_limit=None, ai_reference_dir=None, ai_authorization: str | None = None,
          pii_parent_groups: bool = False, plan_overrides: dict | None = None, cell_caps: dict | None = None,
          negative_reviews: dict | None = None):
    """``ai_reference_dir`` makes a provisional build: review-gated rows take single-AI labels (status ai_reviewed,
    basis llm) instead of human review, and reserves the AI review admitted join the profanity pool.
    ``pii_parent_groups`` groups AI4Privacy fragments by parent document before splitting; releases up to v1.1-ai were
    built without it and stay as they are.
    ``plan_overrides`` replaces the sources of some (feature, subtask) cells for a new version; ``cell_caps`` caps
    rows per expected class for some cells. ``negative_reviews`` maps (source, row id) review verdicts for negatives
    that must be verified: a reviewed "present" row is excluded, and ``build.unverified`` lists chosen negatives not
    yet reviewed."""
    rng = random.Random(seed)
    plan = {**PILOT_PLAN, **(plan_overrides or {})}
    loaded = {}
    ai_rows, ai_res = ai_reference(ai_reference_dir) if ai_reference_dir else ({}, {})
    for name in sorted({s for srcs in plan.values() for s in srcs}):
        kw = dict(LOAD_KWARGS.get(name, {}))
        if ai_reference_dir and name == "civil_comments_profanity":
            kw["released"] = set(ai_res)
        if ai_reference_dir and name == "bias_pairs_reviewed":
            kw["ai_reference"] = ai_reference_dir
        loaded[name] = SOURCES[name].load(limit=sources_limit, **kw)
        if pii_parent_groups and name == "ai4privacy":
            for r in loaded[name]:
                r.group = pii_parent_group(r.provenance.source_id)
    if ai_reference_dir:
        build.review_counts = apply_ai_reference([r for rs in loaded.values() for r in rs], ai_rows, ai_res,
                                                 ai_authorization or "owner instruction")
    else:
        build.review_counts = apply_reviews([r for rs in loaded.values() for r in rs], final_reviews())
    chosen = []
    build.unverified = []
    for rows_ in loaded.values():
        for r in rows_:
            v = (negative_reviews or {}).get(r.provenance.source, {}).get(r.id)
            if v is not None and v != "absent" and r.expected == "no" and r.provenance.exclude_reason is None:
                r.provenance.exclude_reason = f"blind review: {v}"
    for (feature, subtask), srcs in plan.items():
        # rows that failed a blind review stay in the pool until after the shuffle, so dropping them refills only
        # their own slots from further down the same order instead of reshuffling the whole cell
        failed = lambda r: str(r.provenance.exclude_reason or "").startswith("blind review:")
        pool = [r for s in srcs for r in loaded[s] if r.feature == feature and r.subtask == subtask
                and (r.provenance.exclude_reason is None or failed(r))]
        pool = dedup(pool)
        by_expected = defaultdict(list)
        for r in pool:
            by_expected[r.expected].append(r)
        seen = examined_ids()
        for expected, rows in by_expected.items():
            rows.sort(key=lambda r: r.id)                  # source order must not matter either
            cell_rng(seed, feature, subtask, expected).shuffle(rows)
            rows.sort(key=lambda r: r.id not in seen)      # authored controls and examined rows are kept ahead of the cap
            rows = [r for r in rows if not failed(r)]
            cap = (cell_caps or {}).get(f"{feature}:{subtask}", per_cell)
            chosen.extend(rows[:cap])
            if expected == "no":
                reviewed = (negative_reviews or {})
                build.unverified += [r.id for r in rows[:cap] if r.provenance.source in reviewed
                                     and r.id not in reviewed[r.provenance.source]]
    # tune/test split, stratified by (feature, subtask, expected), 15% tune, decided per group so related rows
    # (an Aegis prompt and its response) never straddle the boundary; already-examined rows are forced to tune.
    reviewed = reviewed_ids()
    for r in chosen:
        r.group = group_of(r)
        r.review_status = review_status_of(r, reviewed)
    seen = examined_ids()
    split_of: dict = {}
    by_cell = defaultdict(list)
    for r in chosen:
        by_cell[(r.feature, r.subtask, r.expected)].append(r)
    # Tune gets about 15% of each cell's rows, counted in rows, not groups: a group joins tune only while the cell's
    # tune row count is under target. Large shared groups (a sentence frame, a source document) would otherwise pull
    # nearly every row into tune.
    for cell, rows in by_cell.items():
        rows.sort(key=lambda r: r.id)
        cell_rng(seed, "split", *cell).shuffle(rows)
        k = max(1, round(TUNE_SHARE.get(cell[:2], 0.15) * len(rows)))
        in_cell = defaultdict(int)
        for r in rows:
            in_cell[r.group] += 1
        tuned = sum(n for g, n in in_cell.items() if split_of.get(g) == "tune")
        for r in rows:
            if tuned >= k:
                break
            if r.group in split_of:
                continue
            split_of[r.group] = "tune"
            tuned += in_cell[r.group]
    for r in chosen:
        if r.id in seen:
            split_of[r.group] = "tune"
    for r in chosen:
        r.split = split_of.get(r.group, "test")
    return chosen


def write(records, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"protocol": "gold-rails::pilot", "files": []}
    by_file = defaultdict(list)
    for r in records:
        by_file[(r.feature, r.split)].append(r)
    for (feature, split), rows in sorted(by_file.items()):
        path = out_dir / f"{feature}.{split}.jsonl"
        write_jsonl(rows, path)
        manifest["files"].append({"path": path.name, "feature": feature, "split": split, "n": len(rows), "sha256": dataset_hash(rows)})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dataset/samples/pilot")
    ap.add_argument("--per-cell", type=int, default=25, help="rows per (feature, subtask, expected) cell")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--sources-limit", type=int, default=None, help="cap rows loaded per source (speed)")
    args = ap.parse_args()
    records = build(args.per_cell, args.seed, args.sources_limit)
    manifest = write(records, Path(args.out))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
