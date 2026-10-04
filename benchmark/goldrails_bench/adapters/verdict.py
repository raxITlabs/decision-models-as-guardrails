"""Base adapter for vendor verdict APIs: OpenAI moderation, hosted guard models, other vendors' decision endpoints.

A verdict API returns its own flag under its own categories. It never reads our questions. A subclass declares, per
task, which of the vendor's categories the suite policy covers (``CATEGORIES``), and implements ``call`` to send one
row and read back the vendor's flag, its per-category scores where it returns any, and its raw response. The base
handles the rest of the contract:

- a task the vendor has no category for is ``not_offered``: no call, not evaluated, no overall rank;
- a call that raises, or returns no flag, is ``failed`` (counted wrong by the scorer);
- ``decision`` is the vendor's own flag over the declared categories, never a threshold we fit;
- ``score`` is the max of the declared categories' scores where the vendor returns scores, else None;
- every result carries the serving config, with the vendor's dated model id as ``model_id``.

Pin a dated model id (``omni-moderation-2024-09-26``, not ``omni-moderation-latest``) so drift checks mean something.

    class OpenAIModerationAdapter(VerdictAPIAdapter):
        name, version, system = "openai-moderation", "1", "openai-moderation"
        CATEGORIES = {("content", "request"): ["hate", "harassment", "sexual", "violence", "illicit"], ...}
        def call(self, state, categories): ...   # -> VendorVerdict
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from ..policy import DEFAULT_POLICY, RetryPolicy, attempt_record
from .base import DECIDED, FAILED, Adapter, AdapterResult, check_task, max_over, serving, state_dict


@dataclass
class VendorVerdict:
    """What one vendor call returned. ``flags`` maps each requested category to the vendor's own flag, ``scores``
    to its score where the vendor returns one. ``flagged`` overrides the any-category rule when the vendor returns
    a single overall flag that covers exactly the requested categories."""
    flags: dict | None = None
    scores: dict | None = None
    flagged: bool | None = None
    model: str | None = None
    usage: Any = None
    raw: Any = None


class _Call:   # the shape policy.attempt_record reads
    def __init__(self, ok, error, latency_s, usage):
        self.ok, self.error, self.latency_s, self.usage = ok, error, latency_s, usage


class VerdictAPIAdapter(Adapter):
    name = "verdict-api"
    version = "0"
    system = "verdict-api"
    CATEGORIES: dict = {}     # (suite, subtask) -> the vendor's category names that this suite policy covers

    def __init__(self, model_id: str, endpoint: str | None = None, revision: str | None = None,
                 max_length: int | None = None, policy: RetryPolicy = DEFAULT_POLICY):
        self.model_id, self.endpoint, self.revision, self.max_length = model_id, endpoint, revision, max_length
        self.policy = policy

    def offers(self, suite: str, subtask: str) -> bool:
        return bool(self.CATEGORIES.get((suite, subtask)))

    def serving(self, served_model: str | None = None, **extra) -> dict:
        return serving(self.endpoint, self.model_id, revision=self.revision, precision=None,
                       max_length=self.max_length, served_model=served_model, adapter=self.adapter,
                       rule="the vendor's own flag over the declared categories", **extra)

    def call(self, state: Any, categories: list) -> VendorVerdict:
        """Send one row; return the vendor's verdict. Raise on any failure: the base records it."""
        raise NotImplementedError

    def evaluate(self, suite: str, subtask: str, row: Any) -> AdapterResult:
        check_task(suite, subtask)
        if not self.offers(suite, subtask):
            return self.not_offered(suite, subtask)
        cats = list(self.CATEGORIES[(suite, subtask)])
        state = state_dict(row)
        attempts, v, error = [], None, None
        t_all = time.perf_counter()
        while True:
            started, t0 = time.time(), time.perf_counter()
            try:
                v, error = self.call(state, cats), None
            except Exception as e:  # noqa: BLE001  a failure is a measurement
                v, error = None, f"{type(e).__name__}: {e}"
            attempts.append(attempt_record(_Call(v is not None, error, time.perf_counter() - t0, getattr(v, "usage", None)),
                                           0, len(attempts) + 1, started=started, ended=time.time()))
            if v is not None or not self.policy.should_retry(error, len(attempts)):
                break
            self.policy.wait(len(attempts))
        latency = round(time.perf_counter() - t_all, 3)
        srv = self.serving(served_model=getattr(v, "model", None), categories=cats)
        if v is None:
            return AdapterResult(None, None, None, FAILED, srv, error=error, latency_s=latency, attempts=attempts)
        flags = {c: bool(f) for c, f in (v.flags or {}).items() if c in cats and f is not None}
        scores = {c: float(s) for c, s in (v.scores or {}).items() if c in cats and isinstance(s, (int, float))}
        if v.flagged is not None:
            decision = bool(v.flagged)
        elif flags:
            decision = any(flags.values())
        else:
            return AdapterResult(None, None, {"flags": flags, "scores": scores}, FAILED, srv,
                                 error="NoDecision: the vendor returned no flag for the declared categories",
                                 latency_s=latency, usage=v.usage, attempts=attempts, raw=v.raw)
        per_q = {"flags": flags, "scores": scores or None}
        return AdapterResult(decision, max_over(scores, cats), per_q, DECIDED, srv, latency_s=latency, usage=v.usage,
                             attempts=attempts, raw=v.raw)
