# Profanity reference datasets: original labels, provenance, licences (verified 2026-09-28)

Scope: published datasets whose original label says whether a text contains profanity (swear words, curse words, vulgar terms), checked at source for a guardrail benchmark. "Inference" and "local measurement" mark my own analysis. Everything else is quoted or paraphrased from the cited source.

Revisions pinned (Hugging Face `sha` from `https://huggingface.co/api/datasets/<id>`, fetched 2026-09-28; GitHub commit from the API):

| Source | Pinned revision | Last modified |
|---|---|---|
| google/civil_comments (HF) | `f2970eb3a55777454c94069077cc8d9b5866312d` | 2024-01-25 |
| google/jigsaw_unintended_bias (HF, loader script only) | `d46022c9df7c8b74ba52876f314f81ef60fa1727` | 2024-01-18 |
| google/jigsaw_toxicity_pred (HF, loader script only) | `9fca5f507ac11049ff34bb13c8546b01afcedbbd` | 2024-01-18 |
| nvidia/Aegis-AI-Content-Safety-Dataset-2.0 (HF) | `d86bb8bedff51d25ac834ab7838f1cc61acb7a2c` | 2025-06-09 |
| Hate-speech-CNERG/hatexplain (HF) | `f6a8b7de6ec31b30919d2f48cf685400ce61185f` | 2024-01-18 |
| cardiffnlp/tweet_eval (HF, `offensive` config = OffensEval 2019) | `b3a375baf0f409c77e6bc7aa35102b7b3534f8be` | 2024-01-04 |
| christophsonntag/OLID (HF mirror) | `37262ae493ed725b68b93aab1632b8207760dc8f` | 2024-03-15 |
| conversationai annotation scheme `toxicity_with_subattributes.md` (GitHub) | last commit touching file `8a88f1fc0a365a3189926cd64f5fab2546cd5315` | 2018-12-10 |
| dadangewp/SWAD-Repository (GitHub) | `23d3c2e59e1064b69bbe24df047abeafe8d31f88` | 2021-10-12 |
| ericholgate/VulgarFunctionsTwitter (GitHub) | `477045787513ebd3d98d56eacdb4f6942ba57fd4` | 2019-01-11 |
| mmathys/profanity (HF mirror of Surge AI list) | `c2a17bf3ec64d9b6418ead1cb5f7ef26dbdffccb` | 2023-09-27 |
| vzhou842/profanity-check (GitHub) | `c835dc0f8ef28c7691688ecb774fd3149c1f097b` | 2020-05-24 |
| TFDS civil_comments | version 1.2.4 (default) | n/a |

## Which source's original label is closest to "the text contains profanity"?

### Takeaway
The Civil Comments / Jigsaw Unintended Bias `obscene` sub-attribute comes closest among row-labelled text datasets. Its crowd question was "Profanity/Obscenity: Contains swear words, curse words, or other obscene or profane language." The rater guide marks "That's fucking amazing ! thanks for sharing." as Profanity = Yes and Toxicity = Not Toxic, so presence and toxicity are separated. Aegis 2.0 "Profanity" reuses that wording, but only as a sub-category on conversations that humans had already judged unsafe, so it measures "unsafe because of profanity", not presence. OLID/OffensEval puts profanity inside OFF. SWAD and Holgate label what a swear word is doing in texts that all contain one, so they have no profanity-free negatives.

### Cited Findings

