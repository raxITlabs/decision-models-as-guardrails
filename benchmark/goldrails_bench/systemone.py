"""One client for every system that speaks the System One contract.

Jev (api.typesafe.ai), Kev (local server), and any rebuild that mirrors
`POST /v1/systemone` are called through the official TypeSafe Python SDK with
`base_url` pointed at the system. Retries are disabled on purpose: in a
benchmark a failed request is a measurement, not something to paper over.
The raw response body, latency, usage, and the model id the server reports
are all kept.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from typesafe_sdk import Choice, Noul, RetryPolicy, Score, TypeSafeClient

NO_RETRY = RetryPolicy(max_retries=0, api_connection_error=False, api_timeout_error=False)


def _sdk_version() -> str:
    try:
        from importlib.metadata import version
        return version("typesafe-sdk")
    except Exception:  # noqa: BLE001
        return "unknown"


# Adapter identity: bump ``version`` whenever ``state_of`` or ``build_question`` changes what a system receives. It is
# part of the config hash (runner.config_hash), so rows made by different preprocessing are never one arm. The SDK
# version is included because it serialises the request.
ADAPTER = {"name": "systemone", "version": f"1+typesafe-sdk-{_sdk_version()}"}

STATE_FIELDS = ("role", "text", "context", "tool_call", "source", "query")

# Untrusted retrieved content (F2 indirect: an email, a web page, a tool result) has one representation, shared by
# every adapter. The record marks it with role "tool"; the trust context (system prompt, user query) is in
# ``context``. A System One model receives exactly that: role "tool" plus the context turns. A service without a tool
# role (Bedrock) receives the same text as user-role / INPUT content that starts with UNTRUSTED_PREFIX, never as an
# assistant turn, because an assistant turn tells the checker the assistant wrote the email and Bedrock documents
# prompt-attack checks for input. See benchmark/suites/prompt_attacks/README.md, "Indirect attacks: readiness".
UNTRUSTED_ROLE = "tool"
UNTRUSTED_PREFIX = "[Untrusted retrieved content]"


def untrusted(text: str) -> str:
    """Retrieved text as a service without a tool role receives it: the fixed tag, a newline, the text unchanged."""
    return f"{UNTRUSTED_PREFIX}\n{text}"


def unrepresentable(state, supported: tuple) -> list:
    """State fields present in ``state`` that an adapter cannot send. An adapter that finds any returns a failed call
    naming them instead of silently dropping part of what every other system receives."""
    if isinstance(state, str):
        return []
    return [k for k in STATE_FIELDS if k not in supported and state.get(k)]


@dataclass
class SystemOneCall:
    system: str
    ok: bool
    model: str | None = None
    answers: dict | None = None      # question id -> answer dict as returned
    usage: dict | None = None
    latency_s: float = 0.0
    error: str | None = None
    raw: Any = None


class SystemOneClient:
    adapter = ADAPTER

    def __init__(self, system: str, base_url: str | None = None, api_key: str | None = None,
                 model: str | None = None, timeout: float = 60.0, identity: dict | None = None):
        self.system = system
        self.model = model
        self.identity = identity   # what the model name resolves to (checkpoint ref + revision); part of the ledger's config hash
        self.client = TypeSafeClient(api_key=api_key or ("local" if base_url and "localhost" in base_url else None),
                                     base_url=base_url, model=model, retry=NO_RETRY, timeout=timeout)

    def ask(self, state: Any, questions: dict) -> SystemOneCall:
        qs = {k: build_question(v) for k, v in questions.items()}
        t0 = time.perf_counter()
        try:
            resp = self.client.system_one(state, qs, model=self.model)
        except Exception as e:  # any failure is a recorded failure, never retried here
            return SystemOneCall(system=self.system, ok=False, error=f"{type(e).__name__}: {e}",
                                 latency_s=time.perf_counter() - t0)
        dt = time.perf_counter() - t0
        raw = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
        meta = server_metadata(resp)
        if meta is not None:
            raw["metadata"] = meta
        return SystemOneCall(system=self.system, ok=True, model=raw.get("model"),
                             answers=raw.get("answers"), usage=raw.get("usage"), latency_s=dt, raw=raw)


def server_metadata(resp) -> dict | None:
    """The ``metadata`` object a self-hosted server adds to its response body (Laya reports its input truncation
    there), or None. The SDK's response model ignores fields outside the API schema, so it is read from the body."""
    try:
        body = resp.raw_http_response.json()
    except Exception:  # noqa: BLE001 - no raw response, or a body that is not JSON: nothing extra to keep
        return None
    meta = body.get("metadata") if isinstance(body, dict) else None
    return meta if isinstance(meta, dict) else None


def build_question(q: dict):
    """A question set entry (plain dict, as stored in question_sets/*.json) to an SDK question."""
    t = q["type"]
    if t == "noul":
        return Noul(instructions=q["instructions"], criteria=q.get("criteria"))
    if t == "score":
        return Score(instructions=q["instructions"], criteria=q["criteria"])
    if t == "choice":
        return Choice(instructions=q["instructions"], criteria=q["criteria"])
    raise ValueError(f"unknown question type {t!r}")


def state_of(record) -> dict:
    """The state a decision model sees: role, text, and prior turns. Never the label."""
    s = {"role": record.state.role, "text": record.state.text}
    if record.state.context:
        s["context"] = record.state.context
    if record.state.tool_call:
        s["tool_call"] = record.state.tool_call
    if record.state.source:          # F6: the grounding source the reply must be judged against
        s["source"] = record.state.source
    if record.state.query:           # F6: the query the reply must answer
        s["query"] = record.state.query
    return s
