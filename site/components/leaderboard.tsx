"use client";

import Link from "next/link";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { JOBS, JOB_BY_ID, type JobId } from "@/lib/jobs";
import { halfCi, maxTier, money, pct, score1, tierVar } from "@/lib/format";
import type { Board, Score, SystemMeta } from "@/lib/types";
import { ArrowRight, ArrowUpLeft, External } from "./icons";
import { Segmented, Select } from "./segmented";
import { SystemMark } from "./system-mark";
import { WallpaperFrame } from "./plate";

type JobPick = "overall" | JobId;
type Axis = "cost" | "fbr";
type Scope = "managed" | "all";

const JOB_OPTIONS = [{ value: "overall" as JobPick, label: "Overall, all use cases" }, ...JOBS.map((j) => ({ value: j.id as JobPick, label: j.title }))];

// Label widths measured with the real font, so placement does not drop labels that fit.
let measureCtx: CanvasRenderingContext2D | null = null;
function textWidth(text: string, measure: boolean): number {
  if (measure) {
    measureCtx ??= document.createElement("canvas").getContext("2d");
    if (measureCtx) {
      measureCtx.font = `500 12px ${getComputedStyle(document.body).fontFamily}`;
      return measureCtx.measureText(text).width;
    }
  }
  return text.length * 6.6;
}

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
        <Select id="lb-job" label="Use case" options={JOB_OPTIONS} value={job} onChange={setJob} hideLabel />
        <Segmented
          label="Horizontal axis"
          value={axis}
          onChange={setAxis}
          options={[
            { value: "cost", label: "Cost per 1,000 checks", short: "Cost" },
            { value: "fbr", label: "False-block rate", short: "False blocks" },
          ]}
        />
        <Segmented
          label="Systems to show"
          value={scope}
          onChange={setScope}
          options={[
            { value: "managed", label: "Managed APIs", short: "Managed" },
            { value: "all", label: "All systems", short: "All" },
          ]}
        />
      </div>
      <p className="m-0 text-[14px] leading-relaxed text-muted">
        {job === "overall"
          ? `The overall score is the plain average of ${board.stats.suites} guardrail suites, which together cover the ${board.stats.jobs} use cases. The leaders change a lot from use case to use case. Select your use case above.`
          : `${JOB_BY_ID[job].sub}. The score is balanced accuracy on this use case. A score of 50 is a coin flip.`}
        {axis === "cost" && scope === "all"
          ? " Dashed squares are self-hosted models. Their cost is our shared GPU time, so it tells you more about our setup than about the model."
          : ""}
      </p>

      <WallpaperFrame src="/plates/headland.webp">
      <Scatter scores={shown} sys={sys} axis={axis} tiers={tiers} selected={sel?.system} onSelect={setSelected} />

      <div className="overflow-x-auto rounded-xl border border-line bg-surface">
        <table className="w-full sm:min-w-[860px] border-collapse text-[14px]">
          <caption className="sr-only">
            {job === "overall" ? "Overall" : JOB_BY_ID[job].title}: rank, score with 95% interval, tier, catch rate, false-block rate, cost and hosting for every system.
          </caption>
          <thead>
            <tr className="border-b border-line text-left text-[12px] text-muted">
              <th scope="col" className="hidden w-10 py-3 pl-5 font-medium sm:table-cell">#</th>
              <th scope="col" className="sticky left-0 z-[1] bg-surface py-2.5 pl-3 pr-3 font-medium sm:static sm:pl-0">System</th>
              <th scope="col" className="py-2.5 pr-3 text-right font-medium sm:text-left">Score <span className="font-normal">±95% CI</span></th>
              <th scope="col" className="hidden py-2.5 pr-3 font-medium sm:table-cell">Tier</th>
              <th scope="col" className="hidden py-2.5 pr-3 text-right font-medium sm:table-cell">Catch rate</th>
              <th scope="col" className="hidden py-2.5 pr-3 text-right font-medium sm:table-cell">False-block rate</th>
              <th scope="col" className="hidden py-2.5 pr-3 text-right font-medium sm:table-cell">$ per 1,000 checks</th>
              <th scope="col" className="hidden py-3 pr-4 font-medium sm:table-cell sm:pr-5">Type</th>
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
                    on ? "bg-selected" : m?.kind === "service" ? "bg-raised hover:bg-raised" : "hover:bg-raised/60"
                  }`}
                >
                  <td className="num hidden py-2.5 pl-5 text-muted sm:table-cell">{s.rank}</td>
                  {/* On a phone the name column stays put while the numbers scroll under it. */}
                  <th scope="row" className={`sticky left-0 z-[1] py-2.5 pl-3 pr-3 text-left font-normal sm:static sm:pl-0 ${on ? "bg-selected" : m?.kind === "service" ? "bg-raised" : "bg-surface"}`}>
                    <button
                      type="button"
                      onClick={() => setSelected(s.system)}
                      aria-pressed={on}
                      className="flex min-h-11 items-center gap-3 text-left"
                    >
                      <SystemMark m={m} size="md" />
                      <span className="flex flex-col items-start">
                        <span className="font-semibold text-fg">{m?.name ?? s.system}</span>
                        <span className="hidden text-[12px] text-muted sm:block">{m?.provider}</span>
                        {m?.kind === "service" && <span className="text-[12px] text-fg-2 sm:hidden">Guardrail service</span>}
                      </span>
                    </button>
                  </th>
                  <td className="py-2.5 pr-3 text-right sm:text-left">
                    <ScoreBar s={s} />
                    {/* Phones: cost and false blocks sit under the score instead of in columns off-screen. */}
                    <span className={`num mt-0.5 block whitespace-nowrap text-[12px] sm:hidden ${s.falseBlockRate >= 0.25 ? "text-warn" : "text-muted"}`}>
                      {money(s.cost)} · {pct(s.falseBlockRate)} blocked
                    </span>
                  </td>
                  <td className="hidden py-2.5 pr-3 sm:table-cell">
                    <span className="inline-flex items-center gap-2 whitespace-nowrap">
                      <span className="size-2.5 rounded-full" style={{ background: tierVar(s.tier) }} aria-hidden="true" />
                      <span className="num text-[13px]">{s.tier}</span>
                    </span>
                  </td>
                  <td className="num hidden py-2.5 pr-3 text-right sm:table-cell">{pct(s.catchRate)}</td>
                  <td className={`num hidden py-2.5 pr-3 text-right sm:table-cell ${s.falseBlockRate >= 0.25 ? "text-warn" : ""}`}>{pct(s.falseBlockRate)}</td>
                  <td className="num hidden py-2.5 pr-3 text-right sm:table-cell">{money(s.cost)}</td>
                  <td className="hidden py-2.5 pr-4 text-[13px] sm:table-cell sm:pr-5">
                    <KindTag kind={m?.kind} />
                    <span className="block text-[12px] text-muted">{m?.hosting === "managed" ? "Managed API" : "Self-hosted"}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      </WallpaperFrame>

      <p className="m-0 text-[13px] leading-relaxed text-muted">
        The shaded row is a guardrail service, not a decision model (<a href="#kinds">see the difference</a>). Every system answers the
        same {board.stats.checks.toLocaleString("en-US")} checks under one fixed rule: a probability of{" "}
        {board.stats.threshold} or more blocks. <a
          href="#fixed-rule"
          onClick={() => {
            const d = document.querySelector<HTMLDetailsElement>("#fixed-rule details");
            if (d) d.open = true;
          }}
        >
          Read why.
        </a> Our statistical tests cannot tell the
        systems in one tier apart from that tier&apos;s leader. Self-hosted cost is our shared GPU time.
      </p>

      {sel && <SystemPanel board={board} s={sel} m={sys[sel.system]} tiers={tiers} job={job} />}
    </div>
  );
}

function ScoreBar({ s }: { s: Score }) {
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - 50) / 50) * 100))}%`;
  return (
    <div className="flex items-center justify-end gap-3 sm:justify-start">
      <span className="relative hidden h-2 w-28 rounded-full bg-raised sm:block" aria-hidden="true">
        <span className="grow absolute inset-y-0 left-0 rounded-full" style={{ width: pos(s.score), background: tierVar(s.tier), animationDelay: `${s.rank * 40}ms` }} />
        <span className="absolute -top-1 h-4 rounded-sm bg-fg/70" style={{ left: pos(s.ciLow), width: `max(2px, calc(${pos(s.ciHigh)} - ${pos(s.ciLow)}))`, opacity: 0.55 }} />
      </span>
      <span className="num whitespace-nowrap">
        <span className="text-[15px] text-fg">{score1(s.score)}</span>
        <span className="ml-1 text-[12px] text-muted">±{halfCi(s).toFixed(1)}</span>
      </span>
    </div>
  );
}

