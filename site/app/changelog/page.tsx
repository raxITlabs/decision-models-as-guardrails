import type { Metadata } from "next";
import { pageOpenGraph, pageTwitter } from "@/lib/og";
import Link from "next/link";
import { loadBoard, loadRowsIndex } from "@/lib/data";
import { HF_URL, REPO_URL, int, longDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Changelog",
  description: "Releases of the decision-models-as-guardrails benchmark.",
  alternates: { canonical: "/changelog" },
  openGraph: pageOpenGraph("/changelog"),
  twitter: pageTwitter(),
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
        <li className="grid gap-4 border-b border-line py-8 sm:grid-cols-[10rem_minmax(0,1fr)]">
          <div className="flex flex-col gap-1">
            <span className="text-[15px] text-fg">Note</span>
            <time dateTime="2026-10-14" className="text-[13px] text-muted">14 October 2026</time>
          </div>
          <div className="flex flex-col gap-4">
            <h2 className="m-0 text-[20px] font-semibold tracking-[-0.01em]">A missed check, and a research page</h2>
            <ul className="m-0 flex flex-col gap-2 pl-5 text-[15px] leading-relaxed text-fg-2 marker:text-muted">
              <li>
                Our evaluation contract says a reworded question set must be checked on at least three non-Jev models before the
                results are frozen. Three sets were reworded for this release (denied topics, prompt attacks and personal data), and
                that check did not run. A reviewer pointed this out. The rewording followed the owner&apos;s rulings, not the results, and no
                score changes. We have since run the check with Perplexity, OpenAI and Clef beside Jev, under a plan we published
                first. It passed. The new wording did not help Jev more than the others. Compared with the old wording, it left Jev 1.2
                points of balanced accuracy worse off than the other three on average for prompt attacks, and 0.6 points worse off
                for denied topics. The check fails only if Jev gains more than 2.0 points over them. The 1.0.0 results stand. The{" "}
                <a href={`${REPO_URL}/blob/main/docs/benchmark/30-question-wording-check-plan.md`}>plan</a> and the{" "}
                <a href={`${REPO_URL}/blob/main/benchmark/results/wording-check/summary.json`}>results</a> are on GitHub.
              </li>
              <li>
                A new <Link href="/research">Research</Link> page holds studies that go beyond the leaderboard, starting with a linear-probe
                study under review and Red Hat&apos;s independent benchmark.
              </li>
            </ul>
          </div>
        </li>
        <li className="grid gap-4 py-8 sm:grid-cols-[10rem_minmax(0,1fr)]">
          <div className="flex flex-col gap-1">
            <span className="num text-[15px] text-fg">{version}</span>
            <time dateTime={date} className="text-[13px] text-muted">{longDate(date)}</time>
          </div>
          <div className="flex flex-col gap-4">
            <h2 className="m-0 text-[20px] font-semibold tracking-[-0.01em]">First public release</h2>
            <ul className="m-0 flex flex-col gap-2 pl-5 text-[15px] leading-relaxed text-fg-2 marker:text-muted">
              <li>{board.stats.systems} systems scored on {int(board.stats.checks)} checks across {board.stats.jobs} guardrail use cases, under one fixed rule: a probability of {board.stats.threshold} or more blocks.</li>
              <li>Accuracy and cost for every system, with 95% intervals and statistical tiers, overall and per use case.</li>
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
