// Row details, split into SHARDS static JSON files (/data/shards/00.json ... 63.json).
import { loadRowDetails } from "@/lib/data";
import { SHARDS, shardFile, shardOf } from "@/lib/shard";
import type { RowDetail } from "@/lib/types";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return Array.from({ length: SHARDS }, (_, i) => ({ shard: shardFile(i) }));
}

export async function GET(_req: Request, ctx: RouteContext<"/data/shards/[shard]">) {
  const { shard } = await ctx.params;
  const n = Number.parseInt(shard, 10);
  const out: Record<string, RowDetail> = {};
  for (const [id, d] of Object.entries(loadRowDetails())) if (shardOf(id) === n) out[id] = d;
  return Response.json(out);
}
