# 24. Bias data: sources, licences and what each release option ships

The Bias config holds three tracks. Their sources and terms differ, so the choice is made per track. Nothing here is
legal advice. It sets out what each row is built from, so the owner can decide.

| Track | Built from | Licence of the source | Current release mode (`dataset/release/redistribution.json`) |
|---|---|---|---|
| B1 identity-mention error rates | Civil Comments comments and rater fractions, read from the third-party parquet mirror `pietrolesci/civilcomments-wilds` | CC0-1.0 (Jigsaw, WILDS); the mirror declares no licence and has not been checked row by row against the CodaLab original | ids-only |
| B2 counterfactual pairs, 16 of 22 | A Civil Comments base comment (CC0) with one identity descriptor swapped for another from HolisticBias | Base text CC0; HolisticBias v1.1 dataset CC-BY-SA-4.0 (code MIT) | ids-only |
| B2 counterfactual pairs, 6 of 22 | HolisticBias template sentences with descriptors filled in | CC-BY-SA-4.0 | ids-only |

Those are the 22 candidate pairs. Review kept 8 pairs (16 rows) in v1.1-ai: 6 HolisticBias template pairs and 2 Civil Comments pairs. Four are test pairs in 3 groups; four are tuning pairs.
| B3 BBQ | BBQ questions and answers | CC-BY-4.0 | text |
| B3 discrim-eval | Anthropic discrim-eval prompts | CC-BY-4.0 | text |

**CC-BY-SA-4.0 obligations.** Anyone who shares an adapted work must credit the source, link the licence, say what
changed, and license the adaptation under CC-BY-SA-4.0 or a compatible licence. The six template-based pairs are
adaptations of CC-BY-SA text. For the 16 comment-based pairs the question is narrower: each carries one descriptor word
from the HolisticBias list inside a CC0 comment. Whether one list word makes the comment an adaptation is a judgment for
the owner, and the conservative answer is yes.

## The two options

**A. Publish B2 text under CC-BY-SA-4.0.** Credit HolisticBias (Meta, v1.1, commit 0ec714eb) and link the licence.
State the change: one descriptor swapped per pair, listed in each row's `transforms`. Put the B2 files under
CC-BY-SA-4.0. B1 stays ids-only until the mirror is verified. B3 ships text with CC-BY attribution.

**B. Ship B2 ids-only.** No pair text is published. Users rebuild the text locally from the pinned sources with
`uv run python -m goldrails_dataset.bias_pairs`. Ids-only is not a clean exemption, because the rows still carry:

- the identity descriptor words (such as "Catholic" and "Sikh") and their character offsets in `attribute` and
  `provenance.notes`;
- the Civil Comments rater fractions, which are CC0;
- our review labels and the base-row ids.

Those are single words, positions and labels, not text. They still come from the HolisticBias list, so option B also
credits HolisticBias in the dataset card.

Until the owner chooses, the release keeps B2 ids-only (option B) and credits HolisticBias. The B3 text and its
CC-BY attribution are unaffected by the choice.
