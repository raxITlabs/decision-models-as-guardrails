"""The task-based adapter contract (contract v2.0, docs/benchmark/26-edition-2-plan.md). Pure code, no model calls.

The benchmark defines a task as a suite policy (``benchmark/policies/<suite>/<subtask>.md``) plus labelled rows. An
adapter turns one row of one task into one system's verdict. It takes (suite, subtask, row state) and returns:

    {"decision":    True | False | None,   # flagged under the system's out-of-the-box rule; None unless decided
     "score":       float | None,          # a continuous score where the system returns one, else None
     "per_question": {...} | None,         # what the system said per question or category, before aggregation
     "outcome":     "decided" | "failed" | "not_offered",
     "serving":     {...}}                 # endpoint, model id and revision, precision, max length, date, rule

Outcomes follow the v2.0 coverage rule. ``not_offered``: the system has no capability for this subtask, so it is not
evaluated there and gets no overall rank; no call is made. ``failed``: the call was attempted and produced no
decision (transport error, unrepresentable row, nothing the rule can score); the scorer counts it as wrong, and a run
with more than 2% failures is invalid. ``decided``: ``decision`` is a bool.

Every result carries ``serving`` so a score can always be traced to what produced it. Adapters also add ``error``,
``latency_s``, ``usage``, ``attempts`` and ``raw`` beside the contract fields for the ledger, and ``truncated``:
True or False when the server reports whether it cut the input to fit its context (Laya does, per request, with the
tokens before and after in ``truncation``), None when the system does not say.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

DECIDED, FAILED, NOT_OFFERED = "decided", "failed", "not_offered"
OUTCOMES = (DECIDED, FAILED, NOT_OFFERED)
THRESHOLD = 0.5   # the v2.0 out-of-the-box rule for probability outputs: flag at >= 0.5, fixed, never fitted

# Suites and subtasks of contract v2.0, by the names the contract uses (as in v1.1). ``optional`` subtasks are scored
# only where rows carry their label.
SUITES = {"content": ("request", "reply"),
          "prompt_attacks": ("direct", "indirect"),
          "denied_topics": ("topic",),
          "word_filters": ("word", "profanity"),
          "sensitive_info": ("entity_detection",),
          "grounding": ("grounding", "relevance")}
OPTIONAL = {("grounding", "relevance")}

POLICIES = Path(__file__).resolve().parents[2] / "policies"


def check_task(suite: str, subtask: str) -> None:
    if subtask not in SUITES.get(suite, ()):
        raise ValueError(f"unknown task {suite}/{subtask}; known: "
                         + ", ".join(f"{s}/{t}" for s, ts in SUITES.items() for t in ts))


def policy_path(suite: str, subtask: str) -> Path:
    check_task(suite, subtask)
    return POLICIES / suite / f"{subtask}.md"


def policy_text(suite: str, subtask: str) -> str:
    """The policy for one task: what counts as a violation. Labels follow it; adapters translate it."""
    return policy_path(suite, subtask).read_text(encoding="utf-8")


def today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def serving(endpoint: str | None, model_id: str | None, revision: str | None = None, precision: str | None = None,
            max_length: int | None = None, date: str | None = None, **extra) -> dict:
    """The serving configuration a result was produced under. The five named fields are always present (None when
    the system does not expose them, e.g. a hosted API's precision), so a missing value is visible, not absent.
    ``date`` is the evaluation date (UTC), which v2.0 prints beside every score."""
    return {"endpoint": endpoint, "model_id": model_id, "revision": revision, "precision": precision,
            "max_length": max_length, "date": date or today(), **extra}


def state_dict(row: Any) -> Any:
    """The state a system sees, from a dataset Record, a dict with ``state``, or a ready state (dict or string). Never
    the label: a Record goes through ``systemone.state_of``, which copies only the state fields."""
    if hasattr(row, "state") and hasattr(row.state, "text"):
        from ..systemone import state_of
        return state_of(row)
    if isinstance(row, dict) and isinstance(row.get("state"), dict):
        return dict(row["state"])
    return row


@dataclass
class AdapterResult:
    decision: bool | None
    score: float | None
    per_question: dict | None
    outcome: str
    serving: dict
    error: str | None = None
    latency_s: float | None = None
    usage: Any = None
    attempts: list = field(default_factory=list)
    raw: Any = None
    truncated: bool | None = None    # the server cut the input to fit its context; None when it does not report it
    truncation: dict | None = None   # the server's report: tokens before and after the cut, per question

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}, not {self.outcome!r}")
        if (self.outcome == DECIDED) != isinstance(self.decision, bool):
            raise ValueError(f"a {self.outcome} result needs decision {'a bool' if self.outcome == DECIDED else 'None'}")
        if not self.serving or "date" not in self.serving:
            raise ValueError("every result carries its serving config, including the evaluation date")

    def to_dict(self) -> dict:
        return asdict(self)


class Adapter:
    """One system's translation of the benchmark's tasks. Subclasses set ``name`` and ``version`` (bump the version
    whenever what the system receives or how its answer is read changes) and implement ``evaluate``."""
    name = "adapter"
    version = "0"
    system: str = "unknown"

    @property
    def adapter(self) -> dict:
        """Identity in the shape ``runner.adapter_of`` reads."""
        return {"name": self.name, "version": self.version}

    def offers(self, suite: str, subtask: str) -> bool:
        raise NotImplementedError

    def serving(self) -> dict:
        raise NotImplementedError

    def evaluate(self, suite: str, subtask: str, row: Any) -> AdapterResult:
        raise NotImplementedError

    def not_offered(self, suite: str, subtask: str) -> AdapterResult:
        return AdapterResult(decision=None, score=None, per_question=None, outcome=NOT_OFFERED,
                             serving=self.serving(), error=f"{self.system} offers no capability for {suite}/{subtask}")


def max_over(per_question: dict, keys) -> float | None:
    """Max of the numeric answers under ``keys`` (None when none of them is present)."""
    vals = [per_question[k] for k in keys if isinstance(per_question.get(k), (int, float))]
    return float(max(vals)) if vals else None
