# Edition 2 grounding: sources

Status: candidate rows, first labeller done, blind second labeller done for the first 780 rows and pending for the
68 rows added on 3 October. Built 2026-10-02/03.

Edition 1 grounding was RAGTruth only, and grounding drives half of Jev's lead. Edition 2 keeps RAGTruth and adds 848
rows from three other sources, balanced per source, split and class. Test alone is 275 unsupported and 275 supported
rows before RAGTruth is counted, so the suite meets the 250/250 target without it.

| Source | Rows | Test | Tune | Private | Label basis | Upstream split |
|---|---|---|---|---|---|---|
| FaithDial | 260 | 168 | 40 | 52 | human (crowd BEGIN tags) | test |
| SummEdits | 392 | 254 | 58 | 80 | human (annotators per edit) | none, the whole release is the benchmark |
| RAGBench | 196 | 128 | 30 | 38 | LLM (GPT-4-turbo), review_status candidate | test |

Every cell is half "yes" (unsupported) and half "no". Private rows carry `split: test, visibility: heldout`.

## Sources used

**FaithDial** (McGill-NLP/FaithDial, MIT, HF revision `7a414e8`). Wizard-of-Wikipedia replies with one knowledge
sentence as the source and the seeker's last turn as the query; earlier turns go in `state.context`. A positive is an
unedited reply whose BEGIN tags are all Hallucination and whose VRM tags include Edification, so it makes an objective
claim. A negative is a reply annotators kept unedited with BEGIN all Entailment. The rewritten faithful replies are not
used, so the two classes are both raw Wizard-of-Wikipedia text and no turn appears twice. Group: one conversation, merged
with any conversation sharing a knowledge sentence. Knowledge sentences are Wikipedia text (CC-BY-SA).

**SummEdits** (Salesforce/summedits, CC-BY-4.0, HF revision `ce0c479`). A document, a verified seed summary, and LLM
edits that annotators labelled consistent (1) or inconsistent (0). Only domains whose documents can be passed on are
loaded: BillSum (US bills), QMSum (MIT; AMI/ICSI transcripts CC-BY-4.0), SciTLDR (Apache-2.0), Shakespeare, and the
synthetic sales call and sales email documents SummEdits wrote. News, podcasts, SAMSum (CC-BY-NC-ND) and ECTSum are out.
Documents over 12,000 characters are dropped. Group: one document, at most two rows per class per document. The query is
"Summarise the source text.", as for RAGTruth's Summary rows.

**RAGBench** (galileo-ai/ragbench, CC-BY-4.0, HF revision `97808f3`), test split of the HAGRID, HotpotQA and PubMedQA
subsets. Retrieved documents joined as the source, the question as the query, unsupported sentences as spans. These
labels come from GPT-4-turbo, not people, so `label_basis` is `llm` and `review_status` is `candidate`. A row is kept
only when the LLM label agrees with both automatic scores RAGBench ships (RAGAS faithfulness and TruLens groundedness:
below 0.5 for a positive, at least 0.99 for a negative). The class quota is split by subset (45% PubMedQA, 40% HAGRID,
15% HotpotQA) because PubMedQA replies are mostly unsupported and HAGRID's mostly supported; unsplit, the subset would
predict the label. HotpotQA and HAGRID ran short of positives, so the final mix is 48 PubMedQA, 32 HAGRID and 10
HotpotQA positives against 40, 36 and 14 negatives.

## Considered and not used

| Candidate | Why not |
|---|---|
| LLM-AggreFact | CC-BY-ND (no derivatives), gated, and one of its subsets is RAGTruth |
| HaluBench (Patronus) | CC-BY-NC-2.0, and it embeds RAGTruth and HaluEval |
| HaluEval QA | Labels by construction; right answers are short spans and hallucinated ones full sentences, so length gives the label away |
| WikiBio GPT-3 (SelfCheckGPT) | Annotators judged accuracy against world knowledge, not against the Wikipedia paragraph, so "accurate" is not "grounded"; also eval-only and positive-heavy |
| XSumFaith, FRANK, FactCC, SummEval | BBC and CNN/DailyMail articles; same rights problem that keeps RAGTruth ids-only |
| DelucionQA, TofuEval, ExpertQA, WiCE | Non-commercial terms or web-scraped evidence with unchecked rights |
| RAGBench MS MARCO, CovidQA, TechQA, EManual, FinQA, TAT-QA, CUAD | MS MARCO is non-commercial and RAGTruth's QA source; the others have few usable positives or documents far longer than everything else |

## First labeller

