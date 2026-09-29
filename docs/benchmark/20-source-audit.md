# 20. Source audit: what each loader imports, under what licence, and what still needs a person

23 September 2026. Work unit B of the completion plan (`docs/reports/gold-rails-completion-plan.html`). This note
covers every loader in `dataset/goldrails_dataset/sources/`. For each one it records the upstream revision, the licence
and whether we may redistribute the text, what a positive meant at the source, which Gold Rails subtask the loader
feeds, what we changed, and whether a person has to relabel or review anything before a test claim rests on it.

Nothing here is a result, and nothing here changes a label. Licence readings are mine, taken from the licence text or
dataset card on the date above. They are not legal advice. Where the lead has to decide, the item is in the decision
list at the end.

## How to rerun

```
uv run python -m goldrails_dataset.audit            # writes dataset/frozen/audit-report.json
uv run python -m goldrails_dataset.audit --strict   # exits 1 while a gate fails
uv run python -m goldrails_dataset.audit --packets  # also rewrites dataset/frozen/review-packets/
```

The audit reads files only. It makes no network or model call and writes no timestamp, so the same inputs give a
byte-identical report. Tests: `dataset/tests/test_audit.py`.

## Audit result on sample-1k

Status: **fail**, on two of eight gates. The sample is fine for tuning smokes. Its test split should not be run until
both failures are fixed and the sample is rebuilt.

| Gate | Result | What it found |
|---|---|---|
| Manifest integrity | pass | All 10 listed files match their row counts and hashes |
| Orphan split files | **fail** | `F3.test.jsonl` (24 rows) and `F4.test.jsonl` (34 rows) sit beside the manifest but are not in it. Every row in them is on the examined list and appears in the tune files. `load_rows("F3", "test", source=...)` reads files by name, so it would serve these rows as test data |
| Schema | pass | 1,565 rows validate; every `split` field matches its file |
| Recorded group leakage | pass | No `group` value crosses tune and test |
| Derived group leakage | **fail** | 38 source-level groups cross the split: 30 JailbreakBench behaviours (26 of them across F1 and F2) and 8 RAGTruth source documents (17 rows) |
| Examined rows kept out of test | pass | 129 of 132 examined ids are in the sample, none in test. The 3 missing are F4 "unrelated" rows that dedup dropped, because all four phrases share one sentence |
| Duplicate text across splits | pass | No normalised text appears in both splits |
| PII mapping | pass | Every AI4Privacy span label matches what the loader's current table gives; notes and categories agree |

