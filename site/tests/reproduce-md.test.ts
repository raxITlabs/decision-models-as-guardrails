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
