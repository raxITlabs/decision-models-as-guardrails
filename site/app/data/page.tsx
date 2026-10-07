import type { Metadata } from "next";
import { DataExplorer } from "@/components/data-explorer";
import { loadBoard } from "@/lib/data";
import { int } from "@/lib/format";

export const metadata: Metadata = {
  title: "Data",
  description: "Every public test row of the benchmark and every system's answer to it, with a heatmap of scores by job.",
};

export default function DataPage() {
  const board = loadBoard();
  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-10 px-4 pt-10 sm:px-6 sm:pt-16">
      <header className="flex flex-col gap-4">
        <h1 className="m-0 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">Browse the data</h1>
        <p className="m-0 max-w-[68ch] text-[17px] leading-relaxed text-fg-2">
          Every public test row and every system&apos;s answer to it. Start from the heatmap to find where a system struggles, then open
          the rows behind the number. Scores also include a held-back slice of {int(board.stats.heldBackRows)} rows, which stays private
          and is not listed here.
        </p>
      </header>
      <DataExplorer board={board} />
    </div>
  );
}
