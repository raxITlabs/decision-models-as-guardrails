"""Hosted decision-model APIs that take System One's request shape at a different URL (docs/benchmark/28).

Each client has the ``ask(state, questions) -> SystemOneCall`` shape ``systemone.SystemOneClient`` has, so the
unchanged ``NoulAdapter`` and ``policy.ask_with_policy`` drive them:

- ``CloudflareSystemOneClient``: Workers AI ``@cf/cloudflare/clef`` and ``@cf/cloudflare/clef-flash``.
- ``PerplexityDecisionsClient``: ``POST https://api.perplexity.ai/v1/decisions``, ``pplx-decider-v1-27b``.
- ``OpenAIDecisionsClient``: ``POST https://api.openai.com/v1/decisions``, ``gpt-6-luna`` (public beta). Its API has
  no roles and its own question type, so the state is serialised to one text string and each Noul question becomes a
  predicate (``OPENAI_INPUT_MAPPING``, recorded in the identity and disclosed with the results).

For Clef and pplx-decider the request body is the System One body (``model``, ``state``, ``questions``), with each
question serialised by the TypeSafe SDK's own question classes, so every system receives the same bytes for the same
question set.

Errors. A client never retries. It turns each transport failure into a failed call whose error starts with a class
name, and the run's retry policy (``policy.TRANSIENT``) decides what is retried: HTTP 429 is ``RateLimitError``,
5xx is ``InternalServerError`` (503 ``ServiceUnavailableError``), timeouts and connection drops keep httpx's class
names (``ReadTimeout``, ``ConnectError``...). Any other HTTP error, an error envelope, an unreadable body or a
response with no answers is final (``HTTPError``, ``APIError``, ``BadResponse``). An answer is never retried.

Nothing here reads a key at import time. ``from_env`` returns None (not configured) when a credential is missing.
"""
from __future__ import annotations

import os
import re
import threading
import time
from typing import Any

import httpx

from .systemone import UNTRUSTED_PREFIX, UNTRUSTED_ROLE, SystemOneCall, build_question, untrusted

DEFAULT_TIMEOUT = 60.0


class Throttle:
    """At most ``rate`` request starts per second across threads, and a shared pause after a 429's Retry-After.

    ``hold(seconds)`` pushes the next start back for every caller, so one throttled worker slows the whole pool
    instead of each worker hammering the API in turn."""

    def __init__(self, rate: float, clock=time.monotonic, sleep=time.sleep):
        self.interval = 1.0 / rate if rate else 0.0
        self.clock, self.sleep = clock, sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self.clock()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            self.sleep(start - now)

    def hold(self, seconds: float) -> None:
        with self._lock:
            self._next = max(self._next, self.clock() + seconds)


def retry_after_s(headers, cap: float = 60.0) -> float | None:
    """Retry-After in seconds (delta-seconds form only; an HTTP date is ignored), capped."""
    v = (headers or {}).get("retry-after")
    try:
        return min(max(float(v), 0.0), cap) if v is not None else None
    except (TypeError, ValueError):
        return None


def status_error(code: int, body: str = "") -> str:
    """An HTTP status as an error string whose class name the run's retry policy reads."""
    detail = re.sub(r"\s+", " ", body or "")[:200]
    if code == 429:
        name = "RateLimitError"
    elif code == 503:
        name = "ServiceUnavailableError"
    elif code >= 500:
        name = "InternalServerError"
    else:
        name = "HTTPError"
    return f"{name}: HTTP {code}" + (f" {detail}" if detail else "")


def normalise_answers(answers: Any) -> dict | None:
    """Answers as ``{question id: answer dict}``. Accepts the System One mapping, a list of ``{"id": ...}`` items,
    and bare probabilities (taken as Noul answers). Returns None for anything else."""
    if isinstance(answers, list):
        out = {}
        for a in answers:
            if not isinstance(a, dict) or not isinstance(a.get("id") or a.get("name"), str):
                return None
            a = dict(a)
            out[a.pop("id", None) or a.pop("name")] = a
        answers = out
    if not isinstance(answers, dict):
        return None
    out = {}
    for k, a in answers.items():
        if isinstance(a, bool):
            return None
        if isinstance(a, (int, float)):
            a = {"type": "noul", "noul": float(a)}
        elif isinstance(a, dict) and "noul" not in a and isinstance(a.get("probability"), (int, float)) \
                and a.get("type", "noul") == "noul":
            a = {**a, "type": "noul", "noul": float(a["probability"])}
        out[k] = a
    return out


