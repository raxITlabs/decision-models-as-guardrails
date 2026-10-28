import { describe, expect, it } from "vitest";
import { follow, podiums } from "../lib/leaders";

const jobs = [{ id: "a" }, { id: "b" }];
const r = (system: string, rank: number) => ({ system, rank });
const rankings = {
  a: [r("x", 2), r("old", 1), r("y", 3), r("z", 4)],
  b: [r("y", 1), r("x", 2), r("z", 3)],
};

describe("podiums", () => {
  it("takes the first n per use case in rank order, earlier versions left out", () => {
    const p = podiums(jobs, rankings, { old: "x" }, 2);
    expect(p.map((x) => x.top.map((s) => s.system))).toEqual([["x", "y"], ["y", "x"]]);
  });
});

describe("follow", () => {
  it("counts the use cases a system leads and the ones it places in", () => {
    const p = podiums(jobs, rankings, { old: "x" }, 2);
    expect(follow(p, "x")).toEqual({ first: 1, inTop: 2, of: 2 });
    expect(follow(p, "z")).toEqual({ first: 0, inTop: 0, of: 2 });
  });
});