/** Decision model or guardrail service, as plain text in the Type column. The service row itself is shaded. */
export function KindTag({ kind }: { kind?: "decision" | "service" }) {
  return <span className={`text-[13px] ${kind === "service" ? "font-medium text-fg" : "text-fg-2"}`}>{kind === "service" ? "Guardrail service" : "Decision model"}</span>;
}

interface Placed {
  s: Score;
  x: number;
  y: number;
  /** the exact data position; x/y may sit up to MAX_SHIFT px away from it */
  tx: number;
  ty: number;
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
  // Measure label widths only after mount, so the first client render matches the server HTML.
  const [measure, setMeasure] = useState(false);
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    setW(el.clientWidth);
    setMeasure(true);
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const compact = w < 560;
  const h = compact ? 340 : 380;
  const pad = { l: 40, r: 28, t: 40, b: 34 };
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
  // The "better" hint sits top left, where the strongest systems land: reserve it first.
  const rects: { x: number; y: number; w: number; h: number }[] = [{ x: 44, y: 4, w: 70, h: 22 }];
  const order = [...scores].sort((a, b) => (a.system === selected ? -1 : b.system === selected ? 1 : b.score - a.score));
  // Half the square's size plus its ring, per system.
  const half = (s: Score) => (s.system === selected ? (compact ? 14 : 19) : compact ? 11 : 15);
  for (const s of order) {
    const x = px(xv(s));
    const y = py(s.score);
    placed.push({ s, x, y, tx: x, ty: y });
  }
  // A square may move at most this far from its exact value to make room; beyond that, squares overlap (the selected
  // one on top) rather than misstate a score. A dot marks the exact value whenever a square moved.
  const MAX_SHIFT = compact ? 10 : 12;
  const bound = (p: Placed) => {
    p.x = Math.min(p.tx + MAX_SHIFT, Math.max(p.tx - MAX_SHIFT, p.x));
    p.y = Math.min(p.ty + MAX_SHIFT, Math.max(p.ty - MAX_SHIFT, p.y));
  };
  // Squares that would overlap are pushed apart a few pixels, mostly vertically, and kept inside the plot, so every
  // square stays visible and can be selected. The table below has the exact numbers.
  const clampX = (p: Placed) => Math.min(w - pad.r - half(p.s), Math.max(pad.l + half(p.s) + 2, p.x));
  const clampY = (p: Placed) => Math.min(h - pad.b - half(p.s), Math.max(pad.t + half(p.s), p.y));
  for (const p of placed) {
    p.x = clampX(p);
    p.y = clampY(p);
  }
  for (let round = 0; round < 60; round++) {
    let moved = false;
    for (let i = 0; i < placed.length; i++) {
      for (let j = i + 1; j < placed.length; j++) {
        const a = placed[i];
        const b = placed[j];
        const need = half(a.s) + half(b.s) + 2;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        if (Math.abs(dx) >= need || Math.abs(dy) >= need) continue;
        const push = (need - Math.abs(dy)) / 2 + 0.5;
        const dir = dy !== 0 ? Math.sign(dy) : a.s.score >= b.s.score ? 1 : -1;
        a.y -= dir * push;
        b.y += dir * push;
        a.y = clampY(a);
        b.y = clampY(b);
        bound(a);
        bound(b);
        // Pinned against the top or bottom edge, the pair cannot separate vertically: spread it sideways instead.
        if (Math.abs(b.y - a.y) < need && (Math.abs(dx) < need / 2 || a.y === clampY({ ...a, y: -1e9 }) || a.y === clampY({ ...a, y: 1e9 }))) {
          const sx = dx !== 0 ? Math.sign(dx) : 1;
          const spread = Math.max(2, (need - Math.abs(dx)) / 2 + 0.5);
          a.x = clampX({ ...a, x: a.x - sx * spread });
          b.x = clampX({ ...b, x: b.x + sx * spread });
          bound(a);
          bound(b);
        }
        moved = true;
      }
    }
    if (!moved) break;
  }
  for (const p of placed) {
    const rr = half(p.s);
    rects.push({ x: p.x - rr, y: p.y - rr, w: 2 * rr, h: 2 * rr });
  }
  // The selected system's distance to the guardrail service: a dashed reference line at the service's score and a
  // thin connector from the selected system's exact value, labelled with the gap in score points.
  const ref = scores.find((s) => sys[s.system]?.kind === "service");
  const selP = placed.find((p) => p.s.system === selected);
  const gap = ref && selP && selP.s.system !== ref.system ? selP.s.score - ref.score : null;
  let gapLabel: { x: number; y: number; text: string } | null = null;
  if (gap !== null && selP && ref) {
    const text = `${gap >= 0 ? "+" : "−"}${Math.abs(gap).toFixed(1)} vs Bedrock`;
    const gw = Math.ceil(textWidth(text, measure)) + 6;
    const mid = (selP.ty + py(ref.score)) / 2;
    const gx = selP.tx + 6 + gw <= w - pad.r ? selP.tx + 6 : selP.tx - 6 - gw;
    gapLabel = { x: gx, y: mid, text };
    rects.push({ x: gx, y: mid - 8, w: gw, h: 16 });
  }

