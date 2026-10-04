"""Edition 2 smoke test: 20 tune rows per adapter subtask per system, through the edition 2 adapters.

    uv run python benchmark/runs/e2_smoke.py plan                      # offline: the row selection and token estimates
    uv run python benchmark/runs/e2_smoke.py run --systems jev,open,bedrock
    uv run python benchmark/runs/e2_smoke.py run --systems clef,clef-flash,perplexity,strands   # new models (docs/28)
    uv run python benchmark/runs/e2_smoke.py report                    # offline: summary from the ledgers

Rows come only from ``dataset/edition2/build/F*.tune.jsonl`` (public tune split; the private slice is test-only and
is checked to be disjoint). Rows the owner excluded (``dataset/edition2/EXCLUDED.jsonl`` and the git-ignored
``*/private/EXCLUDED.jsonl``) are never picked. Nothing from the test split is read. Ledgers in ``benchmark/results/edition2-smoke/`` keep
row ids, labels and system outputs, never the row text, because many tune rows come from ids-only sources
(owner ruling 10). Error strings are cut to 300 characters and checked for row text before they are written.

New decision models (docs/benchmark/28): ``clef`` and ``clef-flash`` (Cloudflare Workers AI), ``perplexity``
(pplx-decider-v1-27b), ``strands`` (Strands Decider 2B on the GCP VM) and ``openai`` (gpt-6-luna, unverified stub).
A system whose credentials or VM slot are missing is skipped as ``not_configured`` before any row is read for it;
nothing is sent and nothing is written for it.

This is a compatibility check (docs/benchmark/28, "Smoke test for every new model"), not a scored run: no manifest,
no freeze, nothing here enters a leaderboard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "dataset" / "edition2" / "build"
OUT = REPO / "benchmark" / "results" / "edition2-smoke"
SEED = "e2-smoke-2026-10-04"
PER_SUBTASK = 20

from goldrails_bench.adapters import BedrockAdapter, NoulAdapter  # noqa: E402
from goldrails_bench.adapters.noul import TASK_QSET  # noqa: E402
from goldrails_bench import question_sets  # noqa: E402

# Adapter subtask -> (build file, row tags it draws from). Word filters have no edition 2 build yet; grounding
# relevance has no labelled rows. Both are reported as not run.
TASKS = {("content", "request"): ("F1", ("harmful_goal", "input", "over_refusal")),
         ("content", "reply"): ("F1", ("output",)),
         ("prompt_attacks", "direct"): ("F2", ("injection", "jailbreak", "leakage")),
         ("denied_topics", "topic"): ("F3", ("topic",)),
         ("sensitive_info", "entity_detection"): ("F5", ("pii",)),
         ("grounding", "grounding"): ("F6", ("grounding",)),
         ("word_filters", "word"): ("F4", ("word",)),
         ("word_filters", "profanity"): ("F4", ("profanity",))}
NOT_RUN = {("grounding", "relevance"): "no edition 2 tune row carries a relevance label"}
# Known request limits, in tokens. Open-Jev is served with --max-length 4096 (infra/gcp/startup.sh); Jev documents
# 32k tokens for state plus the longest question (docs/reference/typesafe/models.md). Kev and Laya do not document
# theirs here, so the 4096 reference is applied to them as a conservative proxy and labelled as such.
LIMITS = {"jev-1.13.0": (32000, "documented"), "open-jev-2b": (4096, "served --max-length"),
          "clef": (65536, "hosted context (Workers AI)"), "clef-flash": (65536, "hosted context (Workers AI)"),
          "pplx-decider-v1-27b": (262144, "hosted input limit (Perplexity docs)"),
          "strands-decider-2b": (4096, "documented window; cut silently, no truncation flag"),
          "gpt-6-luna": (None, "undocumented (limited preview)"),
          "laya": (512, "observed: usage.input_tokens tops out at 512 x questions, so each prompt is cut at 512"),
          "bedrock-guardrails": (None, "service")}
# Servers whose usage.input_tokens is the sum over one prompt per question: per-prompt tokens = usage / questions.
PER_PROMPT_USAGE = {"open-jev-2b", "laya"}
# Hosted joint-schema models report one input count for the whole request: at the limit means the input was capped.
WHOLE_REQUEST_USAGE = {"clef", "clef-flash", "pplx-decider-v1-27b"}
DEFAULT_LIMIT = (4096, "proxy: undocumented, 4096 reference")
NEAR = 0.8   # a row is near the limit at >= 80% of it
CHARS_PER_TOKEN = 3.5   # conservative (over-)estimate for English with a BPE tokenizer


def rows_of(feature: str) -> list:
    return [json.loads(x) for x in (BUILD / f"{feature}.tune.jsonl").open(encoding="utf-8")]


def private_ids() -> set:
    ids = set()
    for p in (BUILD / "private").glob("*.jsonl"):
        for x in p.open(encoding="utf-8"):
            try:
                ids.add(json.loads(x)["id"])
            except (ValueError, KeyError):
                pass
    return ids


def excluded_ids() -> set:
    """Ids the owner took out of edition 2 (public list plus any git-ignored private lists)."""
    ids = set()
    root = REPO / "dataset" / "edition2"
    for p in [root / "EXCLUDED.jsonl", *root.glob("*/private/EXCLUDED.jsonl")]:
        if p.exists():
            for x in p.open(encoding="utf-8"):
                if x.strip():
                    ids.add(json.loads(x)["id"])
    return ids


def _h(rid: str) -> str:
    return hashlib.sha256(f"{SEED}|{rid}".encode()).hexdigest()


def select() -> dict:
    """{(suite, subtask): [row dicts]}: 20 per subtask, round-robin over (tag, label) strata in a seeded order,
    preferring rows that need no owner review."""
    priv, excl = private_ids(), excluded_ids()
    out = {}
    for (suite, sub), (feat, tags) in TASKS.items():
        rows = [r for r in rows_of(feat) if r["subtask"] in tags and r["id"] not in excl]
        assert all(r["split"] == "tune" and r["visibility"] == "public" for r in rows), "non-tune or non-public row"
        assert not {r["id"] for r in rows} & priv, "a tune row is in the private slice"
        strata = defaultdict(list)
        for r in sorted(rows, key=lambda r: (bool(((r.get("attribute") or {}).get("e2") or {}).get("needs_owner_review")),
                                             _h(r["id"]))):
            strata[(r["subtask"], r["expected"])].append(r)
        keys = sorted(strata)
        picked, i = [], 0
        while len(picked) < PER_SUBTASK and any(strata[k] for k in keys):
            k = keys[i % len(keys)]
            if strata[k]:
                picked.append(strata[k].pop(0))
            i += 1
        out[(suite, sub)] = picked
    return out


def state_chars(r: dict) -> int:
    s = r["state"]
    n = len(s.get("text") or "") + len(s.get("source") or "") + len(s.get("query") or "")
    for c in s.get("context") or []:
        n += len(json.dumps(c, ensure_ascii=False))
    return n


def longest_question_chars(suite: str, sub: str) -> int:
    qs = question_sets.load("e2", TASK_QSET[(suite, sub)])["questions"]
    return max(len(json.dumps(q, ensure_ascii=False)) for q in qs.values())


def est_tokens(r: dict, suite: str, sub: str, system: str) -> int:
    q = 0 if system == "bedrock-guardrails" else longest_question_chars(suite, sub)
    return int((state_chars(r) + q) / CHARS_PER_TOKEN)


def limit_of(system: str):
    return LIMITS.get(system, DEFAULT_LIMIT)


def ids_only_flags() -> dict:
    from goldrails_dataset import e2_local
    pol = e2_local.policy()
    return lambda src: not e2_local.text_cleared(src, pol)


# --- text-leak guard -------------------------------------------------------------------------------------------

def _windows(text: str, n: int = 8) -> set:
    w = re.findall(r"\w+", (text or "").lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))} if len(w) >= n else ({" ".join(w)} if len(w) >= 4 else set())


def scrub(msg: str | None, r: dict) -> str | None:
    if not msg:
        return msg
    msg = msg[:300]
    s = r["state"]
    texts = [s.get("text"), s.get("source"), s.get("query")] + [json.dumps(c) for c in s.get("context") or []]
    low = " ".join(re.findall(r"\w+", msg.lower()))
    for t in texts:
        if t and len(t) >= 12 and (t.lower()[:40] in msg.lower() or any(w in low for w in _windows(t, 6))):
            return "[error text withheld: it echoed row text]"
    return msg


def leak_check(paths, rows_by_id: dict) -> list:
    """Row ids whose text (8-word runs, or the whole text when shorter) appears in any ledger."""
    blob = " ".join(re.findall(r"\w+", " ".join(p.read_text(encoding="utf-8") for p in paths).lower()))
    bad = []
    for rid, r in rows_by_id.items():
        s = r["state"]
        for t in (s.get("text"), s.get("source"), s.get("query")):
            if t and any(w in blob for w in _windows(t)):
                bad.append(rid)
                break
    return bad


# --- systems ---------------------------------------------------------------------------------------------------

NEW_KINDS = ("clef", "clef-flash", "perplexity", "strands", "openai")
KINDS = ("jev", "open", "bedrock") + NEW_KINDS


def build_systems(kinds: set, env=None) -> tuple[dict, dict]:
    """({system name: (adapter, workers)}, {kind: why it is not configured}). A missing credential or VM slot is
    reported, never raised, so one unconfigured system does not stop the others."""
    import os
    from goldrails_bench.systemone import SystemOneClient
    env = os.environ if env is None else env
    out, skipped = {}, {}
    if "jev" in kinds:
        c = SystemOneClient("jev-1.13.0", model="jev-1.13.0", identity={"model": "jev-1.13.0", "provider": "api.typesafe.ai"})
        out["jev-1.13.0"] = (NoulAdapter(c, endpoint="https://api.typesafe.ai"), 8)
    if "open" in kinds:
        from goldrails_bench.endpoints import resolve_models
        for m in resolve_models(mode="tunnel"):
            c = SystemOneClient(m["name"], base_url=m["url"], model=m["model"], identity=m["identity"], timeout=300)
            out[m["name"]] = (NoulAdapter(c, endpoint=m["url"]), 2)
    if "bedrock" in kinds:
        a = BedrockAdapter(config=bedrock_config())
        a.blocked = bedrock_blocked()
        out["bedrock-guardrails"] = (a, 1)
    out_new, skipped = build_new_systems(kinds, env)
    out.update({k: v for k, v in out_new.items() if k not in out})   # "open" may already hold the Strands slot
    return out, skipped


def build_new_systems(kinds: set, env) -> tuple[dict, dict]:
    """The docs/benchmark/28 systems. Hosted ones come from env (names in .env.example); Strands from the VM."""
    from goldrails_bench import hosted
    out, skipped = {}, {}
    for kind in ("clef", "clef-flash"):
        if kind in kinds:
            c = hosted.CloudflareSystemOneClient.from_env(kind, env=env)
            if c is None:
                skipped[kind] = hosted.not_configured(kind)
            else:
                out[c.system] = (NoulAdapter(c, endpoint=c.endpoint), 4)
    if "perplexity" in kinds:
        c = hosted.PerplexityDecisionsClient.from_env(env=env)
        if c is None:
            skipped["perplexity"] = hosted.not_configured("perplexity")
        else:
            out[c.system] = (NoulAdapter(c, endpoint=c.endpoint), 4)   # the client throttles the pool to 5/s
    if "openai" in kinds:
        c = hosted.OpenAIDecisionsClient.from_env(env=env)
        if c is None:
            skipped["openai"] = hosted.not_configured("openai")
        else:
            out[c.system] = (NoulAdapter(c, endpoint=c.endpoint), 2)
    if "strands" in kinds:
        found, why = strands_models()
        if not found:
            skipped["strands"] = f"not_configured: strands needs a kind=strands model on the GCP VM ({why})"
        from goldrails_bench.systemone import SystemOneClient
        for m in found:
            c = SystemOneClient(m["name"], base_url=m["url"], model=m["model"], identity=m["identity"], timeout=300)
            out[m["name"]] = (NoulAdapter(c, endpoint=m["url"]), 2)
    return out, skipped


def strands_models() -> tuple[list, str | None]:
    """([served kind=strands models], why there are none)."""
    try:
        from goldrails_bench.endpoints import resolve_models
        found = [m for m in resolve_models(mode="tunnel") if m["kind"] == "strands"]
    except Exception as e:  # noqa: BLE001  no gcloud, no VM, VM stopped: the system is not configured
        return [], f"{type(e).__name__}: {str(e)[:160]}"
    return found, None if found else "the VM serves no kind=strands model; add it to terraform.tfvars and apply"


def bedrock_config() -> dict | None:
    """ApplyGuardrail ids from the infra/aws Terraform outputs. A worktree has no state of its own, so the outputs are
    read (read only) from the state file of the checkout that holds it."""
    import subprocess
    for state in (REPO / "infra/aws/terraform.tfstate", REPO.parents[2] / "infra/aws/terraform.tfstate"):
        if state.exists():
            out = json.loads(subprocess.run(["terraform", "output", "-json", f"-state={state}"], cwd=REPO / "infra" / "aws",
                                            check=True, capture_output=True, text=True).stdout)
            return {**out["guardrails"]["value"], "region": out["region"]["value"]}
    return None


def bedrock_blocked() -> str | None:
    """Why no Bedrock call can be made (credentials), or None. Checked once before any call."""
    import os
    try:
        import boto3
        boto3.Session(profile_name=os.environ.get("AWS_PROFILE") or None).client("sts").get_caller_identity()
        return None
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:200]}"


def bedrock_offers(suite: str, sub: str) -> bool:
    # Denied topics use the 8-topic edition 2 guardrail (infra/aws "topics_e2"), created 5 October 2026.
    return True


def record(system, suite, sub, r, res, ids_only, rerun=False) -> dict:
    d = res.to_dict()
    exp = r["expected"]
    correct = None if d["decision"] is None else (d["decision"] == (exp == "yes"))
    srv = dict(d["serving"] or {})
    srv.pop("identity", None) if srv.get("identity") is None else None
    attempts = [{k: a.get(k) for k in ("attempt", "ok", "latency_s", "at")} | {"error": scrub(a.get("error"), r)}
                for a in d.get("attempts") or []]
    tok = est_tokens(r, suite, sub, system)
    # The servers' usage.input_tokens is not comparable with a per-prompt limit: Open-Jev sums one prompt per
    # question, Laya reports padded batch lengths. Near-limit uses the per-prompt estimate (state plus the longest
    # question); the reported count is kept beside it.
    used = (d.get("usage") or {}).get("input_tokens") if isinstance(d.get("usage"), dict) else None
    lim, basis = limit_of(system)
    nq = len(question_sets.load("e2", TASK_QSET[(suite, sub)])["questions"])
    tokens_basis = "per-prompt chars/3.5 estimate (state + longest question)"
    if system in PER_PROMPT_USAGE and isinstance(used, int):
        tok, tokens_basis = round(used / nq), "usage.input_tokens / questions (mean per prompt)"
    at_cap = capped(system, used, nq, lim)
    return {"system": system, "suite": suite, "subtask": sub, "row_id": r["id"], "row_tag": r["subtask"],
            "expected": exp, "source": r["provenance"]["source"], "ids_only_source": ids_only,
            "outcome": d["outcome"], "decision": d["decision"], "score": d["score"], "correct": correct,
            "per_question": d["per_question"], "error": scrub(d.get("error"), r), "latency_s": d.get("latency_s"),
            "usage": d.get("usage"), "attempts": attempts, "serving": srv,
            "state_chars": state_chars(r), "est_tokens": tok, "tokens_basis": tokens_basis, "usage_input_tokens": used, "questions": nq,
            "at_cap": at_cap, "limit_tokens": lim, "limit_basis": basis,
            "near_limit": bool(lim and (tok >= NEAR * lim or at_cap)), "rerun": rerun,
            "truncated": d.get("truncated"), "truncation_reported": srv.get("truncation_reported"),
            "truncation": trunc_summary(d.get("truncation")),
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def capped(system: str, used, nq: int, lim) -> bool:
    """usage.input_tokens shows the input reached the system's limit (so part of it was probably cut)."""
    if not lim or not isinstance(used, int) or isinstance(used, bool):
        return False
    if system in PER_PROMPT_USAGE:
        return used >= nq * lim
    if system in WHOLE_REQUEST_USAGE:
        return used >= 0.99 * lim
    return False


