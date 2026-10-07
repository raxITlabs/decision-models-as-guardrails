import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { generate, hasRealInputs, textCleared } from "../scripts/generate";
import { JOBS } from "../lib/jobs";

const FIXTURE = path.join(__dirname, "..", "fixtures", "source");

describe("generator on the synthetic fixture", () => {
  const g = generate(FIXTURE, "fixture");

  it("finds the fixture inputs", () => {
    expect(hasRealInputs(FIXTURE)).toBe(true);
  });

  it("builds a board with every system and every job", () => {
    expect(g.board.source).toBe("fixture");
    expect(g.board.release.version).toBe("1.0.0");
    expect(g.board.systems.map((s) => s.id)).toEqual(g.board.overall.map((s) => s.system));
    for (const job of JOBS) expect(g.board.jobs[job.id].length).toBe(g.board.systems.length);
    expect(g.board.stats.jobs).toBe(8);
    expect(g.board.stats.suites).toBe(6);
    expect(g.board.stats.threshold).toBe(0.5);
  });

  it("marks hosting from the cost records", () => {
    const hosting = Object.fromEntries(g.board.systems.map((s) => [s.id, s.hosting]));
    expect(hosting["fixture-alpha"]).toBe("managed");
    expect(hosting["fixture-charlie"]).toBe("managed");
    expect(hosting["fixture-delta"]).toBe("self-hosted");
  });

  it("keeps public rows of the eight jobs only, with one decision per system", () => {
    expect(g.index.rows.length).toBe(48); // 8 jobs x 6 public rows; the custom-word rows are not a job
    for (const r of g.index.rows) {
      expect(r[4].length).toBe(g.index.systems.length);
      expect(r[0]).not.toMatch(/held/);
    }
  });

  it("ships text only for sources cleared for text", () => {
    for (const d of Object.values(g.details)) {
      if (d.source === "synthetic_open") {
        expect(d.withheld).toBe(false);
        expect(d.text).toMatch(/^Synthetic example/);
      } else {
        expect(d.withheld).toBe(true);
        expect(d.text).toBeUndefined();
        expect(d.context).toBeUndefined();
      }
    }
  });

  it("never copies latency or other run internals", () => {
    const s = JSON.stringify(g);
    expect(s).not.toMatch(/latency/i);
    expect(s).not.toMatch(/attempts/);
  });

  it("treats a text source as withheld until its licence review is recorded", () => {
    const pol = { sources: { a: { mode: "text", reviewed: true }, b: { mode: "text", reviewed: false }, c: { mode: "ids_only", reviewed: true } } };
    expect(textCleared("a", pol)).toBe(true);
    expect(textCleared("b", pol)).toBe(false);
    expect(textCleared("c", pol)).toBe(false);
    expect(textCleared("missing", pol)).toBe(false);
  });

  it("keeps the latest decided record when a row was retried", () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dmag-"));
    fs.cpSync(FIXTURE, tmp, { recursive: true });
    const ledger = path.join(tmp, "benchmark/results/final/ledgers/main-run/fixture-alpha.jsonl");
    const lines = fs.readFileSync(ledger, "utf8").trim().split("\n").map((l) => JSON.parse(l));
    const first = lines[0];
    const failed = { ...first, outcome: "failed", decision: null, score: null, attempts: [{ at: "2026-01-02T00:00:00Z" }] };
    const decided = { ...first, outcome: "decided", decision: true, score: 0.9, attempts: [{ at: "2026-01-01T12:00:00Z" }] };
    fs.writeFileSync(ledger, [...lines.slice(1), decided, failed].map((l) => JSON.stringify(l)).join("\n") + "\n");
    const g2 = generate(tmp, "fixture");
    const res = g2.details[first.row_id].results.find((r) => r.system === "fixture-alpha");
    expect(res?.outcome).toBe("decided");
    expect(res?.score).toBe(0.9);
  });
});
