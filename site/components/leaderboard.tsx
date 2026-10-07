"use client";

import Link from "next/link";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { JOBS, JOB_BY_ID, type JobId } from "@/lib/jobs";
import { halfCi, maxTier, money, pct, score1, tierVar } from "@/lib/format";
import type { Board, Score, SystemMeta } from "@/lib/types";
import { ArrowRight, ArrowUpLeft } from "./icons";
import { Segmented, Select } from "./segmented";
import { SystemMark } from "./system-mark";

type JobPick = "overall" | JobId;
type Axis = "cost" | "fbr";
type Scope = "managed" | "all";

const JOB_OPTIONS = [{ value: "overall" as JobPick, label: "Overall, all jobs" }, ...JOBS.map((j) => ({ value: j.id as JobPick, label: j.title }))];

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

/** Round tick values from 0 to max: steps of 1, 2, 2.5 or 5 times a power of ten. */
function ticks(max: number, target = 4): number[] {
  const raw = max / target;
  const p = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw) ?? raw;
  const out: number[] = [];
  for (let v = 0; v <= max + step * 1e-6; v += step) out.push(Math.round(v / step) * step);
  return out;
}

export function Leaderboard({ board }: { board: Board }) {
  const [job, setJob] = useState<JobPick>("overall");
  const [axis, setAxis] = useState<Axis>("cost");
  const [scope, setScope] = useState<Scope>("managed");
  const sys = useMemo(() => Object.fromEntries(board.systems.map((s) => [s.id, s])) as Record<string, SystemMeta>, [board]);
  const scores: Score[] = useMemo(
    () => [...(job === "overall" ? board.overall : board.jobs[job])].sort((a, b) => a.rank - b.rank),
    [board, job],
  );
  const [selected, setSelected] = useState<string>(board.overall[0]?.system ?? "");
  const tiers = maxTier(scores);
  const shown = scores.filter((s) => scope === "all" || sys[s.system]?.hosting === "managed");
  const sel = scores.find((s) => s.system === selected) ?? scores[0];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Select id="lb-job" label="Job" options={JOB_OPTIONS} value={job} onChange={setJob} hideLabel />
        <Segmented
          label="Horizontal axis"
          value={axis}
          onChange={setAxis}
          options={[
            { value: "cost", label: "Cost per 1,000 checks" },
            { value: "fbr", label: "False-block rate" },
          ]}
        />
        <Segmented
          label="Systems on the chart"
          value={scope}
          onChange={setScope}
          options={[
            { value: "managed", label: "Managed APIs" },
            { value: "all", label: "All systems" },
          ]}
        />
      </div>
      <p className="m-0 max-w-[64ch] text-[14px] leading-relaxed text-muted">
        {job === "overall"
          ? `The plain average of the ${board.stats.suites} guardrail types. The leaders change a lot from job to job, so pick yours above.`
          : `${JOB_BY_ID[job].sub}. Score is balanced accuracy on this job; 50 is a coin flip.`}
        {axis === "cost" && scope === "all"
          ? " Hollow dots are self-hosted models; their cost is our shared GPU time and says more about our setup than about the model."
          : ""}
      </p>

      <Scatter scores={shown} sys={sys} axis={axis} tiers={tiers} selected={sel?.system} onSelect={setSelected} />

      <div className="-mx-4 overflow-x-auto sm:mx-0">
        <table className="w-full min-w-[860px] border-collapse text-[14px]">
          <caption className="sr-only">
            {job === "overall" ? "Overall" : JOB_BY_ID[job].title}: rank, score with 95% interval, tier, catch rate, false-block rate, cost and hosting for every system.
          </caption>
          <thead>
            <tr className="border-b border-line text-left text-[12px] text-muted">
              <th scope="col" className="w-10 py-2.5 pl-4 font-medium sm:pl-2">#</th>
              <th scope="col" className="py-2.5 pr-3 font-medium">System</th>
              <th scope="col" className="py-2.5 pr-3 font-medium">Score <span className="font-normal">±95% CI</span></th>
              <th scope="col" className="py-2.5 pr-3 font-medium">Tier</th>
              <th scope="col" className="py-2.5 pr-3 text-right font-medium">Catch rate</th>
              <th scope="col" className="py-2.5 pr-3 text-right font-medium">False-block rate</th>
              <th scope="col" className="py-2.5 pr-3 text-right font-medium">$ per 1,000 checks</th>
              <th scope="col" className="py-2.5 pr-4 font-medium sm:pr-2">Hosting</th>
            </tr>
          </thead>
          <tbody>
            {scores.map((s, i) => {
              const m = sys[s.system];
              const on = s.system === sel?.system;
              const newTier = i > 0 && scores[i - 1].tier !== s.tier;
              return (
                <tr
                  key={s.system}
                  onClick={() => setSelected(s.system)}
                  className={`cursor-pointer transition-colors ${newTier ? "border-t border-line-strong" : "border-t border-line"} ${
                    on ? "bg-selected" : "hover:bg-raised/60"
                  }`}
                >
                  <td className="num py-2.5 pl-4 text-muted sm:pl-2">{s.rank}</td>
                  <th scope="row" className="py-2.5 pr-3 text-left font-normal">
                    <button
                      type="button"
                      onClick={() => setSelected(s.system)}
                      aria-pressed={on}
                      className="flex min-h-11 items-center gap-3 text-left"
                    >
                      <SystemMark m={m} size="md" />
                      <span className="flex flex-col items-start">
                        <span className="font-semibold text-fg">{m?.name ?? s.system}</span>
                        <span className="text-[12px] text-muted">{m?.provider}</span>
                      </span>
                    </button>
                  </th>
                  <td className="py-2.5 pr-3">
                    <ScoreBar s={s} />
                  </td>
                  <td className="py-2.5 pr-3">
                    <span className="inline-flex items-center gap-2 whitespace-nowrap">
                      <span className="size-2.5 rounded-full" style={{ background: tierVar(s.tier) }} aria-hidden="true" />
                      <span className="num text-[13px]">{s.tier}</span>
                    </span>
                  </td>
                  <td className="num py-2.5 pr-3 text-right">{pct(s.catchRate)}</td>
                  <td className={`num py-2.5 pr-3 text-right ${s.falseBlockRate >= 0.25 ? "text-warn" : ""}`}>{pct(s.falseBlockRate)}</td>
                  <td className="num py-2.5 pr-3 text-right">{money(s.cost)}</td>
                  <td className="py-2.5 pr-4 text-[13px] text-fg-2 sm:pr-2">{m?.hosting === "managed" ? "Managed API" : "Self-hosted"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="m-0 max-w-[72ch] text-[13px] leading-relaxed text-muted">
        Every system answers the same {board.stats.checks.toLocaleString("en-US")} checks under one fixed rule: a probability of{" "}
        {board.stats.threshold} or more blocks. <Link href="/#fixed-rule">Read why.</Link> Systems in one tier cannot be told apart
        statistically from the tier&apos;s leader. Self-hosted cost is our shared GPU time.
      </p>

      {sel && <SystemPanel board={board} s={sel} m={sys[sel.system]} tiers={tiers} job={job} />}
    </div>
  );
}

function ScoreBar({ s }: { s: Score }) {
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - 50) / 50) * 100))}%`;
  return (
    <div className="flex items-center gap-3">
      <span className="relative hidden h-2 w-28 rounded-full bg-raised sm:block" aria-hidden="true">
        <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: pos(s.score), background: tierVar(s.tier) }} />
        <span className="absolute -top-1 h-4 rounded-sm bg-fg/70" style={{ left: pos(s.ciLow), width: `max(2px, calc(${pos(s.ciHigh)} - ${pos(s.ciLow)}))`, opacity: 0.55 }} />
      </span>
      <span className="num whitespace-nowrap">
        <span className="text-[15px] text-fg">{score1(s.score)}</span>
        <span className="ml-1 text-[12px] text-muted">±{halfCi(s).toFixed(1)}</span>
      </span>
    </div>
  );
}

interface Placed {
  s: Score;
  x: number;
  y: number;
  label?: { x: number; y: number; w: number; anchor: "left" | "right" };
}

function Scatter({
  scores,
  sys,
  axis,
  tiers,
  selected,
  onSelect,
}: {
  scores: Score[];
  sys: Record<string, SystemMeta>;
  axis: Axis;
  tiers: number;
  selected?: string;
  onSelect: (id: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  // Start narrow and grow to the measured width, so the chart never pushes a phone page wider than the screen.
  const [w, setW] = useState(320);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    setW(el.clientWidth);
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const h = w < 560 ? 300 : 380;
  const pad = { l: 40, r: 16, t: 16, b: 34 };
  const xv = (s: Score) => (axis === "cost" ? s.cost ?? 0 : s.falseBlockRate);
  const xMax = niceMax(Math.max(...scores.map(xv), axis === "cost" ? 0.05 : 0.05) * 1.08);
  const yMinRaw = Math.min(...scores.map((s) => s.ciLow), 90);
  const yMin = Math.max(0, Math.floor((yMinRaw - 1) / 5) * 5);
  const yMax = Math.min(100, Math.ceil((Math.max(...scores.map((s) => s.ciHigh), 60) + 1) / 5) * 5);
  const px = (v: number) => pad.l + (v / xMax) * (w - pad.l - pad.r);
  const py = (v: number) => pad.t + ((yMax - v) / (yMax - yMin)) * (h - pad.t - pad.b);
  const yTicks: number[] = [];
  for (let v = yMin; v <= yMax; v += yMax - yMin > 30 ? 10 : 5) yTicks.push(v);
  const xTicks = ticks(xMax, w < 560 ? 3 : 4);
  const fmtX = (v: number) => (axis === "cost" ? `$${v === 0 ? "0" : v < 0.01 ? v.toFixed(3) : v.toFixed(2)}` : `${Math.round(v * 100)}%`);

  // Greedy label placement: right of the dot, else left, else nudged; dropped when nothing fits.
  const placed: Placed[] = [];
  const rects: { x: number; y: number; w: number; h: number }[] = [];
  const order = [...scores].sort((a, b) => (a.system === selected ? -1 : b.system === selected ? 1 : b.score - a.score));
  for (const s of order) {
    const x = px(xv(s));
    const y = py(s.score);
    rects.push({ x: x - 8, y: y - 8, w: 16, h: 16 });
    placed.push({ s, x, y });
  }
  for (const p of placed) {
    const name = sys[p.s.system]?.short ?? sys[p.s.system]?.name ?? p.s.system;
    const lw = name.length * 6.9 + 6;
    const tries: { x: number; y: number; anchor: "left" | "right" }[] = [];
    for (const dy of [0, -14, 14, -26, 26]) {
      tries.push({ x: p.x + 15, y: p.y + dy, anchor: "right" });
      tries.push({ x: p.x - 15 - lw, y: p.y + dy, anchor: "left" });
    }
    for (const t of tries) {
      const r = { x: t.x, y: t.y - 8, w: lw, h: 16 };
      const inside = r.x >= pad.l - 4 && r.x + r.w <= w - 2 && r.y >= 0 && r.y + r.h <= h - pad.b + 4;
      const hit = rects.some((o) => o !== rects[placed.indexOf(p)] && r.x < o.x + o.w && r.x + r.w > o.x && r.y < o.y + o.h && r.y + r.h > o.y);
      if (inside && !hit) {
        rects.push(r);
        p.label = { x: t.x, y: t.y, w: lw, anchor: t.anchor };
        break;
      }
    }
  }

  const present = [...new Set(scores.map((s) => s.tier))].sort((a, b) => a - b);
  return (
    <figure className="m-0 flex flex-col gap-3">
      <div ref={box} className="relative w-full select-none overflow-hidden rounded-xl border border-line bg-surface" style={{ height: h }}>
        <svg width={w} height={h} className="absolute inset-0 max-w-full" aria-hidden="true">
          {yTicks.map((v) => (
            <g key={`y${v}`}>
              <line x1={pad.l} x2={w - pad.r} y1={py(v)} y2={py(v)} stroke="var(--line)" strokeDasharray="3 4" />
              <text x={pad.l - 8} y={py(v)} dy="0.32em" textAnchor="end" className="num" fontSize="12" fill="var(--muted)">
                {v}
              </text>
            </g>
          ))}
          {xTicks.map((v) => (
            <text key={`x${v}`} x={px(v)} y={h - pad.b + 18} textAnchor="middle" className="num" fontSize="12" fill="var(--muted)">
              {fmtX(v)}
            </text>
          ))}
          <line x1={pad.l} x2={w - pad.r} y1={h - pad.b} y2={h - pad.b} stroke="var(--line-strong)" />
          <line x1={pad.l} x2={pad.l} y1={pad.t} y2={h - pad.b} stroke="var(--line-strong)" />
          {placed.map((p) => {
            const s = p.s;
            const half = (py(s.ciLow) - py(s.ciHigh)) / 2;
            return <line key={`ci${s.system}`} x1={p.x} x2={p.x} y1={p.y - half} y2={p.y + half} stroke={tierVar(s.tier)} strokeOpacity="0.45" strokeWidth="2" />;
          })}
        </svg>
        <div className="pointer-events-none absolute left-12 top-3 flex items-center gap-1.5 text-[12px] font-medium text-link">
          <ArrowUpLeft className="size-3.5" />
          better
        </div>
        {placed.map((p) => {
          const m = sys[p.s.system];
          const on = p.s.system === selected;
          const self = m?.hosting === "self-hosted";

          return (
            <button
              key={p.s.system}
              type="button"
              onClick={() => onSelect(p.s.system)}
              aria-pressed={on}
              aria-label={`${m?.name ?? p.s.system}: score ${score1(p.s.score)}, ${axis === "cost" ? `${money(p.s.cost)} per 1,000 checks` : `${pct(p.s.falseBlockRate)} false blocks`}, tier ${p.s.tier}`}
              title={`${m?.name ?? p.s.system} · ${score1(p.s.score)} · ${axis === "cost" ? money(p.s.cost) : pct(p.s.falseBlockRate)}`}
              className="absolute grid size-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full"
              style={{ left: p.x, top: p.y }}
            >
              <span
                className="block size-3 rounded-full transition-transform duration-150 ease-out"
                style={{
                  transform: on ? "scale(1.34)" : undefined,
                  background: self && axis === "cost" ? "var(--surface)" : tierVar(p.s.tier),
                  border: `2px solid ${tierVar(p.s.tier)}`,
                  boxShadow: on ? "0 0 0 3px var(--surface), 0 0 0 5px var(--fg)" : "0 0 0 2px var(--surface)",
                }}
              />
            </button>
          );
        })}
        {placed.map((p) =>
          p.label ? (
            <span
              key={`l${p.s.system}`}
              aria-hidden="true"
              className={`pointer-events-none absolute -translate-y-1/2 whitespace-nowrap text-[12px] leading-none ${
                p.s.system === selected ? "font-semibold text-fg" : "text-fg-2"
              }`}
              style={{ left: p.label.x, top: p.label.y, width: p.label.w, textAlign: p.label.anchor === "left" ? "right" : "left" }}
            >
              {sys[p.s.system]?.short ?? sys[p.s.system]?.name ?? p.s.system}
            </span>
          ) : null,
        )}
      </div>
      <figcaption className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 text-[12px] text-muted">
        <span>
          Score (balanced accuracy, 50 is a coin flip) against {axis === "cost" ? "USD per 1,000 checks" : "the share of safe rows blocked"}. Lines show the 95% interval. The table below has every number.
        </span>
        <span className="flex flex-wrap items-center gap-3" aria-label="Tier colours">
          {present.map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ background: tierVar(t) }} aria-hidden="true" />
              Tier {t}
            </span>
          ))}
          <span className="sr-only">of {tiers}</span>
        </span>
      </figcaption>
    </figure>
  );
}

function SystemPanel({ board, s, m, tiers, job }: { board: Board; s: Score; m?: SystemMeta; tiers: number; job: JobPick }) {
  const best = Object.fromEntries(JOBS.map((j) => [j.id, Math.max(...board.jobs[j.id].map((x) => x.score))]));
  const stats = [
    { label: job === "overall" ? "Overall score" : "Score on this job", value: score1(s.score) },
    { label: "95% interval", value: `${score1(s.ciLow)} to ${score1(s.ciHigh)}` },
    { label: "Catches harmful rows", value: pct(s.catchRate) },
    { label: "Blocks safe rows", value: pct(s.falseBlockRate) },
    { label: "Cost per 1,000 checks", value: money(s.cost) },
    { label: "Statistical tier", value: `${s.tier} of ${tiers}` },
  ];
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - 50) / 50) * 100))}%`;
  return (
    <section aria-label={`${m?.name ?? s.system} in detail`} className="grid gap-8 rounded-xl border border-line bg-surface p-5 sm:p-6 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <SystemMark m={m} size="lg" />
          <span className="flex flex-col">
            <span className="text-[20px] font-semibold tracking-[-0.01em]">{m?.name ?? s.system}</span>
            <span className="text-[13px] text-muted">
              {m?.provider}
              {m ? (m.hosting === "managed" ? " · managed API" : " · self-hosted on our GPUs") : ""}
            </span>
          </span>
        </div>
        <dl className="m-0 grid grid-cols-2 gap-2">
          {stats.map((x) => (
            <div key={x.label} className="rounded-lg bg-raised px-3.5 py-3">
              <dt className="text-[12px] text-muted">{x.label}</dt>
              <dd className="num m-0 mt-1 text-[17px]">{x.value}</dd>
            </div>
          ))}
        </dl>
        <Link href={`/data?system=${encodeURIComponent(s.system)}${job === "overall" ? "" : `&job=${job}`}#rows`} className="inline-flex min-h-11 items-center gap-1.5 self-start text-[14px]">
          See the rows it got wrong <ArrowRight />
        </Link>
      </div>
      <div className="flex min-w-0 flex-col gap-3">
        <h3 className="m-0 text-[16px] font-semibold">{m?.name ?? s.system} by job</h3>
        <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
          {JOBS.map((j) => {
            const js = board.jobs[j.id].find((x) => x.system === s.system);
            return (
              <li key={j.id} className="grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_3rem] items-center gap-3 sm:grid-cols-[12rem_minmax(0,1fr)_3rem]">
                <span className={`text-[13px] leading-tight ${job === j.id ? "font-semibold text-fg" : "text-fg-2"}`}>
                  <span className="sm:hidden">{j.short}</span>
                  <span className="hidden sm:inline">{j.title}</span>
                </span>
                <span className="relative h-2 rounded-full bg-raised" aria-hidden="true">
                  {js && <span className="absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: pos(js.score) }} />}
                  <span className="absolute -top-1 h-4 w-0.5 bg-fg" style={{ left: pos(best[j.id]) }} />
                </span>
                <span className="num text-right text-[13px]">{js ? score1(js.score) : "n/a"}</span>
              </li>
            );
          })}
        </ul>
        <p className="m-0 text-[12px] text-muted">Bars start at 50, a coin flip. The thin mark is the best score on that job. Pick any system in the chart or table.</p>
      </div>
    </section>
  );
}
