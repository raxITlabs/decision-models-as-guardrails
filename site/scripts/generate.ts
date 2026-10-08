// Turns the benchmark's published results into the compact JSON the site reads.
//
// Inputs, relative to the benchmark repository root:
//   benchmark/results/final/leaderboard.json
//   benchmark/results/final/ledgers/{main-run,prompt-attacks,gpt-6-luna}/*.jsonl   (never the private/ folders)
//   dataset/edition2/build/F*.test.jsonl                                           (never build/private/)
//   dataset/release/redistribution.json                                            (which sources may ship text)
//
// Privacy rules enforced here and re-checked by tests/privacy.test.ts:
//   - an id found in any private/ file is dropped everywhere;
//   - a row ships text only when its source is listed with mode "text" and reviewed true, its ledger records do
//     not flag it ids_only, and the row itself is not marked redistribution ids_only. Every other row ships
//     its id, job, source and label, with the text withheld.
import fs from "node:fs";
import path from "node:path";
import { JOBS, JOB_BY_LEDGER_SUBTASK, SUITE_COUNT, type JobId } from "../lib/jobs";
import type {
  Baseline,
  Board,
  Facts,
  Hosting,
  RowDetail,
  RowLite,
  RowResult,
  RowsIndex,
  Score,
  SystemMeta,
  Turn,
} from "../lib/types";

export const LEDGER_RUNS = ["main-run", "prompt-attacks", "gpt-6-luna"];
export const RELEASE_VERSION = "1.0.0";

/** Display names, makers and marks for the systems on the board. Ids not listed fall back to the id itself.
 *  `short` labels the chart dots. `logo` is a file in public/logos; systems without one show `mono`, the maker's initials. */
export const SYSTEM_DISPLAY: Record<string, { name: string; short?: string; provider: string; mono: string; logo?: string }> = {
  "pplx-decider-v1-27b": { name: "pplx-decider v1 27B", short: "pplx-decider", provider: "Perplexity", mono: "Px", logo: "/logos/perplexity.svg" },
  "gpt-6-luna": { name: "GPT-6 Luna", provider: "OpenAI · Decisions API", mono: "Oa", logo: "/logos/openai.svg" },
  clef: { name: "Clef", provider: "Cloudflare · Workers AI", mono: "Cf", logo: "/logos/cloudflare.svg" },
  "jev-1.13.0": { name: "Jev 1.13.0", provider: "TypeSafe", mono: "Ts", logo: "/logos/typesafe.svg" },
  "clef-flash": { name: "Clef Flash", provider: "Cloudflare · Workers AI", mono: "Cf", logo: "/logos/cloudflare.svg" },
  "kev-4b": { name: "Kev 4B", provider: "Jared Palmer · open weights", mono: "JP" },
  "kev-9b": { name: "Kev 9B", provider: "Jared Palmer · open weights", mono: "JP" },
  "bedrock-guardrails": { name: "Amazon Bedrock Guardrails", short: "Bedrock Guardrails", provider: "Amazon Web Services", mono: "Aw", logo: "/logos/aws.svg" },
  "strands-decider-2b": { name: "Strands Decider 2B", short: "Strands 2B", provider: "Amazon Web Services · open weights", mono: "St", logo: "/logos/aws.svg" },
  "open-jev-2b": { name: "Open-Jev 2B", provider: "Zefan Cai · open weights", mono: "ZC" },
  "kev-0-8b": { name: "Kev 0.8B", provider: "Jared Palmer · open weights", mono: "JP" },
  laya: { name: "Laya", provider: "Convai Innovations · open weights", mono: "CI", logo: "/logos/laya.svg" },
};

/** The system whose native question format every decision model receives (disclosed in the FAQ). */
export const QUESTION_FORMAT_SYSTEM = "jev-1.13.0";
/** A vendor model that is also scored without its vendor's own dataset rows. */
export const OWN_ROWS = { system: "gpt-6-luna", vendor: "OpenAI", view: "excluding_openai_owned" };

