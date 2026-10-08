import type { Metadata } from "next";
import Link from "next/link";
import { loadBoard, loadRowsIndex } from "@/lib/data";
import { HF_URL, REPO_URL, int, longDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Changelog",
  description: "Releases of the decision-models-as-guardrails benchmark.",
  alternates: { canonical: "/changelog" },
};

export default function Changelog() {
  const board = loadBoard();
  const rows = loadRowsIndex().rows.length;
  const { version, date } = board.release;
  return (
    <div className="mx-auto max-w-[1200px] px-4 pt-10 sm:px-6 sm:pt-16">
      <div className="flex max-w-[820px] flex-col gap-10">
      <header className="flex flex-col gap-4">
      <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Release notes</span>
      <h1 className="m-0 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">Changelog</h1>
      </header>
      <ol className="m-0 list-none border-t border-line p-0">
        <li className="grid gap-4 py-8 sm:grid-cols-[10rem_minmax(0,1fr)]">
          <div className="flex flex-col gap-1">
            <span className="num text-[15px] text-fg">{version}</span>
            <time dateTime={date} className="text-[13px] text-muted">{longDate(date)}</time>
          </div>
          <div className="flex flex-col gap-4">
            <h2 className="m-0 text-[20px] font-semibold tracking-[-0.01em]">First public release</h2>
            <ul className="m-0 flex flex-col gap-2 pl-5 text-[15px] leading-relaxed text-fg-2 marker:text-muted">
              <li>{board.stats.systems} systems scored on {int(board.stats.checks)} checks across {board.stats.jobs} guardrail jobs, under one fixed rule: a probability of {board.stats.threshold} or more blocks.</li>
              <li>Accuracy and cost for every system, with 95% intervals and statistical tiers, overall and per job.</li>
              <li>{int(rows)} public test rows with every system&apos;s answer on the <Link href="/data">Data</Link> page, plus a held-back slice of {int(board.stats.heldBackRows)} rows.</li>
              <li>Jev results are for Jev 1.13.0. Every call asked TypeSafe&apos;s API for that version, and the API reported it on every call (5 and 6 October 2026).</li>
              <li>The dataset on <a href={HF_URL}>Hugging Face</a>. The code, scoring rules and run records on <a href={REPO_URL}>GitHub</a>.</li>
            </ul>
          </div>
        </li>
      </ol>
    </div>
    </div>
  );
}