  for (const p of placed) {
    const name = sys[p.s.system]?.short ?? sys[p.s.system]?.name ?? p.s.system;
    const lw = Math.ceil(textWidth(name, measure)) + 4;
    const off = p.s.system === selected ? (compact ? 20 : 24) : compact ? 17 : 20;
    const tries: { x: number; y: number; anchor: "left" | "right" }[] = [];
    // Labels stay beside their square; one that cannot is listed under the chart instead of floating away from it.
    for (const dy of [0, -12, 12]) {
      tries.push({ x: p.x + off, y: p.y + dy, anchor: "right" });
      tries.push({ x: p.x - off - lw, y: p.y + dy, anchor: "left" });
    }
    // The selected system is always annotated: it may also sit centred above or below its square, or further out.
    if (p.s.system === selected) {
      const v = half(p.s) + 10;
      tries.push({ x: p.x - lw / 2, y: p.y - v, anchor: "right" }, { x: p.x - lw / 2, y: p.y + v, anchor: "right" });
      for (const dy of [-24, 24]) tries.push({ x: p.x + off, y: p.y + dy, anchor: "right" }, { x: p.x - off - lw, y: p.y + dy, anchor: "left" });
    }
    for (const t of tries) {
      const r = { x: t.x, y: t.y - 8, w: lw, h: 16 };
      const inside = r.x >= pad.l - 4 && r.x + r.w <= w - 2 && r.y >= 0 && r.y + r.h <= h - pad.b + 4;
      const hit = rects.some((o) => o !== rects[placed.indexOf(p) + 1] && r.x < o.x + o.w && r.x + r.w > o.x && r.y < o.y + o.h && r.y + r.h > o.y);
      if (inside && !hit) {
        rects.push(r);
        p.label = { x: t.x, y: t.y, w: lw, anchor: t.anchor };
        break;
      }
    }
  }