/** Build row subtask (row tag) to job. Rows whose tag is not listed (the custom-words check) are left out. */
const ROW_TAG_JOB: Record<string, JobId> = {
  input: "input",
  harmful_goal: "input",
  over_refusal: "input",
  output: "output",
  indirect: "indirect",
  injection: "direct",
  jailbreak: "direct",
  leakage: "direct",
  topic: "topics",
  profanity: "profanity",
  pii: "pii",
  grounding: "grounding",
};
const BASELINE_TAG_JOB: Record<string, JobId> = { injection: "direct", jailbreak: "direct", leakage: "direct", indirect: "indirect" };

/* eslint-disable @typescript-eslint/no-explicit-any */
type Json = any;

export function readJsonl(file: string): Json[] {
  const out: Json[] = [];
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const t = line.trim();
    if (t) out.push(JSON.parse(t));
  }
  return out;
}

function listJsonl(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".jsonl"))
    .sort()
    .map((f) => path.join(dir, f));
}

const round = (v: number, d = 4) => Math.round(v * 10 ** d) / 10 ** d;

export interface Paths {
  leaderboard: string;
  ledgerDirs: string[];
  buildDir: string;
  redistribution: string;
  privateFiles: string[];
}

export function repoPaths(repo: string): Paths {
  const final = path.join(repo, "benchmark", "results", "final");
  const ledgerDirs = LEDGER_RUNS.map((r) => path.join(final, "ledgers", r));
  const buildDir = path.join(repo, "dataset", "edition2", "build");
  const privateFiles = [
    ...ledgerDirs.flatMap((d) => listJsonl(path.join(d, "private"))),
    ...listJsonl(path.join(buildDir, "private")),
  ];
  return {
    leaderboard: path.join(final, "leaderboard.json"),
    ledgerDirs,
    buildDir,
    redistribution: path.join(repo, "dataset", "release", "redistribution.json"),
    privateFiles,
  };
}

export function hasRealInputs(repo: string): boolean {
  const p = repoPaths(repo);
  return fs.existsSync(p.leaderboard) && fs.existsSync(p.buildDir) && fs.existsSync(p.redistribution);
}

/** Ids of the public test rows: every F<n>.test.jsonl directly under the build folder. */
export function publicIds(p: Paths): Set<string> {
  const ids = new Set<string>();
  for (const f of buildTestFiles(p.buildDir)) for (const r of readJsonl(f)) if (typeof r.id === "string") ids.add(r.id);
  return ids;
}

export function buildTestFiles(buildDir: string): string[] {
  if (!fs.existsSync(buildDir)) return [];
  return fs
    .readdirSync(buildDir)
    .filter((f) => /^F\d+\.test\.jsonl$/.test(f))
    .sort()
    .map((f) => path.join(buildDir, f));
}

/**
 * Ids that must never ship: every row in the build's private/ folder (the unpublished slice and rows that were
 * dropped or held for review), and every row a raw private ledger holds that is not a public test row.
 * The raw ledgers also hold the public rows, so those are subtracted; a public id that also appears in the
 * build's private/ folder stays private.
 */
export function privateIds(p: Paths, pub: Set<string> = publicIds(p)): Set<string> {
  const ids = new Set<string>();
  const buildPrivate = new Set(listJsonl(path.join(p.buildDir, "private")));
  for (const f of p.privateFiles) {
    const fromBuild = buildPrivate.has(f);
    for (const r of readJsonl(f)) {
      for (const id of [r.row_id, r.id]) {
        if (typeof id !== "string") continue;
        if (fromBuild || !pub.has(id)) ids.add(id);
      }
    }
  }
  return ids;
}

export function textCleared(source: string, policy: Json): boolean {
  const e = policy?.sources?.[source];
  return Boolean(e && e.mode === "text" && e.reviewed === true);
}