class HostedDecisionClient:
    """Shared HTTP plumbing. Subclasses set ``url``, ``body`` and ``unwrap``."""
    provider = "hosted"
    adapter = {"name": "hosted-systemone", "version": "1"}

    def __init__(self, system: str, model: str, url: str, api_key: str, *, identity: dict | None = None,
                 timeout: float = DEFAULT_TIMEOUT, http: httpx.Client | None = None, throttle: Throttle | None = None,
                 sleep=time.sleep):
        if not api_key:
            raise ValueError(f"{system}: no API key")
        self.system, self.model, self.url = system, model, url
        self.identity = identity
        self.throttle = throttle
        self.sleep = sleep
        self._key = api_key
        self.http = http or httpx.Client(timeout=timeout)

    def __repr__(self):   # never print the key
        return f"{type(self).__name__}(system={self.system!r}, model={self.model!r}, url={self.url!r})"

    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    def body(self, state: Any, questions: dict) -> dict:
        qs = {k: build_question(v).model_dump(exclude_none=True) for k, v in questions.items()}
        return {"model": self.model, "state": state, "questions": qs}

    def unwrap(self, payload: Any) -> tuple[dict | None, str | None]:
        """(the System One response object, error) from the parsed body."""
        return (payload, None) if isinstance(payload, dict) else (None, "BadResponse: body is not a JSON object")

    def on_status(self, resp: httpx.Response) -> str:
        return status_error(resp.status_code, resp.text)

    def response_meta(self, resp: httpx.Response) -> dict | None:
        """Response headers worth keeping as serving identity (none by default)."""
        return None

    def check(self, call: SystemOneCall) -> SystemOneCall:
        """A last look at a successful call (identity checks, truncation flags). Returns the call to record."""
        return call

    def ask(self, state: Any, questions: dict) -> SystemOneCall:
        body = self.body(state, questions)
        if self.throttle:
            self.throttle.wait()
        t0 = time.perf_counter()
        try:
            resp = self.http.post(self.url, json=body, headers=self.headers())
        except httpx.HTTPError as e:   # timeouts, connection drops: keep httpx's class name for the retry policy
            return SystemOneCall(system=self.system, ok=False, error=f"{type(e).__name__}: {str(e)[:200]}",
                                 latency_s=time.perf_counter() - t0)
        dt = time.perf_counter() - t0
        if resp.status_code >= 400:
            return SystemOneCall(system=self.system, ok=False, error=self.on_status(resp), latency_s=dt,
                                 raw={"status": resp.status_code})
        try:
            payload = resp.json()
        except ValueError:
            return SystemOneCall(system=self.system, ok=False, error="BadResponse: body is not JSON", latency_s=dt)
        result, err = self.unwrap(payload)
        if err:
            return SystemOneCall(system=self.system, ok=False, error=err, latency_s=dt, raw=payload)
        answers = normalise_answers(result.get("answers"))
        if not answers:
            return SystemOneCall(system=self.system, ok=False, error="BadResponse: no answers in the response",
                                 latency_s=dt, raw=payload)
        usage = result.get("usage") if isinstance(result.get("usage"), dict) else None
        raw = dict(result)
        raw["answers"] = answers
        if payload is not result and "result" in payload:
            raw["envelope"] = {k: v for k, v in payload.items() if k != "result"}
        meta = self.response_meta(resp)
        if meta:
            raw["response_headers"] = meta
        call = SystemOneCall(system=self.system, ok=True, model=result.get("model"), answers=answers, usage=usage,
                             latency_s=dt, raw=raw)
        return self.check(call)


# --- Cloudflare Workers AI: Clef and Clef-flash ---------------------------------------------------------------------

CLOUDFLARE_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"
CLEF = {  # system name -> (Workers AI model id, Hugging Face weights, pinned revision for provenance)
    "clef": ("@cf/cloudflare/clef", "Cloudflare/clef", "2f3de3dd85f379784083b0814d997ab627200f0c"),
    "clef-flash": ("@cf/cloudflare/clef-flash", "Cloudflare/clef-flash", "17f0b0ad64efb65d273590632833508766b2aae6"),
}
CLEF_CONTEXT = 65_536   # hosted context in tokens (Workers AI model page, read 2 October 2026)
CAPPED_AT = 0.99        # usage.input_tokens at >= 99% of the context looks capped: flag possible truncation


