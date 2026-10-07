// Build-time data access. Reads the generated site/data/ (real results, release day) when present, else the
// synthetic fixtures/data/. Server only: pages import this during prerendering.
import "server-only";
import fs from "node:fs";
import path from "node:path";
import type { Board, RowDetail, RowsIndex } from "./types";

const SITE = process.cwd();
const REAL = path.join(SITE, "data");
const FIXTURE = path.join(SITE, "fixtures", "data");

let logged = false;
function dataDir(): string {
  const real = fs.existsSync(path.join(REAL, "board.json"));
  if (!logged) {
    logged = true;
    console.log(
      real
        ? "[site] using real results from site/data/"
        : "[site] site/data/ not found: using the synthetic fixture in fixtures/data/ (names and numbers are fake)",
    );
  }
  return real ? REAL : FIXTURE;
}

const cache = new Map<string, unknown>();
function read<T>(file: string): T {
  const p = path.join(dataDir(), file);
  if (!cache.has(p)) cache.set(p, JSON.parse(fs.readFileSync(p, "utf8")));
  return cache.get(p) as T;
}

export const loadBoard = () => read<Board>("board.json");
export const loadRowsIndex = () => read<RowsIndex>("rows-index.json");
export const loadRowDetails = () => read<Record<string, RowDetail>>("rows-detail.json");