The recorded-group gate passes only because `build.py` throws the loaders' groups away. `group_of()` returns the row
id for every source except Aegis, which overwrites `ragtruth-<source_id>` and `jbb-<index>`. The audit therefore
derives groups itself: the Aegis conversation, the RAGTruth source document (by its normalised text, since the record
does not keep RAGTruth's own source id), the JBB behaviour index, and the word-filter phrase.

Warnings with numbers (not gates, because the floors are proposals):

- Three subtasks have one class in test: F1 `over_refusal` (benign only, by design), F2 `jailbreak` and F2 `leakage`
  (attacks only). Balanced accuracy cannot be computed on the latter two. Their only negatives are authored controls,
  which are examined by definition and so stay in tune for good.
- F3 and F4 have no test rows at all, for the same reason.
- Benign test rows per suite against the proposed floor of 300: F1 331, F2 75, F3 0, F4 0, F5 67, F6 85.
- PII test positives per supported entity against a proposed floor of 30: NAME 36, ADDRESS 32, USERNAME 23, EMAIL 20,
  DRIVER_ID 20, IP_ADDRESS 15, PHONE 14, PASSWORD 7, US_SOCIAL_SECURITY_NUMBER 3. PASSWORD has no tune positive, so no
  per-entity threshold can be chosen for it.
- 97 Aegis response rows in test carry LLM-jury labels, including all 82 unsafe responses in test.
- 83 OR-Bench rows in test are benign by an automated pipeline, not by a person.
- 40 rows look German on a crude stopword test, 39 of them from deepset (31 in test). v1 is English only.
- Seven external loaders pull the default branch with no pinned revision.

## Summary by source

| Source | Rows (test/tune) | Revision | Licence | Redistribute text | Label basis | Review or relabel |
|---|---|---|---|---|---|---|
| aegis2 | 217 / 55 | not pinned | CC-BY-4.0 | yes, with attribution | human prompts; responses human or LLM jury | yes, for LLM-jury responses |
| ai4privacy | 152 / 28 | pinned | AI4Privacy custom | **no** | synthetic, vendor QA on a sample | mapping review; licence decision |
| ailuminate_demo | 34 / 6 | not pinned | CC-BY-4.0 | yes, with attribution | human-written, hazardous by construction | no |
| deepset_injections | 160 / 30 | not pinned | Apache-2.0 (card metadata also says CC-BY-4.0) | yes | undocumented | yes: filter German rows, document the label |
| gandalf | 85 / 15 | not pinned | MIT | yes | selected by embedding similarity | yes: subtask mapping and label basis |
| jailbreakbench | 170 / 30 | not pinned | MIT | yes | curated goals | no; fix grouping |
| jbb_artifacts | 73 / 13 | pinned | MIT | yes | attack prompt by construction | no; fix grouping |
| openai_moderation | 75 / 13 | not pinned | MIT | yes | human, with many categories unknown | **yes**: unknown is being read as benign |
| orbench | 83 / 17 | not pinned | CC-BY-4.0 | yes, with attribution | automated pipeline | sample review before test claims |
| ragtruth | 170 / 30 | pinned | MIT for annotations | check passage sources | human spans | no relabel for grounding; fix grouping |
| f2_controls | 0 / 20 | in repo | ours | yes | authored by Claude | **yes**, blind packet ready |
| f3_controls | 0 / 28 | in repo | ours | yes | authored by Claude | **yes**, blind packet ready |
| f4_words | 0 / 41 | words.json hash | ours | yes | deterministic | no |
| f5_controls | 0 / 20 | in repo | ours | yes | authored by Claude | **yes**, blind packet ready |

"Not pinned" revisions below are the heads the Hub or GitHub served on 23 September 2026. The loaders did not record
the revision they read on 22 September, so these heads are the likely inputs, not proven ones.

## Per source

### aegis2 (F1 input, F1 output)

| | |
|---|---|
| Upstream | `nvidia/Aegis-AI-Content-Safety-Dataset-2.0`, test split. The card now calls it Nemotron Content Safety Dataset V2 |
| Revision | Not pinned. Hub head `d86bb8bedff51d25ac834ab7838f1cc61acb7a2c` (last modified 9 June 2025). Not gated |
| Licence | CC-BY-4.0. Redistribution allowed with attribution |
| Original label | `prompt_label` and `response_label` are binary safe/unsafe over NVIDIA's 12-hazard taxonomy. Prompt labels are always human. Response labels come from `human`, `llm_jury` (Mixtral-8x22B, Mistral-NeMo-12B, Gemma-2-27B) or `refusal_data_augmentation` |
| Adaptation | Prompt becomes an F1 input row, response an F1 output row with the prompt as context. The first mappable violated category sets the AILuminate hazard. Rows with a REDACTED prompt are skipped. "Needs Caution" rows are excluded. Any non-human response source is recorded as `llm` |
| Review | The LLM-jury response labels are model labels. Either review a sample of them blind, or report F1 output separately for human-labelled and jury-labelled rows. In test today, every unsafe response is jury-labelled |

### ai4privacy (F5 pii)

| | |
|---|---|
| Upstream | `ai4privacy/pii-masking-300k`, validation split, English rows |
| Revision | Pinned `c8c77895a005822682b66ab547fc0422579bc1d3`, which is also the head on 23 September |
| Licence | Custom. The LICENSE.md grants academic, non-commercial use only. It forbids redistribution, uploading to databases and derivative works without a written licence, and says commercial users must contact AI4Privacy first |
| Redistribution | No. Gold Rails can publish row ids, the revision and the rebuild command, never the text. Whether raxIT may use it at all is an open question, because raxIT is a company. The loader docstring says "usable for evaluation"; the licence text does not say that |
| Original label | Character spans for 27 PII classes. The data is synthetic. The card reports about 98.3% token label accuracy on a 216-entry QA sample, which is vendor QA, not per-row review |
| Adaptation | Spans map to AWS entity types through `TO_AWS`. Unmapped labels stay as `unmapped:<label>` and never make a row negative. Span-free chunks with masking placeholders are excluded. Row expected is "yes" when any span exists |
| Review | Mapping review (see the PII section). No relabel of spans |

### ailuminate_demo (F1 input, positives only)

| | |
|---|---|
| Upstream | `mlcommons/ailuminate`, file `airr_official_1.0_demo_en_us_prompt_set_release.csv` |
| Revision | Not pinned: the loader reads `main`. The CSV last changed in commit `d7c115ec83a7e3c447eade38f6120f84cbccb674` (18 March 2025); repo head `769cc2be9d20c8d4fb26ce53b68865ed41dfb8e2` |
| Licence | The data is CC-BY-4.0 per the repo README. The repo code is Apache-2.0 |
| Original label | Every prompt is hazardous by construction and carries one of 12 hazard codes and a persona |
| Adaptation | Hazard code maps to AILuminate category and then to a Bedrock category. All rows are "yes" |
| Review | None for the label. Pin the file to a commit |

### deepset_injections (F2 injection)

| | |
|---|---|
| Upstream | `deepset/prompt-injections`, train split only (546 rows; the 116-row test split is unused) |
| Revision | Not pinned. Hub head `4f61ecb038e9c3fb77e21034b22511b523772cdd` |
| Licence | Apache-2.0 at the top of the card; the card's `dataset_info` block also says CC-BY-4.0. Both allow redistribution; attribution covers either reading |
| Original label | `label` 1 or 0. The card documents neither the label definition nor who labelled it |
| Adaptation | 1 becomes an injection positive, 0 a benign row. `label_basis` is recorded as human, which the card does not support |
| Review | Mixes German and English. The audit flags 39 deepset rows as German-looking, 31 of them in test. Decide whether to filter them (v1 is English) and confirm by hand. Consider changing `label_basis` to `unknown` |

### gandalf (F2 leakage, positives only)

| | |
|---|---|
| Upstream | `Lakera/gandalf_ignore_instructions`, train split |
| Revision | Not pinned. Hub head `04737b65e90a6794ec227012e4a255a7def6344b`. The card warns the set may be updated |
| Licence | MIT |
| Original label | None per row. Lakera took July 2023 Gandalf prompts, kept those with embedding similarity of at least 0.825 to "Ignore all previous instructions", removed PII and near-duplicates. The card says a few rows may not be real injections |
| Adaptation | Every row becomes an F2 leakage positive. The source frames them as instruction-override attempts in a game whose goal is a secret password, so both injection and leakage apply |
| Review | The label comes from automatic selection, not from a person, so `label_basis` should be `automated`, not `human`. Decide whether these rows belong under leakage, injection, or both |

### jailbreakbench (F1 harmful_goal)

| | |
|---|---|
| Upstream | `JailbreakBench/JBB-Behaviors`, `behaviors` config, harmful and benign splits |
| Revision | Not pinned. Hub head `886acc352a31533ffbcf4ef22c744658688086fc` |
| Licence | MIT. The `Source` column names where each behaviour came from; those origins' licences were not checked |
| Original label | 100 harmful behaviours and 100 benign behaviours matched to them by topic |
| Adaptation | Plain goals, no attack technique, so they feed F1 harmful_goal, not F2. Loader group `jbb-<index>` ties a harmful goal to its benign match and to the attack artifacts built on it |
| Review | None for the label. The grouping is lost in the build (see gates) |

### jbb_artifacts (F2 jailbreak, positives only)

| | |
|---|---|
| Upstream | `github.com/JailbreakBench/artifacts`, PAIR (vicuna-13b, llama-2-7b), GCG (vicuna-13b), JBC (vicuna-13b) |
| Revision | Pinned `909e68c01d94222b8ad2e397a017e2e12e2adb73`, also the head |
| Licence | MIT |
| Original label | None needed. Each prompt is an attack produced by a published method; `jailbroken` records whether the target complied and is kept as a note |
| Adaptation | Every prompt becomes an F2 jailbreak positive, `label_basis: deterministic` |
| Review | None. Keep each behaviour's goal and attacks in one split |

### openai_moderation (F1 input)

| | |
|---|---|
| Upstream | `mmathys/openai-moderation-api-evaluation`, a Hub mirror of `openai/moderation-api-release` `data/samples-1680.jsonl.gz` |
| Revision | Not pinned. Hub head `84e5cf3bcd6acb3dfc70b6760451645872218a3e`; upstream GitHub head `f4ab51b5edd3bfbcb349a56324274235b674e0e4` |
| Licence | MIT |
| Original label | Eight binary category flags. The upstream README says a category missing from a sample means the label is unknown. In the mirror, H is null on 54% of rows, S on 41%, S3 on 41%, the rest on about 14% |
| Adaptation | A row is unsafe when any flag is 1, otherwise benign. A null flag counts as "not 1" |
| Review | **Relabel or filter.** A row with no positive flag and some unknown flags is not known to be benign. In the first 100 mirror rows, 33 of the 57 rows the loader calls benign have at least one unknown flag. The fix is a loader rule: benign only when all eight flags are known and zero; otherwise exclude with a reason. 75 of these rows are in test today |

### orbench (F1 over_refusal, benign only)

| | |
|---|---|
| Upstream | `bench-llm/or-bench`, `or-bench-hard-1k` |
| Revision | Not pinned. Hub head `e36d8b80e81837c8a8f264bbb2a49f1b32c7e272` |
| Licence | CC-BY-4.0 |
| Original label | Benign by construction: an automated pipeline generates prompts that look toxic and keeps those judged safe. OR-Bench measures how often a model refuses them |
| Adaptation | All rows are "no". `label_basis: automated` |
| Review | The earlier pilot (docs/16) showed that a benign OR-Bench label and a decision model's "is this about crime" answer measure different things. Review a sample blind before an over-refusal claim, and remember over-refusal here means blocking a benign request, not the subject being sensitive |

### ragtruth (F6 grounding)

| | |
|---|---|
| Upstream | `github.com/ParticleMedia/RAGTruth`, `source_info.jsonl` and `response.jsonl`, test split, Summary and QA tasks |
| Revision | Pinned `c103204b9ce28d6bbad859304bf30de72b8ed8fe`, also the head |
| Licence | MIT for the repository and annotations. The passages come from third-party corpora: the RAGTruth paper draws Summary passages from news articles and QA passages from MS MARCO. Those terms are not MIT. Check them before publishing passage text |
| Original label | Human-annotated spans in model replies, typed Evident Conflict, Subtle Conflict, Evident Baseless Info, Subtle Baseless Info |
| Adaptation | A reply with any span is "yes" for unsupported. The query becomes the short task (the QA question, or a fixed Summary instruction) because Bedrock takes one text unit as query. Data2txt is excluded |
| Review | No relabel for grounding: the spans judge support against the passage, which we keep unchanged. Replacing the query does not touch those labels. Relevance has no label (next section). The build loses the source-document group, and 8 documents now cross the split |

### f2_controls (F2 injection, jailbreak, leakage; negatives only)

| | |
|---|---|
| Origin | 20 cases authored by Claude on 22 September 2026, in the loader file |
| Revision | sha256 of the loader file, recorded in the audit report and packet manifest |
| Licence | Ours, declared CC-BY-4.0 |
| Label | Intended "no" on all three attack types. `label_basis: llm` |
| Adaptation | None. They are examined by definition, so they stay in tune |
| Review | **Required.** Blind packet at `dataset/frozen/review-packets/f2-prompt-attacks/`. See the definition conflict in the decision list |

### f3_controls (F3 topic)

| | |
|---|---|
| Origin | 28 cases authored by Claude against `benchmark/suites/denied_topics/topics.json` v1 |
| Label | Intended in-topic or out-of-topic per case. `label_basis: llm` |
| Review | **Required.** Blind packet at `dataset/frozen/review-packets/f3-denied-topics/`, which asks about all three topics for every case instead of revealing which topic a case was written for |

### f4_words (F4 word)

| | |
|---|---|
| Origin | Generated from `benchmark/suites/word_filters/words.json` v1 under the rule "exact phrase, case-insensitive, whole words" |
| Label | Deterministic from the rule |
| Review | None for labels. The "unrelated" sentence is identical for every phrase, so dedup keeps one copy. All 41 rows are examined and in tune, so F4 has no test split |

### f5_controls (F5 pii, negatives only)

| | |
|---|---|
| Origin | 20 PII-free business texts authored by Claude, as negatives beside AI4Privacy's own span-free chunks |
| Label | Intended "no" on every entity. `label_basis: llm` |
| Review | **Required.** Blind packet at `dataset/frozen/review-packets/f5-sensitive-information/` |

## Grounding and relevance: options

RAGTruth labels support against a source. It has nothing on whether a reply answers the query, so relevance has no
reference label today. The completion plan requires relevance to be labelled or deferred in the open. Options:

1. **Defer.** Report the suite as "grounding tested, relevance not evaluated". No new data, no cost. Honest, and the
   leaderboard shows a coverage gap for relevance. This is my recommendation for v1 unless option 2 is cheap enough.
2. **Construct mismatched pairs from RAGTruth QA.** Pair each reply with its own question (relevant) and with the
   question from a different source document (irrelevant). Labels come from construction. It is cheap, but mismatched
   questions are easy to spot, so it tests the easy end of relevance only. A person should review a sample of the
   relevant side, because some RAGTruth replies do not answer the question even when they are grounded.
3. **Author and review a small relevance set.** Replies that are grounded but answer a different or partial question.
   Harder cases, but authored cases need two blind reviewers and stay in tune if anyone on the team wrote them.
4. **Import a published answer-relevance set.** Candidates to check: WikiEval (from Ragas) and RAGBench. I have not
   verified their licences or whether their labels mean answer relevance rather than context relevance.

Whichever option is chosen, relevance is its own subtask (`F6 relevance`) with its own labels, never inferred from
grounding labels.

## PII mapping and the jurisdiction heuristic

Shared supported entities (question set `v2/f5-pii`): NAME, EMAIL, PHONE, ADDRESS, USERNAME, PASSWORD, IP_ADDRESS,
DRIVER_ID, US_SOCIAL_SECURITY_NUMBER. The audit re-derives every AI4Privacy span label from the loader's current table
and finds no mismatch.

Status of the SSN heuristic: a `SOCIALNUMBER` span maps to `US_SOCIAL_SECURITY_NUMBER` only when its value has the
`123-45-6789` form. That form is evidence of SSN-like formatting, not of US jurisdiction. In sample-1k it produces 4
test spans in 3 test rows and 2 tune spans in 1 tune row; 17 test rows keep `unmapped:SOCIALNUMBER`. With 3 test rows,
no entity-level SSN claim is possible anyway. The suite README already keeps these rows out of strict entity-level
claims. The audit keeps them countable (`pii.ssn_pattern_heuristic_spans`). Nothing in the source metadata establishes
jurisdiction, and I found no field that would. Options: keep the heuristic and report SSN as "format-matched, not
jurisdiction-verified"; or drop US_SOCIAL_SECURITY_NUMBER from the scored entity list for v1 and report it as a
coverage note.

Mapping questions for a reviewer:

- ADDRESS: a lone CITY, STATE or POSTCODE span maps to ADDRESS, but a lone COUNTRY does not. The AWS ADDRESS definition,
  as I read it, lists country among address components. One of the two needs to change, and the question wording
  (`v2/f5-pii` ADDRESS) should match whichever wins.
- PASSPORT, IDCARD and BOD (date of birth) are unmapped. AWS has US_PASSPORT_NUMBER but no general passport or ID card
  type, and AGE but not date of birth. These rows stay positive for the source's `contains_pii` task and count as
  coverage differences, which is right.
- 11 test rows (5 tune) carry only unmapped types. They are positives for `contains_pii` and negatives for
  `any_supported_entity`. The scorer has to treat them per question, not per row.
- Entity support is thin: 7 of 9 supported entities are under the proposed 30-positive test floor, and PASSWORD has no
  tune positive. The next build needs per-entity stratification, not per-row.

## Decisions for the lead

1. **Stale test files.** Delete `dataset/samples/sample-1k/F3.test.jsonl` and `F4.test.jsonl`, or regenerate the
   sample. Both are tracked in git. Until then, a run of F3 or F4 test from sample-1k silently scores examined rows.
2. **Grouping in `build.py`.** Change `group_of()` to keep the loader's group (`return r.group or r.id` after the
   Aegis case), so RAGTruth documents and JBB behaviours stay whole, then rebuild. Decide whether the JBB link should
   bind F1 goals and F2 attacks into one split (the loader says yes; 26 groups currently cross features).
