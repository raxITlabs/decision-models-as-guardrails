# About this repository

This is the public export of the Gold Rails benchmark, public version `v0.0.1`, revision built from internal dataset release v1.3. The first upload of `v0.0.1` used internal dataset release v1.2, Hugging Face revision 3e3ed7f3bbed, code commit 26b578fea60c (tag `v0.0.1` in both places). This export was built from commit `f54b312a3f19` of the private development repository by `scripts/export_public.py`, from an allowlist of files. The dataset is published separately at https://huggingface.co/datasets/raxITLabs/goldrails.

The private repository keeps the full history, including the git commits that date the freeze manifests before the test runs. This repository starts fresh, so its own history does not prove when anything was frozen. The freeze manifests, approvals, ledgers and their sha256 values are included; `export-manifest.json` maps every file to its private sha256.

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
| AWS account masked | 1258 |
| local path masked | 57 |

502 files. Gold Rails is a non-commercial research benchmark; each source's rows stay under that source's licence (dataset/publish/v1.1-ai/SOURCES.md).
