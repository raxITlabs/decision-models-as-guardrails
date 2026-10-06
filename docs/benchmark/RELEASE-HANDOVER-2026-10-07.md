# Release handover: decision-models-as-guardrails 1.0.0

Written 6 October 2026, the night before release. Everything below is committed locally on `main`. Nothing is pushed,
nothing new is on the Hugging Face Hub, and the GPU VM is TERMINATED.

## Final results (all 11 systems, six suites, contract v2.0 as amended)

`benchmark/results/edition2-final/` (leaderboard.json, README.md, plots). `valid_for_publication: true`, no blockers,
privacy check passes, no latency anywhere (ruling 22). Site export written by `site_results.py --leaderboard-v2`.

| Rank | System | Overall (95% CI) | Tier | Catch | False block | $ per 1,000 |
|---|---|---|---|---|---|---|
| 1 | pplx-decider-v1-27b | 89.5 (88.8–90.1) | 1 | 87.1% | 8.2% | 0.056 |
| 2 | Clef | 88.7 (87.9–89.3) | 1 | 90.1% | 12.8% | 0.202 |
| 3 | Jev 1.13.0 | 87.5 (86.8–88.2) | 2 | 87.1% | 12.2% | 0.039 |
| 4 | Clef-flash | 81.1 (80.2–81.9) | 3 | 79.3% | 17.1% | 0.076 |
| 5 | Kev-4B | 80.6 (79.9–81.4) | 3 | 70.1% | 8.9% | 0.228 |
| 6 | Kev-9B | 79.5 (78.7–80.3) | 4 | 68.8% | 9.7% | 0.123 |
| 7 | Bedrock Guardrails | 78.3 (77.5–79.2) | 4 | 67.6% | 10.9% | 0.112 |
| 8 | Strands Decider 2B | 74.8 (73.9–75.7) | 5 | 62.0% | 12.3% | 0.123 |
| 9 | Open-Jev-2B | 66.3 (65.6–67.1) | 6 | 37.3% | 4.7% | 0.275 |
| 10 | Kev-0.8B | 65.8 (64.9–66.7) | 6 | 52.0% | 20.5% | 0.140 |
| 11 | Laya | 60.7 (59.7–61.6) | 7 | 44.6% | 23.2% | 0.149 |

Prompt attacks (r26 suite, direct and indirect, confounds-only gate, ruling 26) are scored, not provisional. Headline
findings for the post: on indirect injection Clef, pplx-decider and Jev score 84–89, and Clef is the only system
above the n-gram baseline (88.7). On direct attacks the n-gram baseline (80–89) beats every system on almost every
tag; hosted models block 45–52% of benign direct rows (over 90% of quoted jailbreaks).

## Evidence trail

- Rulings 19–29: `docs/benchmark/29-owner-rulings-2026-10-03.md`.
- Prompt-attack suite: `dataset/edition2/r26/prompt_attacks/` (DESIGN.md, gate.json, counts.json,
  label-agreement.json: sealed AI second label, 95.0% agreement, kappa 0.88, n = 400).
- Freeze before calls: `benchmark/subsets/edition2/freeze-manifest-prompt-attacks-r26.json`.
- Disclosures to carry: injection floor exception (151 / 167 public test rows), AI second labels (content sample and
  prompt-attack sample, both done with an AI), n-gram baseline beside every prompt-attack score, Bedrock's indirect
  input mapping, independence statement, question format native to Jev, fixed 0.5 rule.
- Prompt-attack rerun cost USD 6.06; full run USD 13.30.

## Release-day steps (ruling 29: first public release, version 1.0.0)

1. Decide whether to squash the Hub history (internal uploads labelled 1.0.0 `bc1849e` and 1.0.1 `f88403e` are in it).
2. Restage `dataset/publish/release-1.0.0` against the commit being pushed (the staged changelog names `c28bb7a`),
   run the gates and the public-text check, upload to `raxITLabs/decision-models-as-guardrails`, then set
   `E2_HF_REVISION` in `benchmark/goldrails_bench/e2_source.py` to the new Hub commit and verify byte parity.
3. Public-text pass on everything that ships (card, results README, site, post): no editions, rulings, owner process
   or earlier versions (ruling 20). The results README currently says "owner ruling 22" on one line.
4. Push `main` to GitHub.
5. Website (`site` repo, branch `feat/guardrails-leaderboard`): swap in the final numbers, apply the accuracy-and-cost
   design (https://claude.ai/artifact/NiPNb3fNtMica9tBczddST), drop edition wording, open a PR for review.
6. Blog post in the Cloudflare Clef post's shape (ruling 19), numbers from this run.
7. Retire `site/leaderboard` in this repo once the website page is live.

## Open, not blocking the release

- Tensor Trust written terms (would lift injection above the floor); SPML as the fallback.
- BIPIA email licence call; recording source licence reviews in `dataset/release/redistribution.json`.
- A person's label check (both samples were AI-labelled).
- Local process stopped during the VM run: `python3 -m http.server 8791` serving
  `~/Documents/Fertility/MyCocoon/scratchpad/pebbles` held a port the VM tunnel needed. Restart if wanted.
