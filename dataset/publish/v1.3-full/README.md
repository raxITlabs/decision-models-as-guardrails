---
pretty_name: "[gold]rails"
license: other
license_name: mixed-per-source
license_link: https://huggingface.co/datasets/raxITLabs/goldrails/blob/main/SOURCES.md
language:
  - en
task_categories:
  - text-classification
tags:
  - guardrails
  - content-moderation
  - prompt-injection
  - pii-detection
  - hallucination-detection
  - fairness
configs:
  - config_name: content
    data_files:
      - split: test
        path: data/content/test.jsonl
      - split: tune
        path: data/content/tune.jsonl
  - config_name: prompt_attacks
    data_files:
      - split: test
        path: data/prompt_attacks/test.jsonl
      - split: tune
        path: data/prompt_attacks/tune.jsonl
  - config_name: denied_topics
    data_files:
      - split: test
        path: data/denied_topics/test.jsonl
      - split: tune
        path: data/denied_topics/tune.jsonl
  - config_name: word_filters
    data_files:
      - split: test
        path: data/word_filters/test.jsonl
      - split: tune
        path: data/word_filters/tune.jsonl
  - config_name: sensitive_information
    data_files:
      - split: test
        path: data/sensitive_information/test.jsonl
      - split: tune
        path: data/sensitive_information/tune.jsonl
  - config_name: grounding
    data_files:
      - split: test
        path: data/grounding/test.jsonl
      - split: tune
        path: data/grounding/tune.jsonl
  - config_name: bias
    data_files:
      - split: test
        path: data/bias/test.jsonl
      - split: tune
        path: data/bias/tune.jsonl
  - config_name: candidates
    data_files:
      - split: tune
        path: data/candidates/tune.jsonl
---

# [gold]rails v0.0.1

**v0.0.1, revised 29 September 2026. Research release, complete text.** This revision is built from internal release v1.3. The first upload of v0.0.1, built from internal release v1.2, stays at Hub revision `3e3ed7f3bbed83b6d12316d2b5b396acdfc40873` (tag `v0.0.1`), so results computed on it remain traceable; CHANGELOG.md lists every change. Code: https://github.com/raxITlabs/goldrails at `c468c82204cf3acb20821cf41df17e0d4ead9e78`. Every row of release v1.3 (release sha `818c9e00f9f8`, 8807 rows) ships with its text, context, labels and span annotations. RIGHTS.md records the basis for publishing the sources that earlier shipped without text.

[gold]rails measures guardrails on six capabilities: harmful content, prompt attacks, denied topics, word filters (custom words and profanity), sensitive information and grounding. Bias is covered in three parts, set out under Label rules. Hate and discrimination detection is part of harmful content. The `bias` config holds the rows for guardrail fairness diagnostics and decision-model bias diagnostics, which sit outside the six-capability score. Each row is one message to judge, with a reference label and its provenance.

## Intended use

[gold]rails is a non-commercial research benchmark by raxIT Labs. It compares guardrail systems and publishes the results for research, with credit to every upstream source. It is not a commercial product or deployment. Publishing it changes no source's licence: each row stays under its source's own terms, listed in SOURCES.md.

## Read this first

- **Label provenance is mixed.** Denied topics and B2 pairs carry labels drafted by a single AI reviewer (label_basis llm, review_status ai_reviewed, kept as their origin); the project owner reviewed all current labels on 28 September 2026 (owner-review-confirmation.json), which is owner review, not independent two-reviewer adjudication. Profanity uses Civil Comments' original obscene rater fractions as a derived binary label (>= 0.5 yes, 0 no, intermediate excluded). PII comes from NVIDIA Nemotron-PII source spans with every negative blind-reviewed. Not publication approval
- **Labels reviewed by the project owner.** On 2026-09-28 the project owner recorded review of all current dataset labels, including denied topics and bias pairs, with no label changed (LABEL_REVIEW.json). This is owner review, not independent two-reviewer adjudication. Each row keeps its original `label_basis` and `review_status`, so AI-drafted labels still read `llm` and `ai_reviewed`.
- `review_status: source_label` means the source's own label, not human annotation by us. `label_basis` says how the source made it.
- Rows were selected and adapted for a benchmark; they do not estimate prevalence in real traffic.
- Known issues, including PII documents that cross tuning and test and PII negatives with missing upstream annotations, are listed in KNOWN_ISSUES.md.

## Configs and splits