class CloudflareSystemOneClient(HostedDecisionClient):
    """Clef on Workers AI. The model is in the URL; the body is the System One body without ``model``. Workers AI
    wraps responses as ``{"result": ..., "success": ..., "errors": [...], "messages": [...]}``; both the wrapped and
    an unwrapped System One body are read. The hosted model is not version-pinned: ``identity.revision`` is the
    Hugging Face commit of the open weights, recorded for provenance, not proof of what served the call."""
    provider = "cloudflare-workers-ai"
    adapter = {"name": "cloudflare-systemone", "version": "1"}

    def __init__(self, system: str, account_id: str, api_token: str, **kw):
        if system not in CLEF:
            raise ValueError(f"unknown Clef system {system!r}; known: {sorted(CLEF)}")
        if not account_id or not re.fullmatch(r"[0-9a-fA-F]{32}", account_id):
            raise ValueError("CLOUDFLARE_ACCOUNT_ID must be the 32-hex account id")
        model, ref, rev = CLEF[system]
        identity = {"provider": self.provider, "model": model, "ref": ref, "revision": rev,
                    "revision_basis": "Hugging Face commit of the open weights, for provenance; the hosted model is not pinned",
                    "max_length": CLEF_CONTEXT, "precision": None}
        super().__init__(system, model, CLOUDFLARE_URL.format(account=account_id, model=model), api_token,
                         identity=identity, **kw)
        self.endpoint = CLOUDFLARE_URL.format(account="{ACCOUNT_ID}", model=model)   # recorded without the account

    @classmethod
    def from_env(cls, system: str, env=os.environ, **kw):
        # Cloudflare's own examples call the token CLOUDFLARE_AUTH_TOKEN; either name works.
        acct = env.get("CLOUDFLARE_ACCOUNT_ID")
        tok = env.get("CLOUDFLARE_API_TOKEN") or env.get("CLOUDFLARE_AUTH_TOKEN")
        return cls(system, acct, tok, **kw) if acct and tok else None

    def body(self, state, questions):
        # Workers AI requires "model": "clef" or "clef-flash" in the body as well as the model id in the URL
        # (Clef model page, input schema, read 5 October 2026).
        b = super().body(state, questions)
        b["model"] = self.system
        return b

    def unwrap(self, payload):
        if not isinstance(payload, dict):
            return None, "BadResponse: body is not a JSON object"
        if "result" not in payload and "success" not in payload:
            return payload, None   # unwrapped System One body
        if payload.get("success") is False or payload.get("errors"):
            errs = "; ".join(f"{e.get('code', '')} {e.get('message', '')}".strip() if isinstance(e, dict) else str(e)
                             for e in payload.get("errors") or []) or "success false"
            return None, f"APIError: {errs[:200]}"
        if not isinstance(payload.get("result"), dict):
            return None, "BadResponse: envelope has no result object"
        return payload["result"], None

    def check(self, call):
        call.model = call.model or self.model
        used = (call.usage or {}).get("input_tokens")
        if isinstance(used, int) and not isinstance(used, bool) and used >= CAPPED_AT * CLEF_CONTEXT:
            call.raw.setdefault("metadata", {})["truncation"] = {
                "truncated": True, "possible": True, "basis_kind": "usage",
                "basis": f"usage.input_tokens {used} at the hosted {CLEF_CONTEXT}-token context: Workers AI may have "
                         "cut the input without saying so", "usage_input_tokens": used, "max_len": CLEF_CONTEXT}
        return call


# --- Perplexity Decisions API ---------------------------------------------------------------------------------------

PERPLEXITY_URL = "https://api.perplexity.ai/v1/decisions"
PPLX_MODEL = "pplx-decider-v1-27b"
PPLX_WEIGHTS = ("perplexity-ai/pplx-decider-v1-27b", "5117a6c7fe73b19308dc1a6b0fb529a40c2ecad4")
PPLX_CONTEXT = 262_144   # hosted input limit in tokens (Perplexity docs, read 2 October 2026)
PPLX_RATE = 5.0          # requests/s, half the documented 10/s organisation limit
JEV_NAME = re.compile(r"^(open-)?jev([-_.].*)?$", re.I)


class ModelIdentityError(ValueError):
    pass


