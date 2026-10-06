<!--
Disclosures for the dataset card. The publisher copies everything below this comment into README.md under
"Disclosures". Staging fails while any [bracket] placeholder remains.
-->

### Independence

raxIT Labs has no relationship with TypeSafe or with any other company whose model is on the leaderboard. This is independent research. No vendor funded it, and none saw the rows, the questions or the results before we published them.

### The question format comes from Jev

Every model answers the same yes/no questions, written in the format Jev's API takes: a question, its answer options and the text to judge. Jev was trained for this format. The other models get it through our adapters, and some of them were trained on prompts that look quite different. That gives Jev a home advantage, and we can't remove it without picking a format that favours someone else. We first wrote some of these questions while checking Jev's answers on a small set of rows outside the test split, so the wording may suit Jev better than it suits other models. Every model gets the same question set, frozen before scoring.

### The 0.5 rule favours calibrated models, mostly Jev

The headline score uses one fixed rule for every model. A probability of 0.5 or more on a question counts as yes. Nobody gets a threshold tuned for them, because that is how a model behaves when you switch it on, and it is the only rule that stays fair across dozens of models. The catch is that the rule rewards models whose probabilities already fit this question format, and that is mostly Jev. When we let each model choose its own threshold in internal testing, the gap between Jev and the next model shrank. The leaderboard also reports AUROC and the catch rate at a 5% false-block rate. Neither depends on the threshold, so read them next to the headline score.

### Some rows come from vendors' own datasets

511 of the 2,088 content test rows come from datasets that companies building safety models published themselves. 311 are from NVIDIA's Aegis 2.0 and 200 are from OpenAI's moderation evaluation set. A vendor may have trained or tuned its own models on that data, so every such row carries `vendor_owned` and its vendor name, and you can score with or without them. Neither NVIDIA nor OpenAI has a model on the leaderboard today. We also removed every row whose text appears in a benchmarked model's training data or in a benchmarked vendor's published material, such as TypeSafe's guardrails cookbook. EXCLUDED.jsonl lists each one with its reason.

### Prompt-attack labels had an AI second reader, not a person

The prompt-attack suite's second label comes from a model, not a person. A separate model labelled a 400-row blind sample of it with no tools and no file access, given only the labelling policy and the rows. We publish its agreement rate. Treat it as an AI cross-check, not a human review.

### Injection has fewer rows than the other prompt-attack subtasks

Injection has 151 attack and 167 benign public test rows. Every other subtask has at least 250 of each. Once we removed prompts that appear in benchmarked models' training data, few real injection prompts with same-source benign messages were left. The injection score's interval is wider for that reason.
