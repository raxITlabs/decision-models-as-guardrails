# Release handover: decision-models-as-guardrails 1.0.0

Written 6 October 2026, the night before release. Everything below is committed locally on `main`. Nothing is pushed,
nothing new is on the Hugging Face Hub, and the GPU VM is TERMINATED.

## Final results (12 systems, six suites, contract v2.0 as amended)

The numbers are held back until release day and are not in the tracked tree. They live in the git-ignored
`benchmark/results/final/`: `leaderboard.json`, `README.md`, `plots/`, and `ledgers/` with the per-row ledgers and
run logs of the three runs behind them (`main-run/`: content, denied topics, word filters, PII and grounding for
eleven systems, 5 October; `prompt-attacks/`: the r26 prompt-attack suite for the same eleven, 6 October;
`gpt-6-luna/`: all six suites for OpenAI's Decisions API, 7 October). Each run folder keeps its raw ledgers, with
unpublished-slice ids, in its own `private/`. A copy of that folder is in the backups.

`uv run --with scikit-learn python benchmark/runs/e2_openai_run.py score --source local` rebuilds `leaderboard.json`
from those ledgers, the three freeze manifests in `benchmark/subsets/edition2/` and the contract, and
`uv run --with matplotlib python benchmark/runs/e2_final_plots.py` redraws the plots. The leaderboard reports
`valid_for_publication: true` with no blocker, and the privacy check passes. There is no latency in it (ruling 22).
gpt-6-luna answered 10 rows with a `refusal`; they count as wrong.

## Evidence trail

- Rulings 19–29: `docs/benchmark/29-owner-rulings-2026-10-03.md`.
- Prompt-attack suite: `dataset/edition2/r26/prompt_attacks/` (DESIGN.md, gate.json, counts.json,
  label-agreement.json: sealed AI second label, 95.0% agreement, kappa 0.88, n = 400).
- Freeze before calls: `benchmark/subsets/edition2/freeze-manifest-prompt-attacks-r26.json`.
- Disclosures to carry: injection floor exception (151 / 167 public test rows), AI second labels (content sample and
  prompt-attack sample, both done with an AI), n-gram baseline beside every prompt-attack score, Bedrock's indirect
  input mapping, independence statement, question format native to Jev, fixed 0.5 rule.

## Release-day steps (ruling 29: first public release, version 1.0.0)

1. The repository was cleaned to what the first release ships on 7 October (see "Clean-up" below). The owner rewrites
   the Git history so it starts at that state.
2. `dataset/publish/release-1.0.0` is staged against the clean-up commit (its card, changelog and `canonical.json` name
   it). If the commit being pushed differs, restage with `uv run python -m goldrails_dataset.publish_e2 stage
   --code-ref <commit>`, rerun the gates, upload to `raxITLabs/decision-models-as-guardrails`, then set
   `E2_HF_REVISION` in `benchmark/goldrails_bench/e2_source.py` to the new Hub commit and verify byte parity
   (`publish_e2 parity`). The Hub history is not squashed (ruling 30).
3. Publish the results: drop `benchmark/results/final/` from `.gitignore` and commit the folder (its README already
   passed the public-text check), or copy it wherever the owner wants it to live.
4. Push `main` to GitHub.
5. Website (`site` repo, branch `feat/guardrails-leaderboard`): its extractor still reads
   `site/leaderboard/runs/edition2-dev-sample.json`, which this repository no longer has. Point it at
   `benchmark/results/final/leaderboard.json`, swap in the final numbers, apply the accuracy-and-cost design
   (https://claude.ai/artifact/NiPNb3fNtMica9tBczddST), drop edition wording, open a PR for review.
6. Blog post in the Cloudflare Clef post's shape (ruling 19), numbers from this run.

## Open, not blocking the release

- Tensor Trust written terms (would lift injection above the floor); SPML as the fallback.
- BIPIA email licence call; recording source licence reviews in `dataset/release/redistribution.json`.
- A person's label check (both samples were AI-labelled).

## Clean-up (7 October)

The tree now holds what the first release ships. Removed: the earlier benchmark runs and their subsets, contracts
v1.1, smoke, pilot, diagnostic and dev-sample results, the r23 and r25 prompt-attack candidates, the 1k and pilot
samples, `dataset/frozen/`, the v1.x release and publish records, the old dataset card, notebooks, `site/leaderboard`,
the export records, research notes and reports not tied to the current method, and the code and tests that only
served those. The full backups are in `~/.goldrails-private/backups/2026-10-07/`.

`dataset/edition2/prior-use-ids.json` records the row ids those removed ledgers and lists held (examined, smoke,
pilot, diagnostic and earlier result ledgers, plus the sha256 of dataset ids that were already public), so the freeze
integrity check and the dataset build give the same result without them. The build's split files and manifests
rebuild byte for byte, and `leaderboard.json` rescores with no change but its run folder paths and the prompt-attack
run's date (now 6 October, as run). The v1 release builds the overlap checks read stay git-ignored on this machine.
