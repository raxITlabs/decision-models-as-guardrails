import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Chevron } from "@/components/icons";
import { HashOpen } from "@/components/hash-open";
import { PillLink } from "@/components/pill-link";
import { DecisionSpace, type Example } from "@/components/decision-space";
import { TwoKinds } from "@/components/two-kinds";
import { CostCalculator } from "@/components/cost-calculator";
import { HeroPlate, Plate } from "@/components/plate";
import { Faq } from "@/components/faq";
import { Leaderboard } from "@/components/leaderboard";
import { faqItems } from "@/lib/copy";
import { loadBoard, loadRowDetails, loadRowsIndex } from "@/lib/data";
import { REPO_URL, int, listNames, longDate, oneLine, pct, score1, systemMap } from "@/lib/format";
import { JOBS } from "@/lib/jobs";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
  openGraph: { url: "/", siteName: "decision-models-as-guardrails", type: "website" },
};

/** Hero examples: published rows, mild enough for a first screen, chosen because the systems disagree on them. */
const HERO_EXAMPLES = [
  "f1-e2_content_xstest-e90bdeb302",
  "f3-e2_denied_topics-562f7db27d",
  "f2-lakera_mosscap-54ec17149d",
  "f5-e2_pii_controls-4a5261be86",
  "f2-e2_attack_controls-7eee9c9a91",
  "f3-e2_denied_topics-0e521b9985",
  "f5-e2_pii_controls-ff89af5c10",
];

export default function Home() {
  const board = loadBoard();
  const index = loadRowsIndex();
  const sys = systemMap(board);
  const details = loadRowDetails();
  const examples: Example[] = HERO_EXAMPLES.map((id) => details[id])
    .filter((r) => r && !r.withheld && r.text)
    .map((r) => ({
      id: r.id,
      job: r.job,
      label: r.label,
      text: r.text as string,
      verdicts: Object.fromEntries(r.results.map((x) => [x.system, x.outcome === "decided" ? x.decision : null])),
    }));
  const rowsPerJob = JOBS.map((_, i) => index.rows.filter((r) => r[1] === i).length);
  const kw = board.baseline.map((b) => b.keyword);
  const best = board.baseline.map((b) => b.best);
  const range = (xs: number[]) => (xs.length ? (Math.min(...xs) === Math.max(...xs) ? `${Math.min(...xs)}` : `${Math.min(...xs)} to ${Math.max(...xs)}`) : "");

  const steps = [
    {
      title: "Clean test rows",
      big: `${int(board.stats.checks)} checks`,
      body: `${board.stats.jobs} guardrail use cases. We remove rows that match a model's published training data. We keep ${int(board.stats.heldBackRows)} rows private as a held-back slice.`,
    },
    {
      title: "Same checks for all",
      big: `${int(board.stats.systems)} systems`,
      body: "Every system answers every row. A failed call counts as wrong. We do not rank a run with more than 2% failures.",
    },
    {
      title: "One fixed rule",
      big: `≥ ${board.stats.threshold} blocks`,
      body: "We tune no threshold on the test rows, so you see each system's default. Verdict APIs use their own flag. Bedrock Guardrails runs at one documented setting.",
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
          {/* One column on the left: the question, then one message the systems disagree on, then the way in. */}
          <div className="flex max-w-[620px] flex-col gap-8">
            <h1 id="hero-h" className="rise rise-1 over-art plate-title m-0 text-[clamp(2.25rem,5.2vw,3.5rem)] font-semibold leading-[1.05] tracking-[-0.025em] text-balance">
              Can a decision model replace your guardrail?
            </h1>
            {examples.length > 0 && (
              <div className="rise rise-2">
                <DecisionSpace examples={examples} systems={board.systems} />
              </div>
            )}
            <div className="rise rise-2 flex flex-wrap gap-3">
              <PillLink href="#leaderboard" variant="paper">
                See the leaderboard <ArrowRight />
              </PillLink>
              <PillLink href="/reproduce" variant="ghost">
                Reproduce it
              </PillLink>
            </div>
          </div>
    </HeroPlate>
    <div className="mx-auto flex max-w-[1200px] flex-col gap-24 px-4 pt-20 sm:gap-28 sm:px-6 sm:pt-24">
      {board.source === "fixture" && (
        <p role="note" className="m-0 border-y border-warn/50 py-3 text-[14px] text-warn">
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

      <CostCalculator board={board} />

      <TwoKinds board={board} />

      <section id="fixed-rule" aria-labelledby="claims-h" className="scroll-mt-24">
        <HashOpen id="fixed-rule" />
        <details className="group border-y border-line-strong">
          <summary className="flex min-h-[72px] flex-wrap items-center justify-between gap-x-6 gap-y-3 py-5">
            <span className="flex flex-col gap-2">
              <span id="claims-h" className="text-[clamp(1.375rem,2.6vw,1.75rem)] font-semibold leading-[1.15] tracking-[-0.02em]">
                How we test every system the same way
              </span>
            </span>
            <span className="inline-flex min-h-11 items-center gap-2 text-[15px] font-medium text-link">
              <span className="group-open:hidden">Show the method</span>
              <span className="hidden group-open:inline">Hide the method</span>
              <Chevron className="size-3.5 rotate-90 transition-transform duration-150 ease-out group-open:-rotate-90" />
            </span>
          </summary>
          <div className="flex flex-col gap-5 pb-8 pt-2">
            {/* Four steps in order, as ruled columns: the sequence is real, so the numbers stay. */}
            <ol className="m-0 grid list-none gap-0 p-0 sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((st, i) => (
                <li key={st.title} className="flex flex-col gap-2 border-t border-line py-5 sm:pr-6 lg:border-l lg:border-t-0 lg:py-1 lg:pl-6 lg:first:border-l-0 lg:first:pl-0">
                  <span className="text-[14px] text-muted">
                    <span className="num">{i + 1}</span> · {st.title}
                  </span>
                  <span className="num text-[24px] font-medium tracking-[-0.02em]">{st.big}</span>
                  <span className="text-[14px] leading-relaxed text-fg-2">{st.body}</span>
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
            <h2 id="jobs-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">The leader changes with the use case</h2>
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
                    {listNames(top.map((s) => oneLine(sys[s.system], s.system)))}
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
