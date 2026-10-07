# Fixtures

Synthetic stand-ins, safe to commit. Every system name and number here is made up.

- `source/` mirrors the benchmark repository layout (leaderboard, ledgers with a `private/` copy, build rows with a
  `private/` folder, a redistribution policy) so the generator and the privacy check can be tested end to end.
- `data/` is the generator's output for `source/`. The site builds from it when `site/data/` is absent.

Rebuild both with `pnpm data:fixture`.
