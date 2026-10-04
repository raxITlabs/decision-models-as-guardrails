"""Laya's input truncation: the server's report reaches every Noul adapter result. Fakes only, no network calls.

The server (infra/gcp/laya_server.py) measures the cut with the laya package; that half runs only where laya is
installed and is skipped otherwise.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from goldrails_bench.adapters import DECIDED, FAILED, NoulAdapter
from goldrails_bench.policy import NO_RETRY
from goldrails_bench.systemone import SystemOneCall, server_metadata

ROOT = Path(__file__).resolve().parents[2]


def report(truncated: bool, before=600, after=512) -> dict:
    return {"max_len": 512, "head_max_len": 192, "encoder_max_positions": 8192, "truncated": truncated,
            "state_truncated": truncated, "state_tokens": 500, "input_tokens_before": before,
            "input_tokens_after": after if truncated else before, "matches_usage": True,
            "questions": {"unsupported": {"input_tokens_before": before, "input_tokens_after": after if truncated else before,
                                          "state_tokens_kept": 400, "head_cut": False, "truncated": truncated}}}


class FakeLaya:
    system, model = "laya", "laya"
    identity = {"ref": "convaiinnovations/laya", "revision": "1c5edc17a7acd8701df6fc341c0d179f1c62c982", "kind": "laya"}

    def __init__(self, trunc=None, fail=None, p=0.7):
        self.trunc, self.fail, self.p = trunc, fail, p

    def ask(self, state, questions):
        if self.fail:
            return SystemOneCall(system=self.system, ok=False, error=self.fail)
        answers = {k: {"type": "noul", "noul": self.p} for k in questions}
        raw = {"model": "laya", "answers": answers, "usage": {"input_tokens": 512}}
        if self.trunc is not None:
            raw["metadata"] = {"ref": self.identity["ref"], "truncation": self.trunc}
        return SystemOneCall(system=self.system, ok=True, model="laya", answers=answers,
                             usage={"input_tokens": 512}, raw=raw)


ROW = {"role": "assistant", "text": "r", "source": "s", "query": "q"}


@pytest.mark.parametrize("cut", [True, False])
def test_laya_results_record_truncated_and_the_served_context(cut):
    res = NoulAdapter(FakeLaya(report(cut)), policy=NO_RETRY).evaluate("grounding", "grounding", ROW)
    assert res.outcome == DECIDED and res.truncated is cut
    assert res.truncation["questions"]["unsupported"]["truncated"] is cut
    s = res.serving
    assert s["max_length"] == 512 and s["served_max_length"] == 512 and s["head_max_length"] == 192
    assert s["truncation_reported"] is True and s["encoder_max_positions"] == 8192
    d = res.to_dict()
    assert d["truncated"] is cut and d["truncation"]["input_tokens_before"] == 600


def test_a_pinned_max_length_is_kept_and_the_served_one_shown_beside_it():
    a = NoulAdapter(FakeLaya(report(True)), max_length=1024, policy=NO_RETRY)
    s = a.evaluate("grounding", "grounding", ROW).serving
    assert s["max_length"] == 1024 and s["served_max_length"] == 512


def test_laya_without_a_report_is_unknown_not_untruncated():
    res = NoulAdapter(FakeLaya(None), policy=NO_RETRY).evaluate("grounding", "grounding", ROW)
    assert res.outcome == DECIDED and res.truncated is None and res.truncation is None
    assert res.serving["truncation_reported"] is False and res.serving["max_length"] is None


def test_failed_laya_call_has_no_truncation_claim():
    res = NoulAdapter(FakeLaya(fail="APIConnectionError: down"), policy=NO_RETRY).evaluate("grounding", "grounding", ROW)
    assert res.outcome == FAILED and res.truncated is None and "truncation_reported" not in res.serving


def test_other_noul_servers_are_untouched():
    class Kev(FakeLaya):
        system, model = "kev-4b", "kev-4b"
        identity = {"ref": "jaredpalmer/kev-4b", "revision": "abc", "kind": "kev"}
    res = NoulAdapter(Kev(None), policy=NO_RETRY).evaluate("grounding", "grounding", ROW)
    assert res.truncated is None and "truncation_reported" not in res.serving


def test_client_keeps_the_metadata_the_sdk_model_drops():
    class Http:
        def __init__(self, body): self.body = body
        def json(self):
            if isinstance(self.body, Exception):
                raise self.body
            return self.body

    def resp(body):
        return types.SimpleNamespace(raw_http_response=Http(body))
    assert server_metadata(resp({"metadata": {"truncation": {"truncated": True}}})) == {"truncation": {"truncated": True}}
    assert server_metadata(resp({"answers": {}})) is None
    assert server_metadata(resp(ValueError("not json"))) is None
    assert server_metadata(object()) is None


def test_server_measures_the_cut_with_the_package():
    pytest.importorskip("laya")
    transformers = pytest.importorskip("transformers")
    from laya.agent import Agent
    spec = importlib.util.spec_from_file_location("laya_server", ROOT / "infra/gcp/laya_server.py")
    ls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ls)
    try:
        tok = transformers.AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")
    except Exception as e:  # noqa: BLE001 - offline
        pytest.skip(f"tokenizer unavailable: {e}")
    agent = types.SimpleNamespace(tok=tok, cfg={"max_len": 512, "head_max_len": 192}, _to_internal=Agent._to_internal)
    qs = {"q": {"type": "noul", "instructions": "Is the reply unsupported by the source?"}}
    short = ls.truncation_report(agent, {"role": "user", "text": "hi"}, qs)
    assert short["truncated"] is False and short["input_tokens_before"] == short["input_tokens_after"]
    long = ls.truncation_report(agent, {"role": "user", "text": "word " * 2000}, qs)
    assert long["truncated"] is True and long["input_tokens_after"] == 512 < long["input_tokens_before"]
