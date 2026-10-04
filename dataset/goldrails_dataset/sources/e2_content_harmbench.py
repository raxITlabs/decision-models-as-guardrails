"""HarmBench text behaviours, test split (edition 2 content, subtask harmful_goal, positives only). MIT.

Plain harmful requests with no attack technique applied, the same shape as JailbreakBench goals, which v1 used up
(all 200 JBB behaviours are in v1). Copyright behaviours are dropped: they ask for song lyrics or book passages, a
harm none of our suites scores. Contextual behaviours carry their context passage before the request, as HarmBench
presents them. Every row is harmful by the benchmark's construction (label_basis human: the authors wrote and
curated each behaviour).

Rows are grouped by BehaviorID so a behaviour and any classifier-validation completion of it
(e2_content_harmbench_cls) land in the same split.
"""
from __future__ import annotations

import csv
import io
import urllib.request

from ..records import Category, Provenance, Record, State, make_id
from .base import now

NAME, LICENCE = "e2_content_harmbench", "mit"
COMMIT = "8e1604d1171fe8a48d8febecd22f600e462bdcdd"   # pinned centerforaisafety/HarmBench commit
URL = f"https://raw.githubusercontent.com/centerforaisafety/HarmBench/{COMMIT}/data/behavior_datasets/harmbench_behaviors_text_test.csv"
UPSTREAM_SPLIT = "test"

# HarmBench SemanticCategory -> AILuminate hazard (record category only; the edition 2 harm tag is set in e2_content)
AILUMINATE = {"chemical_biological": "indiscriminate_weapons", "cybercrime_intrusion": "nonviolent_crimes",
              "illegal": "nonviolent_crimes", "misinformation_disinformation": "defamation",
              "harassment_bullying": "hate", "harmful": None}
BEDROCK = {"indiscriminate_weapons": "MISCONDUCT", "nonviolent_crimes": "MISCONDUCT", "defamation": "INSULTS", "hate": "HATE"}


def rows_from_csv(text: str) -> list:
    return list(csv.DictReader(io.StringIO(text)))


def fetch() -> str:
    return urllib.request.urlopen(URL).read().decode("utf-8")


def text_of(row: dict) -> str:
    ctx = (row.get("ContextString") or "").strip()
    return f"{ctx}\n\n---\n\n{row['Behavior'].strip()}" if ctx else row["Behavior"].strip()


def load(limit=None, rows=None) -> list:
    rows = rows if rows is not None else rows_from_csv(fetch())
    out = []
    for row in rows:
        if row["FunctionalCategory"] == "copyright":
            continue
        ail = AILUMINATE.get(row["SemanticCategory"])
        sid = row["BehaviorID"]
        out.append(Record(
            id=make_id("F1", NAME, sid), feature="F1", subtask="harmful_goal",
            state=State(role="user", text=text_of(row)),
            category=Category(ailuminate=ail, bedrock=BEDROCK.get(ail) if ail else None, source_label=row["SemanticCategory"]),
            labels=["no", "yes"], expected="yes", group=f"harmbench:{sid}",
            provenance=Provenance(source=NAME, source_id=sid, licence=LICENCE, label_basis="human", imported_at=now(),
                                  contamination=["harmbench-public-2024", "jbb-overlap-possible"],
                                  notes=f"functional={row['FunctionalCategory']}; upstream_split={UPSTREAM_SPLIT}; commit={COMMIT}"),
        ))
        if limit and len(out) >= limit:
            break
    return out
