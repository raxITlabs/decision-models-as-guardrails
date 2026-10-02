# Sources

Every source in this release, with the facts copied from its publisher at the pinned revision. Row-level `provenance.source` and `provenance.source_id` link each row to its entry here.

## aegis2

- Redistribution here: **text**
- Publisher: NVIDIA (card: "Curated by: NeMo Guardrails team, Nvidia.")
  - Original: https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0
  - Pinned revision: d86bb8bedff51d25ac834ab7838f1cc61acb7a2c
  - Licence: CC-BY-4.0
  - Licence text: https://creativecommons.org/licenses/by/4.0/
  - Restrictions: Card: "The data are intended for research purposes, especially research that can make models less harmful." "These data are not intended for training dialogue agents as this will likely lead to harmful model behavior." "Non-Identification: Users of this data agree to not attempt to determine the identity of individuals in this dataset." The ~358 Suicide Detection (Kaggle) samples are not distributed; their prompts read "REDACTED".
  - Requested citation:

```
@inproceedings{ghosh-etal-2025-aegis2,
    title = "{AEGIS}2.0: A Diverse {AI} Safety Dataset and Risks Taxonomy for Alignment of {LLM} Guardrails",
    author = "Ghosh, Shaona and Varshney, Prasoon and Sreedhar, Makesh Narsimhan and Padmakumar, Aishwarya and Rebedea, Traian and Varghese, Jibin Rajan and Parisien, Christopher",
    editor = "Chiruzzo, Luis and Ritter, Alan and Wang, Lu",
    booktitle = "Proceedings of the 2025 Conference of the Nations of the Americas Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)",
    month = apr,
    year = "2025",
    address = "Albuquerque, New Mexico",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.naacl-long.306/",
    doi = "10.18653/v1/2025.naacl-long.306",
    pages = "5992--6026",
    ISBN = "979-8-89176-189-6"
}
```

- Our adaptation: NVIDIA Aegis AI Content Safety Dataset 2.0, test split. CC-BY-4.0. Prompts are human-labelled; responses are labelled by humans or an LLM jury (recorded in label_basis). Rows whose prompt is REDACTED are skipped. Response rows carry their prompt as context, because a reply is only judgeable next to the request that caused it.
- Loader: `dataset/goldrails_dataset/sources/aegis2.py`

## ai4privacy

- Redistribution here: **withheld**
- Why withheld: The AI4Privacy licence separates research use from redistribution: making the dataset or derived annotations available needs written permission, even for a non-commercial project, and its research terms mention a licensing process. Ids-only rows still carry its span annotations and derived labels, so they are withheld while we clarify both with AI4Privacy (request drafted in docs/requests/ai4privacy-permission-request.md). The benchmark results that used these rows are unchanged and stay qualified.
- Publisher: Ai4Privacy (card: "AI4Privacy is a project affiliated with Ai Suisse SA")
  - Original: https://huggingface.co/datasets/ai4privacy/pii-masking-300k
  - Pinned revision: c8c77895a005822682b66ab547fc0422579bc1d3
  - Licence: LicenseRef-AI4Privacy-Dataset-and-Derivative-Products-License (card YAML: license: other, license_name: license.md)
  - Licence text: https://huggingface.co/datasets/ai4privacy/pii-masking-300k/blob/c8c77895a005822682b66ab547fc0422579bc1d3/LICENSE.md
  - Restrictions: LICENSE.md: access "granted exclusively for academic research and non-commercial purposes", AI4Privacy must be acknowledged in scholarly output; "To utilize this dataset beyond these conditions, including any form of redistribution, uploading to databases, sharing through any medium, or the creation and dissemination of derivative works, an explicit written license must be obtained from AI4Privacy." Commercial use needs contact with licensing@ai4privacy.com. States the dataset is watermarked and unauthorized use is traceable.
- Our adaptation: AI4Privacy pii-masking-300k, English rows: synthetic texts with labelled PII spans and a masked target text.
- Loader: `dataset/goldrails_dataset/sources/ai4privacy.py`

## ailuminate_demo

- Redistribution here: **text**
- Publisher: MLCommons (AI Risk & Reliability working group)
  - Original: https://github.com/mlcommons/ailuminate
  - Pinned revision: 769cc2be9d20c8d4fb26ce53b68865ed41dfb8e2
  - Licence: CC-BY-4.0 (data, per README); repo LICENSE.md is Apache-2.0
  - Licence text: https://creativecommons.org/licenses/by/4.0/deed.en