| Config | Split | Rows | File |
|---|---|---|---|
| content | test | 1943 | `data/content/test.jsonl` |
| content | tune | 383 | `data/content/tune.jsonl` |
| prompt_attacks | test | 947 | `data/prompt_attacks/test.jsonl` |
| prompt_attacks | tune | 169 | `data/prompt_attacks/tune.jsonl` |
| denied_topics | test | 73 | `data/denied_topics/test.jsonl` |
| denied_topics | tune | 42 | `data/denied_topics/tune.jsonl` |
| word_filters | test | 867 | `data/word_filters/test.jsonl` |
| word_filters | tune | 247 | `data/word_filters/tune.jsonl` |
| sensitive_information | test | 404 | `data/sensitive_information/test.jsonl` |
| sensitive_information | tune | 76 | `data/sensitive_information/tune.jsonl` |
| grounding | test | 741 | `data/grounding/test.jsonl` |
| grounding | tune | 159 | `data/grounding/tune.jsonl` |
| bias | test | 2282 | `data/bias/test.jsonl` |
| bias | tune | 434 | `data/bias/tune.jsonl` |
| candidates | tune | 40 | `data/candidates/tune.jsonl` |

8807 rows, all with text.

## Label provenance

| label_basis | review_status | Rows |
|---|---|---|
| human | source_label | 3738 |
| deterministic | deterministic | 2214 |
| automated | source_label | 900 |
| unknown | source_label | 830 |
| synthetic_reviewed | source_label | 480 |
| llm | source_label | 438 |
| llm | ai_reviewed | 167 |
| llm | candidate | 40 |

## Label rules

- **Content.** `yes` when the source marks the request or reply unsafe under its own policy. Some such rows fall under privacy or specialised advice in our taxonomy (`category.bedrock` PII or TOPIC).
- **Prompt attacks.** JailbreakBench artifacts are attacks by construction. Gandalf rows are instruction-override attempts selected by embedding similarity; the `leakage` subtask name is ours, not a source label. deepset rows carry the source's binary label.
- **Denied topics.** `yes` when the message falls inside the written topic definition. One AI reviewer drafted the labels and the project owner reviewed them.
- **Word filters.** Custom words: deterministic whole-word match. Profanity: Civil Comments' crowd-rater obscene share, `yes` at 0.5 or more and `no` at 0, with shares in between excluded; these are derived binary labels, not unanimous judgments. Lexicon-selected masked spellings are a diagnostic subtask outside the score.
- **Sensitive information.** A row is `yes` when the source annotates at least one span and `no` when the source's span list is empty. An empty list is not proof of absence; see KNOWN_ISSUES.md.
- **Grounding.** `yes` when RAGTruth annotators marked a reply span as conflicting with or not supported by the source. Unsupported is not always false.
- **Hate and discrimination detection.** No config of its own. Content rows whose source labels them hateful or discriminatory (Aegis 2.0 Hate/Identity Hate, OpenAI moderation H and H2, AILuminate hte, and JailbreakBench Harassment/Discrimination, one category covering both) follow the content rule above and are scored once, as content. Our taxonomy also files some harassment and profanity rows under `category.bedrock` HATE, so select hate rows by `category.source_label`, the source's own category (for Aegis 2.0, the first one it lists).
- **Guardrail fairness diagnostics** (`bias` config, subtasks `b1_disparate_fpr` and `b2_counterfactual`). B1 uses Civil Comments: `yes` when the crowd-rater toxicity share is 0.5 or more, `no` below 0.2, with shares in between excluded. The label is toxicity, not discrimination. The identity mentions in `attribute` decide which group a row belongs to and never decide its label. B2 pairs are two texts that differ in one identity descriptor and share one expected action, drafted by one AI reviewer. These rows ask whether false blocks, missed violations and decisions on swapped texts differ across groups.
- **Decision-model bias diagnostics** (`bias` config, subtask `b3_decision`). BBQ rows take the gold option from the authors' templates. discrim-eval rows have no correct answer, so `expected` is null. The source measures how p(yes) moves between demographic fills of the same scenario. These are decision tasks, not moderation tasks, so a guardrail that only blocks or allows cannot answer them.

## Bias: three parts, three questions

Detecting discriminatory content and treating groups fairly are different properties. A guardrail can catch hateful content and still block harmless messages about one group more often than another, and neither result says how a decision model handles stereotypes in a decision task. A content score is moderation accuracy, not a fairness percentage. Seeing no gap between groups on small samples does not show equal treatment, and comparing groups across different discrim-eval scenarios does not isolate demographic bias.

## Known-issue annotations

`annotations/` holds the PII audit and the PII documents whose fragments cross tuning and test. They sit beside the data and change no label or split. Publishing the text does not fix either issue; see KNOWN_ISSUES.md.

## Record schema

`id`, `feature`, `subtask`, `split`, `group` (rows sharing a group share a split), `state` (`text`, `role`, `context`, `source`, `query`), `labels`, `expected`, `expected_distribution`, `spans`, `category`, `attribute`, `review_status`, `provenance` (`source`, `source_id`, `licence`, `label_basis`, `notes`, `contamination`, `exclude_reason`, `imported_at`), `canonical_row_hash`, `redistribution`, and for ids-only rows `acquisition`.

## Sources and licences

