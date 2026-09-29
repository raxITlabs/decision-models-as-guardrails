# Rebuilding from the original sources

Every row here carries its text. To rebuild the whole release from the original publishers and check it:

```bash
git clone https://github.com/raxITlabs/goldrails
cd goldrails
git checkout c468c82204cf3acb20821cf41df17e0d4ead9e78
uv sync
uv run python -m goldrails_dataset.release --version v1.3
```

The command downloads each source at its pinned revision, rebuilds every row, and compares the result with the committed release manifest before writing anything. Each row's `canonical_row_hash` lets you check a single row. You need access to each source under its own licence.
