// The row browser's index, emitted as a static file at build time (/data/rows-index.json).
import { loadRowsIndex } from "@/lib/data";

export const dynamic = "force-static";

export function GET() {
  return Response.json(loadRowsIndex());
}
