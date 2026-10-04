# Registration for the integration agent (edition 2 content)

Content-agent files: `dataset/goldrails_dataset/sources/e2_content*.py`, `dataset/edition2/content/`,
`dataset/tests/test_e2_content.py`. I did not edit the shared registry. Please apply the changes below.

## 1. `.gitignore` (before committing)

```
dataset/edition2/content/private/
```

The repository is public. `private/` holds the 397 private-slice rows and their blind packet.

## 2. `dataset/goldrails_dataset/sources/__init__.py`

```python
from . import e2_content_aegis2_val, e2_content_harmbench, e2_content_harmbench_cls, e2_content_orbench80k, e2_content_xstest

SOURCES.update({
    "e2_content_aegis2_val": e2_content_aegis2_val, "e2_content_harmbench": e2_content_harmbench,
    "e2_content_harmbench_cls": e2_content_harmbench_cls, "e2_content_xstest": e2_content_xstest,
    "e2_content_orbench80k": e2_content_orbench80k,
})
```

`e2_content.py` is the builder and tagger. It is not a source, so it stays out of `SOURCES`.

## 3. `dataset/goldrails_dataset/build.py`

Edition 2 content does not go through `PILOT_PLAN`. `candidates.jsonl` is already selected and split. If a v2
build plan is wanted:

```python
E2_CONTENT_PLAN = {
    ("F1", "input"): ["aegis2", "openai_moderation", "ailuminate_demo"],
    ("F1", "output"): ["e2_content_aegis2_val", "e2_content_harmbench_cls"],
    ("F1", "harmful_goal"): ["e2_content_harmbench", "e2_content_xstest", "e2_content_orbench80k"],
    ("F1", "over_refusal"): ["orbench", "e2_content_orbench80k"],
}
```

`group_of` must keep the loader's group for `e2_content_aegis2_val`. It already does, because only source
`aegis2` is rewritten, and the new loader sets `aegis2:<conversation>` itself. `e2_content.merge_groups` merges
groups across sources. Run it, or read `group` from `candidates.jsonl`, rather than recomputing groups.

## 4. `dataset/goldrails_dataset/taxonomy.py`

No change is required. The edition 2 harm tags live in `e2_content.py` (`TAG_VERSION = "e2-content-tags-v1"`). If
the owner adopts them as the v2 taxonomy:
- Add to `AEGIS2`: `"Malware": "nonviolent_crimes"`, `"Immoral/Unethical": None`, `"High Risk Gov Decision Making": None`. They are missing today, so those rows get no category.
- Consider remapping `defamation` and `intellectual_property` away from INSULTS and MISCONDUCT (see SOURCES.md).

## 5. `dataset/release/redistribution.json`

Add `mode: "text"` entries:

| Source | Basis | Evidence |
|---|---|---|
| e2_content_aegis2_val | CC-BY-4.0 | same HF repo and revision as aegis2 (d86bb8b), not gated |
| e2_content_orbench80k | CC-BY-4.0 | same HF repo and revision as orbench (e36d8b8), not gated |
| e2_content_harmbench, e2_content_harmbench_cls | MIT | GitHub licence MIT, centerforaisafety/HarmBench at 8e1604d |
| e2_content_xstest | CC-BY-4.0 | GitHub licence CC-BY-4.0, paul-rottger/xstest at d7bb5bd |

## 6. Hand-offs

- Denied-topics agent: `counts.json` → `topic_handoff_ids` (124 specialised-advice positives), plus the 4 v1 rows marked `move_to_denied_topics:*` in `v1-outside-five.jsonl`. The v1 rows are evidence for topic definitions only, since they are already v1 test rows.
- Scoring agent: `v1-content-tags.jsonl` (`in_bedrock_five`, `vendor_owned`) for the "with and without Bedrock's coverage gap" and "without vendor-owned data" views.
- Integrity agent: `e2_content.load_reference` and `overlap_reason` follow the same id, text and group rules as `goldrails_bench/overlap.py`, and add a near-duplicate check. Run `overlap.py` on `candidates.jsonl` as well when you freeze.

## Rebuild

```
uv run python -m goldrails_dataset.sources.e2_content \
  --v1-build <main>/dataset/release/v1.0/build --v1-build <main>/dataset/release/v1.1-ai/build \
  --v1-build <main>/dataset/release/v1.2/build --v1-build <main>/dataset/release/v1.3/build
```

The release builds are git-ignored. The command refuses to run without at least one build. The output is
deterministic except `provenance.imported_at`.
