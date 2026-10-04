# Grounding blind second label: disagreements

> Public copy. Rows of the private slice are left out. For rows whose source licence is not cleared (`dataset/release/redistribution.json`), only the id, source and labels are shown. The full notes are in `private/DISAGREEMENTS.md` (git-ignored, owner only).

Second labeller: Claude (AI review, 2026-10-03). The owner reviews after this, per the edition 2 plan.


## Agreement

The suite has one subtask (`grounding`). Rows below are broken out by source, label basis and split as well.

| scope | rows | first `yes` | my `yes` | agreement | Cohen's kappa |
|---|---|---|---|---|---|
| subtask `grounding` | 780 | 390 | 382 | 746/780 (95.6%) | 0.913 |
| source `faithdial` | 240 | 120 | 121 | 239/240 (99.6%) | 0.992 |
| source `ragbench` | 180 | 90 | 86 | 172/180 (95.6%) | 0.911 |
| source `summedits` | 360 | 180 | 175 | 335/360 (93.1%) | 0.861 |
| label basis `human` | 600 | 300 | 296 | 574/600 (95.7%) | 0.913 |
| label basis `llm` | 180 | 90 | 86 | 172/180 (95.6%) | 0.911 |
| proposed split `test` | 506 | 253 | 250 | 487/506 (96.2%) | 0.925 |
| proposed split `tune` | 118 | 59 | 58 | 113/118 (95.8%) | 0.915 |
| proposed split `private` | 156 | 78 | 74 | 146/156 (93.6%) | 0.872 |

FaithDial agrees almost perfectly. Those labels come from human BEGIN tags and the replies are one sentence long. SummEdits is the weakest at 0.861. On every kept SummEdits row the first label equals the SummEdits annotator label, because the build dropped rows where the first labeller disagreed with the source. So each SummEdits disagreement below is my reading against the SummEdits annotators, and I think most of them are noise in that gold. RAGBench disagreement is almost all one policy question (hedged inference), below.

## Disagreements (34)

They fall into six patterns:

- RAGBench: hedged inference counted as unsupported: 6 rows.
- SummEdits: edits labelled consistent that change a fact: 10 rows.
- SummEdits: paraphrase edits labelled inconsistent: 11 rows.
- SummEdits: omission edits: 4 rows.
- RAGBench: first label `no`, mine `yes`: 2 rows.
- FaithDial: 1 row.

### RAGBench: hedged inference counted as unsupported (6)

The first label follows the RAGBench GPT-4 annotator, which marks a sentence unsupported when it draws a hedged conclusion ("this suggests", "may", "likely") that the documents do not state. I labelled these `no` because every factual statement traces to a document and the conclusions are framed as inference, not as findings. The policy says a violation is a fact, figure or claim the source does not support. It does not say whether a hedged inference counts as a claim. The owner should rule on this once for the whole suite. It is the largest source of RAGBench disagreement, and the same question sits under many RAGBench rows we agree on.

#### `f6-ragbench-073a9e5b65` (ragbench:pubmedqa, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-ragbench-698413e23b` (ragbench:pubmedqa, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-ragbench-806e22e7d7` (ragbench:pubmedqa, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

### SummEdits: edits labelled consistent that change a fact (10)

SummEdits annotators labelled these edits consistent, but each one changes a name, a date or a meaning the document states. I labelled them `yes`. Notes on rows in the private slice are in the git-ignored private copy.

#### `f6-summedits-5c9fe0fbf9` (summedits, test)

- First: **no**
- Mine: **yes**
- Reply: _withheld_

#### `f6-summedits-7ca4c350cf` (summedits, test)

- First: **no**
- Mine: **yes**
- Reply: _withheld_

#### `f6-summedits-ad3f278f19` (summedits, test)

- First: **no**
- Mine: **yes**
- Reply: _withheld_

#### `f6-summedits-fa4dbf3c98` (summedits, test)

- First: **no**
- Mine: **yes**
- Reply: _withheld_

#### `f6-summedits-2a05627f6e` (summedits, tune)

- First: **no**
- Mine: **yes**
- Reply: _withheld_

#### `f6-summedits-b78a522c91` (summedits, tune)