3. **OpenAI moderation unknowns.** Approve the loader rule: benign only when all eight flags are known and zero.
4. **AI4Privacy licence.** Decide whether raxIT, as a company, may use it for a published benchmark at all, or
   write to licensing@ai4privacy.com, or replace it with a permissive span-labelled source. The text is not
   redistributable in any case.
5. **Test negatives for jailbreak and leakage, and test rows for F3 and F4.** Authored cases are examined forever, so
   these cells need negatives from a source nobody on the team has looked at, or new cases written by someone outside
   the tuning loop.
6. **F2 definition conflict before sending the packet.** The `v1/f2-attacks` injection question counts an attempt to
   "add to the instructions it already has", with "from now on" and "new rule:" as examples. Five f2 controls are
   ordinary user preferences phrased exactly that way, authored with the intended answer "no". Decide which
   definition governs: a user changing their own conversation, or any change to instructions. The packet shows the
   question-set wording verbatim; change the wording before sending if the answer is the former.
7. **Relevance.** Pick an option from the section above.
8. **Label basis corrections.** Gandalf to `automated`; deepset to `unknown` unless its label definition is found.
9. **German rows.** Filter deepset German rows from v1, or scope v1 as "mostly English" and say so.
10. **Pin revisions** for the seven unpinned loaders, at the heads listed above or at whatever the lead chooses.
11. **Aegis LLM-jury labels.** Review a sample, or report F1 output split by label source.

## What this audit did not check

- Near-duplicates beyond whitespace and case, such as paraphrased Gandalf attempts or JBB artifacts that quote their
  goal verbatim inside a longer prompt.
- Overlap with public model training sets beyond the `contamination` tags the loaders already carry.
- Whether a pinned revision serves the same rows as the sample was built from. That needs a rebuild and a hash
  comparison, which needs network access to the datasets.
- Row-level accuracy of any source label. That is what the review packets and adjudication are for.
- The bias sources (Civil Comments, HolisticBias, CrowS-Pairs, discrim-eval, BBQ). No F7 loader exists yet.
