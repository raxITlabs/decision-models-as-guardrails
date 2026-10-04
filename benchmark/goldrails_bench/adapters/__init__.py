"""Task-based adapters (contract v2.0). See ``base`` for the contract and README.md in this directory for the rules.

    from goldrails_bench.adapters import NoulAdapter, BedrockAdapter, policy_text
"""
from .base import (DECIDED, FAILED, NOT_OFFERED, OUTCOMES, SUITES, THRESHOLD, Adapter, AdapterResult, policy_path,
                   policy_text, serving)
from .bedrock import BedrockAdapter
from .noul import NoulAdapter
from .sandbox import SandboxError, hf_load_kwargs, sandbox_record
from .verdict import VendorVerdict, VerdictAPIAdapter

__all__ = ["DECIDED", "FAILED", "NOT_OFFERED", "OUTCOMES", "SUITES", "THRESHOLD", "Adapter", "AdapterResult",
           "policy_path", "policy_text", "serving", "BedrockAdapter", "NoulAdapter", "SandboxError", "hf_load_kwargs",
           "sandbox_record", "VendorVerdict", "VerdictAPIAdapter"]