function scoreFrom(entry: Json, cost: number | null): Score {
  return {
    system: entry.name,
    rank: entry.rank,
    tier: entry.tier,
    score: round(entry.balanced_accuracy, 2),
    ciLow: round(entry.ci?.low ?? entry.balanced_accuracy, 2),
    ciHigh: round(entry.ci?.high ?? entry.balanced_accuracy, 2),
    catchRate: round(entry.catch_rate),
    falseBlockRate: round(entry.false_block_rate),
    cost: cost === null ? null : round(cost, 5),
  };
}

function hostingOf(arms: Json[], system: string): Hosting {
  const types = new Set(arms.filter((a) => a.system === system).map((a) => a.cost?.implementation_type));
  return types.has("self_hosted") ? "self-hosted" : "managed";
}

function latestDate(lb: Json): string {
  const env = process.env.RELEASE_DATE;
  if (env && /^\d{4}-\d{2}-\d{2}$/.test(env)) return env;
  const dates: string[] = [];
  for (const r of Object.values(lb.full_run?.runs ?? {}) as Json[]) if (typeof r?.date === "string") dates.push(r.date);
  if (typeof lb.label_amendment?.date === "string") dates.push(lb.label_amendment.date);
  return dates.sort().at(-1) ?? new Date().toISOString().slice(0, 10);
}

export function buildBoard(lb: Json, source: Board["source"]): Board {
  const arms: Json[] = lb.arms ?? [];
  const ranking: Json[] = lb.overall.ranking;
  const runCost: Json = lb.run?.cost ?? {};

  const systems: SystemMeta[] = ranking.map((r) => {
    const d = SYSTEM_DISPLAY[r.name] ?? lb.display?.[r.name];
    return {
      id: r.name,
      name: d?.name ?? r.name,
      provider: d?.provider ?? "",
      mono: d?.mono ?? r.name.slice(0, 2),
      ...(d?.short ? { short: d.short } : {}),
      ...(d?.logo ? { logo: d.logo } : {}),
      hosting: hostingOf(arms, r.name),
    };
  });

  const overall = ranking.map((r) => scoreFrom(r, typeof runCost[r.name]?.usd_per_1000 === "number" ? runCost[r.name].usd_per_1000 : null));

  const jobs = {} as Record<JobId, Score[]>;
  for (const job of JOBS) {
    const sub = lb.subtasks?.[job.key];
    const subName = job.key.split("/")[1];
    jobs[job.id] = (sub?.ranking ?? [])
      .filter((r: Json) => typeof r.balanced_accuracy === "number")
      .map((r: Json) => {
        const arm = arms.find((a) => a.arm_id === r.arm_id);
        const c = arm?.cost?.subtasks?.[subName]?.usd_per_1000 ?? arm?.cost?.usd_per_1000;
        return scoreFrom(r, typeof c === "number" ? c : null);
      });
  }

  const baseline: Baseline[] = Object.entries(lb.prompt_attacks?.ngram_baseline?.by_tag ?? {})
    .filter(([tag]) => tag in BASELINE_TAG_JOB)
    .map(([tag, v]) => {
      const b = v as Json;
      return { tag, job: BASELINE_TAG_JOB[tag], keyword: b.keyword_regex, best: b.best };
    });

  const facts: Facts = {};
  const slice = lb.unpublished_slice_view;
  if (slice?.public && slice?.unpublished) {
    let gap = 0;
    for (const s of Object.keys(slice.public)) {
      const a = slice.public[s]?.overall?.balanced_accuracy;
      const b = slice.unpublished[s]?.overall?.balanced_accuracy;
      if (typeof a === "number" && typeof b === "number") gap = Math.max(gap, Math.abs(a - b));
    }
    facts.sliceGapMax = round(gap, 1);
  }
  const own = lb.content_views?.systems?.[OWN_ROWS.system];
  if (own?.all_rows && own?.[OWN_ROWS.view]) {
    facts.ownRows = {
      system: OWN_ROWS.system,
      vendor: OWN_ROWS.vendor,
      allRows: round(own.all_rows.balanced_accuracy, 1),
      withoutOwnRows: round(own[OWN_ROWS.view].balanced_accuracy, 1),
    };
  }
  const qf = ranking.find((r) => r.name === QUESTION_FORMAT_SYSTEM);
  if (qf) facts.questionFormat = { system: qf.name, tier: qf.tier, tiers: Math.max(...ranking.map((r) => r.tier)) };
  const la = lb.label_amendment;
  if (la && typeof la.reviewed === "number") {
    facts.labelReview = { minWrong: la.threshold, systems: la.systems, reviewed: la.reviewed, corrected: la.corrected, removed: la.removed };
  }

  const lp = lb.label_provenance;
  if (lp?.content_sample && lp?.prompt_attack_sample) {
    facts.labelAgreement = {
      contentRows: lp.content_sample.rows,
      content: round(lp.content_sample.agreement_population_weighted ?? lp.content_sample.agreement, 3),
      attackRows: lp.prompt_attack_sample.rows,
      attacks: round(lp.prompt_attack_sample.agreement, 3),
    };
  }

  const anyCost = Object.values(runCost).find((v: Json) => typeof v?.checks === "number") as Json;
  const fr = lb.full_run ?? {};
  return {
    source,
    release: { version: RELEASE_VERSION, date: latestDate(lb) },
    stats: {
      checks: fr.rows_total ?? anyCost?.checks ?? 0,
      publicRows: fr.rows_public ?? 0,
      heldBackRows: fr.rows_unpublished ?? 0,
      systems: systems.length,
      suites: SUITE_COUNT,
      jobs: JOBS.length,
      threshold: lb.rules?.headline?.operating_point ?? 0.5,
    },
    systems,
    overall,
    jobs,
    baseline,
    facts,
  };
}

