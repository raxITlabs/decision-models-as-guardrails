import { describe, expect, it } from "vitest";
import { chartSystems, logAxis } from "../lib/chart";

const rows = Array.from({ length: 14 }, (_, i) => ({ system: `s${i + 1}`, rank: i + 1 }));
const meta: Record<string, { kind?: string; hosting?: string }> = Object.fromEntries(
  rows.map((r) => [r.system, { kind: "decision", hosting: Number(r.system.slice(1)) % 3 === 0 ? "self-hosted" : "managed" }]),
);
meta.s13 = { kind: "service", hosting: "managed" };

describe("chartSystems", () => {
  it("draws the top ten plus the guardrail service by default", () => {
    expect(chartSystems(rows, "top", meta).map((r) => r.system)).toEqual([...rows.slice(0, 10).map((r) => r.system), "s13"]);
  });
  it("keeps a selected system wherever it ranks", () => {
    expect(chartSystems(rows, "top", meta, ["s14"]).map((r) => r.system)).toContain("s14");
  });
  it("shows managed APIs or everything when asked", () => {
    expect(chartSystems(rows, "managed", meta).every((r) => meta[r.system].hosting === "managed")).toBe(true);
    expect(chartSystems(rows, "all", meta)).toHaveLength(14);
  });
});

describe("logAxis", () => {
  it("spans the values on 1-2-5 ticks", () => {
    const a = logAxis([0.013, 0.027, 0.2018]);
    expect(a.lo).toBeLessThanOrEqual(0.013 / 1.8);
    expect(a.hi).toBeGreaterThanOrEqual(0.2018 * 1.15);
    expect(a.ticks).toEqual([0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]);
  });
  it("drops the 2s on a crowded axis when sparse", () => {
    const a = logAxis([0.013, 0.96], true);
    expect(a.ticks).toEqual([0.005, 0.01, 0.05, 0.1, 0.5, 1, 5].filter((t) => t >= a.lo && t <= a.hi));
  });
  it("ignores zero and missing costs", () => {
    expect(logAxis([0, 0.05]).ticks.length).toBeGreaterThan(0);
  });
});
