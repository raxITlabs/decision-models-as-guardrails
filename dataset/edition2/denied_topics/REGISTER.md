# Registration needed (for the integration agent)

The denied-topics agent did not edit shared files. These changes wire edition 2 denied topics in.

## 1. `dataset/goldrails_dataset/sources/__init__.py`

```python
from . import e2_denied_topics, e2_denied_topics_oasst
SOURCES["e2_denied_topics"] = e2_denied_topics          # authored, offline; load() -> list[Record]
SOURCES["e2_oasst2"] = _E2Oasst                          # see below
```

`e2_denied_topics_oasst.load()` returns `{message_id: {text, message_tree_id, upstream_split}}`, not Records. Records come from `e2_denied_topics.load_oasst()`. If the registry needs a module with `load() -> list[Record]`, register a small shim:

```python
class _E2Oasst:
    NAME, LICENCE = e2_denied_topics_oasst.NAME, e2_denied_topics_oasst.LICENCE
    @staticmethod
    def load(limit=None, **_):
        rs = e2_denied_topics.load_oasst()
        return rs[:limit] if limit else rs
```

Alternatively, the edition 2 build can read `dataset/edition2/denied_topics/candidates.jsonl` directly: `Record.from_dict(row["record"])` gives each row's record.

## 2. `dataset/goldrails_dataset/build.py` (edition 2 plan only, not `PILOT_PLAN`)

- Cell: `("F3", "topic"): ["e2_denied_topics", "e2_oasst2"]`.
- Add both names to `AUTHORED` / `REVIEW_GATED`. Every label is a first-labeller candidate and must not score until the second labeller and the owner confirm it.
- Keep the proposed splits instead of the 15% re-split: `attribute["proposed_split"]` (test, dev or private), `split` and `visibility` (private = test + heldout) are already set per group. A group never straddles splits.
- Score these rows only against the topic set `dataset/edition2/denied_topics/topics-e2.json` (`attribute["topic_set"] == "e2"`). They are wrong against v1 `topics.json`, which lacks five of the eight topics.

## 3. `dataset/release/redistribution.json`

```json
"e2_denied_topics": {"mode": "text", "basis": "authored by raxIT (AI-assisted drafting), CC-BY-4.0", "reviewed": true},
"e2_oasst2": {"mode": "text", "basis": "Apache-2.0", "reviewed": true,
              "evidence": "HF tags license:apache-2.0 at 179dd21, not gated",
              "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision",
              "attribution": "named in the dataset card"}
```

## 4. Topic set and question set

- Copy `topics-e2.json` to `benchmark/suites/denied_topics/` (for example as `topics-e2.json`) once the owner approves TaxAdvice and the four v2 topics.
- The Noul question set needs one question per topic plus `any_denied_topic`, with definitions verbatim. The Bedrock topics guardrail needs a new version with all eight topics. All eight fit the Classic limits (checked in `dataset/tests/test_e2_denied_topics.py`).

## 5. Review flow

- Send only `review-packet/` (packet.md, labels.template.jsonl) to the blind second labeller.
- `_lead/e2-denied-topics.key.json` maps `e2t-rNNNN` to record ids and proposed labels, and lists `second_look` ids (the ambiguous rows). Keep it away from the reviewer, and keep `candidates.jsonl` away too.
- Final labels go to `dataset/frozen/reviews.jsonl` in the existing format (`id`, `label`, `final`).

## 6. Integrity

The overlap check in `e2_denied_topics.overlap()` covers ids and normalised text against v1 loaders, samples, frozen, subsets and result-ledger ids. The integrity agent's freeze check should also include `candidates.jsonl`.