- Our adaptation: MLCommons AILuminate v1.0 demo prompt set (en_US), 1,200 human-written prompts across the 12 hazards. CC-BY-4.0. All rows are hazardous by construction; the benign side of F1 input comes from other sources.
- Loader: `dataset/goldrails_dataset/sources/ailuminate_demo.py`

## bbq

- Redistribution here: **text**
- Publisher: NYU Machine Learning for Language (nyu-mll); authors Parrish, Chen, Nangia, Padmakumar, Phang, Thompson, Htut, Bowman
  - Original: https://github.com/nyu-mll/BBQ
  - Pinned revision: bea11bd97d79217245b5871acd247b9d6eb24598
  - Licence: CC-BY-4.0
  - Licence text: https://creativecommons.org/licenses/by/4.0/legalcode
- Our adaptation: BBQ, the Bias Benchmark for QA (Parrish et al., Findings of ACL 2022), for F7 B3. CC-BY-4.0.
- Loader: `dataset/goldrails_dataset/sources/bbq.py`

## bias_pairs_reviewed

- Redistribution here: **ids_only**
- Publisher: Meta (facebookresearch/ResponsibleNLP)
  - Original: https://github.com/facebookresearch/ResponsibleNLP/tree/main/holistic_bias
  - Pinned revision: 0ec714eb084217f44cd9ac466d9e988c795302f9
  - Licence: CC-BY-SA-4.0 (HolisticBias dataset); MIT (HolisticBias and AdvPromptSet code)
  - Licence text: https://creativecommons.org/licenses/by-sa/4.0/
  - Restrictions: ShareAlike: the repo LICENSE applies 'Creative Commons Attribution-ShareAlike 4.0 International Public License' to the HolisticBias dataset, so adapted material shared publicly must carry the same or a BY-SA-compatible licence.
  - Requested citation:

```
@article{smith2022imsorry,
  doi = {10.48550/ARXIV.2205.09209},
  url = {https://arxiv.org/abs/2205.09209},
  author = {Smith, Eric Michael and Hall, Melissa and Kambadur, Melanie and Presani, Eleonora and Williams, Adina},
  keywords = {Computation and Language (cs.CL), Computers and Society (cs.CY), FOS: Computer and information sciences, FOS: Computer and information sciences},
  title = {"I'm sorry to hear that": Finding New Biases in Language Models with a Holistic Descriptor Dataset},
  publisher = {arXiv},
  year = {2022},
  copyright = {Creative Commons Attribution Share Alike 4.0 International}
}
```

- Our adaptation: B2 counterfactual pairs that passed review, as scorable F7 rows: human review in v1.1, single-AI reference review (label_basis llm, review_status ai_reviewed) in the provisional v1.1-ai.
- Loader: `dataset/goldrails_dataset/sources/bias_pairs_reviewed.py`

## civil_comments_identity

- Redistribution here: **ids_only**
- Publisher: Civil Comments platform archive with Jigsaw labels (google/civil_comments card: 'Jigsaw extended this dataset by adding additional labels for toxicity and identity mentions')
  - Original: https://huggingface.co/datasets/google/civil_comments
  - Mirror used: https://huggingface.co/datasets/pietrolesci/civilcomments-wilds
  - Pinned revision: google/civil_comments@f2970eb3a55777454c94069077cc8d9b5866312d (profanity rows); pietrolesci/civilcomments-wilds@c227534cc0a34cf21db6a0bf0edd0f9050c8b305 (identity rows)
  - Licence: CC0-1.0
  - Licence text: https://creativecommons.org/publicdomain/zero/1.0/
  - Requested citation:

```
@article{DBLP:journals/corr/abs-1903-04561,
  author    = {Daniel Borkan and
               Lucas Dixon and
               Jeffrey Sorensen and
               Nithum Thain and
               Lucy Vasserman},
  title     = {Nuanced Metrics for Measuring Unintended Bias with Real Data for Text
               Classification},
  journal   = {CoRR},
  volume    = {abs/1903.04561},
  year      = {2019},
  url       = {http://arxiv.org/abs/1903.04561},
  archivePrefix = {arXiv},
  eprint    = {1903.04561},
  timestamp = {Sun, 31 Mar 2019 19:01:24 +0200},
  biburl    = {https://dblp.org/rec/bib/journals/corr/abs-1903-04561},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}
```

