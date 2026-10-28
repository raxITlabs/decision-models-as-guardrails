/** Per use case, the leaderboard's first few systems (newest versions only), and one system followed across them. */

export interface Podium<S> {
  job: string;
  top: S[];
}

export function podiums<S extends { system: string; rank: number }>(
  jobs: { id: string }[],
  rankings: Record<string, S[]>,
  hide: Record<string, string> = {},
  n = 5,
): Podium<S>[] {
  return jobs.map((j) => ({
    job: j.id,
    top: [...(rankings[j.id] ?? [])].filter((s) => !hide[s.system]).sort((a, b) => a.rank - b.rank).slice(0, n),
  }));
}

/** How one system places across the podiums: use cases it leads, and use cases where it makes the first few. */
export function follow(rows: Podium<{ system: string }>[], system: string): { first: number; inTop: number; of: number } {
  return {
    first: rows.filter((r) => r.top[0]?.system === system).length,
    inTop: rows.filter((r) => r.top.some((s) => s.system === system)).length,
    of: rows.length,
  };
}
