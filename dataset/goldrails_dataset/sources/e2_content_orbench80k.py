"""OR-Bench 80k: benign prompts that look unsafe (edition 2 content, subtasks over_refusal and harmful_goal negatives).
CC-BY-4.0.

The superset OR-Bench hard-1k (sources/orbench.py) was drawn from. Labels are by construction: an LLM-ensemble
moderator judged each prompt benign (label_basis automated, no per-row human judgment). The hub only publishes a
split named "train"; it is the benchmark itself, not training data, and is flagged as an upstream train split.
Rows whose text is also in hard-1k are dropped later by the edition 2 overlap check. Each row is its own group.
"""
from __future__ import annotations

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "e2_content_orbench80k", "cc-by-4.0"
REVISION = "e36d8b80e81837c8a8f264bbb2a49f1b32c7e272"   # pinned Hugging Face dataset revision (same as orbench)
URL = "https://huggingface.co/datasets/bench-llm/or-bench"
UPSTREAM_SPLIT = "train"     # the only split published; flagged


def load(limit=None, subtask: str = "over_refusal", rows=None) -> list:
    if rows is None:
        from datasets import load_dataset
        rows = load_dataset("bench-llm/or-bench", "or-bench-80k", split="train", revision=REVISION)
    out = []
    for i, row in enumerate(rows):
        out.append(Record(
            id=make_id("F1", NAME, str(i)), feature="F1", subtask=subtask,
            state=State(role="user", text=row["prompt"]),
            category=Category(ailuminate="benign", bedrock="NONE", source_label=row["category"]),
            labels=["no", "yes"], expected="no", group=f"orbench80k:{i}",
            provenance=Provenance(source=NAME, source_id=str(i), licence=LICENCE, label_basis="automated", imported_at=now(),
                                  contamination=["orbench-public-2024", "upstream-train-split"],
                                  notes=f"upstream_split={UPSTREAM_SPLIT}; revision={REVISION}"),
        ))
        if limit and len(out) >= limit:
            break
    return out