- Our adaptation: Civil Comments with identity-mention annotations, for F7 B1 (guardrail error rates by identity mention). CC0-1.0.
- Loader: `dataset/goldrails_dataset/sources/civil_comments_identity.py`

## civil_comments_profanity

- Redistribution here: **text**
- Publisher: Civil Comments platform archive with Jigsaw labels (google/civil_comments card: 'Jigsaw extended this dataset by adding additional labels for toxicity and identity mentions')
  - Original: https://huggingface.co/datasets/google/civil_comments
  - Mirror used: https://huggingface.co/datasets/pietrolesci/civilcomments-wilds
  - Pinned revision: google/civil_comments@f2970eb3a55777454c94069077cc8d9b5866312d (profanity rows); pietrolesci/civilcomments-wilds@c227534cc0a34cf21db6a0bf0edd0f9050c8b305 (identity rows)
  - Licence: CC0-1.0
  - Licence text: https://creativecommons.org/publicdomain/zero/1.0/
  - Requested citation:

```
@article{DBLP:journals/corr/abs-1903-04561,
  author    = {Daniel Borkan and
               Lucas Dixon and
               Jeffrey Sorensen and
               Nithum Thain and
               Lucy Vasserman},
  title     = {Nuanced Metrics for Measuring Unintended Bias with Real Data for Text
               Classification},
  journal   = {CoRR},
  volume    = {abs/1903.04561},
  year      = {2019},
  url       = {http://arxiv.org/abs/1903.04561},
  archivePrefix = {arXiv},
  eprint    = {1903.04561},
  timestamp = {Sun, 31 Mar 2019 19:01:24 +0200},
  biburl    = {https://dblp.org/rec/bib/journals/corr/abs-1903-04561},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}
```

- Publisher: David Sojevic
  - Original: https://github.com/dsojevic/profanity-list
  - Pinned revision: main (resolved c27924319aa9bd6f917e3782b4f4b6604a50b652 on 2026-09-24)
  - Licence: MIT
  - Licence text: https://github.com/dsojevic/profanity-list/blob/main/LICENSE
- Our adaptation: Profanity-presence candidates for the word-filters suite (F4 subtask ``profanity``), from Civil Comments. CC0-1.0.
- Loader: `dataset/goldrails_dataset/sources/civil_comments_profanity.py`

## deepset_injections

- Redistribution here: **text**
- Publisher: deepset
  - Original: https://huggingface.co/datasets/deepset/prompt-injections
  - Pinned revision: 4f61ecb038e9c3fb77e21034b22511b523772cdd
  - Licence: Apache-2.0 (top-level card YAML); card also declares cc-by-4.0 nested under dataset_info
  - Licence text: https://www.apache.org/licenses/LICENSE-2.0
- Our adaptation: deepset/prompt-injections: 546 short texts labelled injection (1) or not (0). Apache-2.0. Small and old (2023); kept for the pilot and as anchor rows.
- Loader: `dataset/goldrails_dataset/sources/deepset_injections.py`

## discrim_eval

- Redistribution here: **text**
- Publisher: Anthropic
  - Original: https://huggingface.co/datasets/Anthropic/discrim-eval
  - Pinned revision: 6986d6ea802e019d01e94dd59597e94fbd8f8c4a
  - Licence: CC-BY-4.0
  - Licence text: https://creativecommons.org/licenses/by/4.0/
  - Restrictions: Card disclaimer (not a licence term): "We do not permit or endorse the use of LMs for high-risk automated decision making."
  - Requested citation:

```
@misc{tamkin2023discrim,
      title={Evaluating and Mitigating Discrimination in Language Model Decisions}, 
      author={Alex Tamkin and Amanda Askell and Liane Lovitt and Esin Durmus and Nicholas Joseph and Shauna Kravec and Karina Nguyen and Jared Kaplan and Deep Ganguli},
      year={2023},
      eprint={},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```

