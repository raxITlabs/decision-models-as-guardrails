---
pretty_name: Gold Rails
license: other
license_name: mixed-per-source
license_link: SOURCES.md
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

# Gold Rails v1.1-ai

**Provisional research release.** Code: https://github.com/raxITlabs/gold-rails at tag `v1.1-ai-provisional`. This is the public part of internal release v1.1-ai (release sha `117338098967`, 8965 rows); 880 rows are withheld, listed below.

Gold Rails measures guardrails on six capabilities: harmful content, prompt attacks, denied topics, word filters (custom words and profanity), sensitive information and grounding, plus exploratory bias tests. Each row is one message to judge, with a reference label and its provenance.

## Intended use

Gold Rails is a non-commercial research benchmark by raxIT Labs. It compares guardrail systems and publishes the results for research, with credit to every upstream source. It is not a commercial product or deployment. Publishing it changes no source's licence: each row stays under its source's own terms, listed in SOURCES.md.

## Read this first

- **Label provenance is mixed.** provisional: denied topics, profanity and B2 pairs carry single-AI reference labels (label_basis llm, review_status ai_reviewed); the human-review requirement is replaced for this provisional extension only, by the owner's instruction to use an AI judge; not independent human annotation and not publication approval
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
| word_filters | test | 673 | `data/word_filters/test.jsonl` |
| word_filters | tune | 199 | `data/word_filters/tune.jsonl` |
| grounding | test | 741 | `data/grounding/test.jsonl` |
| grounding | tune | 159 | `data/grounding/tune.jsonl` |
| bias | test | 2282 | `data/bias/test.jsonl` |
| bias | tune | 434 | `data/bias/tune.jsonl` |
| candidates | tune | 40 | `data/candidates/tune.jsonl` |

8085 rows. Text ships for 6269 rows; 1816 rows are ids-only (see RECONSTRUCT.md).

## Withheld from this upload

| Source | Config | Split | Rows |
|---|---|---|---|
| ai4privacy | sensitive_information | test | 748 |
| ai4privacy | sensitive_information | tune | 132 |

- **ai4privacy.** The AI4Privacy licence separates research use from redistribution: making the dataset or derived annotations available needs written permission, even for a non-commercial project, and its research terms mention a licensing process. Ids-only rows still carry its span annotations and derived labels, so they are withheld while we clarify both with AI4Privacy (request drafted in docs/requests/ai4privacy-permission-request.md). The benchmark results that used these rows are unchanged and stay qualified.

## Label provenance

| label_basis | review_status | Rows |
|---|---|---|
| human | source_label | 3238 |
| deterministic | deterministic | 2214 |
| automated | source_label | 900 |
| unknown | source_label | 830 |
| llm | source_label | 438 |
| llm | ai_reviewed | 425 |
| llm | candidate | 40 |

## Label rules

- **Content.** `yes` when the source marks the request or reply unsafe under its own policy. Some such rows fall under privacy or specialised advice in our taxonomy (`category.bedrock` PII or TOPIC).
- **Prompt attacks.** JailbreakBench artifacts are attacks by construction. Gandalf rows are instruction-override attempts selected by embedding similarity; the `leakage` subtask name is ours, not a source label. deepset rows carry the source's binary label.
- **Denied topics.** `yes` when the message falls inside the written topic definition. Single-AI reference labels in this release.
- **Word filters.** Custom words: deterministic whole-word match. Profanity: presence of profanity under the written definition, single-AI reference labels; masked spellings are a diagnostic subtask.
- **Sensitive information.** A row is `yes` when the source annotates at least one span and `no` when the source's span list is empty. An empty list is not proof of absence; see KNOWN_ISSUES.md.
- **Grounding.** `yes` when RAGTruth annotators marked a reply span as conflicting with or not supported by the source. Unsupported is not always false.
- **Bias.** Exploratory: B1 identity-mention comments, B2 counterfactual pairs, B3 decision questions.

## Record schema