class PerplexityDecisionsClient(HostedDecisionClient):
    """pplx-decider-v1-27b on Perplexity's Decisions API, throttled to 5 requests/s across threads.

    The open-source server of this model answers to ``jev-latest`` / ``jev-1.13.0``, so a response that reports a
    Jev name cannot be told apart from Jev in a ledger. The client keeps the model name the response reports and
    fails the call (``ModelIdentityError``, never retried) when that name is a Jev name; it refuses to be built
    under a Jev system or model name at all. HTTP 504 is final (``GatewayTimeout``): Perplexity returns it for a
    request the backend could not finish, and resending the same row does not change that. A 429 pauses the
    shared throttle for Retry-After seconds before the run's retry policy sends again."""
    provider = "perplexity"
    adapter = {"name": "perplexity-decisions", "version": "1"}

    def __init__(self, api_key: str, system: str = PPLX_MODEL, model: str = PPLX_MODEL, url: str = PERPLEXITY_URL,
                 throttle: Throttle | None = None, **kw):
        if JEV_NAME.match(system) or JEV_NAME.match(model):
            raise ModelIdentityError(f"refusing to record Perplexity results under a Jev name ({system!r}, {model!r})")
        identity = {"provider": self.provider, "model": model, "ref": PPLX_WEIGHTS[0], "revision": PPLX_WEIGHTS[1],
                    "revision_basis": "Hugging Face commit of the open weights, for provenance; the hosted model is not pinned",
                    "max_length": PPLX_CONTEXT, "precision": None}
        super().__init__(system, model, url, api_key, identity=identity,
                         throttle=throttle if throttle is not None else Throttle(PPLX_RATE), **kw)
        self.endpoint = url

    @classmethod
    def from_env(cls, env=os.environ, **kw):
        key = env.get("PERPLEXITY_API_KEY")
        return cls(key, **kw) if key else None

    def on_status(self, resp):
        # Perplexity's docs say to retry 5xx (including the ~60 s 504 timeout) with backoff, so 504 takes the
        # shared InternalServerError path, which the run's retry policy retries (docs read 5 October 2026).
        if resp.status_code == 429:
            wait = retry_after_s(resp.headers)
            if wait is not None and self.throttle:
                self.throttle.hold(wait)
            return status_error(429, f"retry-after {wait}s" if wait is not None else "")
        return super().on_status(resp)

    def check(self, call):
        reported = call.model
        call.raw["reported_model"] = reported
        if isinstance(reported, str) and JEV_NAME.match(reported):
            return SystemOneCall(system=self.system, ok=False, model=reported, usage=call.usage,
                                 latency_s=call.latency_s, raw={"reported_model": reported},
                                 error=f"ModelIdentityError: the response reports model {reported!r}, a Jev name; "
                                       "refusing to record it as pplx-decider-v1-27b")
        return call


# --- OpenAI Decisions API -------------------------------------------------------------------------------------------

OPENAI_URL = "https://api.openai.com/v1/decisions"
OPENAI_MODEL = "gpt-6-luna"
OPENAI_RATE = 5.0   # requests/s across threads; OpenAI publishes no Decisions API rate limit for the beta
OPENAI_DOCS = "OpenAI Decisions API docs (public beta), as pasted by the project owner on 7 October 2026"
# Response headers kept as serving identity: version and model headers only. Organisation, project and request ids
# identify the account or one call, not the model, and are never recorded.
OPENAI_KEEP_HEADERS = re.compile(r"^(openai-version|openai-model|x-model[-a-z]*|x-openai-model[-a-z]*)$", re.I)
OPENAI_HEADER_DENY = re.compile(r"organi[sz]ation|project|request-id|ratelimit|processing-ms|cookie|auth", re.I)
ROLE_LABELS = {"user": "User", "assistant": "Assistant", "system": "System", UNTRUSTED_ROLE: "Tool"}
# How the System One state becomes the one text string the API takes (input: a string or user messages only). This
# dict is recorded in the identity, so the mapping travels with every result.
OPENAI_INPUT_MAPPING = {
    "input": "one text string (the API takes a string or user messages only; no system, assistant or tool role)",
    "sections": "blank-line separated, in this order, each only when the state has it: 'Context turns:' then one "
                "'Role: text' line per earlier turn (System, User, Assistant, Tool); 'Source document:' then "
                "state.source; 'Query:' then state.query; 'Tool call:' then state.tool_call as sorted JSON; "
                "'Text under review (<role>):' then state.text",
    "untrusted": f"a tool-role text (retrieved content: email, web page, tool output) is tagged '{UNTRUSTED_PREFIX}' "
                 "on its own line, the same tag Bedrock receives",
    "questions": "each Noul question becomes a predicate: name = the question key, instructions = the question's "
                 "instructions, then 'Answer true if: <criteria.true>' and 'Answer false if: <criteria.false>'; all "
                 "of a row's predicates go in one request; a Score or Choice question (content's severity) is not "
                 "sent: it is outside every decision list",
    "answer": "answers[].probability of each predicate is read as the Noul probability; the fixed 0.5 rule applies",
}
INPUT_MAPPING_VERSION = "1"