I (Claude, an AI) read every selected row against its source before it was kept. FaithDial and RAGBench rows were
read in full. SummEdits rows were checked by reading the edit against the verified seed summary (the diff is in each
row's `label_rationale`), not by rereading the whole document. A row where my label differed from the source label, or
that I marked borderline, was dropped and replaced by another row I then read. All decisions are in
`first_labels.jsonl` (1,041 rows read) and the drops in `exclusions.jsonl`.

Agreement with the source label, rows read:

| Source, class | Agree | Disagree | Borderline, dropped |
|---|---|---|---|
| FaithDial, unsupported | 120 | 36 | 67 |
| FaithDial, supported | 138 | 4 | 8 |
| SummEdits, unsupported | 181 | 17 | 9 |
| SummEdits, supported | 180 | 3 | 4 |
| RAGBench, unsupported | 106 | 10 | 31 |
| RAGBench, supported | 104 | 13 | 10 |

FaithDial's Hallucination tag is the weak point: only 54% of the tagged replies I read were clearly unsupported. Many
are paraphrases of the knowledge sentence, opinions, or chit-chat. The SummEdits disagreements are mostly edits that
only swap synonyms yet were labelled inconsistent. The RAGBench disagreements are mostly PubMedQA replies that answer
"Yes, ..." when the documents give only a study's aim, which GPT-4 sometimes passed.

What this means for scoring:

- Dropping rows I found ambiguous makes the set cleaner and somewhat easier than the raw sources. A model whose judgement
  resembles mine gains from the filter. The blind second labeller and the owner review are the check on that.
- Unsupported replies are longer than supported ones in FaithDial (median 104 vs 78 characters) and RAGBench. That is
  partly inherent, since a longer reply has more room for an unsupported claim, but a length-only baseline should be
  reported beside the suite.
- All three sources are public and may be in some models' training data. The private share protects against tuning on
  our released files, not against upstream contamination.

## 3 October: quota raise for the test floor

The second label disagreed on 34 rows, and the build holds a disputed row out of every split until an owner ruling
settles it. With those rows out, the public test split had 242 unsupported and 245 supported rows, under the 250 floor.
I raised the per-class quotas (FaithDial 120 to 130, SummEdits 180 to 196, RAGBench 90 to 98). The selection now takes
the previous build's rows first in every cell, so the raise only adds rows: all 780 earlier rows keep their ids,
splits and groups.

The builder picked 68 new rows (22 per class in test). 19 of them I had read on 2 October and kept outside the quota.
I read the other 49, plus 11 replacements, on 3 October under owner ruling 4: any claim the source does not support
counts as unsupported, hedged or not, and an omission is not a grounding failure. The ruling decided three rows. A RAGBench
reply that closes with "this suggests cardiologists may not always follow guidelines" is unsupported, because no
document mentions guidelines, so it disagrees with the RAGBench "supported" label and is dropped. Two SummEdits edits
that only delete a qualifier ("a correct output" to "an output", "the first verification" to "evidence") are omissions,
so they are supported, disagree with the SummEdits "inconsistent" label and are dropped. Two more disagreed with the
source for ordinary reasons (a synonym swap SummEdits called inconsistent, a FaithDial reply that only restates the
knowledge), and six were borderline and are excluded. All 60 decisions are in `first_labels.jsonl` with labeller `first labeller (Claude, AI), 2026-10-03,
owner ruling 4 applied`.

After the build holds out the disputed rows awaiting the owner and applies the resolved ones (`resolutions.jsonl`),
the public test split has 272 unsupported and 267 supported rows from three sources, none of them RAGTruth. The 68 new
rows have no second label yet; they are in the blind packet with the rest.

## Second labeller

`packet/` holds a blind packet in the `dataset/frozen/review-packets` format: `packet.md` and `labels.template.jsonl`
with one `unsupported` question per row, the e2 question set's definition, and no source names, labels or rationales.
`packet/_lead/e2-grounding.key.json` maps review ids to record ids; keep it from the reviewer. The packet covers all 848
rows, including private ones.

## Rebuild

```
uv run python -m goldrails_dataset.sources.e2_grounding --v1-build <path>/dataset/release/v1.0/build [--v1-build ...]
```

This downloads the three sources at their pinned revisions, applies the filters, the overlap check (ids and normalised
reply text against the v1 builds passed in, `dataset/samples`, every ledger under `benchmark/results`, and
`dataset/frozen/examined-ids.txt`), the first-labeller decisions, the group split and the quotas. It rewrites
`candidates.jsonl`, `counts.json`, `exclusions.jsonl` and the packet. The committed files were built against the v1.0,
v1.1-ai, v1.2 and v1.3 builds (10,209 ids, 10,019 texts); none overlap.
