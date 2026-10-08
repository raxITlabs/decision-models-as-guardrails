import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// The site serves a copy of the repo's REPRODUCE.md at /reproduce.md (Vercel deploys site/ alone, so it cannot read
// the parent folder at build time). This keeps the two from drifting.
describe("reproduce.md", () => {
  const repoCopy = path.resolve(__dirname, "../../REPRODUCE.md");
  const siteCopy = path.resolve(__dirname, "../public/reproduce.md");

  it.skipIf(!fs.existsSync(repoCopy))("matches the repository's REPRODUCE.md", () => {
    expect(fs.readFileSync(siteCopy, "utf8")).toBe(fs.readFileSync(repoCopy, "utf8"));
  });
});

describe("source links", () => {
  it("cover every source with withheld rows", async () => {
    const { SOURCES } = await import("../lib/sources");
    const dataDir = fs.existsSync(path.resolve(__dirname, "../data/rows-index.json")) ? "../data" : "../fixtures/data";
    const index = JSON.parse(fs.readFileSync(path.resolve(__dirname, dataDir, "rows-index.json"), "utf8"));
    if (dataDir === "../fixtures/data") return; // synthetic sources have no upstream
    const withheld = new Set<string>(index.rows.filter((r: unknown[]) => r[5] === 1).map((r: number[]) => index.sources[r[2]]));
    expect([...withheld].filter((s) => !SOURCES[s])).toEqual([]);
  });
});
