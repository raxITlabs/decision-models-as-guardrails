import { describe, expect, it } from "vitest";
import { caseFromSearch, downloadName } from "../components/share-panel";
import { SHARE_VIEWS, shareLink } from "../lib/share";

describe("share panel helpers", () => {
  it("reads a known use case from ?case= and ignores anything else", () => {
    for (const v of SHARE_VIEWS) expect(caseFromSearch(new URL(shareLink(v)).search) ?? "overall").toBe(v);
    expect(caseFromSearch("")).toBeNull();
    expect(caseFromSearch("?case=nope")).toBeNull();
    expect(caseFromSearch("?case=")).toBeNull();
  });
  it("names downloads by view and size", () => {
    expect(downloadName("overall", "square")).toBe("raxit-guardrails-overall-square.png");
  });
});
