import type { Metadata } from "next";
import { RowView } from "@/components/row-view";
import { loadBoard, loadRowDetails } from "@/lib/data";

// One static shell serves every row: /data/rows/<id> is rewritten to /data/rows/view (vercel.json, public/serve.json)
// and the page loads the row from its JSON shard. Prerendering a page per row would write tens of thousands of files.
// In development every id is listed so links work without the rewrite.
export const dynamicParams = false;

export function generateStaticParams() {
  const shell = [{ id: "view" }];
  if (process.env.NODE_ENV !== "development") return shell;
  return [...shell, ...Object.keys(loadRowDetails()).map((id) => ({ id }))];
}

export const metadata: Metadata = {
  title: "Row",
  description: "One benchmark row: its text where the licence allows, its label, and every system's answer.",
};

export default function RowPage() {
  const board = loadBoard();
  return <RowView board={board} />;
}
