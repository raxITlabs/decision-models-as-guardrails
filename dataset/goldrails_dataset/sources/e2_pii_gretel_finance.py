"""Edition 2 driver's-licence rows from Gretel's synthetic PII finance set, English rows of the test split. Apache-2.0.

Read only for DRIVER_ID, which Nemotron-PII has almost no labels for. Only rows with a verified driver's-licence
number are offered to the selector, because this set's labels are the noisiest of the three sources: a sample showed
``driver_license_number`` on a policy number and on a wallet address. A ``driver_license_number`` span counts only
when a driver's-licence label sits right before it (``e2_pii.driver_context_ok``); a row with any span failing that
is left out. Other types map as in ``e2_pii_gretel``; every row passes ``e2_pii.screen``. A row must also hold at
least one other supported type, so its row-level label stays yes if DRIVER_ID leaves the score.

Source ids are row positions in ``data/test-00000-of-00001.parquet`` at the pinned revision (the file has no id
column). Groups join rows across shared values.

    load()  reads dataset/edition2/pii/candidates.jsonl (offline). eligible() reads upstream (network or HF cache).
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from ..records import make_id
from .e2_pii import ambiguous_context, JOIN_LABELS, MAX_CHARS, candidate, driver_context_ok, join_on_values, load_source, screen, source_rationale

NAME = SOURCE = "gretel_pii_finance"
LICENCE = "apache-2.0"
REPO, REVISION = "gretelai/synthetic_pii_finance_multilingual", "7b844d16738527a04264f50214cb426a4cea0897"
FILE = "data/test-00000-of-00001.parquet"
URL = f"https://huggingface.co/datasets/{REPO}/tree/{REVISION}"
TO_TYPE = {"name": "NAME", "first_name": "NAME", "last_name": "NAME", "email": "EMAIL", "phone_number": "PHONE",
           "street_address": "ADDRESS", "user_name": "USERNAME", "password": "PASSWORD", "ipv4": "IP_ADDRESS",
           "ipv6": "IP_ADDRESS", "ssn": "US_SOCIAL_SECURITY_NUMBER", "driver_license_number": "DRIVER_ID"}
AMBIGUOUS = ("account_pin",)
US_SSN = re.compile(r"^\d{3}-\d{2}-\d{4}$")


def rows_from_source() -> list:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    p = hf_hub_download(REPO, FILE, repo_type="dataset", revision=REVISION)
    rows = pq.read_table(p).to_pylist()
    for i, r in enumerate(rows):
        r["source_id"] = f"test:{i}"
        r["spans"] = json.loads(r["pii_spans"]) if isinstance(r["pii_spans"], str) else (r["pii_spans"] or [])
    return [r for r in rows if r["language"] == "English"]


def map_spans(text: str, raw: list) -> tuple:
    spans, src, why = [], defaultdict(set), []
    for s in raw:
        lab = s["label"]
        if lab in AMBIGUOUS:
            why.append(f"{lab} span: may be a passcode")
            continue
        t = TO_TYPE.get(lab)
        if t is None:
            continue
        value = text[s["start"]:s["end"]]
        if not value.strip():
            why.append(f"empty {lab} span")
            continue
        if t == "DRIVER_ID" and not driver_context_ok(text, s["start"]):
            why.append("driver_license_number span without a driver's-licence label")
            continue
        if t == "US_SOCIAL_SECURITY_NUMBER" and not US_SSN.match(value.strip()):
            why.append("ssn value not in the US shape")
            continue
        if ambiguous_context(t, text, s["start"]):
            why.append(f"{t} value in a doubtful context (hash, token, SSID or example)")
            continue
        spans.append({"start": int(s["start"]), "end": int(s["end"]), "label": t, "source_label": lab})
        src[t].add(lab)
    return spans, src, why


def eligible(refs: dict) -> tuple:
    rows = rows_from_source()
    root = join_on_values([(r["source_id"], [r["generated_text"][s["start"]:s["end"]] for s in r["spans"]
                                              if s["label"] in JOIN_LABELS]) for r in rows])
    out, why = [], Counter()
    for r in rows:
        text = r["generated_text"]
        rid = make_id("F5", SOURCE, r["source_id"])
        group = f"{SOURCE}-{root[r['source_id']].replace(':', '-')}"
        if rid in refs["ids"] or group in refs["groups"]:
            why["id or group in v1"] += 1
            continue
        if not any(s["label"] == "driver_license_number" for s in r["spans"]):
            why["no driver_license_number span (only DRIVER_ID rows are read)"] += 1
            continue
        if len(text) > MAX_CHARS:
            why["longer than 4096 characters"] += 1
            continue
        spans, src, reasons = map_spans(text, r["spans"])
        types = set(src)
        if "DRIVER_ID" in types and len(types) < 2:
            reasons.append("DRIVER_ID is the only supported type")
        reasons += screen(text, types, negative=not types)
        if reasons:
            why[reasons[0]] += 1
            continue
        out.append(candidate(
            id=rid, source=SOURCE, source_id=r["source_id"], licence=LICENCE, revision=REVISION, upstream="test",
            text=text, entity_types=types, spans=spans, group=group, label_basis="synthetic_reviewed",
            review_status="source_label", label_rationale=source_rationale(sorted(types), src),
            notes={"language": r["language"], "domain": r["domain"], "document_type": r["document_type"],
                   "source_labels": ",".join(sorted({s["label"] for s in r["spans"]}))}))
    return out, dict(sorted(why.items()))


def load(limit=None) -> list:
    return load_source(SOURCE, limit)
