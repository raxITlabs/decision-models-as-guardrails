/** Which systems the leaderboard chart draws, and its log cost axis. */

export type ChartScope = "top" | "managed" | "all";

/** The chart's default: the top systems by rank, plus the guardrail service as the reference and any system the page
 *  points at (the selected one, a recommendation), so nothing the reader picked disappears from the chart. */
export function chartSystems<T extends { system: string; rank: number }>(
  rows: T[],
  scope: ChartScope,
  meta: Record<string, { kind?: string; hosting?: string } | undefined>,
  keep: (string | undefined)[] = [],
  top = 10,
): T[] {
  if (scope === "all") return rows;
  if (scope === "managed") return rows.filter((r) => meta[r.system]?.hosting === "managed");
  const best = new Set([...rows].sort((a, b) => a.rank - b.rank).slice(0, top).map((r) => r.system));
  const pinned = new Set(keep.filter(Boolean));
  return rows.filter((r) => best.has(r.system) || pinned.has(r.system) || meta[r.system]?.kind === "service");
}

const STEPS = [1, 2, 5];

/** A log axis from just below the cheapest to just above the dearest value, on 1-2-5 ticks. `sparse` keeps only the
 *  1s and 5s when the axis would carry more than five ticks. Values of zero or less are ignored. */
export function logAxis(values: number[], sparse = false): { lo: number; hi: number; ticks: number[] } {
  const v = values.filter((x) => x > 0);
  if (!v.length) return { lo: 0.01, hi: 1, ticks: [0.01, 0.1, 1] };
  const min = Math.min(...v) / 1.8;   // room on the left for the cheapest systems' labels
  const max = Math.max(...v) * 1.15;
  const all: number[] = [];
  for (let e = Math.floor(Math.log10(min)) - 1; e <= Math.ceil(Math.log10(max)) + 1; e++) {
    for (const s of STEPS) all.push(Number((s * 10 ** e).toPrecision(3)));
  }
  const lo = [...all].reverse().find((t) => t <= min) ?? min;
  const hi = all.find((t) => t >= max) ?? max;
  let ticks = all.filter((t) => t >= lo && t <= hi);
  if (sparse && ticks.length > 5) ticks = ticks.filter((t) => !String(t).replace(/0|\./g, "").startsWith("2"));
  return { lo, hi, ticks };
}