#### 1. Civil Comments / Jigsaw Unintended Bias in Toxicity Classification (2019): `obscene`
- **Annotator definition (exact).** The Conversation AI "Toxicity with sub-attributes" crowd instructions say: "We are additionally interested in determining if the comment contains profanity/obscenity, sexually explicit content, identity based attacks, threatening language and insults." The definition given is "Profanity/Obscenity: Contains swear words, curse words, or other obscene or profane language." — [conversationai toxicity_with_subattributes.md](https://github.com/conversationai/conversationai.github.io/blob/main/crowdsourcing_annotation_schemes/toxicity_with_subattributes.md)
- **Answer scale.** Each attribute is answered "on a 3 point scale (2: Yes, has *attribute*; 1: hard to say or only slightly has *attribute*; 0: No *attribute*)". Raters also answer a separate toxicity question (Very Toxic / Toxic / Slightly Toxic or hard to say / Not toxic) and tick a box if the comment is not in English. — [same file](https://github.com/conversationai/conversationai.github.io/blob/main/crowdsourcing_annotation_schemes/toxicity_with_subattributes.md)
- **Calibration examples that separate profanity from toxicity:**
  - Example 5, "That's fucking amazing ! thanks for sharing.": Toxicity "Not Toxic, or Hard to say", Profanity/Obscenity "Yes". The stated reasoning is that "fucking" is profane language, "however in this case it is used in a positive way."
  - Example 2: "fking" counts as profanity as a misspelling of "fucking".
  - Example 1: an insult with no swear words ("He looks like a caveman…") gets Profanity/Obscenity "No".
  - Source for all three: [same file](https://github.com/conversationai/conversationai.github.io/blob/main/crowdsourcing_annotation_schemes/toxicity_with_subattributes.md)
- **Same guidelines as Perspective, per the paper.** Borkan et al. (2019) say the data "was also labeled for toxicity using the same crowd rating guidelines as published by the Perspective API", that "Raters were also asked about several subtypes of toxicity, although these labels were not used for the analysis in this work", and that the result is "a dataset of 1.8 million comments". The paper does not quote the sub-attribute wording. — [Borkan et al. 2019, arXiv:1903.04561](https://arxiv.org/abs/1903.04561)
- **Value format.** "the toxicity and other tags are a value between 0 and 1 indicating the fraction of annotators that assigned these attributes to the comment text." — [TFDS civil_comments](https://www.tensorflow.org/datasets/catalog/civil_comments). On HF, `obscene` is a `float32`. — [google/civil_comments card @f2970eb](https://huggingface.co/datasets/google/civil_comments/raw/f2970eb3a55777454c94069077cc8d9b5866312d/README.md). The jigsaw_unintended_bias card describes it as "value between 0(non-obscene) and 1(obscene)" and also exposes `toxicity_annotator_count`. — [google/jigsaw_unintended_bias card @d46022c](https://huggingface.co/datasets/google/jigsaw_unintended_bias/raw/d46022c9df7c8b74ba52876f314f81ef60fa1727/README.md)
- **Input context.** Single public news-site comments "created from 2015 - 2017" on "approximately 50 English-language news sites". The HF card says "This data set is an exact replica of the data released for the Jigsaw Unintended Bias in Toxicity Classification Kaggle challenge." Splits: 1,804,874 train, 97,320 validation, 97,320 test. — [google/civil_comments card](https://huggingface.co/datasets/google/civil_comments/raw/f2970eb3a55777454c94069077cc8d9b5866312d/README.md). A separate TFDS config, CivilCommentsInContext, adds parent comment text. — [TFDS](https://www.tensorflow.org/datasets/catalog/civil_comments)
- **Language.** English. — [jigsaw_unintended_bias card](https://huggingface.co/datasets/google/jigsaw_unintended_bias/raw/d46022c9df7c8b74ba52876f314f81ef60fa1727/README.md)
- **Class balance (local measurement, test split, parquet @f2970eb, n=97,320).**
  - Mean `obscene` 0.014.
  - obscene > 0: 7,927 rows (8.15%).
  - obscene ≥ 0.5 ("> 0.5" in my script): 427 rows (0.44%).
  - obscene > 0.8: 70 rows (0.07%).
  - Positives are very rare, and the values are fractional (e.g. 0.0006), which fits the "up to thousands of raters" weighting described below.
- **Local measurement: `obscene` is not a lexicon match.** I ran a simple swear-word regex (fuck*/shit*/bitch*/asshole*/damn*/crap/bastard*/dick*/piss*/cunt*). It matched 1,010 test comments. Of those, 28.5% have `obscene` == 0 and only 29.4% have `obscene` ≥ 0.5. In the other direction, only 54.7% of `obscene` ≥ 0.5 comments match the regex. So neither the label nor a word list is a clean proxy for the other. Mild words ("damn", "crap") and ambiguous words ("dick" as a name) probably account for much of this (inference).
- **Rater counts.** The HF jigsaw_unintended_bias card says the competition target "was a binarized version of the toxicity column, which can be easily reconstructed using a >=0.5 threshold". — [card](https://huggingface.co/datasets/google/jigsaw_unintended_bias/raw/d46022c9df7c8b74ba52876f314f81ef60fa1727/README.md). I could not load the Kaggle data page (JavaScript-rendered), so I could not verify the Kaggle wording on rater counts (commonly quoted as "up to 10 annotators", some "up to thousands"). Listed under Gaps.

#### 2. Jigsaw Toxic Comment Classification Challenge (2018, Wikipedia talk pages): `obscene`
- **Label format.** "`obscene`: value of 0(non-obscene) or 1(obscene) classifying the comment". Other labels: `toxic`, `severe_toxic`, `threat`, `insult`, `identity_hate`. The text is "a large number of Wikipedia comments which have been labeled by human raters for toxic behavior." Language: English. — [google/jigsaw_toxicity_pred card @9fca5f5](https://huggingface.co/datasets/google/jigsaw_toxicity_pred/raw/9fca5f507ac11049ff34bb13c8546b01afcedbbd/README.md)
- **No published annotator definition for `obscene` found.** The HF card's Annotation process and annotators sections are empty ("More Information Needed"). The only definitions I found were in secondary blog posts, which I did not treat as authoritative. — [same card](https://huggingface.co/datasets/google/jigsaw_toxicity_pred/raw/9fca5f507ac11049ff34bb13c8546b01afcedbbd/README.md)
- **The card itself warns about a swear-word bias.** "If words that are associated with swearing, insults or profanity are present in a comment, it is likely that it will be classified as toxic, regardless of the tone or the intent of the author". — [same card](https://huggingface.co/datasets/google/jigsaw_toxicity_pred/raw/9fca5f507ac11049ff34bb13c8546b01afcedbbd/README.md)
- **Hosting.** At the pinned revision the HF repo contains only `README.md` and a loader script `jigsaw_toxicity_pred.py`, with no data files. The data has to come from the Kaggle competition page. The same holds for `google/jigsaw_unintended_bias`. — [HF API file listing](https://huggingface.co/api/datasets/google/jigsaw_toxicity_pred). `google/civil_comments`, by contrast, hosts parquet files directly. — [HF API](https://huggingface.co/api/datasets/google/civil_comments)
- **Downstream reuse.** The `profanity-check` library was trained on this data plus Davidson et al.'s tweets. — [profanity-check README](https://github.com/vzhou842/profanity-check)

#### 3. NVIDIA Aegis 2.0 / Nemotron Content Safety Dataset V2: `Profanity` in `violated_categories`
- **Definition (exact, from the taxonomy policy in the paper's guard-model prompt appendix):** "S12: Profanity. Should not - Contain swear words, curse words, or other obscene or profane language - This includes offensive words used without any intention to act on them or without any explicit targetted recipient". — [Ghosh et al., NAACL 2025, AEGIS2.0](https://aclanthology.org/2025.naacl-long.306/). The Aegis 1.0 paper gives the same first line ("O12: Profanity. Should not - Contain swear words, curse words, or other obscene or profane language") and states "We include Profanity and Threat from Perspective's taxonomy." — [Ghosh et al. 2024, arXiv:2404.05993](https://arxiv.org/abs/2404.05993)
- **How categories are assigned (conditional on unsafe).** "Annotators were asked to provide an overall dialogue level annotation of safe, needs caution or unsafe. If the dialogue was marked unsafe, annotators additionally had to identify one or more risk categories associated with the response." Each instance got "at least three annotations"; Fleiss' kappa was "approximately 74%". — [AEGIS2.0 paper §4.1](https://aclanthology.org/2025.naacl-long.306/)
- **Annotators are told to judge context, not words.** From the annotator instructions (Table 6): "Choose the label(s) based on intonation and context: Read the text and based on the context, decide the label that suits best instead of identifying words separately to assign labels." Also: "If the text is not toxic, label the text as 'Safe'". — [AEGIS2.0 paper, Table 6](https://aclanthology.org/2025.naacl-long.306/)
- **Label fields (card).** `prompt_label` and `response_label` are "binary safety label"; `prompt_label_source` is "always `human` annotated"; `response_label_source` is "either `human`, `llm_jury`, or `refusal_data_augmentation`"; `violated_categories` is a "comma-separated list of categories in order of frequency of annotations." — [Aegis 2.0 card @d86bb8b](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0/raw/d86bb8bedff51d25ac834ab7838f1cc61acb7a2c/README.md)
- **Prompt and response labels split from one conversation vote.** A single conversation-level human vote is split across prompt and response. For prompts with a majority unsafe vote, response labels come from a jury of three LLMs (Mixtral-8x22B, Mistral-NeMo-12B, Gemma-2-27B). "If the conversation-level human vote is safe, we assume this applies for both the prompt and response." — [AEGIS2.0 paper §4.1.1–4.1.2](https://aclanthology.org/2025.naacl-long.306/)
- **Input context.** Prompts come from Anthropic HH-RLHF, DAN jailbreaks and AART; responses were generated by Mistral-7B-v0.1. Language: "English (may contain small samples in other languages)". — [card](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0/raw/d86bb8bedff51d25ac834ab7838f1cc61acb7a2c/README.md)
- **Local measurement: how often Profanity appears (files @d86bb8b).**
  - Train: 1,546 of 25,007 rows list Profanity; 436 list only Profanity.
  - Validation: 91 of 1,245 (23 only).
  - Test: 115 of 1,964 (33 only).
- **Local measurement: Profanity is tied to unsafe prompts.** In train, 1,527 of the 1,546 Profanity rows have `prompt_label` = unsafe, and 19 have `prompt_label` = safe. Some Profanity rows carry `response_label` = safe (201 in train), so on those rows the tag may come from the prompt side or from annotator categories over the whole conversation (inference).
- **Local measurement: safe prompts can contain swear words.** In train, 29 prompts labelled safe contain a swear substring, e.g. "Damn, that's crazy." (test split, `prompt_label` safe, no category).
- **Local measurement: the tag is noisy and not about the prompt text itself.** In train, 47 unsafe prompts contain swear words but are not tagged Profanity. Some Profanity-only rows contain no swear word in the prompt, e.g. "okay, sure, please do." (unsafe/unsafe, Profanity), where the profanity is presumably in the response or elsewhere in the conversation (inference).
- **Annotators.** About 12 annotators, all resident in the United States, working in Label Studio. — [card](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0/raw/d86bb8bedff51d25ac834ab7838f1cc61acb7a2c/README.md)

#### 4. OLID / OffensEval 2019 (Zampieri et al., NAACL 2019)
- **Level A definitions (exact):**
  - "Not Offensive (NOT): Posts that do not contain offense or profanity"
  - "Offensive (OFF): Posts containing any form of non-acceptable language (profanity) or a targeted offense, which can be veiled or direct. This includes insults, threats, and posts containing profane language or swear words."
  - Source: [Zampieri et al. 2019, N19-1144](https://aclanthology.org/N19-1144.pdf)
- **Level B definition (exact):** "Untargeted (UNT): Posts containing non-targeted profanity and swearing. Posts with general profanity are not targeted, but they contain non-acceptable language." — [same](https://aclanthology.org/N19-1144.pdf)
- **Class balance and annotation.** 14,100 English tweets: 13,240 train, 860 test. NOT = 9,460; OFF = 4,640, of which OFF/UNT = 551 (524 train, 27 test). Annotated by crowd on Figure Eight with test questions. — [same, Table 3 and §3](https://aclanthology.org/N19-1144.pdf)
- **Evidence that NOT still contains swear words.** SWAD re-examined OLID tweets that contain swear words (from the noswearing.com list). 215 of them carry the OLID label NOT. — [Pamungkas et al. LREC 2020, Table 2](https://aclanthology.org/2020.lrec-1.765.pdf)
- **Mirrors.** `tweet_eval` `offensive` config labels are "0: non-offensive, 1: offensive". — [tweet_eval card @b3a375b](https://huggingface.co/datasets/cardiffnlp/tweet_eval/raw/b3a375baf0f409c77e6bc7aa35102b7b3534f8be/README.md). HF mirror christophsonntag/OLID: "annotations_creators: crowdsourced", licence "[More Information Needed]". — [OLID mirror card @37262ae](https://huggingface.co/datasets/christophsonntag/OLID/raw/37262ae493ed725b68b93aab1632b8207760dc8f/README.md)

#### 5. SWAD: Swear Words Abusiveness Dataset (Pamungkas, Basile, Patti, LREC 2020)
- **Scope and label.** "1,511 unique swear words from 1,320 tweets", taken from OLID and "filtered… based on the presence of swear words taken from www.noswearing.com". The label is whether the highlighted swear word "is used in an abusive context (by using the tag "yes")" or "does not have an abusive context". — [SWAD annotation guidelines PDF @23d3c2e](https://github.com/dadangewp/SWAD-Repository); [paper](https://aclanthology.org/2020.lrec-1.765.pdf)
- **Annotators and balance.** Three expert annotators (the authors), Cohen's kappa 0.708. 620 abusive vs 891 not-abusive. — [paper §4, Table 2](https://aclanthology.org/2020.lrec-1.765.pdf)
- **Files.** The repo ships `SWAD v1.tsv` (1,511 rows: No, Tweets, Label with `<b>` markup) and `SWAD v2.tsv` (2,577 rows). — [repo @23d3c2e](https://github.com/dadangewp/SWAD-Repository)
- **Fit for this benchmark (inference).** Every row contains a swear word by construction (lexicon filter), so SWAD offers no profanity-free negatives. The label is abusiveness, not presence.

#### 6. Vulgar Functions Twitter (Holgate et al., EMNLP 2018)
- **Scope and label.** "7,800 tweets… where all instances of vulgar words are annotated with one of six categories": aggression, emotion, emphasis, auxiliary, signal group identity, non-vulgar. Vulgar tokens were found using "the vulgarity lexicon available at www.noswearing.com". Annotation was done on Amazon Mechanical Turk by seven annotators per token. "Non-vulgar Use… The use of this word is not vulgar (e.g., named entities that involve vulgar words)" makes up 8.2%. — [Holgate et al. 2018, D18-1471](https://aclanthology.org/D18-1471.pdf)
- **Local measurement (file @477045).** The file `Vulgar_Functions_Dataset.tsv` has 8,524 rows with tweet text, target word, a `Function` code and per-function vote counts. Code counts: 0 = 1,293, 1 = 2,108, 2 = 2,561, 3 = 1,456, 4 = 399, 5 = 707. Code 5 is probably Non-vulgar (inference: 707/8,524 = 8.3%, matching the paper's 8.2%).
- **Fit for this benchmark (inference).** The Non-vulgar class is useful for lexicon false positives (a swear word used in a name or title), but there are no texts without a lexicon hit.

#### 7. Lexicons and derived resources (not sentence-labelled)
- **Surge AI "The Obscenity List".** "1600+ popular English profanities and their variations", with categories and a `severity_rating` that is the mean of 5 Surge labelers on a 1–3 scale. This is a word list, not labelled sentences. The canonical GitHub repo `github.com/surge-ai/profanity` returned HTTP 404 on 2026-09-28. An HF mirror, `mmathys/profanity`, is tagged MIT. — [mmathys/profanity card](https://huggingface.co/datasets/mmathys/profanity); [HTTP check of github.com/surge-ai/profanity (404)](https://github.com/surge-ai/profanity)
- **Surge AI toxicity sample.** 500 toxic and 500 non-toxic comments, with the note "Rather than operating under a strict definition of toxicity, we asked our team to identify comments that they personally found toxic." It is a toxicity label, not a profanity label. MIT. — [surge-ai/toxicity @ea80324](https://github.com/surge-ai/toxicity)
- **profanity-check.** A linear SVM "trained on 200k human-labeled samples of clean and profane text strings", built from Davidson et al.'s hate/offensive tweets plus the Jigsaw 2018 Kaggle data. MIT (code). The "profane" label is derived from offensive/toxic labels, not from its own profanity annotation (inference from the source list). HF `tarekziade/profanity` (Apache-2.0 tag) says only that it "is originaly from https://github.com/vzhou842/profanity-check". — [profanity-check README](https://github.com/vzhou842/profanity-check); [tarekziade/profanity](https://huggingface.co/datasets/tarekziade/profanity)
- **FrancophonIA/multilingual-swear-profanity.** A word list in fr/tr/it/ru/es/pt compiled from web pages and Wikipedia, mirrored from Kaggle. It is a lexicon with no licence tag on HF. — [card](https://huggingface.co/datasets/FrancophonIA/multilingual-swear-profanity)
- **Other HF "profanity" repos.** Many are small or undocumented (e.g. the Sowmya15/* series, Intuit-GenSRF/combined_toxicity_profanity_v2 with an empty card, BibbyResearch/ProfanityBench which is gated). None had documented provenance I could verify. — [HF search "profanity"](https://huggingface.co/datasets?search=profanity)

### Inferences
- Civil Comments `obscene` is the best-documented presence-style label. Weaknesses:
  - The attribute merges "Profanity/Obscenity" into one question.
  - Values are rater fractions, not binary, and the "hard to say / slightly" option (scale value 1) makes it unclear how those answers enter the fraction (see Gaps).
  - Positives are rare (0.44% at ≥ 0.5 in test).
- A benchmark would need a documented threshold, e.g. ≥ 0.5 by analogy with the competition's toxicity target. That threshold is a choice, not an original label.
- Aegis Profanity cannot serve as a presence label. The category exists only where a conversation was already judged unsafe, it may attach to the response rather than the prompt, and safe prompts with swear words exist ("Damn, that's crazy.").
- OLID NOT is defined as "no offense or profanity", so in principle NOT tweets are profanity-negative. In practice SWAD found 215 NOT tweets containing noswearing.com words. OFF mixes profanity with insults and threats, and only OFF/UNT (551 tweets) is "profanity without target".

### Gaps
- I could not load the Kaggle data pages (both competitions render with JavaScript). The exact Kaggle wording on raters per comment, the aggregation method (how "hard to say" = 1 is counted in the fraction), and the Kaggle rules/terms remain unverified from primary text.
- I found no primary-source annotator definition for the 2018 Wikipedia `obscene` label.
- I found no dataset with per-sentence human labels of profanity presence, balanced positives and negatives, and a permissive licence. BibbyResearch/ProfanityBench (MIT tag, 2026-05) is gated, so its label definition could not be checked.

## Which labels are really toxicity, obscenity, offensiveness or a safety-policy category?

### Takeaway
Only the Jigsaw/Civil Comments `obscene` question asks about profanity as such, and even it pairs profanity with obscenity. Aegis Profanity is a safety-policy harm category conditional on "unsafe". OLID OFF and HateXplain "offensive" are offensiveness labels. SWAD and Holgate label the function or abusiveness of swearing. Jigsaw toxic/severe_toxic, Surge toxicity and profanity-check are toxicity or offensiveness proxies.

### Cited Findings
- Jigsaw/Civil Comments ask about toxicity in a separate question ("a rude, disrespectful, unreasonable comment or otherwise somewhat likely to make a user leave a discussion"), and the guide rates profane-but-friendly text as not toxic. — [toxicity_with_subattributes.md](https://github.com/conversationai/conversationai.github.io/blob/main/crowdsourcing_annotation_schemes/toxicity_with_subattributes.md)
- The same scheme has a separate "Sexually explicit" attribute ("references to sexual acts or body parts sexual way, or other lewd content"). Example 3 is rated both Profanity/Obscenity Yes and Sexually explicit Yes, so sexual obscenity and profanity overlap in practice. — [same](https://github.com/conversationai/conversationai.github.io/blob/main/crowdsourcing_annotation_schemes/toxicity_with_subattributes.md)
- The Aegis 2.0 taxonomy lists Profanity among "Core Unsafe Categories", with "Safe" and "Needs Caution" as "Non-Unsafe Categories". — [card](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0/raw/d86bb8bedff51d25ac834ab7838f1cc61acb7a2c/README.md). The paper maps OpenAI moderation categories S, H, HR and V2 onto Profanity among others (Table 11). It notes that "content containing profane or disturbing language may also qualify as hate speech or violence". — [AEGIS2.0 paper](https://aclanthology.org/2025.naacl-long.306/)
- HateXplain is a 3-class "hate, offensive or normal" label from MTurk (about 20K posts, 3 annotators each, with rationales). The paper motivates the offensive class with words like 'nigga', 'hoe' and 'bitch' used commonly. It is an offensiveness label with no profanity definition. — [Mathew et al., arXiv:2012.10289](https://arxiv.org/abs/2012.10289); card licence cc-by-4.0 — [HF API](https://huggingface.co/api/datasets/Hate-speech-CNERG/hatexplain)
- OLID OFF covers "insults, threats, and posts containing profane language or swear words". — [N19-1144](https://aclanthology.org/N19-1144.pdf)
- SWAD's label is "abusive context of swearing… name-calling, harassment, hate speech, and bullying… with intention… to insult or abuse a target". — [SWAD guidelines](https://github.com/dadangewp/SWAD-Repository)
- Surge toxicity is "comments that they personally found toxic". — [surge-ai/toxicity](https://github.com/surge-ai/toxicity)

### Inferences
- Treat these labels as different measurements:
  - Civil Comments `obscene` → profanity/obscenity presence, as judged by humans.
  - Aegis Profanity → policy violation with profanity as the reason.
  - OLID OFF → offensiveness, with profanity included.
  - SWAD / Holgate → pragmatic function of swearing.
  - Jigsaw toxic / Surge / HateXplain → toxicity or offensiveness.
- None is interchangeable with "contains a swear word" without re-labelling.

### Gaps
- The HateXplain annotator definition of "offensive" is not quoted here. I found the paper's motivation text but not its guideline text.

## What licence and attribution each requires; can the text be redistributed?

### Takeaway
Civil Comments is the cleanest: CC0 for labels and comment text, hosted as parquet on HF, and citation of Borkan et al. 2019 is requested. Aegis 2.0 is CC-BY-4.0, so redistribution is allowed with attribution, but its prompts derive from third-party sources. Jigsaw 2018 is CC0 labels over CC-BY-SA-3.0 Wikipedia text, available only via Kaggle. Twitter-based sets (OLID, tweet_eval offensive, SWAD, Holgate) carry X/Twitter terms and undefined or GPL licences.

### Cited Findings
- **Civil Comments.** "This dataset is released under CC0, as is the underlying comment text." Citation is Borkan et al. 2019, "Nuanced Metrics for Measuring Unintended Bias with Real Data for Text Classification", arXiv:1903.04561. — [google/civil_comments card](https://huggingface.co/datasets/google/civil_comments/raw/f2970eb3a55777454c94069077cc8d9b5866312d/README.md). TFDS lists the licence as CC0, current version 1.2.4. — [TFDS](https://www.tensorflow.org/datasets/catalog/civil_comments). The HF jigsaw_unintended_bias card says "No citation is available for this dataset, though you may link to the kaggle competition". — [card](https://huggingface.co/datasets/google/jigsaw_unintended_bias/raw/d46022c9df7c8b74ba52876f314f81ef60fa1727/README.md)
- **Jigsaw 2018.** "The "Toxic Comment Classification" dataset is released under [CC0], with the underlying comment text being governed by Wikipedia's [CC-SA-3.0]." Citation: "No citation information." Data is not hosted on HF, only a loader script. — [google/jigsaw_toxicity_pred card](https://huggingface.co/datasets/google/jigsaw_toxicity_pred/raw/9fca5f507ac11049ff34bb13c8546b01afcedbbd/README.md); [HF API](https://huggingface.co/api/datasets/google/jigsaw_toxicity_pred)
- **Aegis 2.0.** "License: CC-BY-4.0". Citation: Ghosh et al., "AEGIS2.0: A Diverse AI Safety Dataset and Risks Taxonomy for Alignment of LLM Guardrails", NAACL 2025, pp. 5992–6026, doi 10.18653/v1/2025.naacl-long.306. The card also states the data "are not intended for training dialogue agents". Suicide Detection rows are "REDACTED" and not distributed. — [card @d86bb8b](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0/raw/d86bb8bedff51d25ac834ab7838f1cc61acb7a2c/README.md)
- **OffensEval via tweet_eval.** "All of the datasets require complying with Twitter Terms Of Service and Twitter API Terms Of Service", and for "Offensive: Undefined". — [tweet_eval card](https://huggingface.co/datasets/cardiffnlp/tweet_eval/raw/b3a375baf0f409c77e6bc7aa35102b7b3534f8be/README.md). The HF OLID mirror's licence is "[More Information Needed]". — [OLID mirror](https://huggingface.co/datasets/christophsonntag/OLID/raw/37262ae493ed725b68b93aab1632b8207760dc8f/README.md)
- **SWAD.** GPL-3.0 (GitHub licence), tweets included as text. — [GitHub API / repo](https://github.com/dadangewp/SWAD-Repository)
- **Holgate.** No licence file. The README says "Use of the data presented here must abide by the Twitter Terms of Service and Developer Policy". Citation is holgate2018vulgar, EMNLP 2018, pp. 4405–4414. — [VulgarFunctionsTwitter](https://github.com/ericholgate/VulgarFunctionsTwitter)
- **HateXplain.** HF tag cc-by-4.0. — [HF API](https://huggingface.co/api/datasets/Hate-speech-CNERG/hatexplain)
- **Surge lists.** MIT (surge-ai/toxicity LICENSE; mmathys/profanity mirror tag). The canonical profanity repo is now 404. — [surge-ai/toxicity](https://github.com/surge-ai/toxicity); [mmathys/profanity](https://huggingface.co/datasets/mmathys/profanity)

### Inferences
- For a public benchmark that redistributes text rows, Civil Comments (CC0) is the only candidate whose text and labels are both clearly redistributable without attribution conditions. Citing Borkan et al. 2019 is still good practice.
- Aegis 2.0 rows can be redistributed under CC-BY-4.0 with attribution. Its prompts, however, originate from HH-RLHF, DAN and AART, whose own terms are not re-verified here.
- Jigsaw 2018 rows carry the Wikipedia CC-BY-SA-3.0 ShareAlike obligation. Twitter-derived sets are best redistributed as IDs, or checked against current X terms before shipping text.
- A GPL-3.0 dataset (SWAD) is an unusual licence for data. Check copyleft implications before bundling.

### Gaps
- I did not verify the Kaggle competition rules for either Jigsaw competition from primary text (page not renderable). Whether they add usage restrictions beyond the CC0 statement is unconfirmed.
- I did not verify the current X/Twitter developer terms for tweet-text redistribution in this pass.
- The licence terms of the Aegis upstream prompt sources (Anthropic HH-RLHF, DAN jailbreak_llms, AART on Kaggle) were not checked.
