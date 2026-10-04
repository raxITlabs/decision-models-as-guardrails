"""Edition 2 PII rows from NVIDIA Nemotron-PII, test split, that v1 never used. CC-BY-4.0.

Same source, revision, ids and groups as ``nemotron_pii`` (v1), so an edition 2 row can never be a v1 row under a
new name: ids are ``make_id("F5", "nemotron_pii", "<uid>:<locale>")`` and groups are v1's (source id joined across
shared email, phone and SSN values, computed over the whole test split). A group is left out when any of its
documents was in v1 (any split), in the v1 negative reviews, or in the source audit.

Labels follow v1's mapping and audit rules (``nemotron_pii.aws_type``, fax counts as PHONE, SSN only on US rows),
plus edition 2 additions:
- DRIVER_ID: a ``certificate_license_number`` or ``national_id`` span counts only when a driver's-licence label sits
  right before it (``e2_pii.driver_context_ok``). Nemotron-PII has no driver's-licence type of its own.
- Left out as ambiguous: rows with a ``certificate_license_number`` span not verified as a driver's licence (one
  in a vehicle-safety text was a Texas licence in all but name), a ``pin`` span (a PIN may be a passcode), a ``county`` span without another
  address component, an ``ssn`` span on an international row, a malformed span, or longer than 4,096 characters.
- A row whose only supported type is DRIVER_ID, or that repeats an earlier row's licence number, is left out.
- Every row passes ``e2_pii.screen``.

    load()  reads dataset/edition2/pii/candidates.jsonl (offline). eligible() reads upstream (network or HF cache).
"""
from __future__ import annotations

from collections import Counter, defaultdict

from ..records import make_id
from . import nemotron_pii as v1
from .e2_pii import ambiguous_context, MAX_CHARS, candidate, driver_context_ok, load_source, screen, source_rationale

NAME = "e2_pii_nemotron"           # registry key
SOURCE = v1.NAME                    # provenance.source and id namespace: the same as v1
LICENCE, REPO, REVISION, URL = v1.LICENCE, v1.REPO, v1.REVISION, v1.URL
DL_LABELS = ("certificate_license_number", "national_id")


def map_spans(r: dict) -> tuple:
    """(spans, types->source labels, reasons to leave the row out)."""
    text, locale = r["text"], r["locale"]
    spans, src, why = [], defaultdict(set), []
    labels = {s["label"] for s in r["spans"]}
    for s in r["spans"]:
        lab = s["label"]
        t = v1.aws_type(lab, locale)
        if lab in DL_LABELS and driver_context_ok(text, s["start"]):
            t = "DRIVER_ID"
        if t is None:
            continue
        value = text[s["start"]:s["end"]]
        if t in v1.FORMAT and not v1.FORMAT[t].search(value.strip()):
            why.append(f"malformed {t} span")
            continue
        if ambiguous_context(t, text, s["start"]):
            why.append(f"{t} value in a doubtful context (hash, token, SSID or example)")
            continue
        spans.append({"start": int(s["start"]), "end": int(s["end"]), "label": t, "source_label": lab})
        src[t].add(lab)
    if "ssn" in labels and locale != "us":
        why.append("ssn label on an international row")
    if "pin" in labels and "PASSWORD" not in src:
        why.append("pin span: may be a passcode")
    if any(s["label"] in DL_LABELS[:1] and not driver_context_ok(text, s["start"]) for s in r["spans"]):
        why.append("certificate_license_number of unknown kind: may be a driver's licence")
    if "county" in labels and "ADDRESS" not in src:
        why.append("county span without another address component")
    return spans, src, why


def eligible(refs: dict) -> tuple:
    rows = v1.rows_from_source()
    root = v1.groups(rows)
    used_uids = set()
    by_id = {make_id("F5", SOURCE, f"{r['uid']}:{r['locale']}"): r["uid"] for r in rows}
    for i in refs["ids"]:
        if i in by_id:
            used_uids.add(by_id[i])
    used_uids |= v1.audited_uids()
    bad_groups = {f"{SOURCE}-{root[u]}" for u in used_uids if u in root} | set(refs["groups"])
    out, why, dl_seen = [], Counter(), set()
    for r in sorted(rows, key=lambda x: (x["uid"], x["locale"])):
        sid = f"{r['uid']}:{r['locale']}"
        rid = make_id("F5", SOURCE, sid)
        group = f"{SOURCE}-{root[r['uid']]}"
        text = r["text"]
        if group in bad_groups:
            why["group touches v1 or the audit"] += 1
            continue
        if rid in refs["ids"]:
            why["id in v1"] += 1
            continue
        if len(text) > MAX_CHARS:
            why["longer than 4096 characters"] += 1
            continue
        spans, src, reasons = map_spans(r)
        types = set(src)
        if types == {"DRIVER_ID"}:
            reasons.append("DRIVER_ID is the only supported type")
        dl = {text[s["start"]:s["end"]].strip().lower() for s in spans if s["label"] == "DRIVER_ID"}
        if dl & dl_seen:
            reasons.append("shares a driver's licence number with an earlier row")
        reasons += screen(text, types, negative=not types)
        if reasons:
            why[reasons[0]] += 1
            continue
        dl_seen |= dl
        out.append(candidate(
            id=rid, source=SOURCE, source_id=sid, licence=LICENCE, revision=REVISION, upstream="test", text=text,
            entity_types=types, spans=spans, group=group,
            label_basis="synthetic_reviewed",
            review_status="source_label" if types else "candidate",
            label_rationale=source_rationale(sorted(types), src),
            notes={"locale": r["locale"], "domain": r["domain"], "document_type": r["document_type"],
                   "document_format": r["document_format"],
                   "source_labels": ",".join(sorted({s["label"] for s in r["spans"]}))}))
    return out, dict(sorted(why.items()))


def load(limit=None) -> list:
    return load_source(SOURCE, limit)
