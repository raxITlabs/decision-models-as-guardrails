import Link from "next/link";
import { ArrowRight } from "@/components/icons";
import { PillLink } from "@/components/pill-link";
import { Plate } from "@/components/plate";
import { Faq } from "@/components/faq";
import { Leaderboard } from "@/components/leaderboard";
import { faqItems } from "@/lib/copy";
import { loadBoard, loadRowsIndex } from "@/lib/data";
import { REPO_URL, int, listNames, longDate, pct, score1, systemMap } from "@/lib/format";
import { JOBS } from "@/lib/jobs";

export default function Home() {
  const board = loadBoard();
  const index = loadRowsIndex();
  const sys = systemMap(board);
  const rowsPerJob = JOBS.map((_, i) => index.rows.filter((r) => r[1] === i).length);
  const kw = board.baseline.map((b) => b.keyword);
  const best = board.baseline.map((b) => b.best);
  const range = (xs: number[]) => (xs.length ? (Math.min(...xs) === Math.max(...xs) ? `${Math.min(...xs)}` : `${Math.min(...xs)} to ${Math.max(...xs)}`) : "");

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-24 px-4 pt-6 sm:gap-28 sm:px-6">
      {board.source === "fixture" && (
        <p role="note" className="m-0 rounded-lg border border-warn/50 px-4 py-3 text-[14px] text-warn">
          Preview build. The systems and numbers on this page are synthetic placeholders. They are not results.
        </p>
      )}

      <section aria-labelledby="hero-h" className="flex flex-col gap-5">
        <Plate src="/plates/hero.webp" priority>
          <div className="flex max-w-[860px] flex-col items-start gap-4 sm:gap-5">
            <span className="over-art plate-title text-[12px] font-medium uppercase tracking-[0.2em]">
              raxIT Labs · Independent benchmark · v{board.release.version}
            </span>
            <h1 id="hero-h" className="over-art plate-title m-0 text-[clamp(2.25rem,5.6vw,3.75rem)] font-semibold leading-[1.05] tracking-[-0.025em] text-balance">
              Can a decision model replace your guardrail?
            </h1>
            <p className="over-art-86 m-0 max-w-[40ch] text-[clamp(1.0625rem,1.8vw,1.25rem)] leading-relaxed text-balance">
              {int(board.stats.systems)} systems answered the same {int(board.stats.checks)} guardrail checks under one fixed rule. See how
              accurate each one is and what it costs.
            </p>
            <div className="mt-2 flex flex-wrap gap-3">
              <PillLink href="#leaderboard" variant="paper">
                See the leaderboard <ArrowRight />
              </PillLink>
              <PillLink href="/reproduce" variant="ghost">
                Reproduce it
              </PillLink>
            </div>
          </div>
        </Plate>
        <p className="m-0 text-[15px] leading-relaxed text-fg-2">
          <span className="num text-fg">{int(board.stats.systems)}</span> systems · <span className="num text-fg">{int(board.stats.checks)}</span> checks ·{" "}
          <span className="num text-fg">{board.stats.jobs}</span> guardrail jobs · one fixed rule: block at a probability of{" "}
          <span className="num text-fg">{board.stats.threshold}</span> or more · accuracy and cost only
        </p>
      </section>

      <section id="leaderboard" aria-labelledby="lb-h" className="flex scroll-mt-24 flex-col gap-6">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
          <div className="flex flex-col gap-2.5">
            <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Leaderboard</span>
            <h2 id="lb-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">Overall, all {board.stats.jobs} jobs</h2>
          </div>
          <p className="m-0 text-[14px] text-muted">
            {board.stats.systems} systems · version {board.release.version} · {longDate(board.release.date)} ·{" "}
            <Link href="/changelog">changelog</Link>
          </p>
        </div>
        <Leaderboard board={board} />
      </section>

      <section aria-labelledby="claims-h" className="grid gap-10 md:grid-cols-[minmax(0,4fr)_minmax(0,7fr)]">
        <div className="flex flex-col gap-4">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Method</span>
          <h2 id="claims-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em]">One method for every system</h2>
          <p className="m-0 max-w-[60ch] text-[16px] leading-relaxed text-fg-2">
            Published guardrail numbers rarely compare. Each vendor picks its own threshold and its own test set. Those test sets often
            overlap with the model&apos;s training data. We sent the same checks to every system and used one method for all of them. So
            the differences you see come from the systems, not from the method.
          </p>
        </div>
        <ul className="m-0 grid list-none gap-x-8 gap-y-8 p-0 sm:grid-cols-2">
          <li id="fixed-rule" className="flex flex-col gap-2 border-t-2 border-fg pt-4">
            <h3 className="m-0 text-[17px] font-semibold">One fixed rule, no tuning.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              Every model blocks at a probability of {board.stats.threshold} or more. No system gets a threshold fitted to the test rows.
              You see how each system behaves by default. Verdict APIs use their own flag. Amazon Bedrock Guardrails runs at
              one documented setting.
            </p>
          </li>
          <li className="flex flex-col gap-2 border-t-2 border-fg pt-4">
            <h3 className="m-0 text-[17px] font-semibold">The same checks for every system.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              All {board.stats.systems} systems answered the same {int(board.stats.checks)} checks across {board.stats.jobs} jobs. A
              call that fails or gives no decision counts as wrong. We do not rank a run with more than 2% failures.
            </p>
          </li>
          <li className="flex flex-col gap-2 border-t-2 border-fg pt-4">
            <h3 className="m-0 text-[17px] font-semibold">Screened for contamination.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              We compared every row with the training data that the model makers published. We removed the matches. Some rows come from
              datasets that a vendor released itself. We keep and flag those rows, and we also score content without them.{" "}
              {int(board.stats.heldBackRows)} of the checks are a held-back slice that we do not publish
              {typeof board.facts.sliceGapMax === "number" ? `. Overall scores on that slice are within ${board.facts.sliceGapMax} points of the scores on the public rows` : ""}.
            </p>
          </li>
          <li className="flex flex-col gap-2 border-t-2 border-fg pt-4">
            <h3 className="m-0 text-[17px] font-semibold">Prompt attacks tested for shortcuts.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              Each direct and indirect attack has safe rows in the same style. A system that reacts to scary words blocks both.
              {kw.length ? ` A keyword classifier scores ${range(kw)} on these rows. We also publish word and character n-gram classifiers that we trained and tested on these same rows. They score ${range(best)}. That shows how far wording alone gets on rows that a classifier has already seen.` : ""}
            </p>
          </li>
        </ul>
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
  );
}
