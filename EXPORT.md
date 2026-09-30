# About this repository

This is the public export of the jev-as-a-guardrails benchmark, public version `v0.0.1`, revision built from internal dataset release v1.3. The first upload of `v0.0.1` used internal dataset release v1.2, Hugging Face revision 3e3ed7f3bbed, code commit 26b578fea60c (tag `v0.0.1` in both places). This export was built from commit `c58ce56703e6` of the private development repository by `scripts/export_public.py`, from an allowlist of files. The dataset is published separately at https://huggingface.co/datasets/raxITLabs/jev-as-a-guardrails.

The private repository keeps the full history, including the git commits that date the freeze manifests before the test runs. This repository starts fresh, so its own history does not prove when anything was frozen. The freeze manifests, approvals, ledgers and their sha256 values are included; `export-manifest.json` maps every file to its private sha256.

The benchmark was called [gold]rails until 30 September 2026. Code identifiers keep the old name (the `goldrails_bench` and `goldrails_dataset` packages, `GOLDRAILS_*` variables, file names), and so do dated records written before the rename. The Hugging Face dataset moved from `raxITLabs/goldrails` to `raxITLabs/jev-as-a-guardrails`.

## What was left out or changed

- AI4Privacy, the PII source before dataset v1.2: its rows, ids, labels and audit files are withheld (its licence needs written permission to redistribute). The v1.1 PII results that used it are kept as numbers only; v1.2 measures PII on NVIDIA Nemotron-PII, which is fully included.
- Pilot samples, review packets with source text, notebooks, internal reports, downloaded transcripts and vendor documents.
- The AWS account number and local file paths are masked.

| Redaction | Count |
|---|---|
| AI4Privacy id masked | 4 |
| AI4Privacy id removed | 14 |
| AI4Privacy row removed | 2240 |
| AI4Privacy source id masked | 52 |
| AWS account masked | 2195 |
| local path masked | 69 |

571 files. jev-as-a-guardrails is a non-commercial research benchmark; each source's rows stay under that source's licence (dataset/publish/v1.1-ai/SOURCES.md).
