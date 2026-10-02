"""Raw Bedrock responses keep no AWS account id, and masking it leaves every frozen arm's identity and config hash as
they were. The hashes come from the committed arm ledgers and freeze manifests, so a change that touched the identity
or the hash inputs would fail here."""
import json
from pathlib import Path

import pytest

from goldrails_bench.bedrock_apply import BedrockApplyClient
from goldrails_bench.bedrock import mask_account_ids
from goldrails_bench.runner import config_hash

REPO = Path(__file__).resolve().parents[2]
ACCOUNT = "123456789012"
ARN = f"arn:aws:bedrock:us-east-1:{ACCOUNT}:guardrail/abc123"


def test_mask_account_ids_replaces_the_account_inside_arns_only():
    raw = {"assessments": [{"appliedGuardrailDetails": {"guardrailArn": ARN, "guardrailId": "abc123"}}],
           "outputs": [{"text": f"call {ACCOUNT} now"}], "usage": {"topicPolicyUnits": 1},
           "list": [ARN, 7, None, "arn:aws:iam::123456789012:role/x"]}
    out = mask_account_ids(raw)
    assert out["assessments"][0]["appliedGuardrailDetails"]["guardrailArn"] == "arn:aws:bedrock:us-east-1:<account>:guardrail/abc123"
    assert out["list"] == ["arn:aws:bedrock:us-east-1:<account>:guardrail/abc123", 7, None, "arn:aws:iam::<account>:role/x"]
    assert out["outputs"][0]["text"] == f"call {ACCOUNT} now"   # row text is data, never rewritten
    assert out["usage"] == {"topicPolicyUnits": 1} and raw["list"][0] == ARN   # the input is not mutated


class Fake:
    def __init__(self): self.calls = []
    def apply_guardrail(self, **kw):
        self.calls.append(kw)
        return {"action": "NONE", "usage": {"topicPolicyUnits": 1}, "ResponseMetadata": {"RequestId": "r"},
                "assessments": [{"topicPolicy": {"topics": [{"name": "InvestmentAdvice", "detected": True}]},
                                 "appliedGuardrailDetails": {"guardrailId": "abc123", "guardrailArn": ARN}}]}


def _control(live: dict):
    """A control-plane fake whose get_guardrail answer reproduces a recorded live_policy exactly."""
    class Control:
        def get_guardrail(self, guardrailIdentifier, guardrailVersion):
            g = {"version": live["version"], "status": live["status"], "updatedAt": live["updated_at"]}
            for k in live["policies"]:
                g[k] = {"present": True}
            if live["topics"]:
                g["topicPolicy"] = {"topics": [{"name": t} for t in live["topics"]]}
            if live["words"] or live["managed_word_lists"]:
                g["wordPolicy"] = {"words": [{"text": w} for w in live["words"]],
                                   "managedWordLists": [{"type": m} for m in live["managed_word_lists"]]}
            return g
    return Control()


def _frozen_apply_arms():
    frozen = set()
    for m in REPO.glob("benchmark/subsets/*/freeze-*.json"):
        frozen |= {a["config_hash"] for a in json.loads(m.read_text(encoding="utf-8")).get("arms", [])}
    arms = {}
    for p in REPO.glob("benchmark/results/*/*.arms.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            a = json.loads(line)
            if a["system"].startswith("bedrock-apply-") and a["config_hash"] in frozen:
                arms[a["config_hash"]] = a
    return list(arms.values())


@pytest.mark.parametrize("arm", _frozen_apply_arms(), ids=lambda a: f"{a['system']}-{a['config_hash']}")
def test_frozen_apply_arms_keep_their_config_hash_and_raw_has_no_account(arm):
    ident = arm["identity"]
    suite = arm["system"].removeprefix("bedrock-apply-")
    cfg = {suite: {"id": ident["guardrail_id"], "version": ident["guardrail_version"], **ident["config"]},
           "region": ident["region"]}
    fake = Fake()
    live = ident.get("live_policy")   # arms recorded before the live policy joined the identity have none
    c = BedrockApplyClient(suite, config=cfg, client=fake, control=_control(live) if live else None)
    qs = {"questions": arm["questions"], "decision": arm.get("decision")}
    assert c.identity == ident
    assert config_hash(c, qs) == arm["config_hash"]
    call = c.ask({"role": "user", "text": "hello"}, {"investmentadvice": {}})
    assert ACCOUNT not in json.dumps(call.raw) and "<account>" in json.dumps(call.raw)
    assert c.identity == ident and config_hash(c, qs) == arm["config_hash"]


def test_some_frozen_apply_arms_were_found():
    assert len(_frozen_apply_arms()) >= 4


def _frozen_checks_arms():
    frozen = set()
    for m in REPO.glob("benchmark/subsets/*/freeze-*.json"):
        frozen |= {a["config_hash"] for a in json.loads(m.read_text(encoding="utf-8")).get("arms", [])}
    arms = {}
    for p in REPO.glob("benchmark/results/*/*.arms.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            a = json.loads(line)
            if a["system"] == "bedrock-checks" and a["config_hash"] in frozen:
                arms[a["config_hash"]] = a
    return list(arms.values())


class FakeChecks:
    def invoke_guardrail_checks(self, **kw):
        return {"results": {}, "usage": {}, "ResponseMetadata": {}, "guardrailArn": ARN}


@pytest.mark.parametrize("arm", _frozen_checks_arms(), ids=lambda a: a["config_hash"])
def test_frozen_checks_arms_keep_their_config_hash_and_raw_has_no_account(arm):
    from goldrails_bench.bedrock import BedrockChecksClient
    c = BedrockChecksClient(region=arm["identity"]["region"], client=FakeChecks())
    qs = {"questions": arm["questions"], "decision": arm.get("decision")}
    assert c.identity == arm["identity"] and config_hash(c, qs) == arm["config_hash"]
    call = c.ask({"role": "user", "text": "hello"}, {"hate": {}})
    assert ACCOUNT not in json.dumps(call.raw)


def test_error_messages_keep_no_account():
    class Denied:
        def apply_guardrail(self, **kw):
            raise PermissionError(f"User: arn:aws:sts::{ACCOUNT}:assumed-role/x is not authorized")
    cfg = {"topics": {"id": "t", "version": "1", "topics": ["A"]}, "region": "us-east-1"}
    call = BedrockApplyClient("topics", config=cfg, client=Denied()).ask("hi", {"a": {}})
    assert not call.ok and ACCOUNT not in call.error and call.error.startswith("PermissionError: User: arn:aws:sts::<account>:")


def test_some_frozen_checks_arms_were_found():
    assert len(_frozen_checks_arms()) >= 1
