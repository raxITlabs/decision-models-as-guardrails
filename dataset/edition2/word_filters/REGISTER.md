# Registration needed (for the integration agent)

The word-filters agent edited no shared file. These changes wire the suite into the edition 2 build.

## 1. `dataset/release/redistribution.json` (owner decision)

None of the four sources has an entry, so every tracked row has its text withheld. Proposed entries:

```json
"e2_word_filters_words": {"mode": "text", "basis": "authored by raxIT, CC-BY-4.0", "reviewed": true},
"e2_profanity_civil_comments": {"mode": "text", "basis": "CC0-1.0", "reviewed": true,
    "evidence": "HF tags license:cc0-1.0 at f2970eb3, not gated; v1 civil_comments_profanity is already cleared"},
"e2_profanity_rtp": {"mode": "text", "basis": "Apache-2.0", "reviewed": false,
    "evidence": "HF tags license:apache-2.0 at f2162971, not gated; the sentences come from OpenWebText pages"},
"e2_profanity_oasst2": {"mode": "text", "basis": "Apache-2.0", "reviewed": false,
    "evidence": "HF tags license:apache-2.0 at 179dd21f, not gated; same upstream as e2_oasst2"}
```

The custom-words entry matters first. Until it exists, the tracked module `e2_word_filters_words.py` holds text that
`candidates.jsonl` withholds, and a leak scan with this suite registered reports it as `withheld_text`
(`test_e2_word_filters.py` allows exactly that case and nothing else). After any change to the file, run
`uv run python -m goldrails_dataset.sources.e2_word_filters build`.

## 2. `dataset/goldrails_dataset/e2_local.py`

Add `"word_filters"` to `SUITES` and `"word_filters": ("relabel.jsonl",)` to `ROW_FILES`. Until then
`e2_word_filters.registered()` adds them for the duration of a call. `rehydrate` needs a fetch for the four sources:
`e2_word_filters.upstream_fields(source)` returns `{id: {"state": ...}}`, the shape `_upstream_fields` returns.

## 3. `dataset/goldrails_dataset/edition2.py`

- `SUITES`: `Suite("word_filters", "F4", lambda c: Record.from_dict(c))`. The candidate rows are Record dicts plus
  `label`, `proposed_split`, `source`, `bucket` and `label_rationale`, like the content rows.
- `SCORED`: `("F4", "profanity"): (TEST_FLOOR, TEST_FLOOR)`. Do not add `("F4", "word")`. Ruling 13 makes it a sanity
  check, and its 100 test rows are below the scored floor by design.
- Done on 4 October 2026. The `word` rows have two second labels: the regex baseline in `relabel.jsonl` (round 1) and
  the blind labeller in `relabel-round5.jsonl`. The build checks both, so a row disputed in either round leaves the
  splits. Every `profanity` row has its blind label in round 5. The 9 disputes (5 profanity, 4 word) wait in
  `resolutions.jsonl` under owner questions WF-Q1 and WF-Q2.
- `e2_local.SUITES` now lists `word_filters`, and the build writes `build/F4.*.jsonl`, so its private rows are needles
  in `tracked_leaks()` like every other suite's.

## 4. `dataset/goldrails_dataset/sources/__init__.py`

```python
from . import e2_word_filters_words
E2_SOURCES["e2_word_filters_words"] = e2_word_filters_words     # load() -> list[Record], offline
```

The three profanity sources come from the frozen pool in `private/pool.jsonl`, not from a `load()`. The build reads
`candidates.jsonl`, as it does for the other suites.

## 5. Review flow

Send only `private/packet/packet.md` and `private/packet/labels.template.jsonl` to the blind second labeller. Keep
`private/packet/_lead/key.json` and `candidates.jsonl` away from them. Import the filled template with
`e2_word_filters.import_second_labels(path)` and write the rows to `relabel.jsonl` before the next `build`.

## 6. Question set

`benchmark/question_sets/e2/f4-obscenity.json` is the frozen v1.3 wording, the Civil Comments raters' own question
("swear words, curse words, or other obscene or profane language"). The edition 2 policy is narrower: sexual content
with no vulgar word is no. The agent left the set unchanged, because changing a frozen set needs the three-model check
the contract requires. The owner should decide whether that gap is worth a revision.
