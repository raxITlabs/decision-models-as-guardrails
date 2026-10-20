# Edition 3 models: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score six decision models taken from the Jev Decision Index 0.3.2 (16 October 2026) on every edition 2 test
row and the unpublished slice, under contract v2.0. The six are Perplexity Decider Flash v1.2 4B, vLLM-SR d3-flash 9B,
OneJev1.5-9B, vLLM-SR d3-mini 4B, Kev 27B and Perplexity Decider v1.2 27B. A seventh system, Microsoft-Decision-1
(released 9 October 2026, not in the index), runs hosted through OpenRouter on the public test rows only.

**Architecture:** This is an extension run, the same mechanism that added Strands Decider, Jev 1.14.0 and gpt-6-luna.
It uses the same rows, question sets and fixed 0.5 rule, and its extension manifest
(`benchmark/subsets/edition2/freeze-manifest-index-models.json`) is committed before the first test call. One run
module, `benchmark/runs/e2_index_run.py`, follows `e2_strands_run.py`. The new serving kinds go on the GCP VM next to
kev/openjev/laya/strands.

**Tech stack:** Python 3.12 with `uv`, Terraform (infra/gcp), and each vendor's own server code pinned by commit.

**Scope note:** These six are called "edition 3" in conversation, but nothing here changes `benchmark/contracts/` or
the edition 2 rows. A true edition 3 (new rows or a new contract) is a separate release and outside this plan.

## The seven systems

| name (VM/ledger) | HF repo @ commit | bf16 size | served by | where |
|---|---|---|---|---|
| `pplx-decider-flash-v1-2` | `perplexity-ai/pplx-decider-flash-v1.2` @ `6d771ad7b5ecff5e93b8fc7b90d4c5ccc341954d` | 9.1 GB | new `infra/gcp/pplx_server.py` wrapping `pplx_decider.Decider` from the checkpoint's `source/` (no server ships) | pass 1, L4 card 0 |
| `d3-mini` | `vllm-sr/d3-mini` @ `97dd054df4b3e0b3beb6af23ab8c82b7c0052e0e` | 9.1 GB | `d3_server.py` from the checkpoint (matches AutoModel exactly; `vllm-sr serve` batching flips near-ties) | pass 1, L4 card 0 |
| `d3-flash` | `vllm-sr/d3-flash` @ `8b35c853b90e777595ec36bacae820fe08ea077a` | 16.8 GB | `d3_server.py` from the checkpoint | pass 1, L4 card 1 |
| `onejev-1-5-9b` | `OmniJev/OneJev1.5-9B` @ `ec2f276eab207810f576fb1f2d68c2acabd3eb71` | 18.8 GB | `qev serve`, github.com/OmniJev/OneJev @ `80d4e5f2f6dd5af55ca78e74d0dfa3536276106d` | pass 1, L4 card 2 |
| `kev-27b` | `jaredpalmer/kev-27b` @ `af0e6d551bdc2cc724f3e9d7a8bee1cd4fb8f7bf` | 51.3 GB, ~65.5 GB resident | `kev.serve`, github.com/jaredpalmer/kev @ `1f04cfa28e6a708485b28a9585010b9e436b776e` | pass 2, one A100 80 GB |
| `microsoft-decision-1` | none (no open weights; HF URL 404). Pinned to the reported snapshot `microsoft/microsoft-decision-1-20261009` | hosted | OpenRouter `POST /api/alpha/decisions`, model `microsoft/microsoft-decision-1` (`hosted.MicrosoftDecisionClient`) | hosted, public test rows only |
| `pplx-decider-v1-2-27b` | `perplexity-ai/pplx-decider-v1.2` @ `225c913ddc8761a8264f04f64548e1f97e443eb3` | 52.2 GB | Perplexity Decisions API if it serves v1.2 (Task 1); otherwise `pplx_server.py` | hosted, or pass 3 on one A100 80 GB |

The six open models are Apache-2.0 and ungated (HF API, read 17 October 2026). The flash v1.2 card still says "the repository is
private". It isn't, and the run records that the download needed no token.

**Kev 27B does not fit on L4 cards.** Its card asks for one B200, H200 or H100 80 GB GPU, and `kev.serve` cannot split
a model across cards (only kind `strands` can). It runs on `a2-ultragpu-1g`, as the Strands 26B-A4B did after its
four-L4 split answered wrongly.

## Global constraints

- `benchmark/contracts/` and the primary and existing extension manifests in `benchmark/subsets/edition2/` stay
  untouched. The new manifest is the only file added there.