def trunc_summary(t: dict | None) -> dict | None:
    """The server's truncation report without the per-question detail (token counts only, no text)."""
    if not isinstance(t, dict):
        return None
    keep = ("max_len", "head_max_len", "encoder_max_positions", "truncated", "state_truncated", "state_tokens",
            "input_tokens_before", "input_tokens_after", "matches_usage")
    return {k: t.get(k) for k in keep} | {"questions_truncated": sum(bool((v or {}).get("truncated"))
                                                                     for v in (t.get("questions") or {}).values())}


def recompute(path: Path, rows: dict) -> None:
    """Re-derive the token fields of an existing ledger from its stored outputs (no calls)."""
    out = []
    for x in path.open(encoding="utf-8"):
        d = json.loads(x)
        r, system, suite, sub = rows[d["row_id"]], d["system"], d["suite"], d["subtask"]
        used = (d.get("usage") or {}).get("input_tokens") if isinstance(d.get("usage"), dict) else None
        lim, basis = limit_of(system)
        nq = len(question_sets.load("e2", TASK_QSET[(suite, sub)])["questions"])
        tok, tb = est_tokens(r, suite, sub, system), "per-prompt chars/3.5 estimate (state + longest question)"
        if system in PER_PROMPT_USAGE and isinstance(used, int):
            tok, tb = round(used / nq), "usage.input_tokens / questions (mean per prompt)"
        at_cap = capped(system, used, nq, lim)
        d.update(est_tokens=tok, tokens_basis=tb, usage_input_tokens=used, questions=nq, at_cap=at_cap,
                 limit_tokens=lim, limit_basis=basis, near_limit=bool(lim and (tok >= NEAR * lim or at_cap)))
        out.append(json.dumps(d, ensure_ascii=False))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def run(kinds: set, only: set | None = None) -> None:
    run_selection(kinds, select(), OUT, only)