interface LedgerPick {
  outcome: RowResult["outcome"];
  decision: boolean | null;
  score: number | null;
  at: string;
  idsOnly: boolean;
}

function attemptTime(r: Json): string {
  const a = Array.isArray(r.attempts) && r.attempts.length ? r.attempts[r.attempts.length - 1] : null;
  return typeof a?.at === "string" ? a.at : "";
}

/** The record that counts per (system, row): the latest decided one, else the latest one. */
export function readLedgers(dirs: string[], drop: Set<string>) {
  const picks = new Map<string, Map<string, LedgerPick>>(); // row id -> system -> pick
  const idsOnlyRows = new Set<string>();
  for (const dir of dirs) {
    for (const file of listJsonl(dir)) {
      for (const r of readJsonl(file)) {
        const id = r.row_id;
        if (typeof id !== "string" || drop.has(id)) continue;
        if (!JOB_BY_LEDGER_SUBTASK[r.subtask]) continue; // the custom-words sanity check is not a job
        if (r.ids_only_source === true) idsOnlyRows.add(id);
        const pick: LedgerPick = {
          outcome: r.outcome === "decided" ? "decided" : "failed",
          decision: typeof r.decision === "boolean" ? r.decision : null,
          score: typeof r.score === "number" ? round(r.score, 4) : null,
          at: attemptTime(r),
          idsOnly: r.ids_only_source === true,
        };
        let bySystem = picks.get(id);
        if (!bySystem) picks.set(id, (bySystem = new Map()));
        const prev = bySystem.get(r.system);
        const better =
          !prev ||
          (pick.outcome === "decided" && prev.outcome !== "decided") ||
          (pick.outcome === prev.outcome && pick.at >= prev.at);
        if (better) bySystem.set(r.system, pick);
      }
    }
  }
  return { picks, idsOnlyRows };
}

function str(v: unknown): string | null {
  return typeof v === "string" && v.length ? v : null;
}

export interface Generated {
  board: Board;
  index: RowsIndex;
  details: Record<string, RowDetail>;
  summary: { rows: number; withheld: number; withText: number; droppedPrivate: number };
}

