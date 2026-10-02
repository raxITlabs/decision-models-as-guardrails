"""Amazon Bedrock Guardrails through ApplyGuardrail: the suites that need a guardrail resource (denied topics, word
filters, contextual grounding and relevance, PII masking). One client per suite, bound to a guardrail id and a pinned
version read from ``infra/aws`` Terraform outputs at run time; the id and version are part of the client's identity,
so a changed topic definition or word list is a new arm in the ledger.

Answers are Noul-shaped so the same scorer applies, with the basis stated because none of these are probabilities:
- topics:    per topic ``detected`` (1.0 / 0.0), basis bedrock_topic_binary; ``any_denied_topic`` is the max
- words:     per configured word, detected (1.0 / 0.0) by case-insensitive match, basis bedrock_word_binary;
             ``profanity`` from the managed list; ``any_word`` is the max
- grounding: ``unsupported`` = 1 - grounding score, ``irrelevant`` = 1 - relevance score (the service scores "grounded"
             and "relevant"; our questions ask for the failure), basis bedrock_grounding_inverted; raw scores kept
- pii:       per entity type detected (1.0 / 0.0), basis bedrock_pii_binary; masked text in raw["masked_text"]
Questions the guardrail cannot answer are listed in raw["unanswered"].
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .bedrock import mask_account_ids
from .question_sets import SEP
from .systemone import UNTRUSTED_ROLE, SystemOneCall, unrepresentable, untrusted

REPO = Path(__file__).resolve().parents[2]
SUITES = ("topics", "words", "grounding", "pii")
# What ApplyGuardrail content blocks can carry per suite. Prior turns and tool calls have no place in a single
# guarded-content request, so a row with them fails loudly instead of being judged on less than other systems see.
SUPPORTED_STATE = {"grounding": ("role", "text", "source", "query")}
DEFAULT_SUPPORTED = ("role", "text")
# Adapter identity, part of the config hash: bump when ``content_of`` or ``answers_of`` change what is sent or read.
# 2 (23 September 2026): retrieved content (role "tool") is sent as INPUT with the untrusted tag.
ADAPTER = {"name": "bedrock-apply", "version": "2"}


def guardrails() -> dict:
    """{suite: {id, version, ...}} plus region, from Terraform outputs. Nothing is stored in the repo or .env."""
    out = json.loads(subprocess.run(["terraform", "output", "-json"], cwd=REPO / "infra" / "aws", check=True,
                                    capture_output=True, text=True).stdout)
    return {**out["guardrails"]["value"], "region": out["region"]["value"]}


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.strip().lower()).strip("_")


def content_of(state: Any, suite: str) -> tuple[str, list[dict]]:
    """(source, content blocks). Grounding needs source, query and the reply as qualified blocks."""
    if isinstance(state, str):
        state = {"role": "user", "text": state}
    if suite == "grounding":
        blocks = []
        if state.get("source"):
            blocks.append({"text": {"text": str(state["source"]), "qualifiers": ["grounding_source"]}})
        if state.get("query"):
            blocks.append({"text": {"text": str(state["query"]), "qualifiers": ["query"]}})
        blocks.append({"text": {"text": str(state.get("text", "")), "qualifiers": ["guard_content"]}})
        return "OUTPUT", blocks
    if state.get("role") == UNTRUSTED_ROLE:   # retrieved content: input to the model, tagged untrusted (systemone.UNTRUSTED_PREFIX)
        return "INPUT", [{"text": {"text": untrusted(str(state.get("text", "")))}}]
    source = "OUTPUT" if state.get("role") == "assistant" else "INPUT"
    return source, [{"text": {"text": str(state.get("text", ""))}}]


def live_policy(g: dict) -> dict:
    """The parts of a deployed guardrail version that decide these suites' answers: topic names in their configured
    order, custom words, managed word lists, and which policies exist. Recorded so a result names the exact setup."""
    wp = g.get("wordPolicy") or {}
    return {"version": g.get("version"), "status": g.get("status"), "updated_at": str(g.get("updatedAt") or ""),
            "topics": [t.get("name") for t in (g.get("topicPolicy") or {}).get("topics", [])],
            "words": [w.get("text") for w in wp.get("words", [])],
            "managed_word_lists": [m.get("type") for m in wp.get("managedWordLists", [])],
            "policies": sorted(k for k in ("topicPolicy", "contentPolicy", "wordPolicy", "sensitiveInformationPolicy",
                                           "contextualGroundingPolicy") if g.get(k))}


class BedrockApplyClient:
    adapter = ADAPTER

    def __init__(self, suite: str, config: dict | None = None, client=None, system: str | None = None, control=None):
        if suite not in SUITES:
            raise ValueError(f"suite must be one of {SUITES}")
        self.suite = suite
        cfg = config or guardrails()
        g = cfg[suite]
        self.guardrail_id, self.version, self.region = g["id"], str(g["version"]), cfg.get("region") or os.environ.get("AWS_REGION", "us-east-1")
        self.config = g
        self.system = system or f"bedrock-apply-{suite}"
        self.model = "bedrock-guardrails/apply-guardrail"
        self.identity = {"api": "ApplyGuardrail", "guardrail_id": self.guardrail_id, "guardrail_version": self.version,
                         "region": self.region, "config": {k: v for k, v in g.items() if k not in ("id", "version")}}
        if client is None:
            import boto3
            from .bedrock import no_retry_config
            session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE") or None, region_name=self.region)
            client = session.client("bedrock-runtime", config=no_retry_config())
            control = control or session.client("bedrock", config=no_retry_config())
        if control is not None:   # the deployed version's policy, as AWS reports it, joins the identity and config hash
            self.identity["live_policy"] = live_policy(control.get_guardrail(guardrailIdentifier=self.guardrail_id,
                                                                              guardrailVersion=self.version))
        self.client = client

    def ask(self, state: Any, questions: dict) -> SystemOneCall:
        missing = unrepresentable(state, SUPPORTED_STATE.get(self.suite, DEFAULT_SUPPORTED))
        if missing:
            return SystemOneCall(system=self.system, ok=False, model=self.model,
                                 error=f"UnrepresentableState: ApplyGuardrail ({self.suite}) cannot carry {', '.join(missing)}",
                                 raw={"unanswered": list(questions), "unrepresentable": missing})
        source, content = content_of(state, self.suite)
        t0 = time.perf_counter()
        try:
            resp = self.client.apply_guardrail(guardrailIdentifier=self.guardrail_id, guardrailVersion=self.version,
                                               source=source, content=content, outputScope="FULL")
        except Exception as e:  # recorded, never retried
            return SystemOneCall(system=self.system, ok=False, model=self.model,
                                 error=f"{type(e).__name__}: {mask_account_ids(str(e))}", latency_s=time.perf_counter() - t0)
        dt = time.perf_counter() - t0
        resp.pop("ResponseMetadata", None)
        resp = mask_account_ids(resp)   # the guardrail ARN carries the account id; ledgers keep <account> instead
        answers, unanswered, extra = self.answers_of(resp, questions)
        return SystemOneCall(system=self.system, ok=True, model=self.model, answers=answers, usage={"input_tokens": None, **(resp.get("usage") or {})},
                             latency_s=dt, raw={**resp, "source": source, "unanswered": unanswered, **extra})

    def answers_of(self, resp: dict, questions: dict) -> tuple[dict, list, dict]:
        a = {}
        for block in resp.get("assessments") or []:
            for k, v in block.items():
                a.setdefault(k, v)
        scores, basis, extra = {}, {}, {}
        if self.suite == "topics":
            det = {t["name"]: 1.0 if t.get("detected") else 0.0 for t in (a.get("topicPolicy") or {}).get("topics", [])}
            for name, v in det.items():
                scores[_slug(name)] = v; basis[_slug(name)] = "bedrock_topic_binary"
            if det:
                scores["any_denied_topic"] = max(det.values()); basis["any_denied_topic"] = "bedrock_topic_binary_max"
        elif self.suite == "words":
            wp = a.get("wordPolicy") or {}
            matched = {str(w.get("match", "")).lower() for w in wp.get("customWords", []) if w.get("detected")}
            for word in self.config.get("words", []):
                scores[_slug(word)] = 1.0 if word.lower() in matched else 0.0; basis[_slug(word)] = "bedrock_word_binary"
            scores["profanity"] = 1.0 if any(m.get("detected") for m in wp.get("managedWordLists", [])) else 0.0; basis["profanity"] = "bedrock_managed_list_binary"
            scores["any_word"] = max([v for k, v in scores.items()] or [0.0]); basis["any_word"] = "bedrock_word_binary_max"
        elif self.suite == "grounding":
            f = {x["type"]: x for x in (a.get("contextualGroundingPolicy") or {}).get("filters", [])}
            if "GROUNDING" in f:
                scores["unsupported"] = round(1.0 - float(f["GROUNDING"]["score"]), 4); basis["unsupported"] = "bedrock_grounding_inverted"
            if "RELEVANCE" in f:
                scores["irrelevant"] = round(1.0 - float(f["RELEVANCE"]["score"]), 4); basis["irrelevant"] = "bedrock_relevance_inverted"
            extra["grounding_scores"] = {k: v.get("score") for k, v in f.items()}
        elif self.suite == "pii":
            ents = (a.get("sensitiveInformationPolicy") or {}).get("piiEntities", [])
            det = {}
            for e in ents:
                if e.get("detected"):
                    det[e["type"]] = 1.0
            for t in self.config.get("entities", []):
                scores[t] = det.get(t, 0.0); basis[t] = "bedrock_pii_binary"
            scores["any_supported_entity"] = max(det.values(), default=0.0); basis["any_supported_entity"] = "bedrock_pii_binary_max"
            extra["masked_text"] = "".join(o.get("text", "") for o in resp.get("outputs") or []) or None
            extra["pii_matches"] = [{"type": e.get("type"), "match": e.get("match"), "action": e.get("action")} for e in ents if e.get("detected")]
        answers, unanswered = {}, []
        for key in questions:
            name = key.split(SEP, 1)[-1]
            if name in scores:
                answers[key] = {"type": "noul", "noul": scores[name], "basis": basis[name]}
            else:
                unanswered.append(key)
        return answers, unanswered, extra
