"""RAGBench (Galileo, CC-BY-4.0): retrieval-augmented QA replies with sentence-level support annotations, test split.

Edition 2 grounding source. Pinned to one Hugging Face revision. Each row is a question, retrieved documents and a
reply from a named generator (GPT-3.5, Claude 3 Haiku, or the HAGRID reference answers). RAGBench's labels come from
an LLM annotator (GPT-4-turbo), not people: ``adherence_score`` False when any reply sentence is unsupported, with the
unsupported sentence keys. ``label_basis`` is therefore "llm" and ``review_status`` "candidate": no RAGBench row is
scored until a person has confirmed it.

Rows, role assistant, the documents joined as the source and the question as the query: expected "yes" (unsupported)
when adherence is False, "no" when True. The unsupported sentences become spans with label ``unsupported``. Two
automatic metrics shipped with the row (RAGAS faithfulness, TruLens groundedness) are kept in the notes so the
candidate builder can require agreement. Replies to the same question share a group.

Only subsets whose passages can be redistributed and that have usable positives are loaded (SUBSETS). MS MARCO
(non-commercial terms, and RAGTruth's QA source), CovidQA, TechQA, EManual, DelucionQA, ExpertQA, FinQA and TAT-QA are
left out; CUAD contracts are mostly far longer than the other sources and are left out by default.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import urllib.request

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "ragbench", "cc-by-4.0"
REVISION = "97808f3e5fd16ede40bbff6c2949af8139b2eb7b"   # pinned Hugging Face dataset revision
URL = "https://huggingface.co/datasets/galileo-ai/ragbench"
RAW = "https://huggingface.co/datasets/galileo-ai/ragbench/resolve/{rev}/{subset}/{split}-00000-of-00001.parquet"
SUBSETS = {"hagrid": "apache-2.0 (HAGRID; MIRACL Wikipedia passages cc-by-sa)",
           "hotpotqa": "cc-by-sa-4.0 (HotpotQA; Wikipedia)",
           "pubmedqa": "mit (PubMedQA; PubMed abstracts, publisher copyright)"}


def fetch(subset: str, split: str = "test") -> list:
    import pandas as pd
    with urllib.request.urlopen(RAW.format(rev=REVISION, subset=subset, split=split), timeout=300) as r:
        return pd.read_parquet(io.BytesIO(r.read())).to_dict("records")


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _sentences(v) -> dict:
    return {str(pair[0]): str(pair[1]) for pair in (v if v is not None else []) if len(pair) >= 2}


def spans_of(response: str, sentences: dict, keys) -> list:
    out, cursor = [], 0
    for k in [str(k) for k in (keys if keys is not None else [])]:
        s = sentences.get(k, "").strip()
        start = response.find(s, cursor) if s else -1
        if start < 0 and s:
            start = response.find(s)
        if start >= 0 and s:
            out.append({"start": start, "end": start + len(s), "label": "unsupported", "source_label": f"ragbench:{k}"})
            cursor = start + len(s)
    return out


def load(limit=None, subsets=tuple(SUBSETS), split="test") -> list:
    out = []
    for subset in subsets:
        for row in fetch(subset, split):
            adherent = row.get("adherence_score")
            if adherent is None or not row.get("response") or row.get("documents") is None:
                continue
            adherent = bool(adherent)
            docs = [str(d) for d in row["documents"]]
            source = "\n\n".join(f"Document {i + 1}: {d}" for i, d in enumerate(docs))
            sents = _sentences(row.get("response_sentences"))
            keys = [str(k) for k in (row.get("unsupported_response_sentence_keys") if row.get("unsupported_response_sentence_keys") is not None else [])]
            spans = [] if adherent else spans_of(row["response"], sents, keys)
            qkey = hashlib.sha1(str(row["question"]).encode("utf-8")).hexdigest()[:12]
            sid = f"{subset}:{split}:{row['id']}:{row.get('generation_model_name')}"
            out.append(Record(
                id=make_id("F6", NAME, sid), feature="F6", subtask="grounding",
                state=State(role="assistant", text=str(row["response"]), source=source, query=str(row["question"])),
                category=Category(ailuminate="benign", bedrock="NONE", source_label="adherent" if adherent else "unsupported:" + ",".join(keys)),
                labels=["no", "yes"], expected="no" if adherent else "yes", group=f"{NAME}-{subset}-{qkey}",
                spans=spans or None, review_status="candidate",
                provenance=Provenance(source=NAME, source_id=sid, licence=LICENCE, label_basis="llm", imported_at=now(),
                                      notes=json.dumps({"revision": REVISION, "subset": subset, "split": split, "subset_licence": SUBSETS.get(subset),
                                                        "generator": row.get("generation_model_name"), "annotator": row.get("annotating_model_name"),
                                                        "unsupported_keys": keys, "unsupported_sentences": [sents.get(k, "") for k in keys],
                                                        "ragas_faithfulness": _num(row.get("ragas_faithfulness")),
                                                        "trulens_groundedness": _num(row.get("trulens_groundedness"))})),
            ))
            if limit and len(out) >= limit:
                return out
    return out
