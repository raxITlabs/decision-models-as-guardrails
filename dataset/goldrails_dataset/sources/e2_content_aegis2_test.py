"""NVIDIA Aegis AI Content Safety Dataset 2.0, test split, rows v1 did not take (edition 2 content). CC-BY-4.0.
Vendor-owned (NVIDIA).

Replaces e2_content_aegis2_val (5 October 2026). pplx-decider-v1-27b's published recipe trains on the Aegis 2.0 train
split and tunes on its validation split, so validation rows cannot be fair test rows for it; the recipe only
evaluates on the test split. v1 (sources/aegis2.py) already drew from the test split: every labelled reply in it is a
v1 row, so this source can only add prompts (subtask input). e2_content.round6 leaves out every row whose id, text,
conversation or near-duplicate text is in v1 or already in edition 2, and every row whose text is in a split a
benchmarked model's recipe trains or tunes on (model_overlap).

Same rules as sources/aegis2.py: REDACTED prompts skipped, "Needs Caution" rows excluded, a reply carries its prompt
as context, the group is the Aegis conversation. Labels are the upstream prompt_label / response_label, labelled by
humans or an LLM jury (label_basis).
"""
from __future__ import annotations

from ..records import Category, Provenance, Record, State, make_id
from ..taxonomy import bedrock_for
from .aegis2 import REVISION, _first_category
from .base import now

NAME, LICENCE = "e2_content_aegis2_test", "cc-by-4.0"
URL = "https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0"
UPSTREAM_SPLIT = "test"


def _basis(src) -> str:
    return "human" if src == "human" else "llm"


def load(limit=None, rows=None) -> list:
    if rows is None:
        from datasets import load_dataset
        rows = load_dataset("nvidia/Aegis-AI-Content-Safety-Dataset-2.0", split=UPSTREAM_SPLIT, revision=REVISION)
    out = []
    for row in rows:
        if row["prompt"] == "REDACTED" or not row["prompt"]:
            continue
        cats = row["violated_categories"] or ""
        caution = "needs_caution" if "Needs Caution" in cats else None
        ail, _ = _first_category(cats)
        conv = row["id"]
        unsafe = row["prompt_label"] == "unsafe"
        notes = f"violated_categories={cats}; upstream_split={UPSTREAM_SPLIT}; revision={REVISION}"
        out.append(Record(
            id=make_id("F1", NAME, f"{conv}:prompt"), feature="F1", subtask="input",
            state=State(role="user", text=row["prompt"]),
            category=Category(ailuminate=ail if unsafe else "benign", bedrock=bedrock_for(ail) if unsafe else "NONE", source_label=cats or None),
            labels=["no", "yes"], expected="yes" if unsafe else "no", group=f"aegis2:{conv}",
            provenance=Provenance(source=NAME, source_id=f"{conv}:prompt", licence=LICENCE, label_basis=_basis(row["prompt_label_source"]),
                                  imported_at=now(), contamination=["qwen3guard-eval", "dynaguard-train"], exclude_reason=caution, notes=notes),
        ))
        if row["response"] and row["response_label"]:
            r_unsafe = row["response_label"] == "unsafe"
            aug = row["response_label_source"] == "refusal_data_augmentation"
            out.append(Record(
                id=make_id("F1", NAME, f"{conv}:response"), feature="F1", subtask="output",
                state=State(role="assistant", text=row["response"], context=[{"role": "user", "text": row["prompt"]}]),
                category=Category(ailuminate=ail if r_unsafe else "benign", bedrock=bedrock_for(ail) if r_unsafe else "NONE", source_label=cats or None),
                labels=["no", "yes"], expected="yes" if r_unsafe else "no", group=f"aegis2:{conv}",
                provenance=Provenance(source=NAME, source_id=f"{conv}:response", licence=LICENCE,
                                      label_basis=_basis(row["response_label_source"]), imported_at=now(),
                                      contamination=["qwen3guard-eval", "dynaguard-train"],
                                      exclude_reason=caution or ("synthetic_refusal_augmentation" if aug else None),
                                      notes=notes + f"; response_label_source={row['response_label_source']}"),
            ))
        if limit and len(out) >= limit:
            break
    return out