- Our adaptation: Anthropic discrim-eval (Tamkin et al., 2023), for F7 B3 (decision-model sensitivity to demographics). CC-BY-4.0.
- Loader: `dataset/goldrails_dataset/sources/discrim_eval.py`

## f2_controls

- Redistribution here: **text**
- Publisher: raxIT Labs (authored)
  - Licence: CC-BY-4.0
  - Note: Authored for Gold Rails by raxIT Labs with an AI assistant (Claude), CC-BY-4.0. Labels are the author's intended labels (label_basis llm or deterministic), not independent annotation.
- Our adaptation: Authored benign controls for the prompt-attack suite: text that shares surface features with attacks but is a legitimate request. They test the question wording, not the model: ordinary instruction changes, quoted attack examples discussed rather than used, authorised configuration questions, and harmless fiction with attack-like words.
- Loader: `dataset/goldrails_dataset/sources/f2_controls.py`

## f3_controls

- Redistribution here: **text**
- Publisher: raxIT Labs (authored)
  - Licence: CC-BY-4.0
  - Note: Authored for Gold Rails by raxIT Labs with an AI assistant (Claude), CC-BY-4.0. Labels are the author's intended labels (label_basis llm or deterministic), not independent annotation.
- Our adaptation: Authored cases for the denied-topics suite, against the topic definitions in benchmark/suites/denied_topics/topics.json.
- Loader: `dataset/goldrails_dataset/sources/f3_controls.py`

## f3_test_candidates

- Redistribution here: **text**
- Publisher: raxIT Labs (authored)
  - Licence: CC-BY-4.0
  - Note: Authored for Gold Rails by raxIT Labs with an AI assistant (Claude), CC-BY-4.0. Labels are the author's intended labels (label_basis llm or deterministic), not independent annotation.
- Our adaptation: Test candidates for the denied-topics suite, against the v1 topic definitions in benchmark/suites/denied_topics/topics.json.
- Loader: `dataset/goldrails_dataset/sources/f3_test_candidates.py`

## f4_words

- Redistribution here: **text**
- Publisher: raxIT Labs (authored)
  - Licence: CC-BY-4.0
  - Note: Authored for Gold Rails by raxIT Labs with an AI assistant (Claude), CC-BY-4.0. Labels are the author's intended labels (label_basis llm or deterministic), not independent annotation.
- Our adaptation: Deterministic cases for the word-filters suite, generated from benchmark/suites/word_filters/words.json.
- Loader: `dataset/goldrails_dataset/sources/f4_words.py`

## f5_controls

- Redistribution here: **text**
- Publisher: raxIT Labs (authored)
  - Licence: CC-BY-4.0
  - Note: Authored for Gold Rails by raxIT Labs with an AI assistant (Claude), CC-BY-4.0. Labels are the author's intended labels (label_basis llm or deterministic), not independent annotation.
- Our adaptation: Authored negatives for the sensitive-information suite: realistic business and personal text with numbers, dates, prices, product codes, generic roles and organisations, but no information that identifies or reaches a specific person. They exist because AI4Privacy has no PII-free rows. Authored by Claude on 22 September 2026 with the intended label; label_basis "llm" until a person reviews them. Expected "no" on every entity question.
- Loader: `dataset/goldrails_dataset/sources/f5_controls.py`

## gandalf

- Redistribution here: **text**
- Publisher: Lakera
  - Original: https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions
  - Pinned revision: 04737b65e90a6794ec227012e4a255a7def6344b
  - Licence: MIT
  - Licence text: https://opensource.org/license/mit/
  - Requested citation:

```
@article{gandalf_paper,
  title={Gandalf the Red: Adaptive Security for LLMs},
  author={Pfister, Niklas and Volhejn, V{\'a}clav and Knott, Manuel and Arias, Santiago and Bazi{\'n}ska, Julia and Bichurin, Mykhailo and Commike, Alan and Darling, Janet and Dienes, Peter and Fiedler, Matthew and others},
  journal={arXiv preprint arXiv:2501.07927},
  year={2025}
}
```

- Our adaptation: Lakera gandalf_ignore_instructions: 777 real user attempts to make the model ignore its instructions and reveal a secret. MIT. All rows are attacks (prompt leakage subtype); benign counterparts come from other sources.
- Loader: `dataset/goldrails_dataset/sources/gandalf.py`

## jailbreakbench