def _turn(t: Any) -> tuple[str, str]:
    if isinstance(t, dict):
        return str(t.get("role") or "user"), str(t.get("text") if t.get("text") is not None else t.get("content") or "")
    return "user", str(t)


def serialise_state(state: Any) -> str:
    """The System One state as the one text string the Decisions API takes (``OPENAI_INPUT_MAPPING``)."""
    import json as _json
    if isinstance(state, str):
        return state
    parts = []
    turns = state.get("context") or []
    if turns:
        lines = []
        for role, text in map(_turn, turns):
            label = ROLE_LABELS.get(role, role.capitalize())
            lines.append(f"{label}: {untrusted(text) if role == UNTRUSTED_ROLE else text}")
        parts.append("Context turns:\n" + "\n".join(lines))
    if state.get("source"):
        parts.append(f"Source document:\n{state['source']}")
    if state.get("query"):
        parts.append(f"Query:\n{state['query']}")
    if state.get("tool_call"):
        parts.append("Tool call:\n" + _json.dumps(state["tool_call"], ensure_ascii=False, sort_keys=True))
    role = str(state.get("role") or "user")
    text = str(state.get("text") or "")
    parts.append(f"Text under review ({role}):\n{untrusted(text) if role == UNTRUSTED_ROLE else text}")
    return "\n\n".join(parts)


def predicate_of(name: str, q: dict) -> dict | None:
    """A Noul question as a Decisions API predicate, or None for a question type that is not sent."""
    if q.get("type") != "noul":
        return None
    text = str(q["instructions"]).strip()
    crit = q.get("criteria") or {}
    if crit.get("true"):
        text += f"\nAnswer true if: {str(crit['true']).strip()}"
    if crit.get("false"):
        text += f"\nAnswer false if: {str(crit['false']).strip()}"
    return {"type": "predicate", "name": name, "instructions": text}


class AccessPending(RuntimeError):
    pass


