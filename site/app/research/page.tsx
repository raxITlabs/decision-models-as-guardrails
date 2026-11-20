import type { Metadata } from "next";
import { pageOpenGraph, pageTwitter } from "@/lib/og";
import Link from "next/link";
import { External } from "@/components/icons";

export const metadata: Metadata = {
  title: "Research",
  description: "Studies that go beyond the leaderboard: independent benchmarks of the same systems, and experiments that use training or model internals.",
  alternates: { canonical: "/research" },
  openGraph: pageOpenGraph("/research"),
  twitter: pageTwitter(),
};

const RED_HAT = "https://developers.redhat.com/articles/2026/10/02/benchmarking-ai-decision-models-against-traditional-guardrails";

/** Further research. The leaderboard measures each system as it ships, with no training; anything here may train,
 *  tune or read model internals, so its numbers are never placed beside leaderboard scores. */
export default function Research() {
  return (
    <div className="mx-auto max-w-[1200px] px-4 pt-10 sm:px-6 sm:pt-16">
      <div className="flex max-w-[820px] flex-col gap-10">
        <header className="flex flex-col gap-4">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Further research</span>
          <h1 className="m-0 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">Research</h1>
          <p className="m-0 max-w-[68ch] text-[17px] leading-relaxed text-fg-2">
            The <Link href="/">leaderboard</Link> scores every system as it ships, under one fixed rule, with no training. The work on
            this page goes further. Some of it trains on labelled rows or reads a model&apos;s internals, so its numbers do not compare
            with leaderboard scores.
          </p>
        </header>

        <ol className="m-0 list-none border-t border-line-strong p-0">
          <li className="flex flex-col gap-3 border-b border-line py-8">
            <span className="text-[13px] text-muted">14 October 2026 · Community study</span>
            <h2 className="m-0 text-[22px] font-semibold tracking-[-0.01em]">Linear probes on two open models</h2>
            <p className="m-0 max-w-[68ch] text-[15px] leading-relaxed text-fg-2">
              Aditya Shrivastava trained a small classifier to read signals inside Strands Decider 2B and Kev 4B.
              On 540 denied-topic prompts, it caught more violations and blocked fewer safe prompts than Strands’s own score.
              Kev’s own score already caught all but one violation.
            </p>
            <Link href="/research/linear-probe" className="inline-flex min-h-11 w-fit items-center text-[15px]">Read the study →</Link>
          </li>
          <li className="flex flex-col gap-3 border-b border-line py-8">
            <span className="text-[13px] text-muted">2 October 2026 · Red Hat, independent</span>
            <h2 className="m-0 text-[22px] font-semibold tracking-[-0.01em]">Red Hat: decision models against traditional guardrails</h2>
            <p className="m-0 max-w-[68ch] text-[15px] leading-relaxed text-fg-2">
              Red Hat&apos;s AI Safety team compared nine guardrails on prompt injection and content safety, using each model&apos;s own
              output with no training. Jev 1.13 ranked first on content safety at 86.2% and fourth on prompt injection at 86.4%. A
              small trained classifier came within 0.3 points of the best prompt-injection score. Rewording the content policy raised
              Laya from 57.9% to 75.2% and lowered Jev from 86.2% to 82.5%. How a policy is worded can favour one model over another.
            </p>
            <a href={RED_HAT} className="inline-flex min-h-11 w-fit items-center gap-1.5 text-[15px]">
              Read the study <External className="size-3.5" />
            </a>
          </li>
        </ol>

        <p className="m-0 max-w-[68ch] text-[14px] leading-relaxed text-muted">
          Have a study that tests these systems or this dataset? Open an issue or a pull request on{" "}
          <a href="https://github.com/raxITlabs/decision-models-as-guardrails">GitHub</a>.
        </p>
      </div>
    </div>
  );
}