def run_selection(kinds: set, sel: dict, out: Path, only: set | None = None, reruns: bool = True,
                  guard=None, retry_failed: bool = False) -> dict:
    """Send ``sel`` ({(suite, subtask): [row dicts]}) to every configured system of ``kinds`` and append one record
    per row to ``out/<system>.jsonl`` as each answer arrives, so an interrupted run resumes where it stopped (rows
    already in the ledger are not sent again). ``guard(row)`` is called before a row is sent and must raise to refuse
    it. ``reruns`` re-sends the first 5 rows of the first offered subtask (determinism check). ``retry_failed``
    sends again only the rows whose latest record failed and appends the new record marked ``retry_of_failure``
    (the failed record stays in the ledger; a scorer takes the latest record per row). Returns
    {system: {seconds, sent, failed, started, finished}}; a Bedrock run with no credentials writes
    ``<system>.blocked.json`` and sends nothing."""
    unknown = kinds - set(KINDS)
    if unknown:
        raise SystemExit(f"unknown --systems {sorted(unknown)}; known: {', '.join(KINDS)}")
    if guard is not None:   # refuse before any system is built or any call is made
        for rows in sel.values():
            for r in rows:
                guard(r)
    systems, skipped = build_systems(kinds)
    for kind, why in skipped.items():
        print(f"{kind:20s} NOT_CONFIGURED, nothing sent: {why}", flush=True)
    timing = {}
    if not systems:
        print("no configured system: nothing to run", flush=True)
        return timing
    out.mkdir(parents=True, exist_ok=True)
    is_ids_only = ids_only_flags()
    now = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())  # noqa: E731
    for name, (adapter, workers) in systems.items():
        if only and name not in only:
            continue
        ledger = out / f"{name}.jsonl"
        done, last = set(), {}
        if ledger.exists():
            for x in ledger.open(encoding="utf-8"):
                d = json.loads(x)
                done.add((d["suite"], d["subtask"], d["row_id"], d["rerun"]))
                last[(d["suite"], d["subtask"], d["row_id"], d["rerun"])] = d["outcome"]
        if retry_failed:
            done = {k for k in done if last[k] != "failed"}
        t0, started, sent, failed = time.time(), now(), 0, 0
        blocked = getattr(adapter, "blocked", None)
        for (suite, sub), rows in sel.items():
            todo = [r for r in rows if (suite, sub, r["id"], False) not in done]
            if blocked and (name != "bedrock-guardrails" or bedrock_offers(suite, sub)):
                print(f"{name:20s} {suite}/{sub:18s} BLOCKED, nothing sent: {blocked}", flush=True)
                (out / f"{name}.blocked.json").write_text(json.dumps({"system": name, "reason": blocked,
                                                                      "at": now()}, indent=1) + "\n")
                continue
            if name == "bedrock-guardrails" and not bedrock_offers(suite, sub):
                res_of = lambda r, s=suite, t=sub: adapter.not_offered(s, t)  # noqa: E731
            else:
                def res_of(r, s=suite, t=sub):
                    if guard is not None:
                        guard(r)
                    return adapter.evaluate(s, t, {"state": r["state"]})
            fails = 0
            with ThreadPoolExecutor(max_workers=workers) as ex, ledger.open("a", encoding="utf-8") as f:
                for r, res in zip(todo, ex.map(res_of, todo)):
                    rec = record(name, suite, sub, r, res, is_ids_only(r["provenance"]["source"]))
                    if retry_failed:
                        rec["retry_of_failure"] = True
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    f.flush()
                    fails += res.outcome == "failed"
            sent, failed = sent + len(todo), failed + fails
            print(f"{name:20s} {suite}/{sub:18s} {len(todo):3d} sent, {fails} failed", flush=True)
        # determinism: rerun the first 5 rows of the first offered subtask
        first = None if (blocked or not reruns) else \
            next(((s, t) for (s, t) in sel if name != "bedrock-guardrails" or bedrock_offers(s, t)), None)
        if first:
            rr = [r for r in sel[first][:5] if (first[0], first[1], r["id"], True) not in done]
            with ThreadPoolExecutor(max_workers=workers) as ex:
                results = list(ex.map(lambda r: adapter.evaluate(first[0], first[1], {"state": r["state"]}), rr))
            with ledger.open("a", encoding="utf-8") as f:
                for r, res in zip(rr, results):
                    f.write(json.dumps(record(name, *first, r, res, is_ids_only(r["provenance"]["source"]), rerun=True),
                                       ensure_ascii=False) + "\n")
        timing[name] = {"seconds": round(time.time() - t0, 1), "sent": sent, "failed": failed,
                        "started": started, "finished": now(), "blocked": blocked}
        print(f"{name}: {time.time() - t0:.0f}s", flush=True)
    return timing


