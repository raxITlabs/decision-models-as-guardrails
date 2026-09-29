# Archived: "What our benchmark proves" feature map (28 September 2026)

Superseded. Kept unchanged as a record of the review it summarised. Not part of the results site.

The map recommended keeping the Civil Comments obscenity task as an auxiliary evaluation beside the managed
profanity score, and waiting for two blind human reviewers before treating denied topics as reviewed. The project
owner decided otherwise later on 28 September 2026:

- Profanity is scored as "Profanity or obscenity — Civil Comments" in leaderboard v1.3, described as performance
  against an external dataset, not identical implementation or vocabulary.
- The project owner reviewed all current labels (`dataset/release/v1.3/owner-review-confirmation.json`). This is
  owner review, not independent two-reviewer adjudication. The blind packet for the 73 denied-topics test rows stays
  available.

Its coverage map (untested masking, span fidelity, grounding relevance, indirect attacks, Automated Reasoning, images,
broad multilingual text) carried into the "Not tested" list on the results page.

It was served from `site/leaderboard/` with an identical copy in `docs/reports/`; both are replaced by this archive.
