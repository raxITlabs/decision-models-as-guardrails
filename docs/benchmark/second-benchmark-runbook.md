# Second benchmark runbook

This is the exact order of commands for the second complete run, `second-benchmark`. The owner's decisions behind it
are in `benchmark/subsets/second-benchmark/run.json`. In short, it is a fresh run. Thresholds and question sets are
fitted again on the tuning rows, every manifest is frozen under the signed contract v1.1 and committed before the
first test call, and then the test and latency passes run. The data subsets are the first run's. Only the run id and
the output folders are new.

Every command below starts with `GOLDRAILS_RUN=second-benchmark`. Leave it off and the scripts point at the first
run's folders, where they refuse to write. Type it on the command line each time. Don't put it in `.env`,
because the scripts resolve their paths before `.env` loads and stop if the two disagree.

Where things go:

- ledgers and offline builds: `benchmark/results/second-benchmark/`
- freeze manifests and selections: `benchmark/subsets/second-benchmark/`
- nothing under `benchmark/results/first-benchmark/` or `benchmark/subsets/first-benchmark*/` changes

Two arms are left out on purpose, and the scripts skip both by default for any run other than the first. Core F5 on
AI4Privacy gave way to the v1.2 Nemotron-PII pass. The extension's lexicon profanity, with its masked-spelling
diagnostic, gave way to the v1.3 Civil Comments pass.

## 0. Before spending anything

These commands are offline and free.

```sh
df -h /System/Volumes/Data
git status --short
uv run pytest -q
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/plan_run.py
```

`plan_run.py` prints every stage with its systems, suites and row counts, and how many rows each ledger already
holds. Before the first call every stage should show `already recorded 0`. Each script also takes `--dry-run` for one
stage, for example `first_benchmark.py test --dry-run`.

## 1. Bring the VM up

```sh
GOLDRAILS_RUN=second-benchmark make status
GOLDRAILS_RUN=second-benchmark GOLDRAILS_ZONES="us-east4-a us-east4-c us-central1-a us-central1-b us-central1-c us-west1-a us-west1-b us-west4-a" make up
mkdir -p benchmark/results/second-benchmark
GOLDRAILS_RUN=second-benchmark gcloud compute instances list --filter=name=gold-rails-serve --format='value(zone.basename())' > benchmark/results/second-benchmark/vm-zone.txt
cat benchmark/results/second-benchmark/vm-zone.txt
```

`infra/ctl.sh` uses `GOLDRAILS_ZONES` in place of its own list and tries the zones in the order given, so us-east4-a
comes first. It reads the list only when no VM exists. If `make status` shows a stopped VM, `make up` resumes it in the
zone it already has and ignores the list. Run `make down` first if that zone is not wanted.

The zone file matters. The core stages copy it onto `serving.jsonl`, and the serving build below puts it on every
serving window. Outside us-east4 each serving record also says that GPU time is priced at the us-east4 tariff. If the
VM is recreated in another zone partway through, stop and ask the owner how to record two zones.

## 2. Tune

```sh
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py tune --systems open,jev,regex,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/extension_run.py tune --systems open,jev,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/pii_v12_run.py tune
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/profanity_v13_run.py tune
```

The VM stops itself after 8 hours. After `make up`, run the same command again and the runner picks up from this run's
own ledger. Each line the scripts print ends with a count of failed rows. Look at them before freezing, because a
failed tuning row gives no evidence to the threshold fit.

## 3. Freeze

Keep the VM up. The freezes build live clients to compute configuration hashes.

```sh
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py freeze
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/extension_run.py freeze --systems open,jev,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/pii_v12_run.py freeze
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/profanity_v13_run.py freeze
```

The order matters. The core manifest comes first, because the other three record its sha256 in their `extends` block
and extension 1 copies its content arms for B2. Expect these arm counts: core 48 (content 7, prompt attacks 7, word
filters 8, grounding 7, B1 7, B3 12), extension 1 14 (denied topics 7, B2 7), PII 7, profanity 7. The core freeze
prints a line per suite. If a system is missing, its client failed to build, so fix that and start again from a clean
`benchmark/subsets/second-benchmark/`, keeping only `run.json`. The freezes refuse to overwrite an existing manifest.

There is no extension 2. The first run needed one only because Bedrock credentials arrived late. Extensions 3 and 4
keep the first run's numbers, so every builder finds its files by the same names.

## 4. Commit the manifests before any test call

```sh
git add benchmark/subsets/second-benchmark/
git commit -m "second-benchmark: freeze manifests and selections before any test call"
git status --short benchmark/subsets/second-benchmark/
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/plan_run.py
```

