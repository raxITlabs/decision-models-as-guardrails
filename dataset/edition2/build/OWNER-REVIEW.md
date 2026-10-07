# Disputed rows left for the owner (edition 2)

> Public copy, written by the build (`goldrails_dataset.e2_owner_review.write_summary`). It names public rows only.
> Private-slice rows count in the totals and are never named. Notes describe rows without quoting them. To decide
> rows, open `build/private/review.html` (git-ignored, holds the text) and import its export with
> `uv run python -m goldrails_dataset.edition2 import-owner-review FILE`.

Rulings are in `docs/benchmark/29-owner-rulings-2026-10-03.md`. Ruling 9 says to apply rulings 2 to 5 to disputed rows
automatically and leave the rest to you. A row was resolved only when one of those rulings decides it. Ruling 2 decides
injection and where persona prompts are filed. Ruling 3 decides Mosscap turns judged on their text. Ruling 4 decides
grounding rows that turn on a hedged claim, an omission or a concrete fact the source does not state. Ruling 5 decides
ADDRESS. Everything else is below, grouped by the question that would settle it, so one answer can settle a group.

The first pass also resolved 14 content rows under ruling 8. Ruling 9 does not name ruling 8, so those rows are back
out of the splits under question C-R8 with the proposed label attached. Confirming it keeps the proposal.

Ruling 5 also binds rows nobody disputed. A PII row whose every ADDRESS span is a bare city or state field loses ADDRESS,
and a row with nothing else left becomes benign. Those changes are in `pii/corrections.jsonl` (private-slice ids in the
git-ignored part).

In all, 0 disputed rows wait: 0 public and 0 private. Ruling 5 changed 128 undisputed PII rows (101 public, 27 private); 118 of them became benign.

## Counts, public rows

| Suite | Disputed | Ruling 2 | Ruling 3 | Ruling 4 | Ruling 5 | Owner decided | Waiting | Dropped by the build |
|---|---|---|---|---|---|---|---|---|
| content | 23 | 0 | 0 | 0 | 0 | 23 | 0 | 0 |
| denied_topics | 4 | 0 | 0 | 0 | 0 | 4 | 0 | 0 |
| grounding | 28 | 0 | 0 | 10 | 0 | 18 | 0 | 0 |
| pii | 19 | 0 | 0 | 0 | 11 | 8 | 0 | 0 |
| word_filters | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 |
| all | 83 | 0 | 0 | 10 | 11 | 62 | 0 | 0 |

## Questions