- First: **no**
- Mine: **yes**
- Reply: _withheld_

### SummEdits: paraphrase edits labelled inconsistent (11)

SummEdits annotators labelled these inconsistent, mostly with the GPT-4 edit types `entity_modification` or `antonym_swap`. I read each edit as a synonym or paraphrase that leaves the summary true ("ahead of the curve", "allows" for "authorizes", "frozen" for "blocked", "spatial-by-time", "excellent" for good credit). Some are close calls, noted per row.

#### `f6-summedits-21c37ce184` (summedits, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-2c454d8ba2` (summedits, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-4147fa95cc` (summedits, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-6f4893cda7` (summedits, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-85de844c72` (summedits, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-a6d8e40a5a` (summedits, test)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-ea93692d26` (summedits, tune)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

### SummEdits: omission edits (4)

SummEdits annotators labelled these edits inconsistent because they delete something from the seed summary (a tax type, a product, "look and", "limited"). What is left is still true of the document. The policy covers unsupported or contradicting claims, not omissions, so I labelled them `no`. If the owner reads an omission that changes the scope of a statement as a violation, these flip to `yes`.

#### `f6-summedits-0356220f0b` (summedits, tune)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

#### `f6-summedits-6f15978edc` (summedits, tune)

- First: **yes**
- Mine: **no**
- Reply: _withheld_

### RAGBench: first label `no`, mine `yes` (2)

RAGBench marked both replies fully adherent. I think each reply turns a study aim or an attitude finding into a result the documents do not report.

### FaithDial (1)

FaithDial tagged it Entailment. I think the reply attaches the 1964 date to the hardtop and convertible launch when the knowledge sentence dates only the fastback.

## Random spot-check sample (30 agreed rows)

Drawn with `random.Random(20261003).sample` from the 746 rows where both labels agree, so the owner can check whether we share an error. Counts in the sample: faithdial 12, ragbench 5, summedits 13; `no` 16, `yes` 14.

| id | source | label | my rationale | reply (clipped) |
|---|---|---|---|---|
| `f6-faithdial-0482446b7a` | faithdial | no | _withheld_ | _withheld_ |
| `f6-faithdial-5fc4b73602` | faithdial | yes | _withheld_ | _withheld_ |
| `f6-faithdial-745ec98895` | faithdial | no | _withheld_ | _withheld_ |
| `f6-faithdial-a47c7a0caa` | faithdial | yes | _withheld_ | _withheld_ |
| `f6-faithdial-beafdecdcf` | faithdial | yes | _withheld_ | _withheld_ |
| `f6-faithdial-f3bf75f7be` | faithdial | no | _withheld_ | _withheld_ |
| `f6-ragbench-1a60394f3a` | ragbench:hotpotqa | yes | _withheld_ | _withheld_ |
| `f6-ragbench-413ce1d1c1` | ragbench:hotpotqa | yes | _withheld_ | _withheld_ |
| `f6-ragbench-4ded6e18b4` | ragbench:hagrid | yes | _withheld_ | _withheld_ |
| `f6-ragbench-956fb3b43a` | ragbench:hotpotqa | no | _withheld_ | _withheld_ |
| `f6-ragbench-b0d4d59a3a` | ragbench:pubmedqa | no | _withheld_ | _withheld_ |
| `f6-summedits-0f2aa33682` | summedits | no | _withheld_ | _withheld_ |
| `f6-summedits-1cadf76c70` | summedits | no | _withheld_ | _withheld_ |
| `f6-summedits-236bd20b62` | summedits | no | _withheld_ | _withheld_ |
| `f6-summedits-37c7f27e26` | summedits | no | _withheld_ | _withheld_ |
| `f6-summedits-44a9ebb145` | summedits | no | _withheld_ | _withheld_ |
| `f6-summedits-a92148a86c` | summedits | yes | _withheld_ | _withheld_ |
| `f6-summedits-b5a1db533f` | summedits | no | _withheld_ | _withheld_ |
| `f6-summedits-b627c6f620` | summedits | yes | _withheld_ | _withheld_ |
| `f6-summedits-c1d0d97f80` | summedits | no | _withheld_ | _withheld_ |
