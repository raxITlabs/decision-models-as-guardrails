// Shapes of the generated data in site/data/ (and the synthetic copy in fixtures/data/).
import type { JobId } from "./jobs";

export type Hosting = "managed" | "self-hosted";

export interface SystemMeta {
  id: string;
  name: string;
  provider: string;
  hosting: Hosting;
  /** two-letter monogram for compact marks */
  mono: string;
}

export interface Score {
  system: string;
  rank: number;
  tier: number;
  /** balanced accuracy x 100 */
  score: number;
  ciLow: number;
  ciHigh: number;
  /** 0..1 */
  catchRate: number;
  /** 0..1 */
  falseBlockRate: number;
  /** USD per 1,000 checks; null when not measured */
  cost: number | null;
}

export interface Baseline {
  /** row tag, e.g. injection, jailbreak, leakage, indirect */
  tag: string;
  job: JobId;
  /** keyword (regex) classifier, balanced accuracy x 100 */
  keyword: number;
  /** best word or character n-gram classifier, balanced accuracy x 100 */
  best: number;
}

export interface Facts {
  /** largest gap, in points, between a system's overall score on the held-back slice and on public rows */
  sliceGapMax?: number;
  /** a vendor model scored with and without rows from the vendor's own dataset */
  ownRows?: { system: string; vendor: string; allRows: number; withoutOwnRows: number };
  /** overall tier of the system whose native question format every model receives */
  questionFormat?: { system: string; tier: number; tiers: number };
  /** rows re-checked after the runs because nearly every system got them wrong */
  labelReview?: { minWrong: number; systems: number; reviewed: number; corrected: number; removed: number };
  /** agreement (0..1) of the second-label samples with the reference labels */
  labelAgreement?: { contentRows: number; content: number; attackRows: number; attacks: number };
}

export interface Board {
  source: "real" | "fixture";
  release: { version: string; date: string };
  stats: {
    checks: number;
    publicRows: number;
    heldBackRows: number;
    systems: number;
    suites: number;
    jobs: number;
    threshold: number;
  };
  systems: SystemMeta[];
  overall: Score[];
  jobs: Record<JobId, Score[]>;
  baseline: Baseline[];
  facts: Facts;
}

/** One public row in the row browser: [id, job index, source index, label (1 = should block), decisions, withheld (1/0), snippet] */
export type RowLite = [string, number, number, 0 | 1, string, 0 | 1, string | null];

export interface RowsIndex {
  /** system ids, in the order of each row's decisions string */
  systems: string[];
  jobs: JobId[];
  sources: string[];
  /** per system: "1" blocked, "0" passed, "x" failed, "." no record */
  rows: RowLite[];
}

export interface RowResult {
  system: string;
  outcome: "decided" | "failed" | "missing";
  decision: boolean | null;
  /** the system's score for the row (a probability for decision models), when it returns one */
  score: number | null;
}

export interface Turn {
  role: string;
  text: string;
}

export interface RowDetail {
  id: string;
  job: JobId;
  source: string;
  licence: string | null;
  label: "yes" | "no";
  withheld: boolean;
  /** present only when the source licence allows the text to be published */
  text?: string | null;
  role?: string | null;
  context?: Turn[];
  query?: string | null;
  document?: string | null;
  toolCall?: string | null;
  results: RowResult[];
}
