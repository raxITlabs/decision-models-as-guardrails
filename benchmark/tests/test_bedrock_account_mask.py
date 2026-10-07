"""Raw Bedrock responses and error messages keep no AWS account id."""
from goldrails_bench.bedrock_apply import BedrockApplyClient
from goldrails_bench.bedrock import mask_account_ids

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


class FakeChecks:
    def invoke_guardrail_checks(self, **kw):
        return {"results": {}, "usage": {}, "ResponseMetadata": {}, "guardrailArn": ARN}


def test_error_messages_keep_no_account():
    class Denied:
        def apply_guardrail(self, **kw):
            raise PermissionError(f"User: arn:aws:sts::{ACCOUNT}:assumed-role/x is not authorized")
    cfg = {"topics": {"id": "t", "version": "1", "topics": ["A"]}, "region": "us-east-1"}
    call = BedrockApplyClient("topics", config=cfg, client=Denied()).ask("hi", {"a": {}})
    assert not call.ok and ACCOUNT not in call.error and call.error.startswith("PermissionError: User: arn:aws:sts::<account>:")