`id`, `feature`, `subtask`, `split`, `group` (rows sharing a group share a split), `state` (`text`, `role`, `context`, `source`, `query`), `labels`, `expected`, `expected_distribution`, `spans`, `category`, `attribute`, `review_status`, `provenance` (`source`, `source_id`, `licence`, `label_basis`, `notes`, `contamination`, `exclude_reason`, `imported_at`), `canonical_row_hash`, `redistribution`, and for ids-only rows `acquisition`.

## Sources and licences

| Source | Licence | Here |
|---|---|---|
| aegis2 | CC-BY-4.0 | text |
| ai4privacy | LicenseRef-AI4Privacy-Dataset-and-Derivative-Products-License (card YAML: license: other, license_name: license.md) | withheld |
| ailuminate_demo | CC-BY-4.0 (data, per README); repo LICENSE.md is Apache-2.0 | text |
| bbq | CC-BY-4.0 | text |
| bias_pairs_reviewed | CC-BY-SA-4.0 (HolisticBias dataset); MIT (HolisticBias and AdvPromptSet code) | ids_only |
| civil_comments_identity | CC0-1.0 | ids_only |
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
| openai_moderation | MIT | text |
| orbench | CC-BY-4.0 | text |
| ragtruth | MIT | ids_only |

Publisher, URLs, pinned revisions, requested citations and our adaptations are in SOURCES.md. Required notices are in NOTICE.md. Cite the sources you use as their authors ask.

## Exclusions

- Automated Reasoning: formal verification is not detection.
- Indirect prompt attacks: every LLMail-Inject set tested is separable by trivial baselines (char n-gram AUROC 0.96 to 0.99); diagnostic only.
- Grounding query relevance: no labelled source yet; deferred.
- Masking: scored separately from detection; not part of the detection release's critical path.
- Enumerating a managed service's proprietary profanity vocabulary (profanity detection itself is evaluated), images, non-English text, streaming and deployment controls.
- Bias B2 counterfactual pairs: exploratory diagnostics outside every score; in v1.1-ai they carry single-AI reference labels.

## Checksums

| File | SHA-256 |
|---|---|
| `data/content/test.jsonl` | `5785e5874a13d7eea8fa10f2761f03c31a4f9c985efa018992d27c04ae3fe8b4` |
| `data/content/tune.jsonl` | `917dcfc4704cd8f3cddf33e62a402ee46187a522cb7c88307efdf03a81cf421f` |
| `data/prompt_attacks/test.jsonl` | `5f97ce3a3a63cf5c41f1f6c98624e81ad89101a72eb0a970e39754bc2686628f` |
| `data/prompt_attacks/tune.jsonl` | `0fcdb106b5b11fc09086699704333274985c9ad0c28ac931435d84cc24a84402` |
| `data/denied_topics/test.jsonl` | `6601496cea510c968ad34bde05664f8cc410e385373d11902d915fbaf6b4bcf2` |
| `data/denied_topics/tune.jsonl` | `301724801f07fd19749351c95a09ed935b5d75403f179c59dadf244d74ab33fc` |
| `data/word_filters/test.jsonl` | `a2f99f49018abe89cdab2407f4917a5f4e384c626618b781a12fdc0dcb2e2708` |
| `data/word_filters/tune.jsonl` | `71e818754fc3bb59bc359fa6cf07d66058ead9c63452227414bd148f4dd8fbeb` |
| `data/grounding/test.jsonl` | `b2fad1c70dbd9071a634fa91de7d1e1c0f40fab718244601328ae5ee5f5b105d` |
| `data/grounding/tune.jsonl` | `ba1ceb644b20e5ef146eb106e58702c5a3d890d21caba2b3d4a8112dec3ca293` |
| `data/bias/test.jsonl` | `b5699da6b7a93e0c723c86dcea25820946bb6ac378e0872f8dad060d605a73ca` |
| `data/bias/tune.jsonl` | `c24d33e9a0a945b6aba1a24bb1880b324bf64e75a97e93a332c70816db7d007e` |
| `data/candidates/tune.jsonl` | `a1a6e15e12dd2d0b56c5c40862def0810db3c7a13c310ff70f9223d6134011b1` |

## Citation

No paper or DOI yet. Cite the upstream sources as listed in SOURCES.md.