- Fixed rule: max over the decision Nouls >= 0.5 (`adapters/noul.py`). No tuning, no per-model question wording.
- Every system sends Noul joint requests, the same as every other Noul system. Perplexity's flash card says it scores
  higher with one question per request, and the run discloses that instead of changing the request.
- The unpublished slice goes only to the project VM. Sending it to Perplexity for v1.2 needs a new owner ruling,
  because ruling 21 covered v1 only.
- Microsoft-Decision-1 gets the public edition 2 test rows only. The unpublished slice never goes to OpenRouter or
  Microsoft, so its unpublished-slice view is reported as not run, with that reason.
- Every open model is pinned by HF commit and every server by package commit. Each server runs with `HF_HUB_OFFLINE=1`
  on the revision `startup.sh` downloaded.
- Ask the owner and wait for a yes before each paid step: the API probe, VM smoke, each VM pass, and the hosted run.
- Keys come from `.env` only. Never print or commit one.

## Review focus

1. **Truncation.** Each server's context limit must reach `e2_smoke.LIMITS`. Kev 27B: 65,536 (documented). pplx
   servers: run at `max_length=32768`, the training length on the card. d3 and OneJev: read each card. If a card gives
   no limit, record the 4,096 proxy with that label. A row over its limit must be counted, never silently scored.
2. **Two models on one card.** d3-mini and pplx flash share L4 card 0. The smoke determinism reruns must agree, and
   neither server may return a CUDA OOM as an answer.
3. **Model identity.** Perplexity's open server answers to `jev-latest`. `pplx_server.py` must report its own name,
   and the hosted v1.2 client must keep `ModelIdentityError` for a reported Jev name.
4. **Response shape.** `d3_server.py` and `qev serve` claim System One. If either returns a field the TypeSafe SDK
   cannot parse, the call fails and must not be scored as 0.
5. **Microsoft-Decision-1 identity.** Any reported model other than `microsoft/microsoft-decision-1-20261009` is a
   final `ModelIdentityError`. If OpenRouter moves to a new snapshot mid-run, stop and record it, never mix snapshots.
   OpenRouter routes it to Azure today; `serving_provider` is recorded per call.
6. **Hardware fallback.** If no zone has an A100 80 GB, stop Kev 27B and record it in `NOT_RUN` with the reason. Do
   not split it over L4s.

---

### Task 1: Confirm Perplexity Decider v1.2 on the Decisions API (gate)

