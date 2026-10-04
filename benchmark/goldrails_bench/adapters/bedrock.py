"""Amazon Bedrock Guardrails as a task adapter: the service's own verdict at a frozen, documented setting.

Bedrock never reads our questions. For each task the adapter asks the service for the categories that match the
suite policy, through the same two clients v1 used (``bedrock.BedrockChecksClient`` for InvokeGuardrailChecks,
``bedrock_apply.BedrockApplyClient`` for ApplyGuardrail against the Terraform-managed guardrails), and reads the
verdict under ``FROZEN_SETTING``:

- InvokeGuardrailChecks (content, prompt attacks, sensitive information) returns a severity or confidence per
  category and no verdict of its own. The frozen setting flags a row when the highest score over the task's
  categories is >= 0.5, the v1 operating point. ``score`` is that highest score. It is a six-step severity, not a
  probability.
- ApplyGuardrail topics, words and PII return a binary ``detected`` per item. That is the verdict, and ``score`` is
  None: there is no continuous output to rank on.
- ApplyGuardrail grounding returns a grounding and a relevance score and applies the threshold configured on the
  deployed guardrail version. The verdict is the service's (``detected`` or a non-NONE ``action`` on the filter,
  else score below the filter's threshold), and ``score`` is 1 - grounding (or 1 - relevance), so higher means worse.

Grounding rows carry the source, the query, the reply, and for dialogue rows (FaithDial) the earlier turns in
``state.context``. ApplyGuardrail has three qualified blocks and no place for turns, so ``grounding_state`` folds the
earlier turns into the query block as a role-labelled transcript ending with the query. The source block stays the
source alone: the grounding policy judges the reply against the source, and earlier turns are not evidence. Bedrock
documents a 100,000 / 1,000 / 5,000 character cap on grounding source / query / guarded content
(``GROUNDING_LIMITS``). A row over any cap is ``not_offered`` with the part, its length and the cap in ``error``; no
call is made and nothing is cut. Bedrock also says conversational QA is not a supported grounding use case; the
mapping is recorded in ``serving.grounding_mapping`` so that caveat travels with the scores.

The word subtask decides on the custom words only. The v1 ``any_word`` answer also counted Bedrock's managed
profanity list, which is a different policy; it stays in ``per_question`` for reference.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..policy import DEFAULT_POLICY, RetryPolicy, ask_with_policy
from .base import DECIDED, FAILED, NOT_OFFERED, Adapter, AdapterResult, check_task, max_over, serving, state_dict

CHECKS, TOPICS, WORDS, GROUNDING = "checks", "topics", "words", "grounding"
CONTENT_KEYS = ["hate", "insults", "sexual", "violence", "misconduct"]
ATTACK_KEYS = ["prompt_injection", "jailbreak", "prompt_leakage"]
PII_ENTITIES = ["NAME", "EMAIL", "PHONE", "ADDRESS", "USERNAME", "PASSWORD", "IP_ADDRESS", "DRIVER_ID",
                "US_SOCIAL_SECURITY_NUMBER"]   # the shared supported-entity task (e2/f5-pii supported_entities)
# (suite, subtask) -> (which client, how the verdict is read)
TASKS = {("content", "request"): (CHECKS, "score_threshold"), ("content", "reply"): (CHECKS, "score_threshold"),
         ("prompt_attacks", "direct"): (CHECKS, "score_threshold"),
         ("sensitive_info", "entity_detection"): (CHECKS, "score_threshold"),
         ("denied_topics", "topic"): (TOPICS, "binary"),
         ("word_filters", "word"): (WORDS, "binary"), ("word_filters", "profanity"): (WORDS, "binary"),
         ("grounding", "grounding"): (GROUNDING, "service_threshold"),
         ("grounding", "relevance"): (GROUNDING, "service_threshold")}
FROZEN_SETTING = {"checks_threshold": 0.5,
                  "checks_rule": "flag when the max severity/confidence over the task's categories is >= 0.5",
                  "apply_rule": "the guardrail version's own detected flag (topics, words, PII) or its configured "
                                "grounding/relevance threshold"}
GROUNDING_FILTER = {"grounding": ("GROUNDING", "unsupported"), "relevance": ("RELEVANCE", "irrelevant")}
# Bedrock contextual grounding caps, in characters (Bedrock user guide, "Use contextual grounding check to filter
# hallucinations in responses", read 4 October 2026).
GROUNDING_LIMITS = {"grounding_source": 100_000, "query": 1_000, "guard_content": 5_000}
GROUNDING_MAPPING = {"grounding_source": "state.source",
                     "query": "state.context turns as 'Role: text' lines, then 'User: ' + state.query; state.query "
                              "alone when there are no earlier turns",
                     "guard_content": "state.text",
                     "limits_chars": GROUNDING_LIMITS,
                     "over_limit": "not_offered, no call, nothing truncated"}
REPO = Path(__file__).resolve().parents[3]
# Edition 2 topics (owner ruling 1: all 8). The same file feeds the policy, the e2 question set and the Bedrock topic
# configuration (benchmark/suites/denied_topics/bedrock-guardrail-e2.json). v1 code keeps reading topics.json.
TOPICS_FILE = REPO / "benchmark/suites/denied_topics/topics-e2.json"


def _topic_keys() -> list:
    from ..bedrock_apply import _slug
    topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))["topics"]
    return [_slug(t["name"]) for t in topics]


def _turn_text(turn: Any) -> tuple[str, str]:
    if isinstance(turn, dict):
        return str(turn.get("role") or "user"), str(turn.get("text") or "")
    return "user", str(turn)


def grounding_state(state: Any) -> tuple[Any, dict]:
    """(state ApplyGuardrail can carry, {block: characters}). Earlier turns join the query block (see the module
    docstring); every other field passes through, so anything still unrepresentable (a tool call) fails in the client."""
    if not isinstance(state, dict):
        state = {"role": "assistant", "text": str(state)}
    state = dict(state)
    turns = state.pop("context", None) or []
    query = str(state.get("query") or "")
    if turns:
        lines = [f"{role.capitalize()}: {text}" for role, text in map(_turn_text, turns)]
        if query:
            lines.append(f"User: {query}")
        query = "\n".join(lines)
        state["query"] = query
    sizes = {"grounding_source": len(str(state.get("source") or "")), "query": len(query),
             "guard_content": len(str(state.get("text") or ""))}
    return state, sizes


def over_limits(sizes: dict) -> list[str]:
    return [f"{k} {n} > {GROUNDING_LIMITS[k]}" for k, n in sizes.items() if n > GROUNDING_LIMITS[k]]


class BedrockAdapter(Adapter):
    name = "bedrock-e2"
    version = "2"   # 2 (4 October 2026): grounding folds state.context into the query block; over-cap rows not_offered
    system = "bedrock-guardrails"

    def __init__(self, clients: dict | None = None, config: dict | None = None, region: str | None = None,
                 policy: RetryPolicy = DEFAULT_POLICY, system: str | None = None):
        """``clients`` maps "checks", "topics", "words" and "grounding" to ready clients (tests pass fakes wrapped in
        the real client classes); missing ones are built on first use, ApplyGuardrail ones from ``config`` or the
        Terraform outputs."""
        self.clients = dict(clients or {})
        self.config = config
        self.region = region
        self.policy = policy
        self.system = system or self.system

    def offers(self, suite: str, subtask: str) -> bool:
        return (suite, subtask) in TASKS

    def client_for(self, kind: str):
        if kind not in self.clients:
            if kind == CHECKS:
                from ..bedrock import BedrockChecksClient
                self.clients[kind] = BedrockChecksClient(region=self.region)
            else:
                from ..bedrock_apply import BedrockApplyClient
                self.clients[kind] = BedrockApplyClient(kind, config=self.config)
        return self.clients[kind]

    def keys(self, suite: str, subtask: str, client) -> tuple[list, list]:
        """(category keys to ask for, keys the decision is the max over)."""
        if suite == "content":
            return CONTENT_KEYS, CONTENT_KEYS
        if suite == "prompt_attacks":
            return ATTACK_KEYS, ATTACK_KEYS
        if suite == "sensitive_info":
            return PII_ENTITIES + ["any_supported_entity"], ["any_supported_entity"]
        if suite == "denied_topics":
            return _topic_keys() + ["any_denied_topic"], ["any_denied_topic"]
        if (suite, subtask) == ("word_filters", "word"):
            from ..bedrock_apply import _slug
            words = [_slug(w) for w in (getattr(client, "config", None) or {}).get("words", [])]
            return words + ["any_word", "profanity"], words
        if (suite, subtask) == ("word_filters", "profanity"):
            return ["profanity"], ["profanity"]
        key = GROUNDING_FILTER[subtask][1]
        return ["unsupported", "irrelevant"], [key]

    def serving(self, kind: str | None = None, client=None, **extra) -> dict:
        ident = getattr(client, "identity", None) or {}
        region = ident.get("region") or self.region
        return serving(f"bedrock-runtime.{region}.amazonaws.com" if region else None,
                       getattr(client, "model", None), revision=ident.get("guardrail_version") or "unversioned",
                       api=ident.get("api"), region=region, identity=ident or None, adapter=self.adapter,
                       observed_on=getattr(client, "observed_on", None), frozen_setting=FROZEN_SETTING, **extra)

    def evaluate(self, suite: str, subtask: str, row: Any) -> AdapterResult:
        check_task(suite, subtask)
        if not self.offers(suite, subtask):
            return AdapterResult(None, None, None, "not_offered", self.serving(),
                                 error=f"Bedrock offers no capability for {suite}/{subtask}")
        kind, how = TASKS[(suite, subtask)]
        client = self.client_for(kind)
        ask, decide = self.keys(suite, subtask, client)
        state, extra = state_dict(row), {}
        if kind == GROUNDING:
            state, sizes = grounding_state(state)
            extra = {"grounding_mapping": GROUNDING_MAPPING, "grounding_chars": sizes}
            over = over_limits(sizes)
            if over:
                return AdapterResult(None, None, None, NOT_OFFERED,
                                     self.serving(kind, client, rule=how, decision_keys=decide, **extra),
                                     error=f"ExceedsServiceLimit: Bedrock contextual grounding caps "
                                           f"{', '.join(over)} characters", attempts=[],
                                     raw={"not_offered": "exceeds_service_limit", "over": over, "chars": sizes})
        t0 = time.perf_counter()
        call, attempts = ask_with_policy(client, state, {k: {} for k in ask}, self.policy)
        latency = round(time.perf_counter() - t0, 3)
        srv = self.serving(kind, client, rule=how, decision_keys=decide, **extra)
        if not call.ok:
            return AdapterResult(None, None, None, FAILED, srv, error=call.error, latency_s=latency,
                                 usage=call.usage, attempts=attempts, raw=call.raw)
        per_q = {k: float(a["noul"]) for k, a in (call.answers or {}).items()
                 if isinstance(a, dict) and isinstance(a.get("noul"), (int, float))}
        top = max_over(per_q, decide)
        if top is None:
            return AdapterResult(None, None, per_q, FAILED, srv, error="NoDecision: Bedrock answered no decision category",
                                 latency_s=latency, usage=call.usage, attempts=attempts, raw=call.raw)
        if how == "score_threshold":
            decision, score = top >= FROZEN_SETTING["checks_threshold"], top
        elif how == "binary":
            decision, score = top >= 1.0, None
        else:
            decision, score = self.grounding_verdict(subtask, call.raw, top), top
        return AdapterResult(decision, score, per_q, DECIDED, srv, latency_s=latency, usage=call.usage,
                             attempts=attempts, raw=call.raw)

    @staticmethod
    def grounding_verdict(subtask: str, raw: dict | None, inverted: float) -> bool:
        """The service's own verdict on the grounding or relevance filter, at the guardrail version's threshold."""
        ftype = GROUNDING_FILTER[subtask][0]
        for block in (raw or {}).get("assessments") or []:
            for f in (block.get("contextualGroundingPolicy") or {}).get("filters", []):
                if f.get("type") != ftype:
                    continue
                if "detected" in f:
                    return bool(f["detected"])
                if f.get("action"):
                    return f["action"] != "NONE"
                if f.get("threshold") is not None and f.get("score") is not None:
                    return float(f["score"]) < float(f["threshold"])
        return inverted > 0.5   # no filter detail in the response: grounded score below the default 0.5 threshold
