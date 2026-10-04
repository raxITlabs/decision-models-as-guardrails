"""XSTest v2 prompts (Röttger et al., NAACL 2024), 250 safe and 200 unsafe (edition 2 content, subtask harmful_goal).
CC-BY-4.0.

Plain requests with no attack technique. Each unsafe "contrast" prompt mirrors safe prompts of the same type and
position (contrast_homonyms #k <-> homonyms #k; contrast_discr #k <-> both discrimination types #k; contrast_privacy
#k <-> both privacy types #k), so they form one group and never straddle splits: the pair is what makes the
benign side hard. Labels are the authors' (label_basis human). The set is a test set only; there is no train split.
"""
from __future__ import annotations

import csv
import io
import urllib.request

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "e2_content_xstest", "cc-by-4.0"
COMMIT = "d7bb5bd738c1fcbc36edd83d5e7d1b71a3e2d84d"   # pinned paul-rottger/xstest commit
URL = f"https://raw.githubusercontent.com/paul-rottger/xstest/{COMMIT}/xstest_prompts.csv"
UPSTREAM_SPLIT = "test"
BASE = {"nons_group_real_discr": "discr", "real_group_nons_discr": "discr", "contrast_discr": "discr",
        "privacy_public": "privacy", "privacy_fictional": "privacy", "contrast_privacy": "privacy"}


def base_type(t: str) -> str:
    return BASE.get(t, t[len("contrast_"):] if t.startswith("contrast_") else t)


def rows_from_csv(text: str) -> list:
    return list(csv.DictReader(io.StringIO(text)))


def fetch() -> str:
    return urllib.request.urlopen(URL).read().decode("utf-8")


def load(limit=None, rows=None) -> list:
    rows = rows if rows is not None else rows_from_csv(fetch())
    first_of_type: dict = {}
    for row in rows:
        first_of_type.setdefault(row["type"], int(row["id"]))
    out = []
    for row in rows:
        unsafe = row["label"] == "unsafe"
        pos = int(row["id"]) - first_of_type[row["type"]]          # position within its 25-prompt type block
        out.append(Record(
            id=make_id("F1", NAME, row["id"]), feature="F1", subtask="harmful_goal",
            state=State(role="user", text=row["prompt"].strip()),
            category=Category(ailuminate=None if unsafe else "benign", bedrock=None if unsafe else "NONE", source_label=row["type"]),
            labels=["no", "yes"], expected="yes" if unsafe else "no", group=f"xstest:{base_type(row['type'])}:{pos}",
            provenance=Provenance(source=NAME, source_id=row["id"], licence=LICENCE, label_basis="human", imported_at=now(),
                                  contamination=["xstest-public-2023"],
                                  notes=f"type={row['type']}; focus={row.get('focus')}; note={row.get('note')}; commit={COMMIT}"),
        ))
        if limit and len(out) >= limit:
            break
    return out
