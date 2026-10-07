// Leak check for generated site data: no unpublished id and no licence-withheld text may appear in it.
import fs from "node:fs";
import path from "node:path";
import { buildTestFiles, privateIds, readJsonl, readLedgers, repoPaths, textCleared } from "./generate";

/* eslint-disable @typescript-eslint/no-explicit-any */

/** Every text field of every public row whose text may not be published (whole field values, 20+ characters). */
export function withheldTexts(repo: string): string[] {
  const p = repoPaths(repo);
  const policy = JSON.parse(fs.readFileSync(p.redistribution, "utf8"));
  const { idsOnlyRows } = readLedgers(p.ledgerDirs, new Set());
  const out: string[] = [];
  for (const f of buildTestFiles(p.buildDir)) {
    for (const r of readJsonl(f)) {
      const src = r.provenance?.source;
      if (textCleared(src, policy) && !idsOnlyRows.has(r.id) && r.redistribution !== "ids_only") continue;
      const st = r.state ?? {};
      const fields = [st.text, st.query, st.source, ...(Array.isArray(st.context) ? st.context.map((t: any) => t?.text) : [])];
      for (const t of fields) if (typeof t === "string" && t.trim().length >= 20) out.push(t.trim());
    }
  }
  return out;
}

/** Text of every held-back row (build private/ folder), so a leak of its wording is caught too. */
export function privateTexts(repo: string): string[] {
  const dir = path.join(repoPaths(repo).buildDir, "private");
  if (!fs.existsSync(dir)) return [];
  const out: string[] = [];
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith(".jsonl"))) {
    for (const r of readJsonl(path.join(dir, f))) {
      const t = r?.state?.text;
      if (typeof t === "string" && t.trim().length >= 20) out.push(t.trim());
    }
  }
  return out;
}

function collectStrings(v: unknown, out: string[]) {
  if (typeof v === "string") out.push(v);
  else if (Array.isArray(v)) for (const x of v) collectStrings(x, out);
  else if (v && typeof v === "object") for (const [k, x] of Object.entries(v)) {
    out.push(k);
    collectStrings(x, out);
  }
}

export interface Leaks {
  privateIds: string[];
  withheldText: string[];
  privateText: string[];
}

/** Scan every .json file in dataDir against the repo's private ids, withheld texts and held-back texts. */
export function findLeaks(repo: string, dataDir: string): Leaks {
  const p = repoPaths(repo);
  const ids = privateIds(p);
  const strings: string[] = [];
  for (const f of fs.readdirSync(dataDir).filter((x) => x.endsWith(".json"))) {
    collectStrings(JSON.parse(fs.readFileSync(path.join(dataDir, f), "utf8")), strings);
  }
  const corpus = strings.filter((s) => s.length >= 20).join("\u0000");
  const tokens = new Set<string>();
  for (const s of strings) for (const t of s.split(/[^A-Za-z0-9_.:-]+/)) if (t) tokens.add(t);
  return {
    privateIds: [...ids].filter((id) => tokens.has(id) || corpus.includes(id)),
    withheldText: withheldTexts(repo).filter((t) => corpus.includes(t)),
    privateText: privateTexts(repo).filter((t) => corpus.includes(t)),
  };
}
