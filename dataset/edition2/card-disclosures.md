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

515 of the 2,091 content test rows come from datasets that companies building safety models published themselves. 311 are from NVIDIA's Aegis 2.0 and 204 are from OpenAI's moderation evaluation set. A vendor may have trained or tuned its own models on that data, so every such row carries `vendor_owned` and its vendor name, and you can score with or without them. OpenAI has a model on the leaderboard, gpt-6-luna, and OpenAI may have trained or tuned it on its own moderation set. For that reason the leaderboard reports every system's content score twice, once on all rows and once without the OpenAI rows. NVIDIA has no model on the leaderboard. We also removed every row whose text appears in a benchmarked model's training data or in a benchmarked vendor's published material, such as TypeSafe's guardrails cookbook. EXCLUDED.jsonl lists each one with its reason.

### Who labelled what

The content second-label sample (400 rows, drawn blind and stratified) was labelled by the project lead personally, with an AI assistant. The project lead also decided every disputed row the same way, with the same assistant. `content-label-agreement.json` gives the agreement rate.

### Some labels were corrected after the benchmark runs

After the 12 systems ran, the project lead reviewed every content and prompt-attack test row that at least 11 of them got wrong, 379 rows in all, public and held back. The review started from an AI-assisted draft. 184 labels were right. 117 were wrong and are corrected here, and each corrected row carries the change and a short reason in `attribute.e2.correction`. 78 rows were too ambiguous to label either way, so we removed them; EXCLUDED.jsonl lists the public ones. We only looked at rows most systems missed, so these changes can only raise the scores of the systems that got those rows wrong. The leaderboard publishes every system's scores from before the review next to the new ones.

### Prompt-attack labels have a sealed AI second label, not a person's

The prompt-attack suite's second label comes from a model, not a person. A sealed model labelled a 400-row blind sample of it with no tools and no file access, given only the labelling policy and the rows. We publish its agreement rate. Treat it as an AI cross-check, not a human review.

### Injection and leakage have fewer attack rows than the other prompt-attack subtasks

Injection has 143 attack and 174 benign public test rows, and leakage has 247 attack rows. Every other subtask has at least 250 of each class. Once we removed prompts that appear in benchmarked models' training data, few real injection prompts with same-source benign messages were left, and the label review described above corrected or removed some more attack rows. The injection and leakage scores have wider intervals for that reason.