class OpenAIDecisionsClient(HostedDecisionClient):
    """gpt-6-luna on OpenAI's Decisions API (public beta; ``OPENAI_DOCS``).

    Request: ``{"model", "input", "questions"}``. ``input`` is ``serialise_state(state)``, one string, because the API
    takes only a string or user messages; ``questions`` holds one predicate per Noul question of the row's question
    set (``predicate_of``), all in one request. Response: ``{"answers": [{"type": "predicate", "name", "probability"}]}``.
    Each predicate's probability becomes a Noul answer under the question's key. A response that leaves a predicate
    unanswered, or gives a probability outside [0, 1], is a final ``BadResponse`` (an answer is never retried).

    Retries are the run's policy (``policy.TRANSIENT``): 429 is ``RateLimitError`` and pauses the shared throttle for
    Retry-After seconds, 5xx is ``InternalServerError`` / ``ServiceUnavailableError``, both retried with backoff. A 403
    or 404 means the organisation has no Decisions API access (or the model is not offered to it): the call fails with
    ``AccessPending`` (final) and ``access_pending`` stops any further sending.

    Usage: ``usage.input_tokens`` and ``usage.output_tokens`` as reported (the whole block is kept under
    ``raw.usage_reported``; ``total_tokens`` is left out of the billable usage because it repeats the two). Serving
    identity: the model the response reports, plus version and model response headers (``OPENAI_KEEP_HEADERS``),
    never organisation, project or request ids."""
    provider = "openai"
    adapter = {"name": "openai-decisions", "version": INPUT_MAPPING_VERSION}

    def __init__(self, api_key: str, system: str = OPENAI_MODEL, model: str = OPENAI_MODEL, url: str = OPENAI_URL,
                 throttle: Throttle | None = None, **kw):
        identity = {"provider": self.provider, "model": model, "revision": None,
                    "revision_basis": "hosted model, not version-pinned; the response's model field and version "
                                      "headers are recorded per call",
                    "max_length": None, "precision": None, "docs": OPENAI_DOCS,
                    "input_mapping": {"version": INPUT_MAPPING_VERSION, **OPENAI_INPUT_MAPPING}}
        super().__init__(system, model, url, api_key, identity=identity,
                         throttle=throttle if throttle is not None else Throttle(OPENAI_RATE), **kw)
        self.endpoint = url
        self.access_pending = False
        self._tl = threading.local()   # the questions of the call in flight, per worker thread

    @classmethod
    def from_env(cls, env=os.environ, **kw):
        key = env.get("OPENAI_API_KEY")
        return cls(key, **kw) if key else None

    def body(self, state, questions):
        preds = [p for k, q in questions.items() if (p := predicate_of(k, q)) is not None]
        return {"model": self.model, "input": serialise_state(state), "questions": preds}

    def ask(self, state, questions):
        if self.access_pending:
            return SystemOneCall(system=self.system, ok=False, error="AccessPending: an earlier call returned 403 or "
                                 "404 (no Decisions API access for this organisation); nothing sent")
        self._tl.asked = [k for k, q in questions.items() if q.get("type") == "noul"]
        self._tl.unasked = [k for k, q in questions.items() if q.get("type") != "noul"]
        return super().ask(state, questions)

    def on_status(self, resp):
        if resp.status_code in (403, 404):
            self.access_pending = True
            return (f"AccessPending: HTTP {resp.status_code}, no Decisions API access for this organisation or model "
                    f"{self.model} not offered: " + re.sub(r"\s+", " ", resp.text or "")[:200])
        if resp.status_code == 429:
            wait = retry_after_s(resp.headers)
            if wait is not None and self.throttle:
                self.throttle.hold(wait)
            return status_error(429, f"retry-after {wait}s" if wait is not None else "")
        return super().on_status(resp)

    def response_meta(self, resp) -> dict | None:
        keep = {k.lower(): v for k, v in resp.headers.items()
                if OPENAI_KEEP_HEADERS.match(k) and not OPENAI_HEADER_DENY.search(k)}
        return keep or None

    def unwrap(self, payload):
        if not isinstance(payload, dict):
            return None, "BadResponse: body is not a JSON object"
        if isinstance(payload.get("error"), dict):
            e = payload["error"]
            return None, f"APIError: {e.get('type') or ''} {e.get('message') or ''}".strip()[:240]
        ans = payload.get("answers")
        if not isinstance(ans, list):
            return None, "BadResponse: answers is not a list"
        out, asked = {}, list(getattr(self._tl, "asked", None) or [])
        for a in ans:
            if not isinstance(a, dict) or not isinstance(a.get("name"), str):
                return None, "BadResponse: an answer has no name"
            p = a.get("probability")
            if a.get("type", "predicate") != "predicate" or isinstance(p, bool) or not isinstance(p, (int, float)):
                return None, f"BadResponse: answer {a['name'][:40]!r} is not a predicate with a probability"
            if not 0.0 <= float(p) <= 1.0:
                return None, f"BadResponse: answer {a['name'][:40]!r} probability {p} is outside [0, 1]"
            out[a["name"]] = {"type": "noul", "noul": float(p), "probability": float(p), "answer_type": "predicate"}
        missing = [k for k in asked if k not in out]
        if missing:
            return None, f"BadResponse: no answer for {', '.join(missing)[:200]}"
        result = {k: v for k, v in payload.items() if k != "answers"}
        result["answers"] = out
        if isinstance(payload.get("usage"), dict):
            # billable counts only: total_tokens repeats input + output and the *_details blocks are breakdowns
            result["usage"] = {k: v for k, v in payload["usage"].items() if k in ("input_tokens", "output_tokens")
                               and isinstance(v, int) and not isinstance(v, bool)} or None
            result["usage_reported"] = payload["usage"]
        return result, None

    def check(self, call):
        call.raw["reported_model"] = call.model
        call.model = call.model or self.model
        call.raw["input_mapping_version"] = INPUT_MAPPING_VERSION
        if getattr(self._tl, "unasked", None):
            call.raw["unasked"] = list(self._tl.unasked)
        return call


def not_configured(system: str) -> str:
    """Why ``from_env`` returned None: the names (never the values) of what is missing."""
    need = {"clef": "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN", "clef-flash": "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN",
            "perplexity": "PERPLEXITY_API_KEY",
            "openai": "OPENAI_API_KEY"}
    return f"not_configured: {system} needs {need.get(system, 'credentials')}"
