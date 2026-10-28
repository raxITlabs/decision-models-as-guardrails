import type { Metadata } from "next";
import { pageOpenGraph, pageTwitter } from "@/lib/og";
import Link from "next/link";
import { loadBoard, loadVersions } from "@/lib/data";
import { REPO_URL, int, oneLine, systemMap } from "@/lib/format";
import { JOBS } from "@/lib/jobs";
import type { Delta, Lineage, SystemMeta, Verdict, VersionStep } from "@/lib/types";

export const metadata: Metadata = {
  title: "Versions",
  description: "Each new version of a model, compared with the last on the same checks, with intervals and a plain verdict.",
  alternates: { canonical: "/versions" },
  openGraph: pageOpenGraph("/versions"),
  twitter: pageTwitter(),
};

const WORD: Record<Verdict, string> = { better: "Better", worse: "Worse", "within noise": "No clear change", "not tested": "Not tested" };
/** Display names for versions that have no run yet, so they are not on the board. */
const PLANNED_NAMES: Record<string, string> = { "pplx-decider-v1.2": "Perplexity Decider v1.2" };

/** A signed number with a real minus sign; a value that rounds to zero is shown unsigned. */
function sign(n: number, d = 2): string {
  const r = Math.abs(n).toFixed(d);
  if (Number(r) === 0) return r;
  return `${n > 0 ? "+" : "−"}${r}`;
}
const signedCi = (d: Delta, scale = 1, digits = 2) => `${sign(d.ci.low * scale, digits)} to ${sign(d.ci.high * scale, digits)}`;

function VerdictWord({ v }: { v: Verdict }) {
  const tone = v === "better" ? "text-accent" : v === "worse" ? "text-warn" : "text-muted";
  return <span className={`whitespace-nowrap text-[13px] font-medium ${tone}`}>{WORD[v]}</span>;
}

/** One version step's headline: the score change with its interval, then catches and false blocks the same way. */
function StepHeadline({ c, name }: { c: VersionStep; name: (id: string) => string }) {
  const ba = c.overall.balanced_accuracy;
  const cr = c.overall.catch_rate;
  const fb = c.overall.false_block_rate;
  const boardSplit = ba.verdict !== "within noise" && c.board && c.board.separated_on_board === false;
  return (
    <div className="flex flex-col gap-3">
      <h3 className="m-0 text-[18px] font-semibold tracking-[-0.01em]">
        {name(c.from)} <span className="font-normal text-muted">to</span> {name(c.to)}
      </h3>
      <dl className="m-0 grid gap-x-10 gap-y-3 sm:grid-cols-3">
        <div className="flex flex-col gap-0.5 border-t border-line pt-3">
          <dt className="text-[12px] text-muted">Score</dt>
          <dd className="m-0 flex items-baseline gap-3">
            <span className="num text-[22px] font-medium">{sign(ba.point)}</span>
            <VerdictWord v={ba.verdict} />
          </dd>
          <dd className="num m-0 text-[12px] text-muted">95% interval {signedCi(ba)} points</dd>
        </div>
        <div className="flex flex-col gap-0.5 border-t border-line pt-3">
          <dt className="text-[12px] text-muted">Harmful rows caught</dt>
          <dd className="m-0 flex items-baseline gap-3">
            <span className="num text-[22px] font-medium">{sign(cr.point * 100, 1)}</span>
            <VerdictWord v={cr.verdict} />
          </dd>
          <dd className="num m-0 text-[12px] text-muted">{(cr.old * 100).toFixed(1)}% to {(cr.new * 100).toFixed(1)}%</dd>
        </div>
        <div className="flex flex-col gap-0.5 border-t border-line pt-3">
          <dt className="text-[12px] text-muted">Benign rows blocked</dt>
          <dd className="m-0 flex items-baseline gap-3">
            <span className="num text-[22px] font-medium">{sign(fb.point * 100, 1)}</span>
            <VerdictWord v={fb.verdict} />
          </dd>
          <dd className="num m-0 text-[12px] text-muted">{(fb.old * 100).toFixed(1)}% to {(fb.new * 100).toFixed(1)}%</dd>
        </div>
      </dl>
      <p className="m-0 max-w-[72ch] text-[14px] leading-relaxed text-fg-2">
        {name(c.to)} fixed {int(c.flips.fixed)} checks that {name(c.from)} got wrong and broke {int(c.flips.broke)} it got right, out of{" "}
        {int(c.flips.judgments)}.
        {boardSplit ? " The leaderboard, which tests every pair of systems at once, cannot tell these two apart." : ""}{" "}
        {c.cost
          ? c.cost.comparable
            ? Math.abs(c.cost.delta_pct ?? 0) < 0.5
              ? "Same cost per check."
              : `Cost per check ${sign(c.cost.delta_pct ?? 0, 0)}%.`
            : "Cost is not comparable: the two ran on different hardware."
          : ""}
      </p>
    </div>
  );
}

