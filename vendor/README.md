# vendor/

External serving code cloned at run time; not committed.

- `kev/`: `git clone --depth 1 https://github.com/jaredpalmer/kev` then
  `cd kev && uv sync --extra serve && KEV_DTYPE=bf16 uv run --extra serve python -m kev.serve --run jaredpalmer/kev-0.8b --port 8009`
