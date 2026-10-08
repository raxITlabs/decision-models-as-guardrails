import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Chevron } from "@/components/icons";
import { HashOpen } from "@/components/hash-open";
import { PillLink } from "@/components/pill-link";
import { Podium } from "@/components/podium";
import { TwoKinds } from "@/components/two-kinds";
import { HeroPlate, Plate } from "@/components/plate";
import { Faq } from "@/components/faq";
import { Leaderboard } from "@/components/leaderboard";
import { faqItems } from "@/lib/copy";
import { loadBoard, loadRowsIndex } from "@/lib/data";
import { REPO_URL, int, listNames, longDate, pct, score1, systemMap } from "@/lib/format";
import { JOBS } from "@/lib/jobs";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
  openGraph: { url: "/", siteName: "decision-models-as-guardrails", type: "website" },
};

export default function Home() {
  const board = loadBoard();
  const index = loadRowsIndex();
  const sys = systemMap(board);
  const rowsPerJob = JOBS.map((_, i) => index.rows.filter((r) => r[1] === i).length);
  const kw = board.baseline.map((b) => b.keyword);
  const best = board.baseline.map((b) => b.best);
  const range = (xs: number[]) => (xs.length ? (Math.min(...xs) === Math.max(...xs) ? `${Math.min(...xs)}` : `${Math.min(...xs)} to ${Math.max(...xs)}`) : "");

  const steps = [
    {
      title: "Clean test rows",
      big: `${int(board.stats.checks)} checks`,
      body: `${board.stats.jobs} guardrail jobs. We remove rows that match a model's published training data. We keep ${int(board.stats.heldBackRows)} rows private as a held-back slice.`,
    },
    {
      title: "Same checks for all",
      big: `${int(board.stats.systems)} systems`,
      body: "Every system answers every row. A failed call counts as wrong. We do not rank a run with more than 2% failures.",
    },
    {
      title: "One fixed rule",
      big: `≥ ${board.stats.threshold} blocks`,
      body: "We tune no threshold on the test rows, so you see each system's default. Verdict APIs use their own flag. Amazon Bedrock Guardrails runs at one documented setting.",
    },
    {
      title: "Score and cost",
      big: "accuracy and $",
      body: "Balanced accuracy with 95% intervals and tiers, catch rate, false blocks, and dollars per 1,000 checks.",
    },
  ];

  return (
    <>
    <HeroPlate src="/plates/hero.webp">
          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] items-end gap-6 sm:gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-12">
          <div className="flex max-w-[760px] flex-col items-start gap-4 sm:gap-5">
            <span className="rise over-art plate-title text-[12px] font-medium uppercase tracking-[0.2em]">
              raxIT Labs · Independent benchmark · v{board.release.version}
            </span>
            <h1 id="hero-h" className="rise rise-1 over-art plate-title m-0 text-[clamp(2.25rem,5.6vw,3.75rem)] font-semibold leading-[1.05] tracking-[-0.025em] text-balance">
              Can a decision model replace your guardrail?
            </h1>
            <div className="rise rise-1 mt-2 flex flex-wrap gap-3">
              <PillLink href="#leaderboard" variant="paper">
                See the leaderboard <ArrowRight />
              </PillLink>
              <PillLink href="/reproduce" variant="ghost">
                Reproduce it
              </PillLink>
            </div>
          </div>
          <Podium board={board} />
          </div>
    </HeroPlate>
    <div className="mx-auto flex max-w-[1200px] flex-col gap-24 px-4 pt-20 sm:gap-28 sm:px-6 sm:pt-24">
      {board.source === "fixture" && (
        <p role="note" className="m-0 rounded-lg border border-warn/50 px-4 py-3 text-[14px] text-warn">
          Preview build. The systems and numbers on this page are synthetic placeholders. They are not results.
        </p>
      )}


      <section id="leaderboard" aria-labelledby="lb-h" className="flex scroll-mt-24 flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="flex flex-col gap-2.5">
            <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Leaderboard</span>
            <h2 id="lb-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">Overall ranking</h2>
          </div>
          <p className="m-0 text-[14px] text-muted">
            {board.stats.systems} systems · version {board.release.version} · {longDate(board.release.date)} ·{" "}
            <Link href="/changelog">changelog</Link>
          </p>
        </div>
        <Leaderboard board={board} />
      </section>

      <TwoKinds board={board} />

      <section id="fixed-rule" aria-labelledby="claims-h" className="scroll-mt-24">
        <HashOpen id="fixed-rule" />
        <details className="group border-y border-line-strong">
          <summary className="flex min-h-[72px] flex-wrap items-center justify-between gap-x-6 gap-y-3 py-5">
            <span className="flex flex-col gap-2">
              <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Method</span>
              <span id="claims-h" className="text-[clamp(1.375rem,2.6vw,1.75rem)] font-semibold leading-[1.15] tracking-[-0.02em]">
                How we test every system the same way
              </span>
            </span>
            <span className="inline-flex min-h-11 items-center gap-2 rounded-full border border-line-strong px-4 text-[14px] font-medium text-fg">
              <span className="group-open:hidden">Show the method</span>
              <span className="hidden group-open:inline">Hide the method</span>
              <Chevron className="size-3.5 rotate-90 transition-transform duration-150 ease-out group-open:-rotate-90" />
            </span>
          </summary>
          <div className="flex flex-col gap-5 pb-8 pt-2">
            <ol className="m-0 flex list-none flex-wrap items-stretch gap-3 p-0">
              {steps.map((st, i) => (
                <li key={st.title} className="flex min-w-[220px] flex-1 items-stretch gap-3">
                  <div className="flex flex-1 flex-col gap-2.5 rounded-xl border border-line bg-surface p-[18px]">
                    <span className="flex items-center gap-2.5">
                      <span className="num grid size-7 place-items-center rounded-md bg-fg text-[13px] text-bg">{i + 1}</span>
                      <span className="text-[16px] font-semibold">{st.title}</span>
                    </span>
                    <span className="num text-[22px] tracking-[-0.02em]">{st.big}</span>
                    <span className="text-[14px] leading-relaxed text-fg-2">{st.body}</span>
                  </div>
                  {i < steps.length - 1 && (
                    <span aria-hidden="true" className="self-center text-link">
                      <ArrowRight />
                    </span>
                  )}
                </li>
              ))}
            </ol>
            <p className="m-0 max-w-[72ch] text-[14px] leading-relaxed text-muted">
              Published guardrail numbers rarely compare. Each vendor picks its own threshold and its own test set. Here every system
              gets the same rows and the same rule, so the differences come from the systems.
              {kw.length
                ? ` Each prompt attack has safe rows in the same style. A keyword classifier scores ${range(kw)} on them. Word and character n-gram classifiers that we trained and tested on these rows score ${range(best)}.`
                : ""}{" "}
              <Link href="/reproduce">Read the full method.</Link>
            </p>
          </div>
        </details>
      </section>

      <section aria-labelledby="jobs-h" className="flex flex-col gap-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-2.5">
            <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">By job</span>
            <h2 id="jobs-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">The leader changes with the job</h2>
          </div>
          <Link href="/data" className="inline-flex min-h-11 items-center gap-1.5 text-[14px]">
            See all {int(index.rows.length)} public rows <ArrowRight />
          </Link>
        </div>
        <ol className="m-0 grid list-none gap-x-14 p-0 md:grid-cols-2">
          {JOBS.map((j, i) => {
            const ranking = board.jobs[j.id];
            const top = ranking.filter((s) => s.tier === 1);
            const lead = ranking[0];
            const fb = top.map((s) => s.falseBlockRate);
            return (
              <li key={j.id} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] gap-x-4 border-t border-line-strong py-5">
                <span className="num pt-1 text-[13px] text-muted">{String(i + 1).padStart(2, "0")}</span>
                <div className="flex min-w-0 flex-col gap-1.5">
                  <h3 className="m-0 text-[18px] font-semibold leading-snug tracking-[-0.01em]">{j.title}</h3>
                  <p className="m-0 text-[14px] leading-snug text-fg-2">{j.sub}</p>
                  <p className="m-0 text-[14px] leading-snug">
                    <span className="text-muted">Top tier: </span>
                    {listNames(top.map((s) => sys[s.system]?.name ?? s.system))}
                  </p>
                  <p className="m-0 text-[13px] text-muted">
                    Top tier blocks{" "}
                    {fb.length ? (fb.length === 1 ? pct(fb[0], 0) : `${pct(Math.min(...fb), 0)} to ${pct(Math.max(...fb), 0)}`) : "n/a"} of safe rows
                  </p>
                  <Link href={`/data?job=${j.id}#rows`} className="inline-flex min-h-11 w-fit items-center gap-1.5 text-[14px]">
                    {int(rowsPerJob[i])} rows<span className="sr-only"> for {j.title}</span> <ArrowRight />
                  </Link>
                </div>
                <div className="flex flex-col items-end">
                  <span className="num text-[26px] tracking-[-0.02em]">{lead ? score1(lead.score) : "n/a"}</span>
                  <span className="text-[12px] text-muted">best score</span>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <section aria-labelledby="faq-h" className="grid gap-8 md:grid-cols-[minmax(0,4fr)_minmax(0,7fr)]">
        <div className="flex flex-col gap-2.5">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Questions</span>
          <h2 id="faq-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">Can you trust these numbers?</h2>
        </div>
        <Faq items={faqItems(board)} />
      </section>

      <section id="notify" aria-labelledby="notify-h">
        <Plate src="/plates/lake.webp" minH="min-h-[360px] sm:min-h-[400px]">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div className="flex max-w-[620px] flex-col gap-3">
              <h2 id="notify-h" className="over-art plate-title m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">
                Run it yourself
              </h2>
              <p className="over-art-86 m-0 text-[17px] leading-relaxed">
                Clone the repository. Get the pinned dataset. Then score your own guardrail on the same checks. We publish new results
                as GitHub releases. Watch the repository to get an email for each release.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <PillLink href="/reproduce" variant="paper">
                Reproduce the board <ArrowRight />
              </PillLink>
              <PillLink href={`${REPO_URL}/releases`} variant="ghost">
                Watch releases
              </PillLink>
            </div>
          </div>
        </Plate>
      </section>
    </div>
    </>
  );
}
