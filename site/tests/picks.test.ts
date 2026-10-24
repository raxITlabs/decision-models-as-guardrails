import { describe, expect, it } from "vitest";
import { pickFor, tierGroups } from "../lib/picks";
import type { Score } from "../lib/types";

const row = (system: string, rank: number, tier: number, score: number, falseBlockRate: number, cost: number | null): Score => ({
  system, rank, tier, score, ciLow: score - 1, ciHigh: score + 1, catchRate: 0.9, falseBlockRate, cost,
});

const rows = [
  row("a", 1, 1, 90.4, 0.079, 0.056),
  row("b", 2, 1, 90.0, 0.123, 0.11),
  row("c", 3, 1, 89.4, 0.112, 0.026),
  row("d", 4, 2, 88.7, 0.05, 0.001),
];

describe("pickFor", () => {
  it("only picks inside the top tier", () => {
    expect(pickFor(rows, "accuracy")).toEqual({ system: "a", lens: "accuracy", tier: 1, tiedWith: ["b", "c"] });
    expect(pickFor(rows, "false_blocks")?.system).toBe("a");
    expect(pickFor(rows, "cost")?.system).toBe("c");          // d is cheaper but in tier 2
  });
  it("skips rows without a cost, and returns nothing for no rows", () => {
    expect(pickFor([row("x", 1, 1, 80, 0.1, null), row("y", 2, 1, 79, 0.1, 0.3)], "cost")?.system).toBe("y");
    expect(pickFor([row("x", 1, 1, 80, 0.1, null)], "cost")).toBeNull();
    expect(pickFor([], "accuracy")).toBeNull();
  });
});

describe("tierGroups", () => {
  it("groups consecutive rows of one tier", () => {
    expect(tierGroups([{ tier: 1 }, { tier: 1 }, { tier: 2 }, { tier: 8 }])).toEqual([
      { tier: 1, first: 0, count: 2 },
      { tier: 2, first: 2, count: 1 },
      { tier: 8, first: 3, count: 1 },
    ]);
  });
});
