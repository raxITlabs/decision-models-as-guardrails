# TypeScript spikes (early, pre-Python)

The first calls to Jev were made from TypeScript with `@typesafe-ai/sdk` before the benchmark moved to Python. Kept for the record; nothing in `dataset/` or `benchmark/` depends on this.

```bash
cd docs/reference/ts-spikes && pnpm install && pnpm test:aegis
```

- `scripts/aegis-sample.ts` runs five Aegis 2.0 rows through the content-filter question set.
- `fixtures/aegis-sample-5.json` is that sample.
- `spikes/` holds the two throwaway size and question-set spikes.
