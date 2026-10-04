"""The sandbox rule for Hugging Face reproductions (contract v2.0, Security).

A model reproduced from the Hugging Face Hub (Llama Guard, ShieldGemma, a vendor's open checkpoint) runs in a sandbox:
a throwaway VM or container with no cloud credentials, no repository secrets and no write access to the benchmark's
ledgers, which the run's output is copied out of afterwards. ``trust_remote_code`` stays off. A repository that
needs it may run only after someone has read the code at the pinned revision and recorded the review (who, when,
which revision, which files). Pin the revision as a commit hash, never a branch name, so the reviewed code is the
code that runs.

``hf_load_kwargs`` is the one place adapter code builds ``from_pretrained`` arguments, so the rule is enforced in code
and the review record ends up in the result's serving config.
"""
from __future__ import annotations

import re

COMMIT = re.compile(r"^[0-9a-f]{40}$")
REVIEW_FIELDS = ("reviewer", "reviewed_on", "revision", "files")


class SandboxError(ValueError):
    pass


def hf_load_kwargs(repo_id: str, revision: str, trust_remote_code: bool = False, code_review: dict | None = None,
                   **extra) -> dict:
    """``from_pretrained`` keyword arguments for a pinned, sandboxed reproduction.

    Raises SandboxError when the revision is not a full commit hash, or when ``trust_remote_code`` is requested
    without a code review record of that exact revision."""
    if not COMMIT.match(revision or ""):
        raise SandboxError(f"{repo_id}: pin a 40-character commit hash, not {revision!r}")
    if extra.get("trust_remote_code") is not None:
        raise SandboxError("pass trust_remote_code as its own argument")
    if trust_remote_code:
        missing = [f for f in REVIEW_FIELDS if not (code_review or {}).get(f)]
        if missing:
            raise SandboxError(f"{repo_id}: trust_remote_code needs a code review record; missing {', '.join(missing)}")
        if code_review["revision"] != revision:
            raise SandboxError(f"{repo_id}: the review covers {code_review['revision']}, the run pins {revision}")
    return {"pretrained_model_name_or_path": repo_id, "revision": revision, "trust_remote_code": bool(trust_remote_code),
            **extra}


def sandbox_record(repo_id: str, revision: str, trust_remote_code: bool = False, code_review: dict | None = None,
                   sandbox: str | None = None) -> dict:
    """What goes into ``serving`` for a Hugging Face reproduction: the pinned source, whether remote code ran, the
    review that allowed it, and where it ran."""
    hf_load_kwargs(repo_id, revision, trust_remote_code, code_review)   # same checks
    return {"hf_repo": repo_id, "hf_revision": revision, "trust_remote_code": bool(trust_remote_code),
            "code_review": code_review if trust_remote_code else None, "sandbox": sandbox}
