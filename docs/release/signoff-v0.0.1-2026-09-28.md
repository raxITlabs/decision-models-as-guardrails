# Gold Rails v0.0.1: sign-off packet

Prepared 28 September 2026 from private commit `091150a`. The results site stays local. Nothing below is uploaded,
pushed or tagged until you approve it. No scores, thresholds, rows or labels change in any step.

## 1. What you are signing

| Item | Exact version | sha256 (first 16) | Commit |
|---|---|---|---|
| Evaluation contract | `benchmark/contracts/v1.1.json`, version `v1.1-draft`, contract hash `463b3349d8c7de6e` | `0f5b448fcdd16074` | `5e7874a` |
| Contract amendment A (AI reference labels) | `benchmark/contracts/v1.1-amendment-ai-reference.md` | `2c959280723ecfb0` | `5ba8173` |
| Analysis approval | `analysis-approval-4.json`: scoring code `92a74bcc31c20f5b` (commit `0744223`), contract hash `463b3349d8c7de6e`, primary manifest `0bc22cbc93f81f45` | `9b3664bae0fb9f22` | `ed79005` |
| Evaluator in use | `benchmark/goldrails_bench/leaderboard.py` (same hash approval 4 names) | `92a74bcc31c20f5b` | |
| Results | `leaderboard-v1.3.json`: Jev 91.9, Bedrock 81.1, gap 10.8 [8.4, 13.2] | `854e4377ad098786` | `3f4ef15` |
| Dataset | internal release v1.3 (release sha `818c9e00f9f84595`, manifest `4c3a7bc5adaa543c`), subset first-benchmark-v1.3 (`90ba5867cc74462e`) | | `bb064b1` |
| Freeze manifests | primary `0bc22cbc93f8` (`6f5390a`); ext 1 `20acbdb040ff` (`3c88be6`); ext 2 `1cd7bab4ca81` (`a08a3b3`); ext 3 `572c327a4bcb` (`cc7918e`); ext 4 `2875cb18b2d9` (`860bde9`) | | |
| Declarations | `implementations.json` (`d9f0f0f`, 23 Sep 04:03 UTC) to `-v1.1` (`5e7874a`, 23 Sep 12:10) to `-v1.3` (`bb064b1`, 28 Sep 07:23) | | |
| Freeze validation | `extension-freeze-validation.json`: 50 of 50 arms declared and frozen before their own first test call | | `0555f2d` |
| Label review | `dataset/release/v1.3/owner-review-confirmation.json`: project-owner review, not independent adjudication | | `c37cb42` |

## 2. The four blockers and what closes each

1. **Contract is a draft.** Signing changes the contract's `status` and `version`. The contract hash covers those
   fields, so it changes too, and approval 4 would no longer match. Closing this takes a signed contract v1.1 plus an
   approval 5 that names the same scoring code (`92a74bcc`) and the signed contract's hash. I then rebuild
   leaderboard v1.3 with no model calls and check the scores are identical.
2. **Approval 4 is unconfirmed.** I recorded it from your written instructions of 23 September. Approval 5 above
   replaces it with your confirmation of the exact hashes.
3. **and 4. Two pre-registration blockers.** The evaluator reads the declaration chain one link deep, so it compares
   the 23 and 28 September files with test calls from 23 September. The per-arm check passes for all 50 arms. One
   caveat: the word-filter composition in `-v1.1` was declared after the custom-word arms ran. It averages their
   frozen scores and changes none. If you accept the per-arm check, approval 5 records that acceptance. The evaluator
   still prints both lines; the page would then list them as accepted by you.

Decision: sign contract v1.1 and approve approval 5 on these terms? Or keep the results interim.

## 3. Proposed update to Hugging Face v0.0.1

- **Destination.** `huggingface.co/datasets/raxITLabs/goldrails`, public. Its current revision is
  `3e3ed7f3bbed83b6d12316d2b5b396acdfc40873`, tag `v0.0.1`, internal release v1.2, 8,565 rows.
- **Package.** `dataset/publish/v1.3-full`, uploaded to `main` as one commit. It holds 8,807 rows in 15 data
  files. The staging check reproduces all 19,735 benchmark inputs from ledgers and finds 0 problems.
- **Row changes, by canonical row hash.** Profanity gains 500 Civil Comments rows (`civil_comments_obscene`,
  CC0-1.0) and loses 258 lexicon-selected rows. The other 8,307 rows are identical. All 15 files are rewritten
  anyway, because each row's `provenance.imported_at` build timestamp changed. That field is outside the hash.
- **Card and sidecars.** The card reads "Gold Rails v0.0.1, revised 28 September 2026" and names the earlier
  revision. New files: `CHANGELOG.md`, with both revisions, both release hashes and the row table, and
  `LABEL_REVIEW.json`. Updated files: `KNOWN_ISSUES.md` (the label-policy metadata correction, profanity notes) and
  `RIGHTS.md` (your 25 September statement, carried forward, plus the new CC0 source).
- **Versioning.** The public version stays v0.0.1, with no new version label. I propose leaving tag `v0.0.1` on
  `3e3ed7f3` so results from the first upload stay traceable. The new revision is known by its commit hash, which I
  record in `dataset/release/v1.3/publication.json` after upload. The page then links that exact revision.
- **Before upload.** Set the card's code reference to the GitHub export commit from section 4. It currently says
  `main`, and the staging report flags that as pending.

Decision: approve this upload? Keep tag `v0.0.1` on the first revision (recommended), or move it?

## 4. GitHub export

- **Destination.** `github.com/raxITlabs/goldrails`. It is private today, with tag `v0.0.1` on `26b578fe`, the
  export of private commit `2eb75ed`.
- **Proposed.** One new commit on `main`, exported from private commit `091150a` or later. The dry run exported 382
  allowlisted files, the withheld-text scan found 0 problems, and a clean install passes 301 tests with 4 skipped.
  Tag `v0.0.1` does not move.
- **Visibility.** The public dataset card links this repository. While the repository stays private, readers cannot
  open the code the card cites. The publication record has listed this as open since the first upload.

Decision: keep private or make public? Approve the push?

## 5. Order after sign-off

1. Record the signed contract and approval 5. Rebuild leaderboard v1.3 and confirm identical scores; page check.
2. Export and push the code commit to GitHub, with the visibility you chose.
3. Re-stage the Hugging Face package with that commit as the code reference, then upload it to `main`.
4. Record the new Hub revision in `dataset/release/v1.3/publication.json` and point the local page at it.

The results site stays local throughout.
