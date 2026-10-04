# Edition 2 sensitive-information rows: sources

Built on 2 October 2026 by `uv run python -m goldrails_dataset.sources.e2_pii` (network or Hugging Face cache).
`uv run python -m goldrails_dataset.sources.e2_pii --check` rechecks the committed file offline. Rebuilding gives
the same `candidates.jsonl` byte for byte; its sha256 is in `counts.json`.

Spec: `docs/benchmark/26-edition-2-plan.md` and `benchmark/policies/sensitive_info/entity_detection.md`.

## Files

| File | What it holds |
|---|---|
| `candidates.jsonl` | 840 rows: id, suite, subtask, state, label, entity_types, spans, source, source_id, licence, revision, upstream_split, group, proposed_split, label_basis, review_status, label_rationale, second_label, notes |
| `counts.json` | Counts by split, class, source and entity type; the eligible pool and every drop reason per source |
| `lexicon.json` | First names and city/state names the sources label, used to drop rows that mention one without listing NAME or ADDRESS |
| `packet/` | Blind packet for the second labeller, in the `audit.py` packet format. `_lead/key.json` maps review ids to row ids; keep it away from reviewers |
| `REGISTER.md` | What the integration agent adds to the shared registry |

## Sources

All four allow redistribution with attribution. Every upstream split read is a test split. No train split is used.

### nemotron_pii (loader `e2_pii_nemotron`)

- NVIDIA Nemotron-PII, https://huggingface.co/datasets/nvidia/Nemotron-PII
- Pinned revision `b70ffaf5ff39e079776134c5bf4381f00a9fd1ed`, file `data/test-00000-of-00001.parquet`, split test
- Licence CC-BY-4.0. Already cleared for text in `dataset/release/v1.3/rights.json`. Citation as in
  `dataset/publish/v1.3-full/SOURCES.md`.
- Same source name, id scheme and groups as v1, so a v1 row cannot come back under a new id. Any group holding a
  document v1 used (any split), reviewed, or read in the source audit is left out: 1,616 rows.

### gretel_pii_en (loader `e2_pii_gretel`)

- Gretel, "gretel-pii-masking-en-v1", https://huggingface.co/datasets/gretelai/gretel-pii-masking-en-v1
- Pinned revision `e06eb1499ca8d54470f085021cd8e54f9efac7fd`, file `data/test-00000-of-00001.parquet`, split test
  (5,000 rows)
- Licence Apache-2.0 (card metadata `license: apache-2.0` at that revision, not gated). Keep the attribution and
  state that rows were selected and re-labelled to our entity types.
- Short single-paragraph texts. Values come without offsets; the loader finds each value in the text.

### gretel_pii_finance (loader `e2_pii_gretel_finance`)

- Gretel, "synthetic_pii_finance_multilingual", https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual
- Pinned revision `7b844d16738527a04264f50214cb426a4cea0897`, file `data/test-00000-of-00001.parquet`, English rows
  of the test split
- Licence Apache-2.0 (card metadata at that revision, not gated). Same attribution note.
- Read only for driver's licence numbers. Its labels are the noisiest of the three. In a sample,
  `driver_license_number` sat on a policy number and on a wallet address. 22 of the 67 English test rows with that label fail the
  driver's-licence context rule.

### e2_pii_controls (loader `e2_pii_controls`)

- Authored by Claude on 2 October 2026 as first labeller. CC-BY-4.0, like `f5_controls`.
- 72 hard negatives, 8 per supported type. Each one names the type's concept without a value, uses a masking
  placeholder or a masked value, or puts another kind of number where the type usually sits.
- 36 driver's-licence positives with invented values in US, UK and Canadian formats. Every one also names a person.
- `label_basis` llm, `review_status` candidate. None is scored until the blind second labeller and the owner have
  reviewed it.

## How rows are labelled

A row's `entity_types` is the set of supported types its source spans map to. `label` is yes when that set is not
empty. The mapping follows v1 (`nemotron_pii.TO_AWS`): fax counts as PHONE, `ssn` counts only on US rows and only in
the NNN-NN-NNNN shape. Edition 2 adds the following:

- **DRIVER_ID.** A licence-number span counts only when a driver's-licence label sits right before it, with no
  more than a short field label between (`driver_context_ok`). A row whose only supported type is DRIVER_ID is left
  out, so a row keeps its yes label if DRIVER_ID leaves the score.