`git status` must print nothing. The runner refuses test rows unless the manifest is committed and unchanged, and it
stamps the commit on every test record. The second `plan_run.py` shows the test and latency stages with the chosen
question sets in place of the candidates.

## 5. Test

```sh
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py test --systems open,jev,regex,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/extension_run.py test --systems open,jev,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/pii_v12_run.py test
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/profanity_v13_run.py test
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py rerun-failed --dry-run
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py rerun-failed
```

`rerun-failed` re-attempts only the core test rows that failed on a retryable connection error, under the same
manifest, and writes them to `test-rerun.jsonl`. It now also builds Bedrock and regex clients when those rows failed.
The extension, PII and profanity scripts have no equivalent, and the leaderboard reads no rerun ledger for them. If
their test rows fail, ask the owner before doing anything.

## 6. Latency

```sh
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/first_benchmark.py latency --systems open,jev,regex,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/extension_run.py latency --systems jev,bedrock
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/pii_v12_run.py latency
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/profanity_v13_run.py latency
```

This matches the first run. Core covers all 10 systems, one request at a time, with up to 100 tuning rows per suite
including B1 and B3. The extension pass covers Jev and Bedrock on denied topics, 42 rows each. PII and profanity cover
7 systems on 50 rows each.

## 7. Take the VM down and check that it is gone

```sh
GOLDRAILS_RUN=second-benchmark make down
GOLDRAILS_RUN=second-benchmark make status
GOLDRAILS_RUN=second-benchmark gcloud compute instances list --filter=name=gold-rails-serve
GOLDRAILS_RUN=second-benchmark gcloud compute disks list --filter=name~gold-rails
```

`make status` should print `vm: none`, and both lists should be empty. Nothing after this step makes a call.

## 8. Offline builds

```sh
R=benchmark/results/second-benchmark
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/serving_from_ledger.py --out $R/serving-v13.json --zone "$(cat $R/vm-zone.txt)" $R/test.jsonl $(test -f $R/test-rerun.jsonl && echo $R/test-rerun.jsonl) $R/ext-test.jsonl $R/ext-test-bias.jsonl $R/pii-v12-test.jsonl $R/prof-v13-test.jsonl
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/leaderboard_v13.py --final
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/validate_extension_freeze.py
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/bias_results.py
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/bias_parts.py
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/bias_audit_copy.py
GOLDRAILS_RUN=second-benchmark uv run python -c "import json; d=json.load(open('$R/leaderboard-final.json')); print(d['valid_for_publication'], d['publication_blockers'])"
```

`serving-v13.json` must come from this run's own test ledgers. `leaderboard_v13.py` refuses to run without it rather
than price this run with the first run's windows. The leaderboard uses the signed contract, the four manifests in
`benchmark/subsets/second-benchmark/`, the unchanged implementations declarations in
`benchmark/subsets/first-benchmark/`, and no approval records. Every manifest was frozen under the same contract and the
same scoring code (`goldrails_bench/leaderboard.py`, sha256 `92a74bcc31c20f5b099019feea79742d2a8b30b5743a84f7450d8fcbf75f9fe0`), so none are needed. Editing that file before
this step would change that. `bias_audit_copy.py` checks that this run's bias rows have the first run's ids. It then
copies the audit and marks the two sentences that cite first-run outcomes.

Then commit the results folder, `vm-zone.txt` included.

## 9. Results site and primer

No calls. The site shows the second run as its current results and keeps the first run's page data beside it.

```sh
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/site_results.py   # site/leaderboard/results.json
GOLDRAILS_RUN=second-benchmark uv run python benchmark/runs/check_page.py     # writes $R/page-check.json, must pass every check
uv run python benchmark/runs/site_results.py                                  # the first run: site/leaderboard/runs/first-benchmark.json
uv run python benchmark/runs/check_page.py                                    # the first run's 33 checks, on that file
uv run docs/teach/diagrams/results_charts.py                                  # primer charts and tables from the second run
```

`site_results.py` writes the current run (`CURRENT_RUN`) to `results.json` and any other run to `runs/<run>.json`;
`index.html?results=runs/first-benchmark.json` shows the first run's page, marked as an earlier run. With no
`GOLDRAILS_RUN` it builds the first run, byte for byte as before runs existed. The second run's page carries a `run`
block: its publication status, the first run's status and blockers, and what changed. `check_page.py` recomputes the
Jev grounding account in that block from the ledgers. `results_charts.py` defaults to the run the primer shows, not
the first run, so a bare re-run never puts older charts into the primer.