# --- report ----------------------------------------------------------------------------------------------------

def load_ledgers() -> list:
    out = []
    for p in sorted(OUT.glob("*.jsonl")):
        out += [json.loads(x) for x in p.open(encoding="utf-8")]
    return out


def summarise(recs: list, picked: dict | None = None) -> dict:
    """``picked`` maps "suite/subtask" to the current selection's ids; ledger records for rows outside it (picked by
    an earlier build of the tune split) are left out of the table and counted under ``superseded``."""
    if picked is not None:
        keep = {(k, i) for k, ids in picked.items() for i in ids}
        stale = Counter(d["system"] for d in recs if (f"{d['suite']}/{d['subtask']}", d["row_id"]) not in keep)
        recs = [d for d in recs if (f"{d['suite']}/{d['subtask']}", d["row_id"]) in keep]
    else:
        stale = Counter()
    main = [d for d in recs if not d["rerun"]]
    by = defaultdict(list)
    for d in main:
        by[(d["system"], d["suite"], d["subtask"])].append(d)
    table = []
    for (sy, su, st), ds in sorted(by.items()):
        n = len(ds)
        c = Counter(d["outcome"] for d in ds)
        adapter_err = sum(1 for d in ds if d["outcome"] == "failed" and (d["error"] or "").startswith("NoDecision"))
        transport = c["failed"] - adapter_err
        sent = n - c["not_offered"]
        dec = [d for d in ds if d["outcome"] == "decided"]
        bad_prob = sum(1 for d in dec for v in (d["per_question"] or {}).values()
                       if isinstance(v, (int, float)) and not 0.0 <= v <= 1.0 and d["system"] != "bedrock-guardrails")
        lat = sorted(d["latency_s"] for d in dec if d["latency_s"] is not None)
        table.append({"system": sy, "suite": su, "subtask": st, "rows": n, "sent": sent, "decided": c["decided"],
                      "failed": c["failed"], "failure_rate": round(c["failed"] / sent, 4) if sent else None,
                      "not_offered": c["not_offered"], "adapter_errors": adapter_err, "transport_errors": transport,
                      "near_limit": sum(d["near_limit"] for d in ds), "at_cap": sum(d.get("at_cap", False) for d in ds),
                      "truncated": sum(1 for d in ds if d.get("truncated") is True),
                      "truncation_reported": sum(1 for d in ds if d.get("truncation_reported") is True),
                      "max_est_tokens": max(d["est_tokens"] for d in ds),
                      "max_usage_input_tokens": max((d.get("usage_input_tokens") or 0 for d in ds), default=0) or None,
                      "limit_tokens": ds[0]["limit_tokens"], "limit_basis": ds[0]["limit_basis"],
                      "correct": sum(1 for d in dec if d["correct"]), "probs_out_of_range": bad_prob,
                      "p50_latency_s": lat[len(lat) // 2] if lat else None,
                      "error_kinds": dict(Counter((d["error"] or "").split(":")[0] for d in ds if d["outcome"] == "failed"))})
    reruns = defaultdict(list)
    first = {(d["system"], d["suite"], d["subtask"], d["row_id"]): d for d in main}
    for d in recs:
        if d["rerun"]:
            a = first.get((d["system"], d["suite"], d["subtask"], d["row_id"]))
            if a and a["score"] is not None and d["score"] is not None:
                reruns[d["system"]].append(abs(a["score"] - d["score"]))
            elif a:
                reruns[d["system"]].append(None)
    det = {s: {"rows": len(v), "max_abs_score_diff": max((x for x in v if x is not None), default=None),
               "unscored": sum(x is None for x in v)} for s, v in reruns.items()}
    return {"table": table, "determinism": det, "superseded_records": dict(stale)}


def write_summary(summary: dict, extra: dict) -> Path:
    p = OUT / "summary.json"
    p.write_text(json.dumps({**extra, **summary}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def plan() -> None:
    sel = select()
    is_ids_only = ids_only_flags()
    for (su, st), rows in sel.items():
        c = Counter((r["subtask"], r["expected"]) for r in rows)
        io = sum(is_ids_only(r["provenance"]["source"]) for r in rows)
        toks = [est_tokens(r, su, st, "kev-4b") for r in rows]
        print(f"{su}/{st}: {len(rows)} rows {dict(c)} ids-only {io}, est tokens max {max(toks)}")
    for k, why in NOT_RUN.items():
        print(f"{k[0]}/{k[1]}: not run ({why})")
    # offline: every tune row's estimated size against the 4096 reference
    for (su, st), (feat, tags) in TASKS.items():
        rows = [r for r in rows_of(feat) if r["subtask"] in tags]
        toks = [est_tokens(r, su, st, "kev-4b") for r in rows]
        print(f"  all tune {su}/{st}: {len(rows)} rows, near 4096 (>= {int(NEAR * 4096)}): "
              f"{sum(t >= NEAR * 4096 for t in toks)}, over: {sum(t >= 4096 for t in toks)}, max {max(toks)}")


def tune_size_scan() -> dict:
    out = {}
    for (su, st), (feat, tags) in TASKS.items():
        rows = [r for r in rows_of(feat) if r["subtask"] in tags]
        for system in ("jev-1.13.0", "kev-4b", "bedrock-guardrails"):
            lim, basis = limit_of(system)
            if not lim:
                continue
            toks = [est_tokens(r, su, st, system) for r in rows]
            out.setdefault(f"{su}/{st}", {"rows": len(rows)})[f"{lim} ({basis})"] = {
                "near": sum(t >= NEAR * lim for t in toks), "over": sum(t >= lim for t in toks), "max_est_tokens": max(toks)}
    return out


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["plan", "run", "report"])
    ap.add_argument("--systems", default="jev,open,bedrock")
    ap.add_argument("--only", default=None, help="comma-separated system names to run")
    a = ap.parse_args(argv)
    if a.stage == "plan":
        plan()
    elif a.stage == "run":
        run(set(a.systems.split(",")), set(a.only.split(",")) if a.only else None)
    else:
        recs = load_ledgers()
        sel = select()
        rows_by_id = {r["id"]: r for rows in sel.values() for r in rows}
        leaks = leak_check(sorted(OUT.glob("*.jsonl")), rows_by_id)
        s = summarise(recs, {f"{k[0]}/{k[1]}": [r["id"] for r in v] for k, v in sel.items()})
        p = write_summary(s, {"seed": SEED, "per_subtask": PER_SUBTASK, "split": "tune",
                              "not_run": {f"{k[0]}/{k[1]}": v for k, v in NOT_RUN.items()},
                              "tune_size_scan": tune_size_scan(), "leak_check": {"rows_with_text_in_ledgers": len(leaks)},
                              "row_ids": {f"{k[0]}/{k[1]}": [r["id"] for r in v] for k, v in sel.items()}})
        for t in s["table"]:
            print(f"{t['system']:20s} {t['suite']}/{t['subtask']:18s} rows {t['rows']:3d} failed {t['failed']:2d} "
                  f"({t['failure_rate']}) not_offered {t['not_offered']:2d} adapter_err {t['adapter_errors']} "
                  f"near_limit {t['near_limit']} at_cap {t['at_cap']} truncated {t['truncated']} reported {t['truncation_reported']} correct {t['correct']}/{t['decided']}")
        print("determinism", s["determinism"])
        print("leaks", leaks)
        print(p)
        return 1 if leaks else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