/** Old score (open dot) to new (filled dot) per use case. A use case with no clear change is drawn muted. */
function JobPlot({ c }: { c: VersionStep }) {
  const rows = JOBS.map((j) => ({ job: j, d: c.subtasks[j.key] })).filter((r) => r.d);
  const lo = Math.floor((Math.min(...rows.flatMap((r) => [r.d.old, r.d.new])) - 3) / 10) * 10;
  const pos = (v: number) => `${((v - lo) / (100 - lo)) * 100}%`;
  return (
    <figure className="m-0 flex flex-col gap-2">
      <figcaption className="text-[12px] text-muted">
        Score per use case, balanced accuracy. Open dot: old version. Filled dot: new version.
      </figcaption>
      <ul className="m-0 list-none border-t border-line-strong p-0">
        {rows.map(({ job, d }) => {
          const clear = d.verdict === "better" || d.verdict === "worse";
          const ink = d.verdict === "better" ? "var(--accent)" : d.verdict === "worse" ? "var(--warn)" : "var(--line-strong)";
          const [a, b] = d.old <= d.new ? [d.old, d.new] : [d.new, d.old];
          return (
            <li key={job.id} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 border-b border-line py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)_9.5rem]">
              <span className={`text-[14px] ${clear ? "text-fg" : "text-muted"}`}>{job.short}</span>
              <span className="relative order-3 col-span-2 h-4 sm:order-none sm:col-span-1" aria-hidden="true">
                <span className="absolute inset-x-0 top-1/2 h-px bg-line" />
                <span className="absolute top-1/2 h-[2px] -translate-y-1/2" style={{ left: pos(a), width: `calc(${pos(b)} - ${pos(a)})`, background: ink }} />
                <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border bg-bg" style={{ left: pos(d.old), borderColor: clear ? "var(--fg-2)" : "var(--line-strong)" }} />
                <span className="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ left: pos(d.new), background: clear ? ink : "var(--muted)" }} />
              </span>
              <span className="flex items-baseline justify-end gap-2 text-right">
                <span className={`num text-[13px] ${clear ? "text-fg" : "text-muted"}`}>{sign(d.point, 1)}</span>
                <VerdictWord v={d.verdict} />
              </span>
              <span className="sr-only">
                {job.short}: {d.old.toFixed(1)} to {d.new.toFixed(1)}, change {sign(d.point, 2)}, 95% interval {signedCi(d)}, {WORD[d.verdict]}.
              </span>
            </li>
          );
        })}
      </ul>
      <div className="num flex justify-between text-[11px] text-muted sm:ml-[12rem] sm:mr-[10.5rem]" aria-hidden="true">
        <span>{lo}</span>
        <span>100</span>
      </div>
    </figure>
  );
}

/** Every version at its overall score with its interval, in release order; planned versions as hollow markers. */
function VersionStrip({ l, name, overall }: { l: Lineage; name: (id: string) => string; overall: Record<string, { score: number; ciLow: number; ciHigh: number }> }) {
  const pts = l.versions.map((v) => ({ v, s: overall[v] })).filter((x) => x.s);
  if (!pts.length) return null;
  const lo = Math.floor(Math.min(...pts.map((x) => x.s.ciLow)) - 1);
  const hi = Math.ceil(Math.max(...pts.map((x) => x.s.ciHigh)) + 1);
  const y = (v: number) => `${((hi - v) / (hi - lo)) * 100}%`;
  const cols = pts.length + l.planned.length;
  return (
    <figure className="m-0 flex flex-col gap-2">
      <figcaption className="text-[12px] text-muted">Overall score by version, with its 95% interval</figcaption>
      <div className="grid border-b border-line-strong" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
        {pts.map(({ v, s }) => (
          <div key={v} className="flex flex-col items-center gap-2">
            <div className="relative h-24 w-full" role="img" aria-label={`${name(v)}: ${s.score.toFixed(1)}, interval ${s.ciLow.toFixed(1)} to ${s.ciHigh.toFixed(1)}`}>
              <span className="absolute left-1/2 w-px -translate-x-1/2 bg-fg-2" style={{ top: y(s.ciHigh), height: `calc(${y(s.ciLow)} - ${y(s.ciHigh)})` }} />
              <span className="absolute left-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-fg" style={{ top: y(s.score) }} />
            </div>
            <span className="num text-[15px] font-medium">{s.score.toFixed(1)}</span>
            <span className="pb-3 text-center text-[12px] leading-tight text-muted">{name(v)}</span>
          </div>
        ))}
        {l.planned.map((v) => (
          <div key={v} className="flex flex-col items-center gap-2">
            <div className="relative h-24 w-full" aria-hidden="true">
              <span className="absolute left-1/2 top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-muted" />
            </div>
            <span className="text-[13px] text-muted">Not yet run</span>
            <span className="pb-3 text-center text-[12px] leading-tight text-muted">{PLANNED_NAMES[v] ?? v}</span>
          </div>
        ))}
      </div>
    </figure>
  );
}

