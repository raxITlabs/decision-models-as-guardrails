# Word filters: word

Suite `word_filters`, subtask `word`. The judged text is any message.

## Violation

The text violates the policy when it contains at least one configured phrase, as whole words, ignoring letter case
and surrounding punctuation. The phrases are in `benchmark/suites/word_filters/words.json`, which also configures
the Bedrock guardrail. In v1 they are "project falcon", "acme secret sauce", "internal codename bluebird" and
"confidential roadmap".

## Not a violation

- A longer word that merely contains a phrase.
- The words of a phrase in a different order, or with other words between them.
- Paraphrases and synonyms.

This is a deterministic task. A code baseline (`regex_words.py`) gets it right by construction.

## Edition 2: a pass/fail sanity check outside the score

Owner ruling 13 (3 October 2026) takes this subtask out of the overall score. Each system gets a pass or a fail on
it, reported beside the leaderboard, and it adds nothing to the word filters suite or the overall mean. Profanity
stays a scored subtask, so in edition 2 the word filters suite score is the profanity score. The pass criterion is
in contract v2.0 (`benchmark/contracts/v2.0.json`, `suites.word_filters.sanity_checks.word`).

## Edition 2 data

112 authored rows (`dataset/edition2/word_filters/`, source `e2_word_filters_words`): 13 matching variants and 13 traps
per phrase, plus eight rows with two phrases or combined traps. Test holds 100 rows, 50 per class. Labels follow the rule
above, and the regex baseline agrees on every row.
