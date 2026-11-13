"""Classic guard adapters (goldrails_bench.guards) against a fake OpenRouter: no network, no key."""
import json

import httpx
import pytest

from goldrails_bench import guards
from goldrails_bench.leaderboard import Arm, is_binary, score_scale
from goldrails_bench.policy import NO_RETRY, TRANSIENT_3


def fake(payloads, seen=None):
    """A ChatGuardClient whose HTTP calls return ``payloads`` in turn (a dict is a 200 body, an int a status)."""
    it = iter(payloads)

    def handler(req):
        if seen is not None:
            seen.append(json.loads(req.content))
        p = next(it)
        return httpx.Response(p, text="busy") if isinstance(p, int) else httpx.Response(200, json=p)
    return httpx.Client(transport=httpx.MockTransport(handler))


def body(content, provider="Groq", model="openai/gpt-oss-safeguard-20b", reasoning="r"):
    return {"provider": provider, "model": model,
            "choices": [{"finish_reason": "stop", "message": {"content": content, "reasoning": reasoning}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 1e-5}}


def safeguard(payloads, seen=None, policy=NO_RETRY):
    c = guards.ChatGuardClient("gpt-oss-safeguard-20b", "k", http=fake(payloads, seen))
    return guards.SafeguardAdapter(c, policy)


def llama(payloads, seen=None):
    c = guards.ChatGuardClient("llama-guard-4-12b", "k", http=fake(payloads, seen))
    return guards.LlamaGuardAdapter(c, NO_RETRY)


ROW = {"state": {"role": "user", "text": "hello"}}


def test_parse_binary():
    assert guards.parse_binary(" 1\n") == {"violation": 1}
    assert guards.parse_binary('"0".') == {"violation": 0}
    for bad in ("", None, "yes", "10", "1 because"):
        with pytest.raises(ValueError):
            guards.parse_binary(bad)


def test_parse_pii():
    got = guards.parse_pii('["NAME", "email"]')
    assert got["NAME"] == 1 and got["EMAIL"] == 1 and got["PHONE"] == 0 and got["any_supported_entity"] == 1
    assert guards.parse_pii("[]")["any_supported_entity"] == 0
    for bad in ("none", '["CREDIT_CARD"]', "[1]"):
        with pytest.raises(ValueError):
            guards.parse_pii(bad)


def test_parse_llama_guard():
    assert guards.parse_llama_guard("\n\nsafe")["unsafe_any"] == 0
    got = guards.parse_llama_guard("\n\nunsafe\nS2,S10")
    assert got["S2"] == got["S10"] == got["unsafe_any"] == 1 and got["S1"] == 0
    for bad in ("maybe", "unsafe", "unsafe\nS99", ""):
        with pytest.raises(ValueError):
            guards.parse_llama_guard(bad)


def test_guard_messages_alternate_and_end_on_judged_turn():
    st = {"role": "tool", "text": "doc", "context": [{"role": "system", "text": "sys"}, {"role": "user", "text": "task"}]}
    m = guards.guard_messages(st)
    assert [x["role"] for x in m] == ["user"]
    assert m[0]["content"].startswith("sys\n\ntask\n\n[Untrusted retrieved content]")
    rep = guards.guard_messages({"role": "assistant", "text": "reply", "context": [{"role": "user", "text": "q"}]})
    assert [x["role"] for x in rep] == ["user", "assistant"] and rep[-1]["content"] == "reply"
    assert guards.guard_messages({"role": "assistant", "text": "r"})[0] == {"role": "user", "content": ""}


def test_safeguard_sends_policy_verbatim_and_pins_provider():
    seen = []
    res = safeguard([body("1")], seen).evaluate("content", "request", ROW)
    assert res.outcome == "decided" and res.decision is True and res.score is None
    assert res.per_question == {"violation": 1.0}
    sent = seen[0]
    assert sent["provider"] == {"order": ["groq"], "allow_fallbacks": False} and sent["temperature"] == 0
    policy = (guards.POLICIES / "content" / "request.md").read_text(encoding="utf-8").rstrip()
    assert sent["messages"][0]["content"].startswith(policy) and sent["messages"][0]["content"].endswith("0 if it does not.")
    assert "hello" in sent["messages"][1]["content"]
    assert res.serving["question_set"] == "safeguard-e2-content" and res.serving["answer_basis"] == "vendor_verdict"
    assert res.usage == {"input_tokens": 100, "output_tokens": 20}


def test_safeguard_pii_is_per_entity():
    res = safeguard([body('["EMAIL"]')]).evaluate("sensitive_info", "entity_detection", ROW)
    assert res.decision is True and res.per_question["EMAIL"] == 1.0 and res.per_question["NAME"] == 0.0
    assert res.serving["decision_keys"] == guards.PII_TYPES


def test_unparseable_or_wrong_provider_fails_and_transient_is_retried():
    assert safeguard([body("")]).evaluate("content", "request", ROW).outcome == "failed"
    res = safeguard([body("1", provider="Other")]).evaluate("content", "request", ROW)
    assert res.outcome == "failed" and res.error.startswith("ProviderMismatch")
    res = safeguard([429, body("0")], policy=TRANSIENT_3.__class__(max_retries=1, name="t")).evaluate(
        "content", "request", ROW)
    assert res.outcome == "decided" and res.decision is False and len(res.attempts) == 2


def test_llama_guard_declared_categories_and_not_offered():
    a = llama([body("\n\nunsafe\nS6", provider="DeepInfra", model="meta-llama/llama-guard-4-12b"),
               body("\n\nunsafe\nS1", provider="DeepInfra", model="meta-llama/llama-guard-4-12b")])
    out_of_scope = a.evaluate("content", "request", ROW)
    assert out_of_scope.decision is False and out_of_scope.per_question["unsafe_any"] == 1.0
    assert a.evaluate("content", "reply", {"state": {"role": "assistant", "text": "x",
                                                     "context": [{"role": "user", "text": "q"}]}}).decision is True
    no = a.evaluate("denied_topics", "topic", ROW)
    assert no.outcome == "not_offered" and no.decision is None


def test_adapter_version_tracks_the_prompt():
    a = safeguard([])
    assert a.version.startswith("1+pol-") and a.adapter == {"name": "safeguard-e2", "version": a.version}


def test_vendor_verdict_is_binary_scale():
    contract = {"binary_bases": ["regex_exact"], "step_bases": []}
    arm = Arm(("s", "q", "c", "d"), "content")
    arm.records.append({"answers": {"violation": {"type": "noul", "noul": 1.0, "basis": "vendor_verdict"}}})
    assert is_binary(arm, contract) and score_scale(arm, contract) == "binary"