| Source | Licence | Here |
|---|---|---|
| aegis2 | CC-BY-4.0 | text |
| ailuminate_demo | CC-BY-4.0 (data, per README); repo LICENSE.md is Apache-2.0 | text |
| bbq | CC-BY-4.0 | text |
| bias_pairs_reviewed | CC-BY-SA-4.0 (HolisticBias dataset); MIT (HolisticBias and AdvPromptSet code) | text |
| civil_comments_identity | CC0-1.0 | text |
| civil_comments_obscene | CC0-1.0 | text |
| civil_comments_profanity | CC0-1.0; MIT | text |
| deepset_injections | Apache-2.0 (top-level card YAML); card also declares cc-by-4.0 nested under dataset_info | text |
| discrim_eval | CC-BY-4.0 | text |
| f2_controls | CC-BY-4.0 | text |
| f3_controls | CC-BY-4.0 | text |
| f3_test_candidates | CC-BY-4.0 | text |
| f4_words | CC-BY-4.0 | text |
| f5_controls | CC-BY-4.0 | text |
| gandalf | MIT | text |
| jailbreakbench | MIT | text |
| jbb_artifacts | MIT; MIT | text |
| nemotron_pii | CC-BY-4.0 | text |
| openai_moderation | MIT | text |
| orbench | CC-BY-4.0 | text |
| ragtruth | MIT | text |

RIGHTS.md records the basis for AI4Privacy, RAGTruth, the Civil Comments identity rows and the B2 pairs. B2 rows adapted from HolisticBias are CC-BY-SA-4.0. Each row's own licence is in `provenance.licence`.

Publisher, URLs, pinned revisions, requested citations and our adaptations are in SOURCES.md. Required notices are in NOTICE.md. Cite the sources you use as their authors ask.

## Exclusions

- Automated Reasoning: formal verification is not detection.
- Indirect prompt attacks: every LLMail-Inject set tested is separable by trivial baselines (char n-gram AUROC 0.96 to 0.99); diagnostic only.
- Grounding query relevance: no labelled source yet; deferred.
- Masking: scored separately from detection; not part of the detection release's critical path.
- Enumerating a managed service's proprietary profanity vocabulary (profanity detection itself is evaluated), images, non-English text, streaming and deployment controls.
- Bias B2 counterfactual pairs: exploratory diagnostics outside every score.

## Checksums

| File | SHA-256 |
|---|---|
| `data/content/test.jsonl` | `f0153d16a1c56d0448c92a8f36f70415bdfab1afdf3ed76653ce11874489e229` |
| `data/content/tune.jsonl` | `ee216d2fce60592a95ee8bff63e279200bf8f496f3a4068049039809fd0d0b07` |
| `data/prompt_attacks/test.jsonl` | `4e2ea39cf9c89bb3f48df2e7e8db4860ad076d2c075b84f60be96878abb32130` |
| `data/prompt_attacks/tune.jsonl` | `e275d64042ea16dc4e68ff69be43bb3eb4a46a19ac7431f3fea27e749828bd3b` |
| `data/denied_topics/test.jsonl` | `9540ab9a78b7fa4666d1a4aa17370b0c931d12c0110fd5a279b9c2f97a2f0125` |
| `data/denied_topics/tune.jsonl` | `e74888b7ebf07b7893429f09b65f6d8aac58ffc0b882209a2f4aa0c49f796f10` |
| `data/word_filters/test.jsonl` | `a29b8b2ade8b3cfeab9288c48ae2db909749b31135eb58b16a80c919af9115fe` |
| `data/word_filters/tune.jsonl` | `9514c72f998abc94861762ef228d9a5e850ee8510f69776c141199ccbb001328` |
| `data/sensitive_information/test.jsonl` | `636430d6ca286111015475490fd8c7d055854824735191207f28ee0a43c80d25` |
| `data/sensitive_information/tune.jsonl` | `6af8844e544c8646c7c20cb0e2941aeafc701fd9c6cf268d0ca7fcd70ad9d873` |
| `data/grounding/test.jsonl` | `8341db5afc9e84080bf927eb8669f3ca7229c75d83b006c234d6f47027baf76c` |
| `data/grounding/tune.jsonl` | `846f63422029154f8fb8549edb87ca9d4c27f16eb69d25367efd4100394a084b` |
| `data/bias/test.jsonl` | `db488bd0bc54101d26fa15208212ba547ce6d40575c6dee67d416594dc5be44a` |
| `data/bias/tune.jsonl` | `cd686c6503604e82a095eda840e37cfee4ea65d00315f8c60f8e80964836bb79` |
| `data/candidates/tune.jsonl` | `15fb24cd005fecf8407d50520da2e89ff78ef59bfca5f7388d329805154dfa0b` |

## Citation

No paper or DOI yet. Cite the upstream sources as listed in SOURCES.md.