- Redistribution here: **text**
- Publisher: JailbreakBench Team
  - Original: https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors
  - Pinned revision: 886acc352a31533ffbcf4ef22c744658688086fc
  - Licence: MIT
  - Licence text: https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/blob/886acc352a31533ffbcf4ef22c744658688086fc/LICENSE
  - Requested citation:

```
@inproceedings{chao2024jailbreakbench,
  title={JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models},
  author={Patrick Chao and Edoardo Debenedetti and Alexander Robey and Maksym Andriushchenko and Francesco Croce and Vikash Sehwag and Edgar Dobriban and Nicolas Flammarion and George J. Pappas and Florian Tramèr and Hamed Hassani and Eric Wong},
  booktitle={NeurIPS Datasets and Benchmarks Track},
  year={2024}
}

@misc{zou2023universal,
  title={Universal and Transferable Adversarial Attacks on Aligned Language Models},
  author={Andy Zou and Zifan Wang and J. Zico Kolter and Matt Fredrikson},
  year={2023},
  eprint={2307.15043},
  archivePrefix={arXiv},
  primaryClass={cs.CL}
}
@inproceedings{tdc2023,
  title={TDC 2023 (LLM Edition): The Trojan Detection Challenge},
  author={Mantas Mazeika and Andy Zou and Norman Mu and Long Phan and Zifan Wang and Chunru Yu and Adam Khoja and Fengqing Jiang and Aidan O'Gara and Ellie Sakhaee and Zhen Xiang and Arezoo Rajabi and Dan Hendrycks and Radha Poovendran and Bo Li and David Forsyth},
  booktitle={NeurIPS Competition Track},
  year={2023}
}
@article{mazeika2024harmbench,
  title={HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal},
  author={Mazeika, Mantas and Phan, Long and Yin, Xuwang and Zou, Andy and Wang, Zifan and Mu, Norman and Sakhaee, Elham and Li, Nathaniel and Basart, Steven and Li, Bo and Forsyth, David and Hendrycks, Dan},
  journal={arXiv preprint arXiv:2402.04249},
  year={2024}
}
```

- Our adaptation: JailbreakBench behaviors: 100 harmful goals and 100 benign lookalikes. MIT.
- Loader: `dataset/goldrails_dataset/sources/jailbreakbench.py`

## jbb_artifacts

- Redistribution here: **text**
- Publisher: JailbreakBench Team and artifacts authors
  - Original: https://github.com/JailbreakBench/artifacts
  - Pinned revision: 909e68c01d94222b8ad2e397a017e2e12e2adb73
  - Licence: MIT
  - Licence text: https://github.com/JailbreakBench/artifacts/blob/909e68c01d94222b8ad2e397a017e2e12e2adb73/LICENSE
  - Requested citation:

```
@misc{chao2024jailbreakbench,
      title={JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models}, 
      author={Patrick Chao and Edoardo Debenedetti and Alexander Robey and Maksym Andriushchenko and Francesco Croce and Vikash Sehwag and Edgar Dobriban and Nicolas Flammarion and George J. Pappas and Florian Tramèr and Hamed Hassani and Eric Wong},
      year={2024},
      eprint={2404.01318},
      archivePrefix={arXiv},
      primaryClass={cs.CR}
}
```

- Publisher: JailbreakBench Team
  - Original: https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors
  - Pinned revision: 886acc352a31533ffbcf4ef22c744658688086fc
  - Licence: MIT
  - Licence text: https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/blob/886acc352a31533ffbcf4ef22c744658688086fc/LICENSE
  - Requested citation:

```
@inproceedings{chao2024jailbreakbench,
  title={JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models},
  author={Patrick Chao and Edoardo Debenedetti and Alexander Robey and Maksym Andriushchenko and Francesco Croce and Vikash Sehwag and Edgar Dobriban and Nicolas Flammarion and George J. Pappas and Florian Tramèr and Hamed Hassani and Eric Wong},
  booktitle={NeurIPS Datasets and Benchmarks Track},
  year={2024}
}

@misc{zou2023universal,
  title={Universal and Transferable Adversarial Attacks on Aligned Language Models},
  author={Andy Zou and Zifan Wang and J. Zico Kolter and Matt Fredrikson},
  year={2023},
  eprint={2307.15043},
  archivePrefix={arXiv},
  primaryClass={cs.CL}
}
@inproceedings{tdc2023,
  title={TDC 2023 (LLM Edition): The Trojan Detection Challenge},
  author={Mantas Mazeika and Andy Zou and Norman Mu and Long Phan and Zifan Wang and Chunru Yu and Adam Khoja and Fengqing Jiang and Aidan O'Gara and Ellie Sakhaee and Zhen Xiang and Arezoo Rajabi and Dan Hendrycks and Radha Poovendran and Bo Li and David Forsyth},
  booktitle={NeurIPS Competition Track},
  year={2023}
}
@article{mazeika2024harmbench,
  title={HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal},
  author={Mazeika, Mantas and Phan, Long and Yin, Xuwang and Zou, Andy and Wang, Zifan and Mu, Norman and Sakhaee, Elham and Li, Nathaniel and Basart, Steven and Li, Bo and Forsyth, David and Hendrycks, Dan},
  journal={arXiv preprint arXiv:2402.04249},
  year={2024}
}
```

- Our adaptation: JailbreakBench attack artifacts: jailbreak prompts produced by published attacks (PAIR, GCG, JBC) against each of the 100 JBB behaviors. MIT. Pinned to one commit of github.com/JailbreakBench/artifacts.
- Loader: `dataset/goldrails_dataset/sources/jbb_artifacts.py`

## openai_moderation

- Redistribution here: **text**
- Publisher: OpenAI
  - Original: https://github.com/openai/moderation-api-release
  - Mirror used: https://huggingface.co/datasets/mmathys/openai-moderation-api-evaluation
  - Pinned revision: mirror mmathys/openai-moderation-api-evaluation@84e5cf3bcd6acb3dfc70b6760451645872218a3e; original openai/moderation-api-release main (resolved f4ab51b5edd3bfbcb349a56324274235b674e0e4 on 2026-09-24)
  - Licence: MIT
  - Licence text: https://github.com/openai/moderation-api-release/blob/main/LICENSE
  - Requested citation:

```
@article{openai2022moderation,
  title={A Holistic Approach to Undesired Content Detection},
  author={Todor Markov and Chong Zhang and Sandhini Agarwal and Tyna Eloundou and Teddy Lee and Steven Adler and Angela Jiang and Lilian Weng},
  journal={arXiv preprint arXiv:2208.03274},
  year={2022}
}
```

- Our adaptation: OpenAI's 2022 moderation evaluation set (1,680 prompts, 8 categories). MIT. Anchor-only: every guard model reports on it. A row is unsafe if any category column is 1; the first set column decides the AILuminate mapping.
- Loader: `dataset/goldrails_dataset/sources/openai_moderation.py`

## orbench

- Redistribution here: **text**
- Publisher: bench-llm (OR-Bench authors)
  - Original: https://huggingface.co/datasets/bench-llm/or-bench
  - Pinned revision: e36d8b80e81837c8a8f264bbb2a49f1b32c7e272
  - Licence: CC-BY-4.0
  - Licence text: https://creativecommons.org/licenses/by/4.0/
- Our adaptation: OR-Bench hard-1k: benign prompts that look unsafe, for over-refusal. CC-BY-4.0. Labels are by construction (the set is curated to be benign), recorded as automated: membership in the curated set, not a human judgment per row.
- Loader: `dataset/goldrails_dataset/sources/orbench.py`

## ragtruth

- Redistribution here: **ids_only**
- Publisher: Particle Media
  - Original: https://github.com/ParticleMedia/RAGTruth
  - Pinned revision: main (resolved c103204b9ce28d6bbad859304bf30de72b8ed8fe on 2026-09-24)
  - Licence: MIT
  - Licence text: https://github.com/ParticleMedia/RAGTruth/blob/main/LICENSE
  - Requested citation:

```
@misc{wu2023ragtruth,
      title={RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models}, 
      author={Yuanhao Wu and Juno Zhu and Siliang Xu and Kashun Shum and Cheng Niu and Randy Zhong and Juntong Song and Tong Zhang},
      year={2023},
      eprint={2401.00396},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```

- Our adaptation: RAGTruth (Particle Media, MIT): sources, model-generated replies, and human-annotated hallucination spans.
- Loader: `dataset/goldrails_dataset/sources/ragtruth.py`