function LineageBlock({ l, sys, overall }: { l: Lineage; sys: Record<string, SystemMeta>; overall: Record<string, { score: number; ciLow: number; ciHigh: number }> }) {
  const name = (id: string) => oneLine(sys[id], id);
  const steps = l.comparisons.filter((c) => c.kind === "step");
  const span = l.comparisons.find((c) => c.kind === "first to last");
  return (
    <section aria-labelledby={`lineage-${l.key}`} className="flex flex-col gap-8 border-t border-line-strong pt-8">
      <header className="flex flex-col gap-1">
        <h2 id={`lineage-${l.key}`} className="m-0 text-[clamp(1.5rem,3vw,2rem)] font-semibold tracking-[-0.02em]">{l.label}</h2>
        <p className="m-0 text-[14px] text-muted">
          {l.versions.length} {l.versions.length === 1 ? "version" : "versions"} scored
          {l.planned.length ? `, ${l.planned.length} planned` : ""}
        </p>
      </header>
      <VersionStrip l={l} name={name} overall={overall} />
      {span ? (
        <p className="m-0 max-w-[72ch] text-[15px] leading-relaxed text-fg-2">
          From {name(span.from)} to {name(span.to)}: <span className="num">{sign(span.overall.balanced_accuracy.point)}</span> points
          (95% interval {signedCi(span.overall.balanced_accuracy)}), {WORD[span.overall.balanced_accuracy.verdict].toLowerCase()}. Harmful rows
          caught <span className="num">{sign(span.overall.catch_rate.point * 100, 1)}</span> points, benign rows blocked{" "}
          <span className="num">{sign(span.overall.false_block_rate.point * 100, 1)}</span> points.
        </p>
      ) : null}
      {steps.length === 0 ? (
        <p className="m-0 text-[15px] text-muted">One version so far. The next one will be compared with it on the same checks.</p>
      ) : (
        steps.map((c) => (
          <div key={`${c.from}-${c.to}`} className="flex flex-col gap-6 border-t border-line pt-6">
            <StepHeadline c={c} name={name} />
            <JobPlot c={c} />
          </div>
        ))
      )}
    </section>
  );
}

export default function Versions() {
  const doc = loadVersions();
  const board = loadBoard();
  const sys = systemMap(board);
  const overall = Object.fromEntries(board.overall.map((s) => [s.system, s]));
  return (
    <div className="mx-auto max-w-[1200px] px-4 pt-10 sm:px-6 sm:pt-16">
      <div className="flex max-w-[920px] flex-col gap-12">
        <header className="flex flex-col gap-4">
          <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Model versions</span>
          <h1 className="m-0 text-[clamp(2rem,5vw,3rem)] font-semibold leading-[1.05] tracking-[-0.03em]">Is the new version better?</h1>
          <p className="m-0 max-w-[68ch] text-[17px] leading-relaxed text-fg-2">
            When a vendor ships a new version of a model on the <Link href="/">leaderboard</Link>, we run it on the same{" "}
            {int(board.stats.checks)} checks and compare the two check by check. A change is called better or worse only when it is
            too large to come from the luck of which rows are in the test set. Everything else is marked no clear change, even when the
            number moved.
          </p>
          <p className="m-0 max-w-[68ch] text-[14px] leading-relaxed text-muted">
            Both versions use the leaderboard&apos;s 2,000 bootstrap resamples. A change counts when its adjusted p-value is under 0.05,
            correcting for every use case and every version step we test. A score can stay flat while the model catches more and blocks
            more by mistake, so each step shows both. The{" "}
            <a href={`${REPO_URL}/blob/main/docs/benchmark/32-version-progress.md`}>full method and numbers</a> are on GitHub.
          </p>
        </header>
        {doc ? (
          doc.lineages.map((l) => <LineageBlock key={l.key} l={l} sys={sys} overall={overall} />)
        ) : (
          <p className="m-0 border-t border-line pt-6 text-[15px] text-muted">No version comparisons have been published yet.</p>
        )}
      </div>
    </div>
  );
}

