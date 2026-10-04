# Suite policies (edition 2)

Under contract v2.0 the benchmark defines a task as a policy plus labelled rows. This directory holds the policies:
one file per suite and subtask, named `<suite>/<subtask>.md` after the contract's suite and subtask names.

Each file says what counts as a violation and what does not. It does not say how to ask a system about it. Adapters
handle that part. The Noul adapter sends the frozen questions in `benchmark/question_sets/e2/`. Bedrock is set up
from its own frozen configuration. A vendor verdict API applies its own categories. A row's label comes from the
policy, so every system is scored against the same text, however its adapter phrases the question.

The wording comes from the v1 question sets, Bedrock's category definitions and the suite READMEs in
`benchmark/suites/`. Edge cases (refusals, quotation, literal senses of a word) are stated only where one of those
sources already stated them, or where the owner ruled on them. The owner's edition 2 rulings
(`docs/benchmark/29-owner-rulings-2026-10-03.md`) are written into the files they affect, each marked with its ruling
number: denied topics (1), prompt attacks (2, 3), grounding (4), sensitive information (5, 6), content (8) and word
filters (13).

Changing a policy changes the task. Edition 2 freezes these files with the dataset. A later edition that changes one
has to say so in its changelog and re-label the affected rows.

| Suite | Subtask | File |
|---|---|---|
| content | request | `content/request.md` |
| content | reply | `content/reply.md` |
| prompt_attacks | direct | `prompt_attacks/direct.md` |
| denied_topics | topic | `denied_topics/topic.md` |
| word_filters | word (pass/fail sanity check, outside the score in edition 2) | `word_filters/word.md` |
| word_filters | profanity | `word_filters/profanity.md` |
| sensitive_info | entity_detection | `sensitive_info/entity_detection.md` |
| grounding | grounding | `grounding/grounding.md` |
| grounding | relevance (optional) | `grounding/relevance.md` |

`goldrails_bench.adapters.policy_text(suite, subtask)` loads a file. A test checks that every subtask an adapter
serves has a policy.
