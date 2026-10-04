# Registration for the integration agent

The PII agent did not edit the shared registry. These are the changes it needs. None of them touches v1 artifacts.

## 1. `dataset/goldrails_dataset/sources/__init__.py`

```python
from . import e2_pii_nemotron, e2_pii_gretel, e2_pii_gretel_finance, e2_pii_controls

SOURCES.update({
    "e2_pii_nemotron": e2_pii_nemotron,          # provenance.source stays "nemotron_pii" (v1 id namespace)
    "e2_pii_gretel": e2_pii_gretel,              # provenance.source "gretel_pii_en"
    "e2_pii_gretel_finance": e2_pii_gretel_finance,  # provenance.source "gretel_pii_finance"
    "e2_pii_controls": e2_pii_controls,
})
```

Registry keys and `provenance.source` differ for the Nemotron loader. `e2_pii_nemotron` keeps `nemotron_pii` as its
source and id namespace, so v1 and edition 2 rows share one id space and the overlap check matches them by id. For
the three Gretel and authored loaders, the module's `NAME` is the registry key; the Gretel module `NAME`s are the
provenance source names (`gretel_pii_en`, `gretel_pii_finance`). Register them under whichever key the edition 2 plan
uses; `load()` filters `candidates.jsonl` by `SOURCE`, not by the key.

Every `load()` is offline. It reads `dataset/edition2/pii/candidates.jsonl` and returns validated `Record`s:
feature F5, subtask `pii`. `proposed_split` private becomes split test with visibility heldout.

## 2. Edition 2 build plan (wherever `build.py` keeps the edition 2 plan)

```python
("F5", "pii"): ["e2_pii_nemotron", "e2_pii_gretel", "e2_pii_gretel_finance", "e2_pii_controls"],
```

Splits are already fixed per row (`proposed_split`, by group hash). The build must keep them and must not
re-stratify or re-split these rows. Positives come in at 300 test, 60 dev, 60 private, and negatives at the same.
No caps are needed.

## 3. Review gating

- Add `e2_pii_controls` to `AUTHORED` / `REVIEW_GATED` in `build.py` and to `AUTHORED_SOURCES` in `audit.py`.
- Source negatives (`label` no, `review_status` candidate) are scored only after the blind second label agrees with
  "no" on every supported type. v1 used the same rule (`dataset/frozen/reviews/nemotron-negatives/`).
- Second-label packet: `dataset/edition2/pii/packet/` (`packet.md`, `labels.template.jsonl`, `_lead/key.json`).
  771 cases. Never send `_lead/` to the reviewer. Rows reviewed as containing an entity they do not list leave the
  pool. A row whose reviewer finds one of its listed types missing is relabelled or dropped. Neither case changes
  anyone's split.
- The owner reviews authored labels (plan: AI review, then owner).

## 4. `dataset/release/redistribution.json`

```json
"nemotron_pii": {"mode": "text", "basis": "CC-BY-4.0, attribution and citation in SOURCES.md", "reviewed": true,
                 "evidence": "card at b70ffaf5ff39e079776134c5bf4381f00a9fd1ed; v1.3 rights.json"},
"gretel_pii_en": {"mode": "text", "basis": "Apache-2.0, attribution in the card", "reviewed": true,
                  "evidence": "HF cardData.license apache-2.0 at e06eb1499ca8d54470f085021cd8e54f9efac7fd, not gated",
                  "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision",
                  "attribution": "named in the dataset card"},
"gretel_pii_finance": {"mode": "text", "basis": "Apache-2.0, attribution in the card", "reviewed": true,
                       "evidence": "HF cardData.license apache-2.0 at 7b844d16738527a04264f50214cb426a4cea0897, not gated",
                       "reviewed_by": "Claude, 2026-10-02: declared licence checked at the pinned revision",
                       "attribution": "named in the dataset card"},
"e2_pii_controls": {"mode": "text", "basis": "authored by raxIT, CC-BY-4.0", "reviewed": true}
```

`nemotron_pii` has no entry today, so it falls back to `ids_only`. v1.3 counts.md shows that, while v1.3
`rights.json` clears its text. The integration agent should decide whether to add the entry.

## 5. Entity floor and DRIVER_ID

`audit.ENTITY_TEST_FLOOR = 30` stays. Every supported type has at least 59 test positives. DRIVER_ID has 29 sourced
and 30 authored. Proposed rule for contract v2.0: score DRIVER_ID only if at least 30 test positives survive second
review, counting authored rows, and publish the authored share beside it. If the owner wants sourced-only rows,
DRIVER_ID drops from the score and is reported as a diagnostic. In both cases, row-level labels stay the same,
because every DRIVER_ID row also holds another supported type.

## 6. Overlap and examined lists

- `goldrails_bench.overlap` can take these rows as test rows and the v1 ledgers and releases as references. The
  generator already ran the same id, text and group check (`e2_pii.reference_index`) and found nothing.
- Second-label reading counts as annotation, so per `build.cleared_ids` it does not put rows on the examined list.
  Any smoke run on these rows does put them on the list.

## 7. Tests

`dataset/tests/test_e2_pii.py`: 22 offline tests. Run `uv run pytest tests/test_e2_pii.py` from `dataset/`.
