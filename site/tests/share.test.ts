import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { SHARE_SIZE_IDS, SHARE_SIZES, SHARE_VIEWS, isShareView, shareCard, shareFile, shareLink } from "../lib/share";
import { lineageSummaries, supersededBy } from "../lib/versions";
import type { Board, VersionsDoc } from "../lib/types";

const dir = fs.existsSync(path.join(__dirname, "..", "data", "board.json")) ? "data" : path.join("fixtures", "data");
const board: Board = JSON.parse(fs.readFileSync(path.join(__dirname, "..", dir, "board.json"), "utf8"));
const vp = path.join(__dirname, "..", dir, "versions.json");
const versions: VersionsDoc | null = fs.existsSync(vp) ? JSON.parse(fs.readFileSync(vp, "utf8")) : null;
const older = supersededBy(lineageSummaries(versions));

describe("shareCard", () => {
  it("covers every view and size, newest versions only, within the row budget", () => {
    for (const view of SHARE_VIEWS)
      for (const size of SHARE_SIZE_IDS) {
        const c = shareCard(board, older, view, size);
        expect(c.rows.length).toBeLessThanOrEqual(SHARE_SIZES[size].rows);
        expect(c.rows.length).toBeGreaterThan(0);
        expect(c.rows.some((r) => older[r.system])).toBe(false);
        expect(c.rows[0].rank).toBe(1);
        expect(c.rows.every((r) => r.ciLow <= r.score && r.score <= r.ciHigh)).toBe(true);
        expect(c.footer.site).toBe("dm-as-guardrails.raxitlabs.com");
        expect(c.alt.length).toBeGreaterThan(20);
      }
  });

  it("names files and links per view", () => {
    expect(shareFile("overall", "square")).toBe("/share/overall/square.png");
    expect(shareLink("overall")).toMatch(/#leaderboard$/);
    expect(shareLink("pii")).toContain("?case=pii");
    expect(isShareView("pii")).toBe(true);
    expect(isShareView("nope")).toBe(false);
  });
});
