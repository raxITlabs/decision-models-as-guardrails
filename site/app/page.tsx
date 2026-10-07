import Link from "next/link";
import { ArrowDown, ArrowRight } from "@/components/icons";
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
  const stats = [
    { label: "checks", value: int(board.stats.checks) },
    { label: "guardrail types", value: int(board.stats.suites) },
    { label: "systems", value: int(board.stats.systems) },
    { label: "fixed rule", value: "1" },
  ];

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-20 px-4 pt-10 sm:gap-24 sm:px-6 sm:pt-16">
      {board.source === "fixture" && (
        <p role="note" className="m-0 rounded-lg border border-warn/50 px-4 py-3 text-[14px] text-warn">
          Preview build: the systems and numbers on this page are synthetic placeholders, not results.
        </p>
      )}

      <section aria-labelledby="hero-h" className="grid gap-10 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
        <div className="flex flex-col gap-6">
          <h1 id="hero-h" className="m-0 text-[clamp(2rem,6vw,3.75rem)] font-semibold leading-[1.02] tracking-[-0.035em] text-balance">
            decision-models-as-guardrails
          </h1>
          <p className="m-0 max-w-[34ch] text-[clamp(1.125rem,2.2vw,1.375rem)] leading-snug text-fg-2">
            Can a decision model replace your guardrail?
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link href="/reproduce" className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 text-[15px] font-medium text-accent-ink no-underline transition-colors hover:bg-accent-hover hover:text-accent-ink">
              Reproduce it <ArrowRight />
            </Link>
            <Link href="/data" className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-line-strong px-4 text-[15px] font-medium text-fg no-underline transition-colors hover:bg-raised hover:text-fg">
              Browse the data
            </Link>
          </div>
          <a href="#notify" className="inline-flex min-h-11 w-fit items-center gap-1.5 text-[14px] text-muted no-underline hover:text-fg">
            Get notified when systems join the board <ArrowDown className="size-3.5" />
          </a>
        </div>
        <dl className="m-0 grid min-w-[15rem] grid-cols-2 gap-x-6 gap-y-3 border-t border-line pt-5 md:grid-cols-1 md:border-t-0 md:border-l md:pl-6 md:pt-0">
          {stats.map((s) => (
            <div key={s.label} className="flex items-baseline justify-between gap-6">
              <dt className="text-[13px] text-muted">{s.label}</dt>
              <dd className="num m-0 text-[15px] text-fg">{s.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="lb-h" className="flex flex-col gap-6">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <h2 id="lb-h" className="m-0 text-[28px] font-semibold tracking-[-0.02em]">Leaderboard</h2>
          <p className="m-0 text-[13px] text-muted">
            {board.stats.systems} systems · version {board.release.version} · {longDate(board.release.date)} ·{" "}
            <Link href="/changelog">changelog</Link>
          </p>
        </div>
        <Leaderboard board={board} />
      </section>

      <section aria-labelledby="claims-h" className="grid gap-10 md:grid-cols-[minmax(0,4fr)_minmax(0,7fr)]">
        <div className="flex flex-col gap-4">
          <h2 id="claims-h" className="m-0 text-[28px] font-semibold tracking-[-0.02em]">Why the numbers compare</h2>
          <p className="m-0 max-w-[60ch] text-[16px] leading-relaxed text-fg-2">
            Guardrail numbers rarely line up. Each vendor reports its own threshold on its own test set, and those sets often overlap with
            what the model trained on. We sent every system the same checks and held the method still, so the gaps you see come from the
            systems.
          </p>
        </div>
        <ul className="m-0 grid list-none gap-x-8 gap-y-8 p-0 sm:grid-cols-2">
          <li id="fixed-rule" className="flex flex-col gap-2 border-t border-line pt-4">
            <h3 className="m-0 text-[17px] font-semibold">One fixed rule, no tuning.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              A probability of {board.stats.threshold} or more blocks, for every model. Nobody gets a threshold fitted to the test rows,
              so you see how each system behaves out of the box. Verdict APIs use their own flag, and Amazon Bedrock Guardrails runs at one documented
              setting.
            </p>
          </li>
          <li className="flex flex-col gap-2 border-t border-line pt-4">
            <h3 className="m-0 text-[17px] font-semibold">The same checks for every system.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              All {board.stats.systems} systems answered the same {int(board.stats.checks)} checks across {board.stats.jobs} jobs. A
              call that fails or returns no decision counts as wrong, and a run with more than 2% failures is not ranked.
            </p>
          </li>
          <li className="flex flex-col gap-2 border-t border-line pt-4">
            <h3 className="m-0 text-[17px] font-semibold">Screened for contamination.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              We checked every row against the training data the model makers published and removed the matches. Rows from datasets a
              vendor released itself stay in and are flagged, and content is also scored without them. {int(board.stats.heldBackRows)} of
              the checks form a held-back slice that stays private
              {typeof board.facts.sliceGapMax === "number" ? `; overall scores on it land within ${board.facts.sliceGapMax} points of the public rows` : ""}.
            </p>
          </li>
          <li className="flex flex-col gap-2 border-t border-line pt-4">
            <h3 className="m-0 text-[17px] font-semibold">Prompt attacks tested for shortcuts.</h3>
            <p className="m-0 text-[15px] leading-relaxed text-fg-2">
              Direct and indirect attacks come with safe rows in the same style, so a system that reacts to scary words blocks both.
              {kw.length ? ` A keyword classifier scores ${range(kw)} on them. Beside it we publish word and character n-gram classifiers trained and tested on these same rows. They reach ${range(best)}, which shows how far wording alone gets on rows a classifier has already seen.` : ""}
            </p>
          </li>
        </ul>
      </section>

      <section aria-labelledby="jobs-h" className="flex flex-col gap-6">
        <div className="flex flex-wrap items-baseline justify-between gap-4">
          <h2 id="jobs-h" className="m-0 text-[28px] font-semibold tracking-[-0.02em]">Eight guardrail jobs</h2>
          <Link href="/data" className="inline-flex min-h-11 items-center gap-1.5 text-[14px]">
            All {int(index.rows.length)} public rows <ArrowRight />
          </Link>
        </div>
        <ul className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 lg:grid-cols-4">
          {JOBS.map((j, i) => {
            const ranking = board.jobs[j.id];
            const top = ranking.filter((s) => s.tier === 1);
            const lead = ranking[0];
            const fb = top.map((s) => s.falseBlockRate);
            return (
              <li key={j.id} className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5 transition-colors hover:border-line-strong">
                <div className="flex flex-col gap-1.5">
                  <h3 className="m-0 text-[16px] font-semibold leading-snug">{j.title}</h3>
                  <p className="m-0 text-[13px] leading-snug text-muted">{j.sub}</p>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-[12px] text-muted">Top tier</span>
                  <span className="text-[14px] leading-snug text-fg">{listNames(top.map((s) => sys[s.system]?.name ?? s.system))}</span>
                </div>
                <dl className="m-0 mt-auto grid grid-cols-2 gap-2 border-t border-line pt-3 text-[12px]">
                  <div>
                    <dt className="text-muted">Best score</dt>
                    <dd className="num m-0 mt-0.5 text-[14px]">{lead ? score1(lead.score) : "n/a"}</dd>
                  </div>
                  <div>
                    <dt className="text-muted">Top tier blocks safe</dt>
                    <dd className="num m-0 mt-0.5 text-[14px]">
                      {fb.length ? (fb.length === 1 ? pct(fb[0], 0) : `${pct(Math.min(...fb), 0)} to ${pct(Math.max(...fb), 0)}`) : "n/a"}
                    </dd>
                  </div>
                </dl>
                <Link href={`/data?job=${j.id}#rows`} className="inline-flex min-h-11 items-center gap-1.5 text-[14px]">
                  {int(rowsPerJob[i])} rows<span className="sr-only"> for {j.title}</span> <ArrowRight />
                </Link>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="faq-h" className="flex flex-col gap-6">
        <h2 id="faq-h" className="m-0 text-[28px] font-semibold tracking-[-0.02em]">Can you trust these numbers?</h2>
        <Faq items={faqItems(board)} />
      </section>

      <section id="notify" aria-labelledby="notify-h" className="flex flex-col items-start gap-4 rounded-xl border border-line bg-surface p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div className="flex flex-col gap-1.5">
          <h2 id="notify-h" className="m-0 text-[20px] font-semibold tracking-[-0.01em]">Get notified when systems join the board</h2>
          <p className="m-0 text-[14px] text-muted">New results ship as GitHub releases. Watch the repository for releases to get an email.</p>
        </div>
        <a href={`${REPO_URL}/releases`} className="inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg bg-accent px-4 text-[15px] font-medium text-accent-ink no-underline hover:bg-accent-hover hover:text-accent-ink">
          Watch releases <ArrowRight />
        </a>
      </section>
    </div>
  );
}
