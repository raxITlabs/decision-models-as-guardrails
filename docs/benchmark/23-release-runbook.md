# 23. Release runbook: from reviewed labels to the published benchmark

Status on 24 September 2026. This version is finished from the runs already collected: all six categories are
scored, with denied topics and profanity on single-AI reference labels and marked provisional. The page passes the
release check against the frozen results and corrections. What remains is the owner's: sign-off (section 5), the
Bias licence and publication (section 6). Sections 1 to 3 describe the human-reviewed path, which moves to the next
version.

## 1. Reviews (next version)

`dataset/frozen/review-packets/RELEASE-REVIEW.md` is the single reviewer brief: four packets, about 420 cases for
reviewer A and a sampled second review for reviewer B (about 770 and 340 judgments); full double review is one
command. `uv run python -m goldrails_dataset.reviews --status` lists exactly which cases still
need a label, a second reviewer or adjudication.

| Packet | Cases | Split after review |
|---|---|---|
| Denied-topics controls (`f3-denied-topics/`) | 28 | tuning |
| Denied-topics candidates (`f3-test-candidates/`) | 90 | about 76 test, 14 tuning |
| Profanity candidates (`f4-profanity/`) | 280 | 40 tuning, 160 test, masked spellings as a diagnostic |
| Counterfactual pairs (`bias/b2-v0/`) | 22 pairs | about 85% test |

The b2-v0 pairs can be test rows: their texts were read only to quality-check the generator, never run through a
model or used for questions or thresholds, and appear in no ledger. `dataset/frozen/examined-clearances.jsonl` records
that clearance with its evidence; `examined-ids.txt` is unchanged. No fresh pair packet is needed.

## 2. Build the reviewed dataset (local, no cost)

```bash
uv run python -m goldrails_dataset.reviews
uv run python -m goldrails_dataset.release --version v1.1
uv run python -m goldrails_bench.subset --release v1.1 --name first-benchmark-v1.1 --carry-over first-benchmark
```

The subset step stops if any core test row differs from the frozen first benchmark, so the existing results carry
over unchanged. Commit `dataset/frozen/reviews.jsonl`, the v1.1 manifest and the new subset manifest.

## 3. Run denied topics, profanity and B2 (about $2.50 to $3.50, one VM session)

```bash
make up
uv run python benchmark/runs/extension_run.py tune --systems open,jev,bedrock
uv run python benchmark/runs/extension_run.py freeze
git add benchmark/subsets/first-benchmark/freeze-extension-1.json benchmark/results/first-benchmark/ext-* && git commit -m "Freeze extension: denied topics, profanity and B2"
uv run python benchmark/runs/extension_run.py test --systems open,jev,bedrock
uv run python benchmark/runs/extension_run.py latency --systems open,jev,bedrock
make down
uv run python benchmark/runs/profanity_diagnostic.py
```

No infrastructure change is needed: the frozen word-filter guardrail already has the managed PROFANITY list, and the
profanity question reads only that list. The denied-topics guardrail is built from `topics.json`, the same file the
question set quotes; a test pins the definitions, examples and order.

The runner refuses the test stage until the extension manifest is committed. Record serving windows:

```bash
uv run python benchmark/runs/serving_from_ledger.py --out benchmark/results/first-benchmark/serving-final.json benchmark/results/first-benchmark/test.jsonl benchmark/results/first-benchmark/test-rerun.jsonl benchmark/results/first-benchmark/ext-test.jsonl benchmark/results/first-benchmark/ext-test-bias.jsonl
```

## 4. Provisional results (done 24 September 2026)

The owner chose single-AI reference labels for this version (contract v1.1 amendment A). Dataset v1.1-ai, both
extension manifests and the extension runs are committed; `leaderboard-provisional.json` holds the six-category
result. `benchmark/runs/check_page.py` checks the page against it, and `EVIDENCE.md` records the release check.
Human review and the interview-based diagnostics (`docs/research/jev-founder-2026-09-24/ASSESSMENT.md`) move to the
next version.

## 5. Owner sign-off (one step)

Signing the contract changes its hash, and every freeze manifest pinned the draft hash. `sign_off.py` writes the
signed contract and one approval per manifest, all carrying the owner's confirmation. The owner runs it with their
own name and words:

```bash
uv run python benchmark/runs/sign_off.py --by "Full Name" --statement "..."
uv run python benchmark/runs/sign_off.py --by "Full Name" --statement "..." --write
```

It prints the commit and the final build commands. The final leaderboard then has no publication blockers, and the
page switches from "not for publication" by itself. Confirming approval 4 alone is not enough, and signing the
contract by hand without the approvals leaves three blockers.

## 6. Publication (owner; outward-facing)

Gold Rails is a non-commercial research benchmark, published with credit to every upstream source. The dataset card
and the page say so. AI4Privacy's rows and annotations stay out of the public upload while its research and
redistribution terms are clarified; the request is drafted in `docs/requests/ai4privacy-permission-request.md` and
does not hold up the other sources. The PII result stays qualified; a fresh PII confirmation can follow once the
usage basis is settled.

Stage the upload with `uv run python -m goldrails_dataset.publish --version v1.1-ai` and review
`dataset/publish/v1.1-ai/` before approving it.

- Decide the Hugging Face licence for the Bias config (HolisticBias descriptors are CC-BY-SA-4.0; docs/21, open
  decision 6).
- Approve the Hugging Face upload of the staged dataset v1.1-ai: provisional, AI-labelled rows marked `ai_reviewed`, ids-only for the sources in `dataset/release/redistribution.json`, AI4Privacy withheld.
- Approve publishing the results page to raxitlabs.com.

The regex baseline's cost is not measured. It is disclosed, shown without a cost point, and does not block release.
