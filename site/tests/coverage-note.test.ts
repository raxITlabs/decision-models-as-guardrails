import { describe, expect, it } from "vitest";
import { coverageNote } from "../lib/coverage";

describe("coverageNote", () => {
  it("names one suite and the count", () => {
    expect(coverageNote(["content"])).toBe("Content only · 1 of 6 suites");
  });
  it("lists several suites", () => {
    expect(coverageNote(["content", "prompt_attacks"])).toBe("Content and prompt attacks · 2 of 6 suites");
  });
});
