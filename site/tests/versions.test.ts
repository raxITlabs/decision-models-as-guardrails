import { describe, expect, it } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { lineageSummaries, supersededBy, visibleRanks } from "../lib/versions";
import type { VersionsDoc } from "../lib/types";

describe("visibleRanks", () => {
  it("renumbers the rows on show and keeps ties together", () => {
    const shown = [
      { system: "a", rank: 1 },
      { system: "b", rank: 2 },
      { system: "c", rank: 2 },
      { system: "d", rank: 5 },
    ];
    expect(visibleRanks(shown)).toEqual({ a: 1, b: 2, c: 2, d: 4 });
  });
});

describe("lineage summaries", () => {
  const p = path.join(__dirname, "..", "data", "versions.json");
  const doc: VersionsDoc | null = fs.existsSync(p) ? JSON.parse(fs.readFileSync(p, "utf8")) : null;

  it("folds every version but the newest, and keeps only consecutive steps", () => {
    if (!doc) return;
    const ls = lineageSummaries(doc);
    expect(ls.every((l) => l.versions.length > 1)).toBe(true);
    const older = supersededBy(ls);
    for (const l of ls) {
      expect(older[l.versions.at(-1) as string]).toBeUndefined();
      for (const v of l.versions.slice(0, -1)) expect(older[v]).toBe(l.versions.at(-1));
      expect(l.steps.length).toBe(l.versions.length - 1);
      expect(l.steps.every((s) => s.score.low <= s.score.point && s.score.point <= s.score.high)).toBe(true);
    }
  });

  it("carries no row ids", () => {
    if (!doc) return;
    expect(JSON.stringify(doc)).not.toMatch(/"f[1-6]-[a-z0-9_]+-[0-9a-f]{10}"/);
  });
});

describe("no version data", () => {
  it("gives no lineages", () => {
    expect(lineageSummaries(null)).toEqual([]);
  });
});
