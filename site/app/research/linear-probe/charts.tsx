"use client";

import { useEffect, useRef, useState } from "react";
import { AxisBottom } from "@visx/axis";
import { GridColumns } from "@visx/grid";
import { scaleLinear } from "@visx/scale";
import { Line } from "@visx/shape";
import { STUDY, type Arm, type ModelKey } from "./data";

const ink = {
  fg: "var(--fg)",
  fg2: "var(--fg-2)",
  muted: "var(--muted)",
  line: "var(--line)",
  strong: "var(--line-strong)",
  accent: "var(--accent)",
  good: "var(--good)",
  warn: "var(--warn)",
  surface: "var(--surface)",
};
const tickLabel = { fill: ink.muted, fontSize: 11, fontFamily: "var(--font-inter)", textAnchor: "middle" as const };
// A thin paper outline behind text, so a gridline passing under a value label never cuts through it.
const halo = { stroke: ink.surface, strokeWidth: 4, strokeLinejoin: "round" as const, paintOrder: "stroke" as const };

/** Gridlines drawn only through the given bands of rows, never through the label lines between them. */
function BandGrid({ x, ticks, bands }: { x: (v: number) => number; ticks: number[]; bands: [number, number][] }) {
  return (
    <g stroke={ink.line} strokeWidth={1}>
      {bands.flatMap(([y0, y1], b) => ticks.map((t) => <line key={b + ":" + t} x1={x(t)} x2={x(t)} y1={y0} y2={y1} />))}
    </g>
  );
}

/** Width-aware wrapper: renders at a fallback width on the server, then at the measured width. Height follows the SVG. */
function Measured({ height, children }: { height: number; children: (width: number) => React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <div ref={ref} className="w-full" style={width ? undefined : { minHeight: height }}>
      {width > 0 ? children(width) : null}
    </div>
  );
}

function Frame({ fig, title, children, caption }: { fig: string; title: string; children: React.ReactNode; caption: React.ReactNode }) {
  return (
    <figure className="m-0">
      <div className="rounded-[4px] border border-line-strong bg-surface px-4 pt-3 pb-4 sm:px-5">
        <div className="mb-3 flex justify-between gap-4 text-xs text-muted">
          <span className="num">{fig}</span>
          <span className="text-right">{title}</span>
        </div>
        {children}
      </div>
      <figcaption className="mx-auto mt-3 max-w-[44rem] text-sm leading-relaxed text-muted">{caption}</figcaption>
    </figure>
  );
}

/* ---------- Fig 4: mistakes on the 540 test requests ---------- */

const MISTAKE_ROWS: { model: ModelKey; metric: "missed" | "falseBlocks"; label: string; of: number }[] = [
  { model: "strands", metric: "missed", label: "Violations missed", of: 256 },
  { model: "strands", metric: "falseBlocks", label: "Safe requests blocked", of: 284 },
  { model: "kev", metric: "missed", label: "Violations missed", of: 256 },
  { model: "kev", metric: "falseBlocks", label: "Safe requests blocked", of: 284 },
];

