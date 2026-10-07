// Fails when generated data holds an unpublished id, a held-back row's text, or text whose licence is withheld.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { generate, hasRealInputs, writeGenerated } from "../scripts/generate";
import { findLeaks, withheldTexts } from "../scripts/privacy";

const SITE = path.join(__dirname, "..");
const FIXTURE = path.join(SITE, "fixtures", "source");
const REPO = path.join(SITE, "..");
const REAL_DATA = path.join(SITE, "data");

const clean = { privateIds: [], withheldText: [], privateText: [] };

describe("privacy: synthetic fixture", () => {
  it("the committed fixture data holds no private id or withheld text", () => {
    expect(findLeaks(FIXTURE, path.join(SITE, "fixtures", "data"))).toEqual(clean);
  });

  it("the check itself catches a leak", () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dmag-leak-"));
    const withheld = withheldTexts(FIXTURE)[0];
    expect(withheld).toMatch(/WITHHELD-LICENCE/);
    fs.writeFileSync(path.join(tmp, "x.json"), JSON.stringify({ a: "fx-input-held-06", b: withheld }));
    const leaks = findLeaks(FIXTURE, tmp);
    expect(leaks.privateIds).toContain("fx-input-held-06");
    expect(leaks.withheldText.length).toBe(1);
  });

  it("drops a held-back row even when it turns up among the public rows", () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "dmag-src-"));
    fs.cpSync(FIXTURE, tmp, { recursive: true });
    const held = fs.readFileSync(path.join(tmp, "dataset/edition2/build/private/F1.test.jsonl"), "utf8");
    fs.appendFileSync(path.join(tmp, "dataset/edition2/build/F1.test.jsonl"), held.replaceAll('"private"', '"public"'));
    const out = path.join(tmp, "out");
    writeGenerated(generate(tmp, "fixture"), out);
    expect(findLeaks(tmp, out)).toEqual(clean);
  });
});

describe.skipIf(!fs.existsSync(path.join(REAL_DATA, "board.json")) || !hasRealInputs(REPO))("privacy: real data in site/data", () => {
  it("holds no unpublished id, held-back text or withheld text", () => {
    const leaks = findLeaks(REPO, REAL_DATA);
    expect(leaks.privateIds.slice(0, 5)).toEqual([]);
    expect(leaks.privateText.slice(0, 5)).toEqual([]);
    expect(leaks.withheldText.slice(0, 5)).toEqual([]);
  });
});
