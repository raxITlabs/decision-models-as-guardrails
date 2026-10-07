// Writes fixtures/source/: a tiny, synthetic stand-in for the benchmark repository, laid out like the real one.
// Every number and name in it is made up. `pnpm data:fixture` then turns it into fixtures/data/, which the site
// builds from whenever site/data/ (the real, held-back results) is absent.
//
//   pnpm exec tsx scripts/make-fixture.ts
import fs from "node:fs";
import path from "node:path";
import { JOBS } from "../lib/jobs";

const ROOT = path.resolve(__dirname, "..", "fixtures", "source");

let seed = 20261008;
const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const r1 = (v: number) => Math.round(v * 10) / 10;

const SYSTEMS = [
  { id: "fixture-alpha", name: "Example Alpha", provider: "Synthetic Labs", mono: "Ea", hosting: "hosted_api", base: 88 },
  { id: "fixture-bravo", name: "Example Bravo", provider: "Synthetic Labs", mono: "Eb", hosting: "hosted_api", base: 84 },
  { id: "fixture-charlie", name: "Example Charlie", provider: "Placeholder Inc.", mono: "Ec", hosting: "managed_service", base: 79 },
  { id: "fixture-delta", name: "Example Delta", provider: "Open weights (fake)", mono: "Ed", hosting: "self_hosted", base: 73 },
  { id: "fixture-echo", name: "Example Echo", provider: "Open weights (fake)", mono: "Ee", hosting: "self_hosted", base: 61 },
];

const TAG: Record<string, string> = {
  indirect: "indirect", direct: "injection", input: "input", output: "output",
  topics: "topic", pii: "pii", grounding: "grounding", profanity: "profanity",
};
const FEATURE: Record<string, string> = {
  indirect: "F2", direct: "F2", input: "F1", output: "F1", topics: "F3", pii: "F5", grounding: "F6", profanity: "F4",
};
const ROLE: Record<string, string> = { indirect: "tool", output: "assistant", grounding: "assistant", profanity: "user" };
const SOURCES = ["synthetic_open", "synthetic_licensed", "synthetic_unreviewed"];

function write(rel: string, body: string) {
  const p = path.join(ROOT, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, body);
}
const jsonl = (rows: unknown[]) => rows.map((r) => JSON.stringify(r)).join("\n") + "\n";

function tiers(list: { score: number }[]) {
  // Fake tiers: a new tier starts wherever the next score is more than 3 points below the tier's leader.
  let tier = 1;
  let lead = list[0]?.score ?? 0;
  return list.map((x) => {
    if (lead - x.score > 3) {
      tier++;
      lead = x.score;
    }
    return tier;
  });
}

function entry(sys: (typeof SYSTEMS)[number], score: number, extra: object = {}) {
  const half = 0.8 + rand() * 1.4;
  return {
    name: sys.id,
    balanced_accuracy: score,
    ci: { low: r1(score - half), high: r1(score + half) },
    catch_rate: Math.min(0.99, Math.round((score / 100 + rand() * 0.1 - 0.05) * 1000) / 1000),
    false_block_rate: Math.round((0.02 + rand() * 0.3) * 1000) / 1000,
    status: "complete",
    ...extra,
  };
}

fs.rmSync(ROOT, { recursive: true, force: true });

// leaderboard.json
const arms: object[] = [];
const subtasks: Record<string, object> = {};
const perSystemJob: Record<string, number[]> = {};
for (const job of JOBS) {
  const scores = SYSTEMS.map((s) => ({ s, score: r1(Math.max(50.5, Math.min(99, s.base + (rand() - 0.5) * 16))) })).sort(
    (a, b) => b.score - a.score,
  );
  const t = tiers(scores);
  subtasks[job.key] = {
    ranking: scores.map((x, i) => {
      const armId = `${x.s.id}|fixture-${job.id}`;
      const cost = r1((x.s.hosting === "self_hosted" ? 0.15 : 0.03) + rand() * 0.2) / 1;
      arms.push({
        arm_id: armId,
        system: x.s.id,
        cost: { implementation_type: x.s.hosting, usd_per_1000: Math.round(cost * 1000) / 1000, subtasks: {} },
      });
      (perSystemJob[x.s.id] ??= []).push(x.score);
      return entry(x.s, x.score, { rank: i + 1, tier: t[i], arm_id: armId });
    }),
    not_ranked: [],
  };
}
const overallScores = SYSTEMS.map((s) => ({
  s,
  score: r1(perSystemJob[s.id].reduce((a, b) => a + b, 0) / perSystemJob[s.id].length),
})).sort((a, b) => b.score - a.score);
const ot = tiers(overallScores);
const leaderboard = {
  schema: "synthetic-fixture",
  note: "Synthetic fixture. Every name and number here is made up.",
  display: Object.fromEntries(SYSTEMS.map((s) => [s.id, { name: s.name, provider: s.provider, mono: s.mono }])),
  rules: { headline: { operating_point: 0.5 } },
  arms,
  subtasks,
  overall: { ranking: overallScores.map((x, i) => entry(x.s, x.score, { rank: i + 1, tier: ot[i], rank_interval: { low: i + 1, high: i + 1 } })) },
  run: {
    cost: Object.fromEntries(
      SYSTEMS.map((s) => [s.id, { checks: 60, usd_per_1000: Math.round(((s.hosting === "self_hosted" ? 0.2 : 0.05) + rand() * 0.15) * 1000) / 1000 }]),
    ),
  },
  full_run: { rows_total: 60, rows_public: 52, rows_unpublished: 8, runs: { a: { date: "2026-01-01" } } },
  prompt_attacks: {
    ngram_baseline: {
      by_tag: {
        injection: { keyword_regex: 51.0, best: 70.0 },
        jailbreak: { keyword_regex: 52.0, best: 71.0 },
        leakage: { keyword_regex: 60.0, best: 75.0 },
        indirect: { keyword_regex: 50.0, best: 72.0 },
      },
    },
  },
  unpublished_slice_view: {
    public: Object.fromEntries(SYSTEMS.map((s) => [s.id, { overall: { balanced_accuracy: s.base } }])),
    unpublished: Object.fromEntries(SYSTEMS.map((s) => [s.id, { overall: { balanced_accuracy: s.base - 1.5 } }])),
  },
  label_provenance: {
    content_sample: { rows: 20, agreement_population_weighted: 0.9 },
    prompt_attack_sample: { rows: 20, agreement: 0.85 },
  },
  label_amendment: { threshold: 4, systems: 5, reviewed: 3, corrected: 1, removed: 1, date: "2026-01-02" },
};
write("benchmark/results/final/leaderboard.json", JSON.stringify(leaderboard, null, 1) + "\n");