export function MistakesChart() {
  const layout = (narrow: boolean) => {
    const rowH = narrow ? 44 : 34;
    let y = 4;
    const titles: { y: number; model: ModelKey }[] = [];
    const rows = MISTAKE_ROWS.map((r, i) => {
      if (i % 2 === 0) {
        if (i) y += 14;
        titles.push({ y: y + 13, model: r.model });
        y += 24;
      }
      const row = { ...r, labelY: narrow ? y + 12 : y + 20, y: narrow ? y + 28 : y + 16 };
      y += rowH;
      return row;
    });
    return { titles, rows, height: y + 30 };
  };
  const height = layout(false).height;
  return (
    <Frame
      fig="Fig 4"
      title="Mistakes on 540 held-out requests"
      caption={
        <>
          Counts from the study’s test metrics: 256 requests the policy says to block, 284 it allows. The open ring is the
          leaderboard’s fixed 0.5 cutoff, for reference. Both the built-in score and the probe had their cutoff chosen on
          the 29 validation requests.
        </>
      }
    >
      <Legend />
      <Measured height={height}>
        {(width) => {
          const narrow = width < 520;
          const { titles, rows, height: h } = layout(narrow);
          const labelW = narrow ? 0 : 160;
          const valueW = 64;
          const x = scaleLinear({ domain: [0, 75], range: [labelW + 6, width - valueW - 8] });
          return (
            <svg width={width} height={h} role="img" aria-label="Dot chart of mistakes by model and decision rule">
              {narrow ? (
                <BandGrid x={x} ticks={[0, 25, 50, 75]} bands={[...rows.map((r) => [r.y - 10, r.y + 10] as [number, number]), [h - 34, h - 26]]} />
              ) : (
                <GridColumns scale={x} top={titles[0].y + 6} height={h - 26 - titles[0].y - 6} stroke={ink.line} tickValues={[0, 25, 50, 75]} />
              )}
              {titles.map((t) => (
                <text key={t.model} x={0} y={t.y} fontSize={13} fontWeight={600} fill={ink.fg}>
                  {STUDY[t.model].name}
                </text>
              ))}
              <text x={width} y={titles[0].y} fontSize={11} textAnchor="end" fill={ink.muted}>built-in → probe</text>
              {rows.map((r) => {
                const arms = STUDY[r.model].arms;
                const built = arms.tuned[r.metric];
                const probe = arms.probe[r.metric];
                const fixed = arms.fixed[r.metric];
                const better = probe <= built;
                return (
                  <g key={r.model + r.metric}>
                    <text x={0} y={r.labelY} fontSize={12.5} fill={ink.fg2}>
                      {r.label} <tspan fill={ink.muted}>of {r.of}</tspan>
                    </text>
                    <Line from={{ x: x(Math.min(built, probe)), y: r.y }} to={{ x: x(Math.max(built, probe)), y: r.y }} stroke={better ? ink.good : ink.warn} strokeWidth={3} strokeLinecap="round" opacity={0.45} />
                    <circle cx={x(fixed)} cy={r.y} r={5} fill="none" stroke={ink.muted} strokeWidth={1.2} strokeDasharray="2 2" />
                    <circle cx={x(built)} cy={r.y} r={5.5} fill={ink.surface} stroke={ink.fg} strokeWidth={1.6} />
                    <circle cx={x(probe)} cy={r.y} r={5.5} fill={ink.accent} />
                    <text x={width} y={r.y + 4} fontSize={13} textAnchor="end" fill={ink.fg} className="num">
                      {built} → <tspan fill={better ? ink.good : ink.warn} fontWeight={600}>{probe}</tspan>
                    </text>
                  </g>
                );
              })}
              <AxisBottom
                top={h - 26}
                scale={x}
                tickValues={[0, 25, 50, 75]}
                stroke={ink.strong}
                tickStroke={ink.strong}
                tickLabelProps={() => tickLabel}
              />
            </svg>
          );
        }}
      </Measured>
    </Frame>
  );
}

function Legend({ items }: { items?: { mark: React.ReactNode; label: string }[] }) {
  const list = items ?? [
    { mark: <circle cx={7} cy={7} r={5} fill={ink.surface} stroke={ink.fg} strokeWidth={1.6} />, label: "Built-in score, tuned cutoff" },
    { mark: <circle cx={7} cy={7} r={5} fill={ink.accent} />, label: "Linear probe" },
    { mark: <circle cx={7} cy={7} r={4.5} fill="none" stroke={ink.muted} strokeWidth={1.2} strokeDasharray="2 2" />, label: "Built-in score, fixed 0.5" },
  ];
  return (
    <ul className="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-[12.5px] text-fg-2">
      {list.map((it) => (
        <li key={it.label} className="flex items-center gap-1.5">
          <svg width={14} height={14} aria-hidden="true">{it.mark}</svg>
          {it.label}
        </li>
      ))}
    </ul>
  );
}

/* ---------- Fig 5: balanced accuracy with intervals, including the controls ---------- */

