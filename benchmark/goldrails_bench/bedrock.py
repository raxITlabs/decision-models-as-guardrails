"""Amazon Bedrock Guardrails as a baseline, asked the same question sets as the decision models.

Bedrock has no free-form questions, so a question set is translated: each question name maps to one of the
categories the service can check, the service runs once per row with every needed check, and its per-category
``severityScore`` (six discrete steps 0, 0.2 ... 1.0; AWS says severity is a property of the content, not model
confidence) is returned under the question's own name as a Noul-shaped answer with ``basis: bedrock_severity``.
Questions Bedrock cannot answer (a severity Score, the v2 intent Noul, hazards outside its five categories) are
left out of ``answers`` and listed in ``raw["unanswered"]``, so a scorer sees exactly what the service could do.

The path is ``InvokeGuardrailChecks`` (June 2026): resourceless, detect-only, the call AgentCore Policy makes,
and the one a buyer compares against. Nothing to create in the account. ``ApplyGuardrail`` with a guardrail
resource returns four buckets instead and can be added as a second system later.

    client = BedrockChecksClient()              # AWS_PROFILE / AWS_REGION from the environment (.env)
    call = client.ask(state, questions)         # same shape as SystemOneClient.ask
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any

from .question_sets import SEP
from .systemone import UNTRUSTED_PREFIX, UNTRUSTED_ROLE, SystemOneCall, unrepresentable, untrusted

# question name -> (check, category). Versioned with the question sets; extend when F2 (prompt attack) and F3 (PII)
# question sets exist. Names that map to nothing are unanswered, not guessed.
CONTENT = {"hate": "HATE", "insults": "INSULTS", "sexual": "SEXUAL", "violence": "VIOLENCE", "misconduct": "MISCONDUCT",
           "violent_crimes": "VIOLENCE", "nonviolent_crimes": "MISCONDUCT", "sex_related_crimes": "SEXUAL",
           "child_sexual_exploitation": "SEXUAL", "indiscriminate_weapons": "MISCONDUCT", "suicide_self_harm": "VIOLENCE",
           "intellectual_property": "MISCONDUCT", "defamation": "INSULTS", "sexual_content": "SEXUAL",
           "extremism_facilitation": "VIOLENCE"}
PROMPT_ATTACK = {"jailbreak": "JAILBREAK", "prompt_injection": "PROMPT_INJECTION", "prompt_leakage": "PROMPT_LEAKAGE",
                 "injection": "PROMPT_INJECTION"}
PII_TYPES = {"ADDRESS", "AGE", "AWS_ACCESS_KEY", "AWS_SECRET_KEY", "CA_HEALTH_NUMBER", "CA_SOCIAL_INSURANCE_NUMBER",
             "CREDIT_DEBIT_CARD_CVV", "CREDIT_DEBIT_CARD_EXPIRY", "CREDIT_DEBIT_CARD_NUMBER", "DRIVER_ID", "EMAIL",
             "INTERNATIONAL_BANK_ACCOUNT_NUMBER", "IP_ADDRESS", "LICENSE_PLATE", "MAC_ADDRESS", "NAME", "PASSWORD", "PHONE",
             "PIN", "SWIFT_CODE", "UK_NATIONAL_HEALTH_SERVICE_NUMBER", "UK_NATIONAL_INSURANCE_NUMBER",
             "UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER", "URL", "USERNAME", "US_BANK_ACCOUNT_NUMBER", "US_BANK_ROUTING_NUMBER",
             "US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER", "US_PASSPORT_NUMBER", "US_SOCIAL_SECURITY_NUMBER",
             "VEHICLE_IDENTIFICATION_NUMBER"}
ANY_SUPPORTED = "any_supported_entity"   # max confidence over the entity types the request asked for: the shared task
# "contains_pii" (the source's broader notion, any personal information) is deliberately not mapped: the service has no
# such check, so it stays unanswered and the report shows it as a coverage difference.
# Bedrock has no tool role. Retrieved content (role "tool") goes as a user message tagged untrusted, never as an
# assistant turn: see systemone.UNTRUSTED_PREFIX for the shared representation.
ROLES = {"user": "user", "assistant": "assistant", "system": "system", UNTRUSTED_ROLE: "user"}
MODEL = "bedrock-guardrails/invoke-guardrail-checks"
SUPPORTED_STATE = ("role", "text", "context", "tool_call")   # the checks API takes messages; no grounding source/query


def _mapping_sha() -> str:
    return hashlib.sha256(json.dumps([CONTENT, PROMPT_ATTACK, sorted(PII_TYPES), ANY_SUPPORTED, ROLES, UNTRUSTED_PREFIX], sort_keys=True).encode()).hexdigest()[:8]


# Adapter identity, part of the config hash: bump ``version`` when ``plan``, ``messages_of`` or ``answers_of`` change;
# the mapping tables are hashed in, so editing a category map is a new arm without anyone remembering to bump.
# 2 (23 September 2026): role "tool" is sent as a tagged user message instead of an assistant turn.
ADAPTER = {"name": "bedrock-checks", "version": f"2+map-{_mapping_sha()}"}


# The AWS account id inside an ARN (``arn:aws:bedrock:us-east-1:<12 digits>:guardrail/...``). Responses and error
# messages go into the ledgers verbatim, so the account is masked before they are kept. Only ``raw`` and ``error`` are
# masked: the identity and the config hash never held an ARN, so frozen arms keep their hashes.
ARN_ACCOUNT = re.compile(r"(arn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:)[0-9]{12}(?=:)")


def mask_account_ids(x):
    """A copy of ``x`` (dict, list or str, nested) with the account id in every ARN replaced by ``<account>``."""
    if isinstance(x, str):
        return ARN_ACCOUNT.sub(r"\1<account>", x)
    if isinstance(x, dict):
        return {k: mask_account_ids(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [mask_account_ids(v) for v in x]
    return x


def no_retry_config():
    """botocore retries throttling and 5xx errors on its own by default (hidden attempts, hidden latency). The
    benchmark's retry policy lives in policy.py, so the SDK makes exactly one attempt per call."""
    from botocore.config import Config
    return Config(retries={"total_max_attempts": 1, "mode": "standard"})


