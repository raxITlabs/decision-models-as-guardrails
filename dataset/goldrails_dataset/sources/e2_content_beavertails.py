"""PKU-Alignment BeaverTails, 330k_test split: model replies with human safety labels (edition 2 content, subtask
output). CC-BY-NC-4.0, so the text is not redistributed (dataset/release/redistribution.json: ids_only); it is
rebuilt locally from the pinned revision.

Added 5 October 2026 as the second reply source after e2_content_aegis2_val left edition 2 (pplx-decider-v1-27b's
recipe tunes on the Aegis 2.0 validation split, and every Aegis 2.0 test reply is already a v1 row). BeaverTails is
in neither Strands Decider 2B's nor pplx-decider-v1-27b's published training recipe, and every row whose text is in a
split those recipes draw from is left out (model_overlap.seen_by_model, applied in e2_content.round6).

Each row is one question-answer pair: the question is the context turn, the answer is the judged reply. Upstream,
crowd annotators marked each pair is_safe and tagged any of 14 harm categories. A pair that occurs more than once in
the split with different is_safe labels is left out ("conflicting_upstream_labels"); a repeated pair with the same
label is loaded once. The group is the question, so every reply to one question lands in one split.
"""
from __future__ import annotations

import hashlib
import json
import lzma
from collections import defaultdict

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "e2_content_beavertails", "cc-by-nc-4.0"
REPO = "PKU-Alignment/BeaverTails"
REVISION = "8401fe609d288129cc684a9b3be6a93e41cfe678"   # pinned Hugging Face dataset revision
FILE = "round0/330k/test.jsonl.xz"
URL = f"https://huggingface.co/datasets/{REPO}"
UPSTREAM_SPLIT = "330k_test"
CATEGORIES = ("animal_abuse", "child_abuse", "controversial_topics,politics", "discrimination,stereotype,injustice",
              "drug_abuse,weapons,banned_substance", "financial_crime,property_crime,theft",
              "hate_speech,offensive_language", "misinformation_regarding_ethics,laws_and_safety",
              "non_violent_unethical_behavior", "privacy_violation", "self_harm", "sexually_explicit,adult_content",
              "terrorism,organized_crime", "violence,aiding_and_abetting,incitement")


def _sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def fetch() -> list:
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(REPO, FILE, repo_type="dataset", revision=REVISION)
    with lzma.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def load(limit=None, rows=None) -> list:
    rows = rows if rows is not None else fetch()
    pairs = defaultdict(list)
    for i, row in enumerate(rows):
        q, a = (row.get("prompt") or "").strip(), (row.get("response") or "").strip()
        if q and a:
            pairs[(q, a)].append((i, row))
    out = []
    for (q, a), seen in sorted(pairs.items(), key=lambda kv: kv[1][0][0]):
        i, row = seen[0]
        safe = {bool(r["is_safe"]) for _, r in seen}
        cats = sorted({c for _, r in seen for c, v in (r.get("category") or {}).items() if v})
        unsafe = not row["is_safe"]
        sid = f"{UPSTREAM_SPLIT}:{_sha(q + chr(0) + a)}"
        out.append(Record(
            id=make_id("F1", NAME, sid), feature="F1", subtask="output",
            state=State(role="assistant", text=a, context=[{"role": "user", "text": q}]),
            category=Category(ailuminate=None if unsafe else "benign", bedrock=None if unsafe else "NONE",
                              source_label=",".join(f"[{c}]" for c in cats) or None),
            labels=["no", "yes"], expected="yes" if unsafe else "no", group=f"beavertails:{_sha(q)}",
            provenance=Provenance(source=NAME, source_id=sid, licence=LICENCE, label_basis="human", imported_at=now(),
                                  contamination=["beavertails-public-2023"],
                                  exclude_reason="conflicting_upstream_labels" if len(safe) > 1 else None,
                                  notes=json.dumps({"upstream_split": UPSTREAM_SPLIT, "revision": REVISION,
                                                    "first_line": i, "copies": len(seen), "categories": cats},
                                                   sort_keys=True)),
        ))
        if limit and len(out) >= limit:
            break
    return out


def categories_of(r: Record) -> list:
    """The BeaverTails harm categories recorded on a row (source_label holds them bracketed, since names hold commas)."""
    lab = r.category.source_label or ""
    return [c for c in CATEGORIES if f"[{c}]" in lab]
