# Rebuilding ids-only text

Rows marked `"redistribution": "ids_only"` ship without their text, context, source or query. Rebuild them from the original publishers with the public code at the tag that matches this dataset:

```bash
git clone https://github.com/raxITlabs/gold-rails
cd gold-rails
git checkout v1.1-ai-provisional
uv sync
uv run python -m goldrails_dataset.rehydrate --data <folder holding data/> --out <new folder>
```

The command downloads each source at its pinned revision, puts the stripped fields back, and keeps a row only if it then matches the row's `canonical_row_hash`. Matching rows are marked `rebuilt_locally`. You need access to each source under its own licence; rebuilding grants no rights the source licence withholds.

| Source | ids-only rows | Public rebuild |
|---|---|---|
| civil_comments_identity | 900 | yes |
| ragtruth | 900 | yes |
| bias_pairs_reviewed | 16 | no: text is not in the public repository |

## What this public dataset does not include

The full internal release v1.1-ai has more rows than this package. Missing here:

- **ai4privacy**: 880 rows, withheld with their annotations (see SOURCES.md). The PII results that used them cannot be reproduced from public files.
- **bias_pairs_reviewed**: ids and labels only; the text cannot be rebuilt from public files until its licence choice is made.