def plan(questions: dict) -> tuple[dict, dict, list]:
    """(question key -> (check, category), checks request body, unanswered keys). Keys may carry a set namespace."""
    mapping, unanswered = {}, []
    for key in questions:
        name = key.split(SEP, 1)[-1]
        if name in CONTENT:
            mapping[key] = ("contentFilter", CONTENT[name])
        elif name in PROMPT_ATTACK:
            mapping[key] = ("promptAttack", PROMPT_ATTACK[name])
        elif name in PII_TYPES:
            mapping[key] = ("sensitiveInformation", name)
        elif name == ANY_SUPPORTED:
            mapping[key] = ("sensitiveInformation", ANY_SUPPORTED)
        else:
            unanswered.append(key)
    checks = {}
    for check in ("contentFilter", "promptAttack"):
        cats = sorted({c for ch, c in mapping.values() if ch == check})
        if cats:
            checks[check] = {"categories": [{"category": c} for c in cats]}
    ents = sorted({c for ch, c in mapping.values() if ch == "sensitiveInformation" and c != ANY_SUPPORTED})
    if any(c == ANY_SUPPORTED for ch, c in mapping.values()) and not ents:
        ents = sorted(PII_TYPES)          # contains_pii alone: ask for every type the service knows
    if ents:
        checks["sensitiveInformation"] = {"entities": [{"type": t} for t in ents]}
    return mapping, checks, unanswered


def message(role: str, text: Any) -> dict:
    """One Bedrock message. Retrieved content (role "tool") becomes a user message tagged untrusted."""
    text = str(text)
    if role == UNTRUSTED_ROLE:
        text = untrusted(text)
    return {"role": ROLES.get(role, "user"), "content": [{"text": text}]}


def messages_of(state: Any) -> list[dict]:
    """Our state (role, text, prior turns) as Bedrock messages, oldest first."""
    if isinstance(state, str):
        return [{"role": "user", "content": [{"text": state}]}]
    out = []
    for turn in state.get("context") or []:
        if isinstance(turn, dict) and turn.get("text"):
            out.append(message(turn.get("role", "user"), turn["text"]))
    text = state.get("text", "")
    if state.get("tool_call"):   # JSON, the same content a System One model receives as a structured field
        tc = state["tool_call"]
        text = f"{text}\n\n{json.dumps(tc, sort_keys=True, ensure_ascii=False) if isinstance(tc, (dict, list)) else tc}".strip()
    out.append(message(state.get("role", "user"), text))
    return out


