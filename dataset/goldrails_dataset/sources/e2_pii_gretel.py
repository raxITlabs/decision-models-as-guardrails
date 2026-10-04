"""Edition 2 PII rows from Gretel's PII masking EN v1, test split (5,000 rows). Apache-2.0.

Synthetic single-paragraph texts across ~30 domains, each with a list of PII values and their types (no offsets).
Shorter and more varied in style than Nemotron-PII's documents, so the suite does not rest on one generator.

Labels. Each listed value is located in the text (every occurrence becomes a span); a row whose value cannot be found
is left out. Types map to the supported set as below. ``ssn`` counts as a US SSN only in the NNN-NN-NNNN shape;
otherwise the row is left out. ``certificate_license_number`` counts as DRIVER_ID only with a driver's-licence label
right before it, and a row with any other ``certificate_license_number`` is left out. A negative with a
``company_name`` is left out (the generator builds them from surnames: "Hubbard, Wu and Malone"). Rows with an
unmapped type that could be read as a supported one (``pin``, ``account_pin``) are
left out, and every row passes ``e2_pii.screen``.

Groups. One per uid, joined across shared values (synthetic personas recur), so related rows share a split.

    load()  reads dataset/edition2/pii/candidates.jsonl (offline). eligible() reads upstream (network or HF cache).
"""
from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict

from ..records import make_id
from .e2_pii import ambiguous_context, JOIN_LABELS, MAX_CHARS, candidate, driver_context_ok, join_on_values, load_source, screen, source_rationale

NAME = SOURCE = "gretel_pii_en"
LICENCE = "apache-2.0"
REPO, REVISION = "gretelai/gretel-pii-masking-en-v1", "e06eb1499ca8d54470f085021cd8e54f9efac7fd"
FILE = "data/test-00000-of-00001.parquet"
URL = f"https://huggingface.co/datasets/{REPO}/tree/{REVISION}"
TO_TYPE = {"first_name": "NAME", "last_name": "NAME", "name": "NAME", "email": "EMAIL", "phone_number": "PHONE",
           "fax_number": "PHONE", "street_address": "ADDRESS", "address": "ADDRESS", "city": "ADDRESS",
           "state": "ADDRESS", "postcode": "ADDRESS", "user_name": "USERNAME", "password": "PASSWORD",
           "ipv4": "IP_ADDRESS", "ipv6": "IP_ADDRESS", "ssn": "US_SOCIAL_SECURITY_NUMBER"}
AMBIGUOUS = ("pin", "account_pin", "county")
US_SSN = re.compile(r"^\d{3}-\d{2}-\d{4}$")
DL_LABELS = ("certificate_license_number",)


def rows_from_source() -> list:
    from huggingface_hub import hf_hub_download
    import pyarrow.parquet as pq
    p = hf_hub_download(REPO, FILE, repo_type="dataset", revision=REVISION)
    rows = pq.read_table(p).to_pylist()
    for r in rows:
        e = r["entities"]
        if isinstance(e, str):
            try:
                e = json.loads(e)
            except json.JSONDecodeError:
                e = ast.literal_eval(e)
        r["entities"] = e or []
    return rows


def map_entities(text: str, entities: list) -> tuple:
    spans, src, why = [], defaultdict(set), []
    for e in entities:
        value = (e.get("entity") or "").strip()
        for lab in e.get("types") or []:
            if lab in AMBIGUOUS:
                why.append(f"{lab} value: may be a supported type")
                continue
            hits = [m.start() for m in re.finditer(re.escape(value), text)] if value else []
            t = TO_TYPE.get(lab)
            if lab in DL_LABELS and hits and all(driver_context_ok(text, h) for h in hits):
                t = "DRIVER_ID"
            if lab in DL_LABELS and t != "DRIVER_ID":
                why.append("certificate_license_number of unknown kind: may be a driver's licence")
                continue
            if t is None:
                continue
            if not hits:
                why.append(f"{lab} value not found in the text")
                continue
            if t == "US_SOCIAL_SECURITY_NUMBER" and not US_SSN.match(value):
                why.append("ssn value not in the US shape")
                continue
            if any(ambiguous_context(t, text, h) for h in hits):
                why.append(f"{t} value in a doubtful context (hash, token, SSID or example)")
                continue
            for h in hits:
                spans.append({"start": h, "end": h + len(value), "label": t, "source_label": lab})
            src[t].add(lab)
    spans.sort(key=lambda s: (s["start"], s["end"], s["label"]))
    return spans, src, why


def eligible(refs: dict) -> tuple:
    rows = rows_from_source()
    root = join_on_values([(r["uid"], [e.get("entity") or "" for e in r["entities"]
                                        if set(e.get("types") or []) & set(JOIN_LABELS)]) for r in rows])
    out, why = [], Counter()
    for r in sorted(rows, key=lambda x: x["uid"]):
        text = r["text"]
        rid = make_id("F5", SOURCE, r["uid"])
        group = f"{SOURCE}-{root[r['uid']]}"
        if rid in refs["ids"] or group in refs["groups"]:
            why["id or group in v1"] += 1
            continue
        if len(text) > MAX_CHARS:
            why["longer than 4096 characters"] += 1
            continue
        spans, src, reasons = map_entities(text, r["entities"])
        types = set(src)
        if not types and any("company_name" in (e.get("types") or []) for e in r["entities"]):
            reasons.append("negative with a company name: generated company names are often surnames")
        reasons += screen(text, types, negative=not types)
        if reasons:
            why[reasons[0]] += 1
            continue
        out.append(candidate(
            id=rid, source=SOURCE, source_id=r["uid"], licence=LICENCE, revision=REVISION, upstream="test", text=text,
            entity_types=types, spans=spans, group=group, label_basis="synthetic_reviewed",
            review_status="source_label" if types else "candidate",
            label_rationale=source_rationale(sorted(types), src),
            notes={"domain": r["domain"], "document_type": r["document_type"],
                   "source_labels": ",".join(sorted({t for e in r["entities"] for t in e.get("types") or []}))}))
    return out, dict(sorted(why.items()))


def load(limit=None) -> list:
    return load_source(SOURCE, limit)