const ARM_ORDER: { key: Arm; label: string; note?: string }[] = [
  { key: "probe", label: "Linear probe" },
  { key: "massMean", label: "Mass-mean probe" },
  { key: "tuned", label: "Built-in score, tuned cutoff" },
  { key: "fixed", label: "Built-in score, fixed 0.5" },
  { key: "text", label: "Text only, no model", note: "control" },
  { key: "shuffled", label: "Probe on shuffled labels", note: "control" },
];

export function AccuracyChart() {
  const rowH = 30;
  return (
    <Frame
      fig="Fig 5"
      title="Balanced accuracy on 540 held-out requests"
      caption={
        <>
          Bars are 95% intervals from 500 resamples of groups of related requests. The two controls show what the probe is
          not doing: a classifier reading only the words of the request reaches 75.6%, and the same probe trained on
          shuffled labels falls below chance.
        </>
      }
    >
      <div className="grid gap-6 md:grid-cols-2 md:gap-8">
        {(["strands", "kev"] as ModelKey[]).map((key) => {
          const study = STUDY[key];
          const height = ARM_ORDER.length * rowH + 50;
          const tall = ARM_ORDER.length * 44 + 50;
          return (
            <div key={key}>
              <p className="mb-1 text-[13px] font-semibold">{study.name}</p>
              <Measured height={height}>
                {(width) => {
                  const narrow = width < 420;
                  const h = narrow ? tall : height;
                  const step = narrow ? 44 : rowH;
                  const labelW = narrow ? 0 : 172;
                  const x = scaleLinear({ domain: [0.3, 1], range: [labelW, width - 14] });
                  return (
                    <svg width={width} height={h} role="img" aria-label={`Balanced accuracy by decision rule for ${study.name}`}>
                      {narrow ? (
                        <>
                          {ARM_ORDER.map((_, i) => (
                            <rect key={i} x={x(0.3)} y={30 + i * step - 10} width={x(0.5) - x(0.3)} height={20} fill="var(--raised)" opacity={0.55} />
                          ))}
                          <BandGrid x={x} ticks={[0.5, 0.6, 0.7, 0.8, 0.9, 1]} bands={ARM_ORDER.map((_, i) => [30 + i * step - 10, 30 + i * step + 10] as [number, number])} />
                        </>
                      ) : (
                        <>
                          <rect x={x(0.3)} y={0} width={x(0.5) - x(0.3)} height={h - 26} fill="var(--raised)" opacity={0.55} />
                          <GridColumns scale={x} height={h - 26} stroke={ink.line} tickValues={[0.5, 0.6, 0.7, 0.8, 0.9, 1]} />
                        </>
                      )}
                      <text x={x(0.4)} y={h - 32} fontSize={10} textAnchor="middle" fill={ink.muted}>chance</text>
                      {ARM_ORDER.map((arm, i) => {
                        const v = study.arms[arm.key];
                        const cy = (narrow ? 30 : 16) + i * step;
                        const colour = arm.key === "probe" ? ink.accent : arm.key === "tuned" ? ink.fg : ink.muted;
                        return (
                          <g key={arm.key}>
                            <text x={0} y={narrow ? cy - 10 : cy + 4} fontSize={11.5} fill={arm.note ? ink.muted : ink.fg2}>
                              {arm.label}
                            </text>
                            <Line from={{ x: x(v.low), y: cy }} to={{ x: x(v.high), y: cy }} stroke={colour} strokeWidth={2} strokeLinecap="round" opacity={0.5} />
                            <circle cx={x(v.ba)} cy={cy} r={arm.key === "probe" || arm.key === "tuned" ? 5 : 4} fill={arm.key === "tuned" ? ink.surface : colour} stroke={colour} strokeWidth={1.6} />
                          </g>
                        );
                      })}
                      <AxisBottom
                        top={h - 26}
                        scale={x}
                        tickValues={narrow ? [0.5, 0.7, 0.9] : [0.5, 0.7, 0.9, 1]}
                        tickFormat={(v) => `${Math.round(Number(v) * 100)}%`}
                        stroke={ink.strong}
                        tickStroke={ink.strong}
                        tickLabelProps={() => tickLabel}
                      />
                    </svg>
                  );
                }}
              </Measured>
              <dl className="mt-2 grid grid-cols-[1fr_auto] gap-x-3 text-[12.5px] text-fg-2">
                <dt>Linear probe</dt>
                <dd className="num m-0 text-right font-semibold text-accent">{(study.arms.probe.ba * 100).toFixed(1)}%</dd>
                <dt>Built-in, tuned</dt>
                <dd className="num m-0 text-right">{(study.arms.tuned.ba * 100).toFixed(1)}%</dd>
              </dl>
            </div>
          );
        })}
      </div>
    </Frame>
  );
}

