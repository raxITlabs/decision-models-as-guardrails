# decision-models-as-guardrails site

The results site for the benchmark: the leaderboard, the public rows with every system's answer, and how to
reproduce the run. Next.js (App Router), exported as static files, so Vercel or any static host can serve it.
It is its own project. It imports nothing from the Python packages and reads only generated JSON.

## Routes

| Route | What it shows |
|---|---|
| `/` | Hero and stats, the leaderboard (job picker, cost or false-block axis, managed or all systems, table, selected system), the four claims, the eight jobs, FAQ, notify, footer |
| `/reproduce` | Quickstart, the dataset at its pinned revision, the run scripts, how scoring works, adapters, adding a system |
| `/data` | Heatmap of systems by job, and the row browser over the public test rows |
| `/data/rows/<id>` | One row: text where the licence allows, label, source and every system's score and decision |
| `/changelog` | The 1.0.0 entry |

## Data

Scores are held until release day, so the site never commits them. `scripts/build-data.ts` reads the benchmark
repository and writes three files into `site/data/`, which is git-ignored:

- `board.json`: systems, overall and per-job scores, tiers, cost, baselines and the facts the copy quotes.
- `rows-index.json`: one compact entry per public row for the row browser.
- `rows-detail.json`: per-row text (cleared sources only) and every system's answer, served as 64 JSON shards.

Inputs are `benchmark/results/final/leaderboard.json`, the public ledgers in
`benchmark/results/final/ledgers/{main-run,prompt-attacks,gpt-6-luna}/*.jsonl`, the public test rows in
`dataset/edition2/build/F*.test.jsonl` and `dataset/release/redistribution.json`.

Two rules hold in the generator and are tested in `tests/privacy.test.ts`:

- Ids from any `private/` folder never ship. The raw private ledgers also hold public rows; only ids that are not
  public test rows, plus every row in `dataset/edition2/build/private/`, count as private.
- A row ships text only when its source is listed with `mode: "text"` and `reviewed: true`, its ledger records do
  not flag it `ids_only_source`, and the row is not marked `redistribution: "ids_only"`. Every other row shows
  "text withheld (licence)".

When `site/data/` is missing the build falls back to `fixtures/data/`, a synthetic data set with made-up names and
numbers, and the home page says so. The build log names the source it used.

## Commands

```bash
pnpm install
pnpm data            # write site/data/ from ../ (does nothing when the results are not on this machine)
pnpm dev             # http://localhost:3000
pnpm build           # runs `pnpm data` first, then exports to out/
pnpm test            # generator and privacy tests; the real-data privacy test runs when site/data/ exists
pnpm lint
pnpm data:fixture    # rebuild fixtures/source/ and fixtures/data/ from scripts/make-fixture.ts
```

## Row pages

Prerendering one page per row writes tens of thousands of files, so `/data/rows/<id>` is a single static shell
(`/data/rows/view.html`) that loads the row from its shard. `vercel.json` rewrites `/data/rows/:id` to the shell,
and `public/serve.json` does the same for `pnpm start`. Another static host needs the same rewrite. In `pnpm dev`
every id is a real route.

## Release day

1. In the benchmark repository, with the final results in place, run `pnpm --dir site data`.
2. Run `pnpm --dir site test` and confirm the real-data privacy test passes, not skipped.
3. Either commit `site/data/` (remove the `site/data/` line from the repository's `.gitignore` in the same commit),
   or generate it in CI before the build. Vercel does not have the results, so one of the two is required.
4. On Vercel, create the project with root directory `site/`. Framework preset Next.js, install with `pnpm install`,
   build with `pnpm build`. The export lands in `out/`.
