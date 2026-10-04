# Registration notes for the integration agent

The prompt-attacks agent did not touch the shared registry (`dataset/goldrails_dataset/__init__.py`,
`sources/__init__.py`, `build.py`, `taxonomy.py`) or `dataset/release/redistribution.json`. Here is what each needs.

## 1. `dataset/goldrails_dataset/sources/__init__.py`

Import the loaders and add them to `SOURCES`. `e2_prompt_attacks_lakera` loads two sources (Mosscap and Gandalf
summarization). Register it once under `lakera_mosscap`. Its rows carry their own `provenance.source`.

```python
from . import (e2_prompt_attacks_controls, e2_prompt_attacks_deepset_test, e2_prompt_attacks_itw,
               e2_prompt_attacks_jackhhao, e2_prompt_attacks_lakera, e2_prompt_attacks_neuralchemy,
               e2_prompt_attacks_notinject, e2_prompt_attacks_yanis)

SOURCES.update({
    "deepset_injections_test": e2_prompt_attacks_deepset_test,
    "jackhhao_jailbreak": e2_prompt_attacks_jackhhao,
    "itw_jailbreak_prompts": e2_prompt_attacks_itw,
    "lakera_mosscap": e2_prompt_attacks_lakera,          # also yields lakera_gandalf_summarization rows
    "neuralchemy_injection": e2_prompt_attacks_neuralchemy,
    "notinject": e2_prompt_attacks_notinject,
    "yanis_prompt_injections": e2_prompt_attacks_yanis,
    "e2_attack_controls": e2_prompt_attacks_controls,
})
```

`e2_prompt_attacks_common.py` and `e2_prompt_attacks_build.py` are helpers, not sources.

## 2. Use the candidate file, not a fresh stratified sample

Selection, near-duplicate grouping, v1 overlap removal, length matching and the split proposal live in
`sources/e2_prompt_attacks_build.py`. `build.py`'s stratified sampler would undo them. Take the rows as built:

```python
from goldrails_dataset.sources.e2_prompt_attacks_build import candidate_to_record
rows = [candidate_to_record(json.loads(l)) for l in open("dataset/edition2/prompt_attacks/candidates.jsonl")]
```

`candidate_to_record` returns validated `Record`s. `proposed_split` maps as follows: `dev` becomes split `dev`,
`test` becomes `test`, and `private` becomes split `test` with `visibility = "heldout"`, because `records.SPLITS` has
no private split. If contract v2.0 adds a `private` split, map it directly. `provenance.notes` keeps
`proposed_split`, `label_rationale`, `labeller`, `revision`, `upstream_split`, `train_split_flag` and `loader_group`.
The file is ASCII JSON, one object per line. Read it with `for line in fh`, not `str.splitlines()`.

To regenerate: `uv run python -m goldrails_dataset.sources.e2_prompt_attacks_build`. It needs network access to
Hugging Face and GitHub (for the v1 JBB artifact pool), and it reads the gitignored v1 release builds from this
checkout or the main checkout. The output is byte-identical across runs (`candidates_sha256` in `counts.json`).

## 3. `build.py` constants (if the shared build handles these rows)

- Add `"e2_attack_controls"` to `AUTHORED` and so to `REVIEW_GATED`. Its rows are `label_basis = "llm"` and must not
  score before review.
- Every other e2 source is a candidate as well (`review_status = "candidate"`, set by the loaders). The rows the first
  labeller screened by rule (Mosscap, in-the-wild, yanismiraoui, neuralchemy mapping) need the second label before
  they leave candidate status. Whether source-labelled rows with `label_basis = "unknown"` may become `source_label`
  without review is the owner's call. My recommendation is no, because I disputed rows in every source I read.
- `PILOT_PLAN` (only if the v1-style build is reused):
  `("F2","injection"): [..., "deepset_injections_test", "yanis_prompt_injections", "neuralchemy_injection", "notinject", "e2_attack_controls", "itw_jailbreak_prompts"]`,
  `("F2","jailbreak"): [..., "jackhhao_jailbreak", "itw_jailbreak_prompts", "neuralchemy_injection", "yanis_prompt_injections", "e2_attack_controls"]`,
  `("F2","leakage"): [..., "lakera_mosscap", "yanis_prompt_injections", "neuralchemy_injection", "e2_attack_controls", "itw_jailbreak_prompts"]`.
- `group_of` needs no change. Every row has a `group` (prefix `e2pa-`), and no group is shared with v1.

## 4. `dataset/release/redistribution.json` entries (reviewed by Claude, 2 Oct 2026, declared licence at the pinned revision)

```json
"deepset_injections_test": {"mode": "text", "basis": "Apache-2.0", "reviewed": true, "evidence": "same repo and revision as deepset_injections (4f61ecb); test split", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card"},
"jackhhao_jailbreak": {"mode": "text", "basis": "Apache-2.0", "reviewed": true, "evidence": "HF cardData.license apache-2.0 at 2f2ceeb, not gated", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card"},
"itw_jailbreak_prompts": {"mode": "text", "basis": "MIT", "reviewed": true, "evidence": "HF cardData.license mit at a10aab8, not gated", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card (Shen et al., CCS 2024)"},
"lakera_mosscap": {"mode": "text", "basis": "MIT", "reviewed": true, "evidence": "HF cardData.license mit at b7e495f, not gated", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card"},
"lakera_gandalf_summarization": {"mode": "text", "basis": "MIT", "reviewed": true, "evidence": "HF cardData.license mit at 8e213cc, not gated", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card"},
"neuralchemy_injection": {"mode": "text", "basis": "Apache-2.0 as declared; rows derive from HackAPrompt (MIT), WildGuardMix (ODC-BY), HarmBench (MIT)", "reviewed": true, "evidence": "HF cardData.license apache-2.0 at 7d70432, not gated; per-row upstream origin kept in notes", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision; upstream licences noted, owner to confirm the ODC-BY rows (36)", "attribution": "named in the dataset card, with HackAPrompt, WildGuardMix and HarmBench"},
"notinject": {"mode": "text", "basis": "MIT", "reviewed": true, "evidence": "HF cardData.license mit at 847ae76, not gated", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card (InjecGuard)"},
"yanis_prompt_injections": {"mode": "text", "basis": "Apache-2.0", "reviewed": true, "evidence": "LICENSE (Apache-2.0) and NOTICE files at bd55359, not gated", "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision", "attribution": "named in the dataset card; NOTICE to be carried"},
"e2_attack_controls": {"mode": "text", "basis": "authored by raxIT (Claude), CC-BY-4.0", "reviewed": true}
```

## 5. Integrity hand-off

- Add the candidate ids to the overlap check's reference sets the usual way. The dev and private rows must never be
  examined in a test run.
- The 18 tests in `dataset/tests/test_e2_prompt_attacks.py` re-check the committed file: ≥ 250 test rows per
  subtask and class, ≥ 2 sources each, unique ids and texts, no group straddling splits, no overlap with examined ids,
  samples, ledgers or available v1 builds, trivial baselines ≤ 0.80, and a blind packet.
- The blind packet for the second labeller is `packet/` (`00-policy.md`, `rows.jsonl`, `labels.template.jsonl`). It
  holds no labels, sources or rationales, and its row order is hashed. Do not give the reviewer `candidates.jsonl`,
  `SOURCES.md` or `label-disputes.jsonl` before they submit.
