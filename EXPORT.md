# How this repository was exported

Until 2026-10-02 this repository was an export of a private working repo; that history is archived offline. This file records what the export did, so the earlier commits make sense.

## The export, 28 to 30 September 2026

`scripts/export_public.py` built each commit here from an allowlist of files committed in the private repository. The last export, commit 89cf766, is public version `v0.0.1` revised for internal dataset release v1.3, built from private commit `c58ce56703e6`. The first upload of `v0.0.1` used internal dataset release v1.2, Hugging Face revision 3e3ed7f3bbed, code commit 26b578fea60c (tag `v0.0.1` in both places). The dataset is published separately at https://huggingface.co/datasets/raxITLabs/jev-as-a-guardrails.

Each export rebuilt the tree from scratch, so the eight export commits date nothing inside them. `export-manifest.json` maps every exported file to its sha256 in the private repository and here, with the redactions applied to it. The last export had 571 files and these redactions:

| Redaction | Count |
|---|---|
| AI4Privacy id masked | 4 |
| AI4Privacy id removed | 14 |
| AI4Privacy row removed | 2240 |
| AI4Privacy source id masked | 52 |
| AWS account masked | 2195 |
| local path masked | 69 |

## Since 2 October 2026

The private repository is a git bundle now, `jev-powered-guardrails-archive-2026-10-02.bundle`, kept offline. Its last commit, edc20ff, changed only `dataset/release/v1.3/publication.json`, and that change is here too. The page checks still need the private history to show freeze manifests committed before test ledgers. The History section of [README.md](README.md) explains how they get it.

Most files the export left out came over on 2 October, masked the same way: the notebooks, the pilot and 1k samples, the pilot and smoke results, the design notes, older dataset records and the profanity and denied-topic research notes. These stay out:

- Anything from AI4Privacy, the PII source before dataset v1.2. That covers the 1k sample's two F5 files, the PII smoke run, the PII-negative corrections and reviews, the F5 review key and `dataset/publish/v1.1-ai/KNOWN_ISSUES.md`. Its licence needs written permission to redistribute. The v1.1 PII results that used it are kept as numbers only. v1.2 measures PII on NVIDIA Nemotron-PII, which is fully included.
- The unsent draft asking AI4Privacy for that permission.

The AWS account number and local file paths stay masked. From 2 October the Bedrock clients replace the account id in every ARN with `<account>` before a response reaches a ledger.

decision-models-as-guardrails is a non-commercial research benchmark. Each source's rows stay under that source's licence, listed in `dataset/publish/v1.3-full/SOURCES.md`.