export function generate(repo: string, source: Board["source"] = "real"): Generated {
  const p = repoPaths(repo);
  const lb = JSON.parse(fs.readFileSync(p.leaderboard, "utf8"));
  const policy = JSON.parse(fs.readFileSync(p.redistribution, "utf8"));
  const drop = privateIds(p);
  const board = buildBoard(lb, source);
  const systemIds = board.systems.map((s) => s.id);
  const { picks, idsOnlyRows } = readLedgers(p.ledgerDirs, drop);

  const rows: Json[] = [];
  let droppedPrivate = 0;
  for (const f of buildTestFiles(p.buildDir)) {
    for (const r of readJsonl(f)) {
      if (drop.has(r.id) || r.visibility === "private" || r.split !== "test") {
        droppedPrivate++;
        continue;
      }
      if (!ROW_TAG_JOB[r.subtask]) continue;
      rows.push(r);
    }
  }
  const jobOrder = Object.fromEntries(JOBS.map((j, i) => [j.id, i]));
  rows.sort((a, b) => jobOrder[ROW_TAG_JOB[a.subtask]] - jobOrder[ROW_TAG_JOB[b.subtask]] || (a.id < b.id ? -1 : 1));

  const sources = [...new Set(rows.map((r) => r.provenance?.source ?? "unknown"))].sort();
  const sourceIdx = Object.fromEntries(sources.map((s, i) => [s, i]));
  const jobIds = JOBS.map((j) => j.id);

  const lite: RowLite[] = [];
  const details: Record<string, RowDetail> = {};
  let withheld = 0;
  for (const r of rows) {
    const src: string = r.provenance?.source ?? "unknown";
    const job = ROW_TAG_JOB[r.subtask];
    const isWithheld = !textCleared(src, policy) || idsOnlyRows.has(r.id) || r.redistribution === "ids_only";
    if (isWithheld) withheld++;
    const bySystem = picks.get(r.id);
    const results: RowResult[] = systemIds.map((s) => {
      const k = bySystem?.get(s);
      if (!k) return { system: s, outcome: "missing", decision: null, score: null };
      return { system: s, outcome: k.outcome, decision: k.decision, score: k.score };
    });
    const decisions = results
      .map((x) => (x.outcome === "missing" ? "." : x.outcome === "failed" || x.decision === null ? "x" : x.decision ? "1" : "0"))
      .join("");
    const st = r.state ?? {};
    const text = isWithheld ? null : str(st.text);
    const snippetSrc = isWithheld ? null : text ?? str(st.query) ?? str(st.source);
    const snippet = snippetSrc ? (snippetSrc.length > 200 ? snippetSrc.slice(0, 200).trimEnd() + "…" : snippetSrc) : null;
    lite.push([r.id, jobIds.indexOf(job), sourceIdx[src], r.expected === "yes" ? 1 : 0, decisions, isWithheld ? 1 : 0, snippet]);

    const d: RowDetail = {
      id: r.id,
      job,
      source: src,
      licence: str(r.provenance?.licence),
      label: r.expected === "yes" ? "yes" : "no",
      withheld: isWithheld,
      results,
    };
    if (!isWithheld) {
      d.text = text;
      d.role = str(st.role);
      d.context = Array.isArray(st.context)
        ? st.context.filter((t: Json) => typeof t?.text === "string").map((t: Json): Turn => ({ role: String(t.role ?? ""), text: t.text }))
        : [];
      d.query = str(st.query);
      d.document = str(st.source);
      d.toolCall = st.tool_call ? JSON.stringify(st.tool_call, null, 2) : null;
    }
    details[r.id] = d;
  }

  return {
    board,
    index: { systems: systemIds, jobs: jobIds, sources, rows: lite },
    details,
    summary: { rows: rows.length, withheld, withText: rows.length - withheld, droppedPrivate },
  };
}

export function writeGenerated(g: Generated, outDir: string) {
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "board.json"), JSON.stringify(g.board, null, 1) + "\n");
  fs.writeFileSync(path.join(outDir, "rows-index.json"), JSON.stringify(g.index) + "\n");
  fs.writeFileSync(path.join(outDir, "rows-detail.json"), JSON.stringify(g.details) + "\n");
}
