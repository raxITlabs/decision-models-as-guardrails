"""NVIDIA Aegis AI Content Safety Dataset 2.0, validation split (edition 2 content, subtasks input and output).
CC-BY-4.0. Vendor-owned (NVIDIA).

v1 drew 776 of the test split's 852 labelled replies, and every remaining one shares a conversation or a text with
a v1 row, so edition 2 takes replies from the validation split (not a training split). Same rules as
sources/aegis2.py: REDACTED prompts skipped, "Needs Caution" rows excluded, a reply carries its prompt as context.
Replies whose label source is "refusal_data_augmentation" are excluded: they are synthetic refusals added to the
dataset, not judged model replies. Reply labels here come from humans or an LLM jury, recorded in label_basis.
"""
from __future__ import annotations

from ..records import Category, Provenance, Record, State, make_id
from ..taxonomy import bedrock_for
from .aegis2 import REVISION, _first_category
from .base import now

NAME, LICENCE = "e2_content_aegis2_val", "cc-by-4.0"
URL = "https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0"
UPSTREAM_SPLIT = "validation"


def _basis(src) -> str:
    return "human" if src == "human" else "llm"


def load(limit=None, rows=None) -> list:
    if rows is None:
        from datasets import load_dataset
        rows = load_dataset("nvidia/Aegis-AI-Content-Safety-Dataset-2.0", split="validation", revision=REVISION)
    out = []
    for row in rows:
        if row["prompt"] == "REDACTED" or not row["prompt"]:
            continue
        cats = row["violated_categories"] or ""
        caution = "needs_caution" if "Needs Caution" in cats else None
        ail, src_label = _first_category(cats)
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