- **Ambiguous types out.** These rows are left out: a PIN (a passcode?), a county with no other address part, an
  unverified certificate or licence number (one Nemotron "certificate license number" in a vehicle-safety text was
  a Texas driver's licence), a password next to "hash", "token" or "example", a username next to "SSID", and a
  Gretel negative with a company name (its generator builds those from surnames).
- **Completeness screen.** Every row is checked for each type it does not list. Scoring is per entity type, so a
  positive row counts as a negative for every type it leaves out. A row is dropped if it shows an email, IPv4 or
  IPv6 address, SSN-shaped number, phone-shaped number, password or username key with a value, @handle,
  driver's-licence mention, street, state-and-ZIP pair, name field or title before a capitalised word, or a first
  name or place from `lexicon.json`. Negatives must also be at least 60 characters long. The screens are
  deliberately strict. They drop many clean rows, which the pools can afford (10,503 Nemotron negatives remain
  eligible).

These screens came from reading samples. The first pass let through Gretel negatives naming "John Doe" and
"Capt. Johnson", and a "Driver ID: S-489142-V" field. Those patterns now fail the screen.

## Splits, groups and overlap

- Groups: Nemotron uses v1's groups. Gretel groups join rows that share an email, phone, SSN, username, password,
  IP, street address or licence number. Joining on first names or cities would chain most of a source into one
  group.
- One row per group. A group's split is a fixed hash: 70% test, 15% dev, 15% private. `private` means record split
  test with visibility heldout.
- No row repeats an id, normalised text or group from v1. The reference set covers every row id in a text file
  under `benchmark/` and `dataset/` (ledgers, subsets, manifests, examined list, reviews, samples), plus the published
  v1 releases in the local Hugging Face cache: 9,346 ids, 9,164 texts, 5,891 groups. The tests repeat the id and
  group check offline, using repo files only.

## Selection

For each split, the selector handles the rarest type first and alternates between sources until the type reaches
60 test, 12 dev and 12 private positives. It then fills positives to 300/60/60 and negatives to 300/60/60,
alternating sources again. All authored rows are kept.

## Counts

| Split | yes | no |
|---|---|---|
| test | 300 | 300 |
| dev | 60 | 60 |
| private | 60 | 60 |

| Source | test yes | test no | dev yes | dev no | private yes | private no |
|---|---|---|---|---|---|---|
| nemotron_pii | 143 | 126 | 31 | 24 | 27 | 23 |
| gretel_pii_en | 106 | 127 | 21 | 24 | 25 | 24 |
| gretel_pii_finance | 21 | 0 | 5 | 0 | 5 | 0 |
| e2_pii_controls | 30 | 47 | 3 | 12 | 3 | 13 |

Positives per entity type (v1 test positives in brackets):

| Type | test | dev | private | test by source |
|---|---|---|---|---|
| NAME | 153 (134) | 32 | 29 | nemotron 69, gretel_en 33, finance 21, authored 30 |
| EMAIL | 91 (111) | 15 | 20 | nemotron 66, gretel_en 22, finance 2, authored 1 |
| PHONE | 60 (53) | 12 | 12 | nemotron 39, gretel_en 20, finance 1 |
| ADDRESS | 85 (60) | 22 | 24 | nemotron 44, gretel_en 22, finance 18, authored 1 |
| USERNAME | 60 (18) | 13 | 12 | nemotron 34, gretel_en 26 |
| PASSWORD | 60 (14) | 12 | 12 | nemotron 45, gretel_en 15 |
| IP_ADDRESS | 66 (12) | 12 | 14 | nemotron 25, gretel_en 38, finance 3 |
| US_SOCIAL_SECURITY_NUMBER | 64 (9) | 12 | 15 | nemotron 33, gretel_en 31 |
| DRIVER_ID | 59 (0) | 12 | 10 | finance 21, nemotron 8, authored 30 |

DRIVER_ID needs a decision. Sourced rows give 29 test positives, one short of the floor of 30. The other 30 test
positives are authored. Two options: score DRIVER_ID only if at least 30 test positives survive second review
counting authored rows, or drop it from the score and report it as a diagnostic. The suggested rule is the first,
with the authored share shown beside the score.

## Review state

- 384 positives carry source labels (`synthetic_reviewed` / `source_label`).
- 348 source negatives are `candidate` until the blind second label. v1 had the same rule: missing annotations
  are never proof that an entity is absent.
- 108 authored rows are `llm` / `candidate`.
- `second_label`: 753 rows need a full blind label. These are every negative, every authored row, and every row
  holding USERNAME, PASSWORD, IP_ADDRESS, SSN or DRIVER_ID. A fixed 20% of the other 87 source positives is
  spot-checked. The packet has 771 cases.
- As first labeller I read about 120 selected negatives and every rare-type value with its context. The screen
  changes above came out of that pass.
