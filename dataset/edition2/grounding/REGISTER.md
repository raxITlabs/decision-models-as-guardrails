# Edition 2 grounding: registration for the integration agent

The grounding agent did not touch the shared registry. These are the edits it needs.

## 1. `dataset/goldrails_dataset/sources/__init__.py`

```python
from . import e2_grounding_faithdial, e2_grounding_summedits, e2_grounding_ragbench

SOURCES.update({
    "faithdial": e2_grounding_faithdial,
    "summedits": e2_grounding_summedits,
    "ragbench": e2_grounding_ragbench,
})
```

`e2_grounding.py` is the candidate builder, not a source; do not register it.

## 2. `dataset/goldrails_dataset/build.py`

The edition 2 plan for F6 grounding:

```python
("F6", "grounding"): ["ragtruth", "faithdial", "summedits", "ragbench"],
```

Use `dataset/edition2/grounding/candidates.jsonl` as the row list for the three new sources rather than re-sampling
them with `--per-cell`. That file already applies the first-labeller drops, the balance per source, split and class, and
the group split. Re-sampling the raw loaders would bring back rows the first labeller rejected. Each line is a full
`Record` (load with `Record.from_dict`, which ignores the extra keys) plus `suite`, `label`, `source`, `licence`,
`proposed_split`, `label_rationale`, `first_labeller`, `upstream_split`.

Split mapping, already set in the records:

| proposed_split | Record.split | Record.visibility |
|---|---|---|
| test | test | public |
| tune | tune | public |
| private | test | heldout |

Keep `group` as written (it already merges rows that share a source text). `build.group_of` returns `r.group`, so no
change is needed there.

## 3. Review gating

- RAGBench rows have `label_basis: llm` and `review_status: candidate`. Score them only after the second labeller and
  the owner confirm the label. Add `"ragbench"` to `REVIEW_GATED` in `build.py`.
- FaithDial and SummEdits rows have `label_basis: human` and `review_status: null`; the build sets `source_label`. Given
  the FaithDial disagreement rate in `SOURCES.md` (46% of Hallucination-tagged replies were not clearly unsupported),
  I recommend gating `"faithdial"` the same way. SummEdits can stay ungated if the owner accepts the first-labeller
  diff check.

## 4. `dataset/release/redistribution.json`

Proposed entries, all `reviewed: false` until the owner checks them:

```json
"faithdial": {"mode": "text", "basis": "MIT; knowledge sentences are Wikipedia (CC-BY-SA)", "reviewed": false,
              "evidence": "HF cardData.license mit at 7a414e8, not gated"},
"summedits": {"mode": "text", "basis": "CC-BY-4.0; only BillSum, QMSum, SciTLDR, Shakespeare and SummEdits' synthetic sales domains are loaded", "reviewed": false,
              "evidence": "HF cardData.license cc-by-4.0 at ce0c479, not gated"},
"ragbench":  {"mode": "ids_only", "basis": "CC-BY-4.0 annotations; PubMedQA passages are publisher abstracts with unchecked terms", "reviewed": false,
              "evidence": "HF cardData.license cc-by-4.0 at 97808f3, not gated"}
```

RAGBench could be split per subset (HAGRID and HotpotQA text are Wikipedia) if the owner wants its text published.

## 5. Overlap check in the freeze

New ids are `f6-faithdial-*`, `f6-summedits-*`, `f6-ragbench-*`. None appears in the v1 builds, samples, ledgers or
`examined-ids.txt` (checked by `dataset/tests/test_e2_grounding.py` and at build time). The 780 rows have been read by
the first labeller only; they were never sent to a model under test. Do not add them to `examined-ids.txt` unless a
pilot run sends them to a model.

## 6. Tests

`dataset/tests/test_e2_grounding.py` (13 tests, offline). Full `uv run pytest dataset/tests` passes: 155 passed, 1 skipped.
