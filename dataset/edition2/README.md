# Edition 2 candidate data: what is in git and what is not

The repository is public, so two kinds of data never go into git.

1. The unpublished slice. These test rows are held out of every public file: their ids, their text, their second
   labels and any note that names them. The slice is not secret. See "What the unpublished slice is" below.
2. Text from a source whose licence is not cleared in `dataset/release/redistribution.json`. A source is cleared only
   when its entry says `mode: text` and `reviewed: true`. A missing entry, `ids_only` or `reviewed: false` all mean
   the text stays local.

`dataset/goldrails_dataset/e2_local.py` does the split and puts the parts back together for all six suites (content,
prompt_attacks, denied_topics, word_filters, pii, grounding). Each suite folder has three
parts.

| Where | In git | What it holds |
|---|---|---|
| `<suite>/candidates.jsonl`, `relabel.jsonl`, `first_labels.jsonl` | yes | Public rows only (proposed split tune or test). A row from an uncleared source keeps its id, labels, spans and group. Its text fields are null, and `redacted` gives the reason and the sha256 of what was removed. Fields that quote the text, such as a rationale or upstream notes, are withheld too and listed in `redacted.also_withheld`. |
| `<suite>/private/` | no, owner only | The unpublished-slice rows and their second labels. Also the review packets, the `_lead` answer keys, the full `DISAGREEMENTS.md`, the prompt-attack `label-disputes.jsonl`, held-out authored cases (`authored.json`) and `order.txt`, which rebuilds the original file order. A public row whose text is also an unpublished row's text lives here as well. |
| `<suite>/local/text.jsonl` | no | The withheld text of the redacted public rows. |

The tracked `DISAGREEMENTS.md` files are public copies. They drop unpublished-slice rows and keep only the id, source
and labels of a redacted row.

Where a suite's `SOURCES.md` or `REGISTER.md` points at `packet/`, `review-packet/`, `_lead/` or
`label-disputes.jsonl`, the file now sits under that suite's `private/`. The content packet for tune and test rows is
in `content/private/review-packet-tune-test/`.

## What the unpublished slice is

Owner ruling 15 (4 October 2026) renamed it. Until then the docs called it the private slice. The code still does:
`private/` folders, `.private-salt`, `e2_local` functions and test names such as
`test_tracked_files_alone_do_not_give_the_private_slice` all mean the unpublished slice. We kept the old identifiers
so paths and ignore rules did not have to move.

Every row in the slice comes from public upstream data, so anyone can rebuild it (see "What this does not cover"
below). It is not a secret test set and must not be described as one. It serves contamination checks. If a system
scores much higher on the public test rows than on the unpublished ones, it may have seen the public rows. A truly
private slice, of rows that exist nowhere else, is planned for edition 3.

## Why the tracked code does not give the unpublished slice

Hiding the rows is not enough if the published code can rebuild the list. The first draw used published seeds, so
anyone with the builders and the upstream data could recompute it. Three things now stop that.

1. A salt. `dataset/edition2/.private-salt` holds 64 hex characters that only the owner has. Every split draw that can
   put a row in the unpublished slice, and every selection order that decides which rows a builder takes, is an HMAC
   under this salt (`e2_local.salted`). Without the file, those builders stop with `LocalDataMissing`.
2. Private config. A selection list or override entry that names an unpublished-slice row sits in
   `<suite>/private/selection.json`, keyed `<module>.<NAME>`. Today that means 15 OASST2 message ids and one ambiguity
   flag (denied topics), one ALSO_IN and four AMBIGUOUS entries for held-out authored cases (denied topics), and four
   HarmBench behaviour ids (content). The builder modules merge these entries back in when the file is present. The
   tracked lists hold public rows only.
3. Salted ids for held-out authored cases. A HeldOut placeholder keeps its list position, but its source id carries a
   salted token (`e2_local.held_out_sid`) in place of the position or pair number. The position no longer gives the id.

On 4 October 2026 the slice was drawn again under the salt (`e2_local redraw`). For each suite and each stratum
(subtask, label, source), the old unpublished rows went to the public test split. The same number of rows came from the
old test rows, in salted order, so the new slice shares no row with the old one. The unit of the draw is a build
cluster (shared group or near-duplicate body). Some rows stayed where they were: tune, authored sources, rows named in
a tracked file the build does not regenerate, disputed rows waiting for the owner, rows the build dropped, and clusters
that cross suites. Content was not drawn again, because a person is labelling its ruling 7 sample and any change to
F1 makes that sample stale. Each suite's `private/redraw.json` records its draw and the salt fingerprint.