// dataset rows: six public rows per job, one private row per job, plus custom-word rows that are not a job
const pub: Record<string, object[]> = {};
const priv: Record<string, object[]> = {};
const ledgerRows: { id: string; job: string; expected: string; source: string }[] = [];
const privateLedgerRows: typeof ledgerRows = [];
let n = 0;
for (const job of JOBS) {
  for (let i = 0; i < 7; i++) {
    const isPrivate = i === 6;
    const source = SOURCES[(i + n) % 3];
    const id = `fx-${job.id}-${isPrivate ? "held" : "pub"}-${String(i).padStart(2, "0")}`;
    const expected = i % 2 === 0 ? "yes" : "no";
    const text = isPrivate
      ? `SECRET-HELD-BACK text for ${id}. This sentence must never reach the site.`
      : source === "synthetic_open"
        ? `Synthetic example ${i + 1} for the ${job.short.toLowerCase()} job. It is placeholder text, not a real check.`
        : `WITHHELD-LICENCE text for ${id}. The licence does not allow publishing this sentence.`;
    const row = {
      id,
      feature: FEATURE[job.id],
      subtask: TAG[job.id],
      split: "test",
      visibility: isPrivate ? "private" : "public",
      expected,
      provenance: { source, licence: source === "synthetic_open" ? "cc0-1.0" : "custom" },
      state: {
        role: ROLE[job.id] ?? "user",
        text,
        context: job.id === "output" ? [{ role: "user", text: `Synthetic question before reply ${i + 1}.` }] : [],
        query: job.id === "grounding" ? `Synthetic query ${i + 1}?` : null,
        source: job.id === "grounding" ? `Synthetic source document ${i + 1}.` : null,
        tool_call: null,
      },
    };
    (isPrivate ? priv : pub)[FEATURE[job.id]] ??= [];
    (isPrivate ? priv : pub)[FEATURE[job.id]].push(row);
    (isPrivate ? privateLedgerRows : ledgerRows).push({ id, job: job.ledgerSubtask, expected, source });
  }
  n++;
}
for (let i = 0; i < 4; i++) {
  pub.F4.push({
    id: `fx-word-${i}`, feature: "F4", subtask: "word", split: "test", visibility: "public", expected: "yes",
    provenance: { source: "synthetic_open", licence: "cc0-1.0" },
    state: { role: "user", text: `Synthetic custom word row ${i}.`, context: [], query: null, source: null, tool_call: null },
  });
}
for (const [f, rows] of Object.entries(pub)) write(`dataset/edition2/build/${f}.test.jsonl`, jsonl(rows));
for (const [f, rows] of Object.entries(priv)) write(`dataset/edition2/build/private/${f}.test.jsonl`, jsonl(rows));

write(
  "dataset/release/redistribution.json",
  JSON.stringify(
    {
      default: "ids_only",
      sources: {
        synthetic_open: { mode: "text", reviewed: true },
        synthetic_licensed: { mode: "ids_only", reviewed: true },
        synthetic_unreviewed: { mode: "text", reviewed: false },
      },
    },
    null,
    1,
  ) + "\n",
);

// ledgers: public copies in main-run/, raw copies (public plus held-back rows) in main-run/private/
const suiteOf = Object.fromEntries(JOBS.map((j) => [j.ledgerSubtask, j.suite]));
function record(sysId: string, base: number, r: (typeof ledgerRows)[number]) {
  const p = Math.round(Math.min(0.999, Math.max(0.001, (r.expected === "yes" ? base / 100 : 1 - base / 100) + (rand() - 0.5) * 0.9)) * 1000) / 1000;
  const failed = rand() < 0.03;
  return {
    system: sysId, suite: suiteOf[r.job], subtask: r.job, row_id: r.id, expected: r.expected, source: r.source,
    ids_only_source: r.source !== "synthetic_open", outcome: failed ? "failed" : "decided",
    decision: failed ? null : p >= 0.5, score: failed ? null : p, latency_s: 0.1,
    attempts: [{ attempt: 1, ok: !failed, at: "2026-01-01T00:00:00Z" }],
  };
}
for (const s of SYSTEMS) {
  const pubRecs = ledgerRows.map((r) => record(s.id, s.base, r));
  write(`benchmark/results/final/ledgers/main-run/${s.id}.jsonl`, jsonl(pubRecs));
  write(
    `benchmark/results/final/ledgers/main-run/private/${s.id}.jsonl`,
    jsonl([...pubRecs, ...privateLedgerRows.map((r) => record(s.id, s.base, r))]),
  );
}
console.log(`wrote ${path.relative(process.cwd(), ROOT)}`);
