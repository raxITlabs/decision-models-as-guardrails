"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LAYER_SWEEP, type SweepKey, type SweepRow } from "./data";

const SERIES: { key: SweepKey; label: string; color: string; dash?: string; width: number }[] = [
  { key: "LR:answer_mean", label: "Linear probe, answer average", color: "var(--accent)", width: 2.25 },
  { key: "LR:option_delta", label: "Linear probe, option difference", color: "var(--fg-2)", width: 1.5 },
  { key: "MM:answer_mean", label: "Mass-mean probe, answer average", color: "var(--muted)", width: 1.25 },
  { key: "MM:option_delta", label: "Mass-mean probe, option difference", color: "var(--muted)", dash: "4 3", width: 1.25 },
];
const tick = { fill: "var(--muted)", fontSize: 11, fontFamily: "var(--font-inter)" };
const fmt = (v: number) => v.toFixed(2);

function Swatch({ color, dash, width }: { color: string; dash?: string; width: number }) {
  return (
    <svg width="22" height="10" aria-hidden="true" className="shrink-0">
      <line x1="1" x2="21" y1="5" y2="5" stroke={color} strokeWidth={width} strokeDasharray={dash} />
      <circle cx="11" cy="5" r="2.6" fill={color} />
    </svg>
  );
}

type TipProps = { active?: boolean; label?: number; payload?: { dataKey?: string | number; value?: number }[] };
function Tip({ active, label, payload }: TipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-[3px] border border-line-strong bg-surface px-3 py-2 text-xs shadow-[0_6px_18px_-8px_rgb(0_0_0/0.25)]">
      <p className="m-0 mb-1 font-medium text-fg">Layer {label}</p>
      {SERIES.map((s) => {
        const v = payload.find((p) => p.dataKey === s.key)?.value;
        return v == null ? null : (
          <p key={s.key} className="m-0 flex items-center justify-between gap-4 text-fg-2">
            <span className="flex items-center gap-1.5">
              <Swatch color={s.color} dash={s.dash} width={s.width} />
              {s.label}
            </span>
            <span className="num text-fg">{fmt(v)}</span>
          </p>
        );
      })}
    </div>
  );
}

function Panel({ name, depth, rows, selected }: { name: string; depth: number; rows: SweepRow[]; selected: number }) {
  return (
    <div className="min-w-0">
      <p className="m-0 mb-2 text-sm font-semibold text-fg">
        {name} <span className="font-normal text-muted">· {depth} layers</span>
      </p>
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 24, right: 12, bottom: 4, left: -18 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis
              dataKey="layer"
              type="number"
              domain={[0, depth - 1]}
              ticks={rows.map((r) => r.layer)}
              tick={tick}
              tickLine={false}
              axisLine={{ stroke: "var(--line-strong)" }}
            />
            <YAxis
              domain={[0.5, 1]}
              ticks={[0.5, 0.6, 0.7, 0.8, 0.9, 1]}
              tickFormatter={(v: number) => v.toFixed(1)}
              tick={tick}
              tickLine={false}
              axisLine={false}
            />
            <ReferenceLine y={0.5} stroke="var(--line-strong)" strokeDasharray="2 3" />
            <ReferenceLine
              x={selected}
              stroke="var(--accent)"
              strokeOpacity={0.35}
              label={{ value: "selected", position: "top", fill: "var(--accent)", fontSize: 11, offset: 8 }}
            />
            <Tooltip content={<Tip />} cursor={{ stroke: "var(--line-strong)" }} isAnimationActive={false} />
            {[...SERIES].reverse().map((s) => (
              <Line
                key={s.key}
                dataKey={s.key}
                name={s.label}
                stroke={s.color}
                strokeWidth={s.width}
                strokeDasharray={s.dash}
                dot={{ r: s.key === "LR:answer_mean" ? 3.6 : 2.8, fill: s.color, stroke: "var(--surface)", strokeWidth: 1 }}
                activeDot={{ r: 5, fill: s.color, stroke: "var(--surface)", strokeWidth: 1.5 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function LayerSweepChart() {
  return (
    <figure className="m-0">
      <div className="rounded-[4px] border border-line-strong bg-surface px-4 pt-3 pb-4 sm:px-5">
        <div className="mb-3 flex justify-between gap-4 text-xs text-muted">
          <span className="num">Fig 2</span>
          <span className="text-right">Every probe, every sampled layer</span>
        </div>
        <ul className="m-0 mb-4 flex list-none flex-wrap gap-x-5 gap-y-1.5 p-0 text-xs text-fg-2">
          {SERIES.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <Swatch color={s.color} dash={s.dash} width={s.width} />
              {s.label}
            </li>
          ))}
        </ul>
        <div className="grid gap-6 md:grid-cols-2 md:gap-8">
          <Panel name="Strands Decider 2B" depth={24} {...LAYER_SWEEP.strands} />
          <Panel name="Kev 4B" depth={32} {...LAYER_SWEEP.kev} />
        </div>
        <p className="m-0 mt-2 text-xs text-muted">Validation AUROC (1.0 is a perfect ranking, 0.5 is chance) by layer, counted from zero.</p>
      </div>
      <figcaption className="mx-auto mt-3 max-w-[44rem] text-sm leading-relaxed text-muted">
        The study’s layer search, redrawn from validation_search.csv. Each probe was trained on the 89 training requests at
        one layer and ranked the 29 validation requests; for linear probes the line shows the best of the regularisation
        settings tried at that layer. The PR’s own chart also draws the model’s built-in score as a reference line; that
        value isn’t in the published files, so it is left out here.
      </figcaption>
    </figure>
  );
}
