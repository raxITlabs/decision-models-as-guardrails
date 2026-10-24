// "Recommend for": one row picked from the top tier on show. The top tier is the set of systems the board's tests cannot
// tell apart from the leader, so within it a second criterion is a fair way to choose. Pure, so tests can check it.
import type { Score } from "./types";

export type Lens = "accuracy" | "false_blocks" | "cost";

export interface Pick {
  system: string;
  lens: Lens;
  tier: number;
  /** the other systems in the same tier, in rank order */
  tiedWith: string[];
}

const byRank = (a: Score, b: Score) => a.rank - b.rank;

export function pickFor(rows: Score[], lens: Lens): Pick | null {
  if (!rows.length) return null;
  const tier = Math.min(...rows.map((r) => r.tier));
  const top = rows.filter((r) => r.tier === tier).sort(byRank);
  let best: Score | undefined;
  if (lens === "accuracy") best = top[0];
  else if (lens === "false_blocks") best = [...top].sort((a, b) => a.falseBlockRate - b.falseBlockRate || byRank(a, b))[0];
  else best = top.filter((r) => r.cost !== null).sort((a, b) => (a.cost as number) - (b.cost as number) || byRank(a, b))[0];
  if (!best) return null;
  return { system: best.system, lens, tier, tiedWith: top.filter((r) => r.system !== best.system).map((r) => r.system) };
}

/** Tier headings for the rows on show, in order: the tier, how many rows it has, and any tiers skipped before it. */
export function tierGroups(rows: { tier: number }[]): { tier: number; first: number; count: number; skipped: number[] }[] {
  const out: { tier: number; first: number; count: number; skipped: number[] }[] = [];
  rows.forEach((r, i) => {
    const last = out.at(-1);
    if (last && last.tier === r.tier) {
      last.count += 1;
      return;
    }
    const skipped = last ? Array.from({ length: Math.max(0, r.tier - last.tier - 1) }, (_, k) => last.tier + 1 + k) : [];
    out.push({ tier: r.tier, first: i, count: 1, skipped });
  });
  return out;
}
