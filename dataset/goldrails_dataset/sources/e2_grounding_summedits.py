"""SummEdits (Salesforce, CC-BY-4.0): summaries of a document, each human-labelled consistent or inconsistent.

Edition 2 grounding source. Pinned to one Hugging Face revision. SummEdits starts from a seed summary that annotators
verified as consistent, has an LLM make small edits, and has annotators label each edited summary consistent (1) or
inconsistent (0); borderline edits were removed by the authors. The release has no splits: all 6,348 rows are the
benchmark (flagged ``upstream_split: none``).

Rows, role assistant, the document as the source and a fixed summarisation instruction as the query (as RAGTruth's
Summary rows): expected "yes" (unsupported) for label 0, "no" for label 1. All summaries of one document share a group.

Only domains whose documents can be redistributed are loaded (DOMAINS): BillSum (US bills, public domain), QMSum
(MIT; AMI/ICSI meeting transcripts CC-BY-4.0), SciTLDR (Apache-2.0), Shakespeare (public domain), and the sales call
and sales email domains (synthetic documents written for SummEdits). News, podcasts, SAMSum (CC-BY-NC-ND) and ECTSum
(earnings calls) are left out.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "summedits", "cc-by-4.0"
REVISION = "ce0c479aaf59259abb6b67e42248b2f49004b7d5"   # pinned Hugging Face dataset revision
URL = "https://huggingface.co/datasets/Salesforce/summedits"
RAW = "https://huggingface.co/datasets/Salesforce/summedits/resolve/{rev}/summedits.json"
DOMAINS = {"billsum": "public-domain (US Congress bills)", "qmsumm": "mit (QMSum; AMI/ICSI cc-by-4.0)",
           "scitldr": "apache-2.0 (SciTLDR)", "shakespeare": "public-domain",
           "sales_call": "cc-by-4.0 (synthetic, SummEdits)", "sales_email": "cc-by-4.0 (synthetic, SummEdits)"}
QUERY = "Summarise the source text."


def fetch() -> list:
    with urllib.request.urlopen(RAW.format(rev=REVISION), timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))


def doc_key(doc: str) -> str:
    return hashlib.sha1(doc.encode("utf-8")).hexdigest()[:12]


def load(limit=None, domains=tuple(DOMAINS)) -> list:
    out = []
    for row in fetch():
        if row["domain"] not in domains or not row.get("summary") or not row.get("doc"):
            continue
        consistent = str(row["label"]) == "1"
        edit_types = row.get("edit_types") or "[]"
        out.append(Record(
            id=make_id("F6", NAME, str(row["id"])), feature="F6", subtask="grounding",
            state=State(role="assistant", text=row["summary"], source=row["doc"], query=QUERY),
            category=Category(ailuminate="benign", bedrock="NONE", source_label="consistent" if consistent else f"inconsistent:{edit_types}"),
            labels=["no", "yes"], expected="no" if consistent else "yes", group=f"{NAME}-{row['domain']}-{doc_key(row['doc'])}",
            provenance=Provenance(source=NAME, source_id=str(row["id"]), licence=LICENCE, label_basis="human", imported_at=now(),
                                  notes=json.dumps({"revision": REVISION, "upstream_split": "none", "domain": row["domain"],
                                                    "domain_licence": DOMAINS.get(row["domain"]), "edit_types": edit_types,
                                                    "seed_summary": row.get("seed_summary"), "is_seed": str(row["id"]).endswith("_og")})),
        ))
        if limit and len(out) >= limit:
            break
    return out