/* ---------- Fig 6: paired gain over the tuned built-in score ---------- */

export function GainChart() {
  const rows = [
    { model: "strands" as ModelKey, arm: "probe" as const, label: "Linear probe" },
    { model: "strands" as ModelKey, arm: "massMean" as const, label: "Mass-mean probe" },
    { model: "kev" as ModelKey, arm: "probe" as const, label: "Linear probe" },
    { model: "kev" as ModelKey, arm: "massMean" as const, label: "Mass-mean probe" },
  ];
  const rowH = 34;
  const gap = 30;
  const height = rows.length * rowH + gap * 2 + 28;
  return (
    <Frame
      fig="Fig 6"
      title="Gain over the tuned built-in score"
      caption={
        <>
          Each request was scored both ways, so the difference is paired. An interval that crosses zero means the study
          cannot tell the two rules apart. Only the Strands linear probe clears it.
        </>
      }
    >
      <Measured height={height}>
        {(width) => {
          const labelW = width < 480 ? 112 : 150;
          const x = scaleLinear({ domain: [-0.05, 0.13], range: [labelW, width - 60] });
          let y = 0;
          const placed = rows.map((r, i) => {
            if (i === 0 || i === 2) y += gap;
            const row = { ...r, y: y + 10 };
            y += rowH;
            return row;
          });
          return (
            <svg width={width} height={height} role="img" aria-label="Paired differences in balanced accuracy with 95% intervals">
              <BandGrid
                x={x}
                ticks={[-0.05, 0.05, 0.1]}
                bands={[[placed[0].y - 12, placed[1].y + 12], [placed[2].y - 12, height - 26]]}
              />
              {[[placed[0].y - 12, placed[1].y + 12], [placed[2].y - 12, height - 26]].map(([y0, y1]) => (
                <Line key={y0} from={{ x: x(0), y: y0 }} to={{ x: x(0), y: y1 }} stroke={ink.fg} strokeWidth={1} />
              ))}
              {[0, 2].map((i) => (
                <text key={i} x={0} y={placed[i].y - 18} fontSize={13} fontWeight={600} fill={ink.fg}>
                  {STUDY[placed[i].model].name}
                </text>
              ))}
              {placed.map((r) => {
                const g = STUDY[r.model].gain[r.arm];
                const clear = g.low > 0;
                const colour = clear ? ink.accent : ink.muted;
                return (
                  <g key={r.model + r.arm}>
                    <text x={0} y={r.y + 4} fontSize={12} fill={ink.fg2}>{r.label}</text>
                    <Line from={{ x: x(g.low), y: r.y }} to={{ x: x(g.high), y: r.y }} stroke={colour} strokeWidth={2.5} strokeLinecap="round" opacity={clear ? 0.55 : 0.6} />
                    <circle cx={x(g.diff)} cy={r.y} r={5} fill={colour} />
                    <text x={x(g.high) + 8} y={r.y + 4} fontSize={12} fill={clear ? ink.accent : ink.fg2} className="num" {...halo}>
                      {g.diff >= 0 ? "+" : "−"}{Math.abs(g.diff * 100).toFixed(1)} pts
                    </text>
                  </g>
                );
              })}
              <AxisBottom
                top={height - 26}
                scale={x}
                tickValues={[-0.05, 0, 0.05, 0.1]}
                tickFormat={(v) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${Math.abs(Math.round(Number(v) * 100))}`}
                stroke={ink.strong}
                tickStroke={ink.strong}
                tickLabelProps={() => tickLabel}
              />
            </svg>
          );
        }}
      </Measured>
      <p className="mt-1 text-right text-xs text-muted">Percentage points of balanced accuracy</p>
    </Frame>
  );
}