  // Tiers 5 and below share one colour, so the legend shows them as one entry.
  const present = [...new Set(scores.map((s) => Math.min(s.tier, 5)))].sort((a, b) => a - b);
  const unlabelled = placed.filter((p) => !p.label).sort((a, b) => a.s.rank - b.s.rank);
  return (
    <figure className="m-0 flex flex-col gap-3 rounded-xl border border-line bg-surface p-3 sm:p-5">
      <div ref={box} className="relative w-full select-none overflow-hidden" style={{ height: h }}>
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
          {gap !== null && ref && selP && (
            <g aria-hidden="true">
              <line x1={pad.l} x2={w - pad.r} y1={py(ref.score)} y2={py(ref.score)} stroke="var(--fg-2)" strokeOpacity="0.45" strokeDasharray="2 4" />
              <line x1={selP.tx} x2={selP.tx} y1={selP.ty} y2={py(ref.score)} stroke="var(--fg)" strokeOpacity="0.55" strokeWidth="1.25" />
              <line x1={selP.tx - 4} x2={selP.tx + 4} y1={py(ref.score)} y2={py(ref.score)} stroke="var(--fg)" strokeOpacity="0.55" strokeWidth="1.25" />
            </g>
          )}
          {placed.map((p) => {
            const s = p.s;
            // The interval and the exact-value dot are drawn at the true position, whatever the square's offset.
            const moved = Math.hypot(p.x - p.tx, p.y - p.ty) > 2;
            return (
              <g key={`ci${s.system}`}>
                <line x1={p.tx} x2={p.tx} y1={py(s.ciHigh)} y2={py(s.ciLow)} stroke={tierVar(s.tier)} strokeOpacity="0.45" strokeWidth="2" />
                {moved && (
                  <>
                    <line x1={p.tx} y1={p.ty} x2={p.x} y2={p.y} stroke={tierVar(s.tier)} strokeOpacity="0.6" strokeWidth="1" />
                    <circle cx={p.tx} cy={p.ty} r="2.5" fill={tierVar(s.tier)} />
                  </>
                )}
              </g>
            );
          })}
        </svg>
        <div className="pointer-events-none absolute left-12 top-2 flex items-center gap-1.5 text-[12px] font-medium text-link">
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
              className={`pop absolute grid place-items-center rounded-md ${on ? "z-10" : ""}`}
              // The hit area is the square plus its ring (half() each way), the same box the layout keeps apart.
              style={{ left: p.x - half(p.s), top: p.y - half(p.s), width: 2 * half(p.s), height: 2 * half(p.s), animationDelay: `${120 + p.s.rank * 45}ms` }}
            >
              {/* A square per system: the maker's mark inside, tier colour on the border and as a wash behind it. */}
              <span
                className={`grid place-items-center rounded-md ${on ? (compact ? "size-6" : "size-[34px]") : compact ? "size-5" : "size-7"}`}
                style={{
                  background: `color-mix(in srgb, ${tierVar(p.s.tier)} 14%, var(--surface))`,
                  border: `2px ${self && axis === "cost" ? "dashed" : "solid"} ${tierVar(p.s.tier)}`,
                  boxShadow: on ? "0 0 0 2px var(--surface), 0 0 0 4px var(--fg)" : "0 0 0 2px var(--surface)",
                }}
              >
                {m?.logo ? (
                  // eslint-disable-next-line @next/next/no-img-element -- static export, tiny SVGs
                  <img src={m.logo} alt="" className={on && !compact ? "size-5" : compact ? "size-3" : "size-4"} />
                ) : (
                  <span className="text-[11px] font-semibold leading-none text-fg-2">{m?.mono}</span>
                )}
              </span>
            </button>
          );
        })}
        {gapLabel && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute -translate-y-1/2 whitespace-nowrap rounded-full bg-surface/90 px-1.5 text-[12px] font-semibold leading-[16px] text-fg"
            style={{ left: gapLabel.x, top: gapLabel.y }}
          >
            {gapLabel.text}
          </span>
        )}
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
      {unlabelled.length > 0 && (
        <p className="m-0 text-[12px] text-muted">
          No room for a label: {unlabelled.map((p) => sys[p.s.system]?.name ?? p.s.system).join(", ")}. Select its square to see it.
        </p>
      )}
      <figcaption className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 text-[12px] text-muted">
        <span>
          Score is balanced accuracy, where 50 is a coin flip. The horizontal axis is {axis === "cost" ? "USD per 1,000 checks" : "the share of safe rows blocked"}. Lines show the 95% interval; if a square had to move to stay readable, a dot marks its exact value.
        </span>
        <span className="flex flex-wrap items-center gap-3" aria-label="Tier colours">
          {present.map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ background: tierVar(t) }} aria-hidden="true" />
              Tier {t}
              {t === 5 && tiers > 5 ? "+" : ""}
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
    { label: job === "overall" ? "Overall score" : "Score on this use case", value: score1(s.score) },
    { label: "95% interval", value: `${score1(s.ciLow)} to ${score1(s.ciHigh)}` },
    { label: "Catches harmful rows", value: pct(s.catchRate) },
    { label: "Blocks safe rows", value: pct(s.falseBlockRate) },
    { label: "Cost per 1,000 checks", value: money(s.cost) },
    { label: "Statistical tier", value: `${s.tier} of ${tiers}` },
  ];
  const pos = (v: number) => `${Math.max(0, Math.min(100, ((v - 50) / 50) * 100))}%`;
  // The same system set against the guardrail service, on the job in view.
  const refMeta = board.systems.find((x) => x.kind === "service");
  const ref = refMeta ? (job === "overall" ? board.overall : board.jobs[job]).find((x) => x.system === refMeta.id) : undefined;
  const vs =
    ref && m?.kind !== "service"
      ? [
          { label: "Score", value: s.score - ref.score, unit: "points", better: s.score >= ref.score },
          { label: "Catches harmful", value: (s.catchRate - ref.catchRate) * 100, unit: "points", better: s.catchRate >= ref.catchRate },
          { label: "Blocks safe", value: (s.falseBlockRate - ref.falseBlockRate) * 100, unit: "points", better: s.falseBlockRate <= ref.falseBlockRate },
          ...(s.cost !== null && ref.cost
            ? [{ label: "Cost", value: s.cost / ref.cost, unit: "ratio", better: s.cost <= ref.cost }]
            : []),
        ]
      : null;
  return (
    <section aria-label={`Details for ${m?.name ?? s.system}`} className="grid gap-8 rounded-xl border border-line bg-surface p-5 sm:p-6 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <SystemMark m={m} size="lg" />
          <span className="flex flex-col">
            <span className="text-[20px] font-semibold tracking-[-0.01em]">{m?.name ?? s.system}</span>
            <span className="text-[13px] text-muted">
              {m?.provider}
              {m ? (m.hosting === "managed" ? " · managed API" : " · self-hosted on our GPUs") : ""}
              {m ? (m.kind === "service" ? " · guardrail service" : " · decision model") : ""}
            </span>
            {(m?.docs || m?.pricing) && (
              <span className="flex flex-wrap gap-x-3 text-[13px]">
                {m.docs && (
                  <a href={m.docs} className="inline-flex min-h-11 items-center gap-1 sm:min-h-0">
                    {m.hosting === "self-hosted" ? "Model card" : "Vendor docs"} <External className="size-3" />
                  </a>
                )}
                {m.pricing && (
                  <a href={m.pricing} className="inline-flex min-h-11 items-center gap-1 sm:min-h-0">
                    {m.hosting === "self-hosted" ? "GPU pricing" : "Vendor pricing"} <External className="size-3" />
                  </a>
                )}
              </span>
            )}
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
        {vs && (
          <div className="flex flex-col gap-2 border-t border-line pt-4">
            <span className="text-[12px] font-medium uppercase tracking-[0.12em] text-muted">Against Amazon Bedrock Guardrails</span>
            <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-2.5">
              {vs.map((x) => (
                <div key={x.label} className="flex flex-col">
                  <dt className="text-[12px] text-muted">{x.label}</dt>
                  <dd className={`num m-0 whitespace-nowrap text-[16px] font-semibold ${x.better ? "text-good" : "text-warn"}`}>
                    {x.unit === "ratio"
                      ? `${x.value < 1 ? (1 / x.value).toFixed(1) + "× cheaper" : x.value.toFixed(1) + "× the cost"}`
                      : `${x.value >= 0 ? "+" : "−"}${Math.abs(x.value).toFixed(1)}`}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        <Link href={`/data?system=${encodeURIComponent(s.system)}${job === "overall" ? "" : `&job=${job}`}#rows`} className="inline-flex min-h-11 items-center gap-1.5 self-start text-[14px]">
          See the rows it got wrong <ArrowRight />
        </Link>
      </div>
      <div className="flex min-w-0 flex-col gap-3">
        <h3 className="m-0 text-[16px] font-semibold">{m?.name ?? s.system} by use case</h3>
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
                  {js && <span className="grow absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: pos(js.score) }} />}
                  <span className="absolute -top-1 h-4 w-0.5 bg-fg" style={{ left: pos(best[j.id]) }} />
                </span>
                <span className="num text-right text-[13px]">{js ? score1(js.score) : "n/a"}</span>
              </li>
            );
          })}
        </ul>
        <p className="m-0 text-[12px] text-muted">Bars start at 50, which is a coin flip. The thin mark shows the best score on that use case. Select a system in the chart or the table to see its details.</p>
      </div>
    </section>
  );
}
