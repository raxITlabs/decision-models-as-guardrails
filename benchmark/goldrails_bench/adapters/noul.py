"""The reference adapter for Noul models: Jev, Kev, Open-Jev, Laya and anything else that speaks System One.

It sends the row's state with the edition's frozen question set for the suite (``benchmark/question_sets/e2/``) and
applies the v2.0 out-of-the-box rule: the decision score is the max over the set's decision Nouls, and the row is
flagged when that score is >= 0.5. Nothing is fitted per model. Questions outside the decision list (severity,
contains_pii) are kept in ``per_question`` and never enter the score.

The question wording is TypeSafe's native format, which favours Jev; contract v2.0 discloses that. The sets are
frozen per edition and chosen by rule, not by results (see the e2 README).

    from goldrails_bench.systemone import SystemOneClient
    a = NoulAdapter(SystemOneClient("jev-1.13.0", model="jev-1.13.0"), endpoint="https://api.typesafe.ai")
    res = a.evaluate("content", "request", record)
"""
from __future__ import annotations

import time
from typing import Any

from .. import question_sets
from ..policy import DEFAULT_POLICY, RetryPolicy, ask_with_policy
from .base import DECIDED, FAILED, THRESHOLD, Adapter, AdapterResult, check_task, max_over, serving, state_dict

EDITION = "e2"
# (suite, subtask) -> the frozen e2 question set the Noul adapter sends.
TASK_QSET = {("content", "request"): "f1-bedrock5", ("content", "reply"): "f1-bedrock5",
             ("prompt_attacks", "direct"): "f2-attacks",
             ("prompt_attacks", "indirect"): "f2-attacks-indirect",       # owner ruling 28
             ("denied_topics", "topic"): "f3-topics",
             ("word_filters", "word"): "f4-words", ("word_filters", "profanity"): "f4-obscenity",
             ("sensitive_info", "entity_detection"): "f5-pii",
             ("grounding", "grounding"): "f6-grounding", ("grounding", "relevance"): "f6-grounding"}
# Subtasks that share a set but decide on a different question than the set's own decision list.
DECISION_OVERRIDE = {("grounding", "relevance"): ["irrelevant"]}
RULE = f"max over the decision Nouls >= {THRESHOLD}"


def decision_keys(suite: str, subtask: str, qs: dict) -> list:
    return list(DECISION_OVERRIDE.get((suite, subtask)) or qs["decision"])


def truncation_of(call) -> dict | None:
    """The input-truncation report a server sent in ``metadata.truncation`` (Laya's server does), or None."""
    meta = (call.raw or {}).get("metadata") if isinstance(call.raw, dict) else None
    rep = meta.get("truncation") if isinstance(meta, dict) else None
    return rep if isinstance(rep, dict) and isinstance(rep.get("truncated"), bool) else None


LAYA_MAX_LEN = 512   # tokens per question: the English checkpoint's max_len (rl_agent_config.json), kept by ruling 16


def usage_truncation(call, n_questions: int, cap: int) -> dict | None:
    """Laya's truncation read from ``usage.input_tokens`` alone, for a server that sends no ``metadata.truncation``.

    Laya scores one sequence per question in a padded batch and reports ``input_tokens`` as questions x the padded
    length, and no sequence is longer than ``cap``. So a count at ``n_questions * cap`` or more means the longest
    sequence reached the cap: the row is marked truncated (owner ruling 16). A count below it is not taken as proof
    that nothing was cut, so it returns None and the result stays unknown."""
    used = (call.usage or {}).get("input_tokens") if isinstance(call.usage, dict) else None
    if not isinstance(used, int) or isinstance(used, bool) or n_questions < 1 or used < n_questions * cap:
        return None
    return {"truncated": True, "basis": "usage.input_tokens at the per-question cap", "usage_input_tokens": used,
            "questions": n_questions, "max_len": cap}


def answer_value(a: Any):
    """A Noul answer as its probability; any other answer type is kept as returned."""
    if isinstance(a, dict) and a.get("type") == "noul" and isinstance(a.get("noul"), (int, float)):
        return float(a["noul"])
    return a