def answers_of(results: dict, mapping: dict, checks: dict | None = None) -> dict:
    scores, basis = {}, {}
    for check, key in (("contentFilter", "category"), ("promptAttack", "category")):
        for entry in (results.get(check) or {}).get("results") or []:
            scores[(check, entry[key])] = float(entry["severityScore"]); basis[(check, entry[key])] = "bedrock_severity"
    pii = (results.get("sensitiveInformation") or {}).get("results") or []
    asked = {e["type"] for e in ((checks or {}).get("sensitiveInformation") or {}).get("entities", [])}
    for t in asked:                        # asked and not detected is 0, not missing: the service answered
        hits = [float(h.get("confidenceScore", 0.0)) for h in pii if h.get("type") == t]
        scores[("sensitiveInformation", t)] = max(hits) if hits else 0.0; basis[("sensitiveInformation", t)] = "bedrock_confidence"
    if asked:
        scores[("sensitiveInformation", ANY_SUPPORTED)] = max((float(h.get("confidenceScore", 0.0)) for h in pii), default=0.0)
        basis[("sensitiveInformation", ANY_SUPPORTED)] = "bedrock_confidence_max"
    return {k: {"type": "noul", "noul": scores[m], "basis": basis[m]} for k, m in mapping.items() if m in scores}


class BedrockChecksClient:
    system = "bedrock-checks"
    adapter = ADAPTER

    def __init__(self, region: str | None = None, profile: str | None = None, client=None, system: str | None = None):
        self.system = system or self.system
        self.model = MODEL
        region = region or os.environ.get("AWS_REGION") or "us-east-1"
        # The service exposes no version; the API name and region are the closest thing to an identity. The date is
        # recorded beside it (observed_on) but kept out of the config hash, so a tuning pass and the frozen test run on
        # different days are the same arm. The service can still change underneath: that limit is disclosed.
        self.identity = {"api": "InvokeGuardrailChecks", "region": region, "versioned": False}
        self.observed_on = time.strftime("%Y-%m-%d")
        if client is None:
            import boto3
            session = boto3.Session(profile_name=profile or os.environ.get("AWS_PROFILE") or None,
                                    region_name=region or os.environ.get("AWS_REGION") or "us-east-1")
            client = session.client("bedrock-runtime", config=no_retry_config())
        self.client = client

    def ask(self, state: Any, questions: dict) -> SystemOneCall:
        mapping, checks, unanswered = plan(questions)
        missing = unrepresentable(state, SUPPORTED_STATE)
        if missing:
            return SystemOneCall(system=self.system, ok=False, model=self.model,
                                 error=f"UnrepresentableState: InvokeGuardrailChecks cannot carry {', '.join(missing)}",
                                 raw={"unanswered": list(questions), "unrepresentable": missing})
        if not checks:
            return SystemOneCall(system=self.system, ok=False, model=self.model,
                                 error="no question maps to a Bedrock check", raw={"unanswered": unanswered})
        t0 = time.perf_counter()
        try:
            resp = self.client.invoke_guardrail_checks(messages=messages_of(state), checks=checks)
        except Exception as e:  # recorded, never retried
            return SystemOneCall(system=self.system, ok=False, model=self.model,
                                 error=f"{type(e).__name__}: {mask_account_ids(str(e))}", latency_s=time.perf_counter() - t0)
        dt = time.perf_counter() - t0
        resp.pop("ResponseMetadata", None)
        resp = mask_account_ids(resp)
        usage = {k: v.get("textUnits") for k, v in (resp.get("usage") or {}).items()}
        return SystemOneCall(system=self.system, ok=True, model=self.model, answers=answers_of(resp.get("results") or {}, mapping, checks),
                             usage={"input_tokens": None, "text_units": usage}, latency_s=dt,
                             raw={**resp, "checks": checks, "unanswered": unanswered})
