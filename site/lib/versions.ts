// The leaderboard's view of version progress: which systems are earlier versions of another, and the change at each
// step. Built from site/data/versions.json (benchmark/runs/e2_versions.py); pure, so pages and tests can share it.
import { JOBS } from "./jobs";
import type { Delta, LineageSummary, VersionChange, VersionsDoc } from "./types";

const change = (d: Delta, scale = 1): VersionChange => ({
  point: d.point * scale,
  low: d.ci.low * scale,
  high: d.ci.high * scale,
  verdict: d.verdict,
});

/** Lineages with at least two scored versions, each with its consecutive steps (never the first-to-last span). */
export function lineageSummaries(doc: VersionsDoc | null): LineageSummary[] {
  if (!doc) return [];
  return doc.lineages
    .filter((l) => l.versions.length > 1)
    .map((l) => ({
      key: l.key,
      versions: l.versions,
      steps: l.comparisons
        .filter((c) => c.kind === "step")
        .map((c) => ({
          from: c.from,
          to: c.to,
          score: change(c.overall.balanced_accuracy),
          catches: change(c.overall.catch_rate, 100),
          falseBlocks: change(c.overall.false_block_rate, 100),
          jobs: Object.fromEntries(JOBS.filter((j) => c.subtasks[j.key]).map((j) => [j.id, change(c.subtasks[j.key])])),
        })),
    }));
}

/** {earlier version: the newest version of its model}, for every version that is not the newest. */
export function supersededBy(lineages: LineageSummary[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const l of lineages) for (const v of l.versions.slice(0, -1)) out[v] = l.versions.at(-1) as string;
  return out;
}