class NoulAdapter(Adapter):
    name = "noul-e2"
    version = "1"

    def __init__(self, client, endpoint: str | None = None, revision: str | None = None, precision: str | None = None,
                 max_length: int | None = None, policy: RetryPolicy = DEFAULT_POLICY, edition: str = EDITION):
        """``client`` is a ``systemone.SystemOneClient`` (or anything with ``system``, ``model`` and ``ask``). The
        serving fields default to what the client's identity holds (``revision``, ``precision``, ``max_length``),
        so a served checkpoint's identity from ``endpoints.resolve_models`` fills them without repeating it."""
        self.client = client
        self.system = client.system
        ident = getattr(client, "identity", None) or {}
        sdk_url = getattr(getattr(client, "client", None), "base_url", None)
        self.endpoint = endpoint or getattr(client, "endpoint", None) or (str(sdk_url) if sdk_url else None)
        self.revision = revision or ident.get("revision")
        self.precision = precision or ident.get("precision")
        self.max_length = max_length or ident.get("max_length")
        self.policy = policy
        self.edition = edition
        self._qsets: dict = {}

    def question_set(self, suite: str, subtask: str) -> tuple[str, dict]:
        name = TASK_QSET[(suite, subtask)]
        if name not in self._qsets:
            self._qsets[name] = question_sets.load(self.edition, name)
        return f"{self.edition}-{name}", self._qsets[name]

    def offers(self, suite: str, subtask: str) -> bool:
        return (suite, subtask) in TASK_QSET

    def serving(self, served_model: str | None = None, **extra) -> dict:
        max_length = extra.pop("max_length", self.max_length)   # a server-reported context fills an unpinned one
        return serving(self.endpoint, getattr(self.client, "model", None), revision=self.revision,
                       precision=self.precision, max_length=max_length, served_model=served_model,
                       identity=getattr(self.client, "identity", None), adapter=self.adapter, **extra)

    def evaluate(self, suite: str, subtask: str, row: Any) -> AdapterResult:
        check_task(suite, subtask)
        if not self.offers(suite, subtask):
            return self.not_offered(suite, subtask)
        qname, qs = self.question_set(suite, subtask)
        keys = decision_keys(suite, subtask, qs)
        extra = {"question_set": qname, "decision_keys": keys, "rule": RULE, "threshold": THRESHOLD}
        t0 = time.perf_counter()
        call, attempts = ask_with_policy(self.client, state_dict(row), qs["questions"], self.policy)
        latency = round(time.perf_counter() - t0, 3)
        trunc = truncation_of(call) if call.ok else None
        ctx = self.context_of(trunc, call.ok)
        if call.ok and trunc is None and self.is_laya():
            trunc = usage_truncation(call, len(qs["questions"]), self.max_length or LAYA_MAX_LEN)
            if trunc:
                ctx["truncation_basis"] = "usage"
        elif trunc:   # a hosted client's own flag (Clef: usage at the hosted context) says so in basis_kind
            ctx["truncation_basis"] = trunc.get("basis_kind", "server")
        srv = self.serving(served_model=call.model, **extra, **ctx)
        cut = {"truncated": trunc["truncated"], "truncation": trunc} if trunc else {}
        if not call.ok:
            return AdapterResult(None, None, None, FAILED, srv, error=call.error, latency_s=latency,
                                 usage=call.usage, attempts=attempts, raw=call.raw)
        per_q = {k: answer_value(a) for k, a in (call.answers or {}).items()}
        score = max_over(per_q, keys)
        if score is None:
            return AdapterResult(None, None, per_q, FAILED, srv, error="NoDecision: no decision question was answered",
                                 latency_s=latency, usage=call.usage, attempts=attempts, raw=call.raw, **cut)
        return AdapterResult(score >= THRESHOLD, score, per_q, DECIDED, srv, latency_s=latency, usage=call.usage,
                             attempts=attempts, raw=call.raw, **cut)

    def context_of(self, trunc: dict | None, answered: bool) -> dict:
        """Serving fields for a server that reports its context. The context the server ran at (Laya: the
        checkpoint's ``max_len``) fills ``max_length`` when the identity did not pin one. A Laya result without a
        report says so, so a ledger from a server that predates the report cannot pass as untruncated."""
        if trunc:
            out = {"truncation_reported": trunc.get("basis_kind", "server") == "server", "head_max_length": trunc.get("head_max_len"),
                   "encoder_max_positions": trunc.get("encoder_max_positions")}
            if trunc.get("max_len") is not None:
                out["served_max_length"] = trunc["max_len"]
                if self.max_length is None:
                    out["max_length"] = trunc["max_len"]
            return out
        return {"truncation_reported": False} if self.is_laya() and answered else {}

    def is_laya(self) -> bool:
        return (getattr(self.client, "identity", None) or {}).get("kind") == "laya"
