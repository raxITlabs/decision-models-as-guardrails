import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { LAYER_SWEEP, STUDY } from "../app/research/linear-probe/data";

// The probe-study charts hard-code their numbers; this keeps them tied to the published files.
const ROOT = join(__dirname, "../public/research/linear-probe");
const DIRS = { strands: ROOT, kev: join(ROOT, "kev-4b") } as const;
const NAMES = { "Native @0.5": "fixed", "Native tuned": "tuned", MM: "massMean", LR: "probe", "Text n-gram": "text", "Shuffled-label LR": "shuffled" } as const;

describe("linear-probe study data", () => {
  for (const [key, dir] of Object.entries(DIRS) as [keyof typeof DIRS, string][]) {
    it(`${key} matches test_metrics_with_intervals.csv`, () => {
      const [head, ...lines] = readFileSync(join(dir, "test_metrics_with_intervals.csv"), "utf8").trim().split("\n");
      const cols = head.split(",");
      for (const line of lines) {
        const row = Object.fromEntries(line.split(",").map((v, i) => [cols[i], v]));
        const arm = STUDY[key].arms[NAMES[row.model as keyof typeof NAMES]];
        expect(arm.ba).toBeCloseTo(Number(row.balanced_accuracy), 3);
        expect(arm.low).toBeCloseTo(Number(row.BA_low), 3);
        expect(arm.high).toBeCloseTo(Number(row.BA_high), 3);
        expect(arm.missed).toBe(Math.round(256 * (1 - Number(row.catch_rate))));
        expect(arm.falseBlocks).toBe(Math.round(284 * Number(row.false_block_rate)));
      }
    });
    it(`${key} matches paired_probe_minus_tuned_native.json`, () => {
      const paired = JSON.parse(readFileSync(join(dir, "paired_probe_minus_tuned_native.json"), "utf8"));
      for (const [arm, src] of [["probe", "LR"], ["massMean", "MM"]] as const) {
        expect(STUDY[key].gain[arm].diff).toBeCloseTo(paired[src].BA_difference, 3);
        expect(STUDY[key].gain[arm].low).toBeCloseTo(paired[src].low, 3);
        expect(STUDY[key].gain[arm].high).toBeCloseTo(paired[src].high, 3);
      }
    });
  }
  for (const [key, dir] of Object.entries(DIRS) as [keyof typeof DIRS, string][]) {
    it(`${key} layer sweep matches validation_search.csv`, () => {
      const [head, ...lines] = readFileSync(join(dir, "validation_search.csv"), "utf8").trim().split("\n");
      const cols = head.split(",");
      const best = new Map<string, number>();
      for (const line of lines) {
        const row = Object.fromEntries(line.split(",").map((v, i) => [cols[i], v]));
        const id = `${row.layer}|${row.kind}:${row.feature}`;
        best.set(id, Math.max(best.get(id) ?? 0, Number(row.validation_AUROC)));
      }
      const sel = JSON.parse(readFileSync(join(dir, "frozen_selection.json"), "utf8")).probes.LR;
      expect(LAYER_SWEEP[key].selected).toBe(sel.layer);
      for (const row of LAYER_SWEEP[key].rows)
        for (const [k, v] of Object.entries(row)) if (k !== "layer") expect(v).toBeCloseTo(best.get(`${row.layer}|${k}`)!, 3);
      expect(LAYER_SWEEP[key].rows.length * 4).toBe(new Set([...best.keys()]).size);
    });
  }
});