**Files:** none (finding recorded in Task 5's `DISCLOSURES`)

- [ ] **Step 1:** Ask the owner to approve one canned request (a synthetic state, no dataset row) costing under
  USD 0.01.
- [ ] **Step 2:** `POST https://api.perplexity.ai/v1/decisions` with `model` set to `pplx-decider-v1.2`, then to
  `pplx-decider-v1.2-27b`. Record each status and the `model` in the response.
- [ ] **Step 3:** Decide. A 200 that reports a v1.2 name means **hosted** (Task 2 applies, Task 3's pass 3 does
  not). Anything else means **self-hosted** (skip Task 2, run pass 3).

### Task 2: Hosted Perplexity v1.2 (only if Task 1 says hosted)

**Files:**
- Modify: `benchmark/goldrails_bench/hosted.py:264-330`
- Modify: `benchmark/goldrails_bench/tariffs.json`, `benchmark/runs/e2_smoke.py:65-80`
- Test: `benchmark/tests/test_hosted.py`

**Interfaces:** Produces `PPLX_WEIGHTS_BY_MODEL: dict[str, tuple[str, str]]` and
`PerplexityDecisionsClient(api_key, system=..., model=...)`. The identity's ref and revision come from that dict, and
the default stays `pplx-decider-v1-27b`, so v1's config hash does not move.

- [ ] **Step 1: Failing tests**

```python
def test_perplexity_v12_records_its_own_weights():
    c = hosted.PerplexityDecisionsClient("k", system="pplx-decider-v1-2-27b", model="<id from Task 1>")
    assert c.identity["ref"] == "perplexity-ai/pplx-decider-v1.2"
    assert c.identity["revision"] == "225c913ddc8761a8264f04f64548e1f97e443eb3"

def test_perplexity_v1_identity_is_unchanged():
    c = hosted.PerplexityDecisionsClient("k")
    assert (c.identity["ref"], c.identity["revision"]) == hosted.PPLX_WEIGHTS
```

- [ ] **Step 2:** `uv run --with scikit-learn python -m pytest -q benchmark/tests/test_hosted.py`. Expected: the new
  tests fail.
- [ ] **Step 3:** Add the dict. Add a tariff entry with the price read from Perplexity's pricing page and
  `checked_on`. Add `LIMITS` and `WHOLE_REQUEST_USAGE` entries for `pplx-decider-v1-2-27b`.
- [ ] **Step 4:** Run the full suite (`make test`). Expected: PASS.
- [ ] **Step 5:** Commit: `Bench: Perplexity client pins v1.2 weights by model`.

### Task 2b: Microsoft-Decision-1 client (done 20 October 2026)

**Files:** `benchmark/goldrails_bench/hosted.py` (`MicrosoftDecisionClient`), `benchmark/goldrails_bench/tariffs.json`
(`openrouter/decisions/microsoft-decision-1`, USD 0.042 per million input tokens, output free),
`benchmark/runs/e2_smoke.py` (kind `microsoft`, limit 32,768, whole-request usage), `.env.example`
(`OPENROUTER_API_KEY`), tests in `benchmark/tests/test_hosted.py`.

- [x] One canned call (synthetic state, no dataset row, USD 0.0000028) confirmed the System One response shape:
  `{"model": "microsoft/microsoft-decision-1-20261009", "answers": {qid: {"type": "noul", "noul": p}}, "usage":
  {"input_tokens", "output_tokens", "cost"}, "id", "provider": "Azure"}`.
- [x] Client sends the System One body, pins the snapshot, keeps 429 Retry-After on a shared 5/s throttle, records
  the upstream provider and drops generation ids. Tests pass with no network.
- [ ] Smoke: `uv run python benchmark/runs/e2_smoke.py run --systems microsoft` (dev rows, paid, ask first).

### Task 3: Serve the new kinds on the VM

**Files:**
- Create: `infra/gcp/pplx_server.py` (standard library HTTP, shaped like `laya_server.py`)
- Modify: `infra/gcp/variables.tf` (kind allowlist `d3`, `onejev`, `pplx`; new vars `onejev_repo_sha`; set
  `kev_repo_sha` per roster)
- Modify: `infra/gcp/startup.sh` (kind allowlist at :194, an install block and a `goldrails-run-<kind>` per kind)
- Modify: `benchmark/goldrails_bench/endpoints.py` (`KIND_MAX_LENGTH` for `pplx`, `d3`, `onejev`; `code_sha` for
  `onejev`)
- Create: `infra/gcp/terraform.tfvars.index-models-pass1.example`, `...-pass2.example` and, if self-hosted,
  `...-pass3.example`
- Test: `benchmark/tests/test_pplx_server.py`, `benchmark/tests/test_hosted.py` (identity)

**Interfaces:** Produces `pplx_server.py --ref <repo> --revision <sha> --port <n> --device cuda:0
--max-length 32768 --name <served name>`. It answers `POST /v1/systemone` with
`{"model": <name>, "answers": {qid: {"noul": p}}, "usage": {"input_tokens": n}}` and `GET /health`.

Ports: 8020 pplx flash, 8021 d3-mini, 8022 d3-flash, 8023 onejev, 8024 kev-27b, 8025 pplx v1.2.

- [ ] **Step 1: Failing tests.** `test_pplx_server.py` loads the module with a stub `Decider`:

```python
def test_translates_noul_questions_and_reports_its_own_name(stub_server):
    body = {"model": "x", "state": "s", "questions": {"harmful": {"type": "noul", "instructions": "Harmful?"}}}
    out = stub_server.post(body)
    assert out["answers"]["harmful"]["noul"] == 0.73 and out["model"] == "pplx-decider-flash-v1-2"

def test_length_error_is_a_413_not_an_answer(stub_server_raising_length_error):
    assert stub_server_raising_length_error.post_status(BODY) == 413
```

  Add `test_identity_records_kind_max_length_for_new_kinds` beside the existing strands test (`test_hosted.py:341`).
- [ ] **Step 2:** Run them. Expected: FAIL (no module, no kinds).
- [ ] **Step 3:** Implement the server, the kinds, the identity entries and the roster examples. Pass 1 uses
  `g2-standard-48` with `gpu` 0, 0, 1, 2. Pass 2 uses `a2-ultragpu-1g` with `kev-27b` on gpu 0.
- [ ] **Step 4:** `make test`, then `terraform -chdir=infra/gcp validate` and `bash -n infra/gcp/startup.sh`.
  Expected: all pass.
- [ ] **Step 5:** Commit: `Infra: serve d3, OneJev and Perplexity Decider checkpoints`.

### Task 4: The run module

**Files:**
- Create: `benchmark/runs/e2_index_run.py`, copied in shape from `e2_strands_run.py`. Keep its subcommands: `plan`,
  `smoke`, `freeze`, `vm-pass --pass N`, `roster --pass N`, `hosted` (Microsoft-Decision-1 on public test rows, plus pplx v1.2 if hosted), `report`, `score`.
- Modify: `benchmark/runs/e2_smoke.py` (`NEW_KINDS` gets `index`; `LIMITS` entries for the six;
  `build_new_systems` builds VM models of kind d3/onejev/pplx, plus kev-27b)
- Test: `benchmark/tests/test_index_run.py`

**Interfaces:** Consumes `smoke.run_selection`, `full.TestRows.guard`, `freeze.write_manifest` and
`ar._select_all_tasks`. Produces `SYSTEMS: dict[name, (ref, revision, port, pass, display, code_sha | None)]`,
`TEMPLATE = "kev-9b"`, `MANIFEST`, `_cfg(name, qs) -> str`, `extension_arms(tr) -> list`, `served() -> list[dict]`
(the VM's models of the new kinds plus kev-27b, from `endpoints.resolve_models`), `build(names) -> (dict, dict)` (it
calls `served()`), and `PROXY_LIMIT_OK: set[str]` (systems whose card gives no limit, so they run on the labelled
4,096 proxy).

- [ ] **Step 1: Failing tests**

```python
def test_extension_copies_kev_9bs_arms_per_system():
    r = _load("e2_index_run")
    arms = r._template_arms()
    assert {a["system"] for a in arms} == {"kev-9b"} and len({a["question_set"] for a in arms}) == 8

def test_build_refuses_a_vm_serving_another_commit(monkeypatch):
    r = _load("e2_index_run")
    monkeypatch.setattr(r, "served", lambda: [{"name": "d3-mini", "identity": {"ref": "vllm-sr/d3-mini",
                        "revision": "0" * 40, "kind": "d3"}, "url": "http://x", "model": "d3-mini"}])
    with pytest.raises(SystemExit, match="not vllm-sr/d3-mini@97dd054"):
        r.build({"d3-mini"})

def test_limits_cover_every_system():
    s, r = _load("e2_smoke"), _load("e2_index_run")
    assert all(s.limit_of(n)[1] != s.DEFAULT_LIMIT[1] or n in r.PROXY_LIMIT_OK for n in r.SYSTEMS)
```

- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement. `DISCLOSURES` starts with the hardware split, the joint-request note, the flash card's
  "private" text and Task 1's outcome. `NOT_RUN` starts empty.
- [ ] **Step 4:** `make test`. Expected: PASS.
- [ ] **Step 5:** Commit: `Bench: extension run for six Decision Index models`.

### Task 5: Smoke, freeze, run, score (paid, gated)

- [ ] **Step 1:** `uv run python benchmark/runs/e2_index_run.py plan --source local`. Show the owner the rows per
  subtask and the forecast: pass 1 is about 4 L4 hours on g2-standard-48, pass 2 about 3 A100 hours, plus the hosted
  tokens if hosted. Wait for a yes and a spend cap.
- [ ] **Step 2:** Bring up pass 1 (`roster --pass 1`, `terraform apply`), then run `smoke --source local`. Check: the
  determinism reruns agree, there are no failed rows from shape errors, and the identity matches every pin.
- [ ] **Step 3:** Run `freeze --source local`, then commit `freeze-manifest-index-models.json` alone.
- [ ] **Step 4:** Run `vm-pass --pass 1`, then `roster --pass 2` and `vm-pass --pass 2` (and pass 3 if self-hosted),
  then `hosted` (Microsoft-Decision-1 always; pplx v1.2 if hosted). Pause the VM after each pass.
- [ ] **Step 5:** Run `report --source local`. Expected: the privacy checks pass and no committed file holds an
  unpublished id.
- [ ] **Step 6:** Run `uv run --with scikit-learn python benchmark/runs/e2_index_run.py score --source local`, then
  check the new rows in `benchmark/results/final/` and on the site leaderboard (`cd site && pnpm dev`).
- [ ] **Step 7:** Commit the ledgers, run log and results: `Results: six Decision Index models and Microsoft-Decision-1 on edition 2`.
