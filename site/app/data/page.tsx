import type { Metadata } from "next";
import { DataExplorer } from "@/components/data-explorer";
import { ContentWarning } from "@/components/sensitive";
import { loadBoard } from "@/lib/data";
import { int } from "@/lib/format";

export const metadata: Metadata = {
  title: "Data",
  description: "Every public test row in the benchmark, each system's answer to it, and a heatmap of scores by use case.",
  alternates: { canonical: "/data" },
  openGraph: { url: "/data", siteName: "decision-models-as-guardrails", type: "website", images: [{ url: "/opengraph-image", width: 1200, height: 630 }] },
};

export default function DataPage() {
  const board = loadBoard();
  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-10 px-4 pt-10 sm:px-6 sm:pt-16">
      <header className="flex flex-col gap-4">
        <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Data</span>
        <h1 className="m-0 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">Browse the data</h1>
        <p className="m-0 max-w-[68ch] text-[17px] leading-relaxed text-fg-2">
          Every public test row and every system&apos;s answer to it. Start at the heatmap to find where a system is weak. Then open the
          rows behind the number. The scores also include a held-back slice of {int(board.stats.heldBackRows)} rows. We keep that slice
          private and do not list it here.
        </p>
      </header>
      <ContentWarning />
      <DataExplorer board={board} />
    </div>
  );
}
