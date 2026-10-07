// Row details ship as a fixed number of JSON shards so the export stays small (one static row page, not thousands).
export const SHARDS = 64;

/** FNV-1a hash of the row id, modulo SHARDS. Same result on the server and in the browser. */
export function shardOf(id: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h % SHARDS;
}

export const shardFile = (n: number) => `${String(n).padStart(2, "0")}.json`;
export const shardUrl = (id: string) => `/data/shards/${shardFile(shardOf(id))}`;