`uv run python -m goldrails_dataset.e2_local derivable` checks all three from the tracked files alone, and so does
`test_tracked_files_alone_do_not_give_the_private_slice`.

What this does not cover. Someone who reruns a builder's selection against the public upstream data, with the old
seeded order, gets the full candidate set of that suite. Taking away the public rows leaves the unpublished slice. That
applies to content, PII and grounding, whose selection depends only on public inputs. The fix for that is fresh
rows that exist nowhere else, or decoy rows, and it needs new labels. Edition 3 plans the first. The last three local commits also hold the old code and the old
split, so they must not reach the public remote as they are.

### Backing up the salt

Keep a copy of `.private-salt` wherever the `private/` folders are kept, in a password manager or on offline storage.
Never commit it, paste it, or put it in an issue. `uv run python -m goldrails_dataset.e2_local salt` prints only a
fingerprint, and that is safe to share. If the salt is lost, the slice on record is still intact, because
`private/candidates.jsonl` holds it. But a builder can no longer draw the same rows, and the redraw record can no
longer be checked. `salt --init` writes a salt only when none exists and never overwrites one.

## Commands

    uv run python -m goldrails_dataset.e2_local status              # which parts this machine has
    uv run python -m goldrails_dataset.e2_local split               # after a builder rewrote a suite's files
    uv run python -m goldrails_dataset.e2_local rehydrate [suite]   # refill local/text.jsonl from upstream
    uv run python -m goldrails_dataset.e2_local salt [--init]       # salt fingerprint; --init writes one if none exists
    uv run python -m goldrails_dataset.e2_local derivable           # what the tracked files give away (counts only)
    uv run python -m goldrails_dataset.e2_local redraw [--apply] [suite]   # salted re-draw (report only by default)

The builders call `split` themselves when they write to this folder. `rehydrate` uses the pinned loaders and needs
the network or a Hugging Face cache. It keeps a row only when the fetched text matches the recorded sha256. Fields
our own pipeline wrote, such as a rationale that quotes the text, come back only from the local cache.

`uv run pytest dataset/tests/test_e2_local.py` scans every tracked file (`git ls-files`), not only the candidate files,
for the text of a held-out authored case and for the id or text of an unpublished-slice row. It skips where the owner-only
parts are missing.

`EXCLUDED.jsonl` at the edition root lists rows the owner took out of edition 2 entirely, by id and reason. Ids from
the unpublished slice go in the git-ignored `<suite>/private/EXCLUDED.jsonl`. The build, the second-label and resolution
readers and the prompt-attack pool builder all skip these ids.

The prompt-attack shortcut gate has two halves. In sample, each baseline runs grouped five-fold CV on the built test
split (and with the unpublished slice). Held back, it is fitted on rows it then does not score: seeded group halves of
test and unpublished, both ways; tune to test; tune to the unpublished slice; test and unpublished to tune; tune plus 70%
of the test and unpublished groups to the other 30%. A constant fit fails. Since 4 October the gate fails (49 of 120
cells, every one of them an n-gram model except source id on tune to the unpublished slice). Under owner ruling 17 the
build still passes, because `benchmark/contracts/v2.0.json` marks the prompt-attack suite provisional and records the
gate's numbers. If a rebuild moves those numbers by more than 0.01, the build fails until the contract is updated.

`<suite>/corrections.jsonl` holds a ruling applied to a row nobody disputed. So far that is ruling 5 on PII rows whose
only ADDRESS spans are a bare city or state (`uv run python -m goldrails_dataset.edition2 ruling5`). Unpublished-slice ids
go in the git-ignored part, as for `resolutions.jsonl`.

The edition 2 build (`uv run python -m goldrails_dataset.edition2`) and the tests read through `e2_local`. Without the
`private/` and `local/` parts, the build stops with `LocalDataMissing` and the data tests skip.

## Disclosures that touch this data

- Laya reads at most 512 tokens per question, its checkpoint's own limit, and edition 2 keeps it there (ruling 16).
  Longer rows are cut from the end of the state. Every Laya result carries `truncated`. The Noul adapter sets it to
  true when Laya's server reports a cut, or, from a server that sends no report, when `usage.input_tokens` reaches
  512 x the number of questions. The count of truncated rows is published with Laya's scores.
- Bedrock's ADDRESS entity counts a bare city or state. Our labels do not (ruling 5). When Bedrock flags only a city
  or state, the row scores as a false block for Bedrock.
- On 2 October 2026, 276 ids from smoke, pilot and diagnostic ledgers were appended to
  `dataset/frozen/examined-ids.txt`. 147 of them are v1 test rows, now flagged as examined. Rerunning the v1 dataset
  audit against the current list gives a different result from the published v1 audit. The v1 files are unchanged.
