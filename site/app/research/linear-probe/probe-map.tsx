"use client";

import { useEffect, useRef, useState } from "react";
import { LAYER_SWEEP, type ModelKey } from "./data";

const MODELS: Record<ModelKey, { name: string; short: string; depth: number }> = {
  strands: { name: "Strands Decider 2B", short: "Strands", depth: 24 },
  kev: { name: "Kev 4B", short: "Kev", depth: 32 },
};

// Fixed pseudo-random offsets so server and client draw the same dots, and dots glide (not jump) between layers.
function rng(seed: number) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rand = rng(11);
const normal = () => {
  const v = Math.sqrt(-2 * Math.log(1 - rand())) * Math.cos(2 * Math.PI * rand());
  return Math.max(-2.2, Math.min(2.2, v)) * 0.8;
};
const N = 32;
const DOTS = Array.from({ length: N * 2 }, (_, i) => ({ block: i < N, x: normal(), y: normal() }));

// AUROC of two unit-variance clouds a distance d apart is Phi(d / sqrt 2); invert it to place the clouds.
function probit(p: number) {
  // Acklam's rational approximation, central region is enough for 0.5..0.999.
  const a = [-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924];
  const b = [-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857];
  const c = [-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878];
  const d = [0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742];
  if (p > 0.97575) {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  const q = p - 0.5;
  const r = q * q;
  return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}
const gapFor = (auroc: number) => Math.SQRT2 * probit(Math.min(Math.max(auroc, 0.5), 0.999));

const W = 640;
const H = 300;
const ANGLE = (-14 * Math.PI) / 180;
const cos = Math.cos(ANGLE);
const sin = Math.sin(ANGLE);
// Rounded so the server and the browser print identical attributes.
const r2 = (v: number) => Math.round(v * 100) / 100;
const place = (x: number, y: number) => [r2(W / 2 + (x * cos - y * sin) * 62), r2(H / 2 + (x * sin + y * cos) * 62)] as const;

function verdict(a: number) {
  if (a >= 0.999) return "a clean split";
  if (a >= 0.97) return "nearly clean";
  if (a >= 0.9) return "mostly apart";
  return "still mixed";
}

export function ProbeMap() {
  const [model, setModel] = useState<ModelKey>("strands");
  const sweep = LAYER_SWEEP[model];
  const [pick, setPick] = useState(() => sweep.rows.findIndex((r) => r.layer === sweep.selected));
  const touched = useRef(false);
  const stage = useRef<HTMLDivElement>(null);
  const m = MODELS[model];
  const row = sweep.rows[pick];
  const auroc = row["LR:answer_mean"];
  const target = gapFor(auroc);
  const [gap, setGap] = useState(target);
  const gapRef = useRef(gap);

  // Ease the two clouds toward the separation this layer's validation AUROC implies.
  useEffect(() => {
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    let last = 0;
    const tick = (now: number) => {
      const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
      last = now;
      gapRef.current += (target - gapRef.current) * (1 - Math.exp(-dt / 0.28));
      if (still || Math.abs(target - gapRef.current) < 0.002) gapRef.current = target;
      setGap(gapRef.current);
      if (gapRef.current !== target) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);

  // A slow walk through the sampled layers while on screen, until someone takes over.
  useEffect(() => {
    const root = stage.current;
    if (!root || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let visible = false;
    const io = new IntersectionObserver(([e]) => (visible = e.isIntersecting), { threshold: 0.4 });
    io.observe(root);
    const timer = window.setInterval(() => {
      if (!touched.current && visible) setPick((p) => (p + 1) % LAYER_SWEEP[model].rows.length);
    }, 2600);
    return () => {
      io.disconnect();
      clearInterval(timer);
    };
  }, [model]);

  const choose = (i: number) => {
    touched.current = true;
    setPick(i);
  };
  const sampled = new Map(sweep.rows.map((r, i) => [r.layer, i]));

  // The probe: the line halfway between the clouds, drawn across the panel, with the block side tinted.
  const [lx1, ly1] = place(0, -6);
  const [lx2, ly2] = place(0, 6);
  const [bx1, by1] = place(8, -6);
  const [bx2, by2] = place(8, 6);

  return (
    <figure className="m-0">
      <div ref={stage} className="overflow-hidden rounded-[4px] border border-line-strong bg-surface">
        <div className="flex justify-between gap-4 px-4 pt-3 text-xs text-muted sm:px-5">
          <span className="num">Fig 1</span>
          <span className="text-right">What a probe sees inside the model</span>
        </div>

        {/* The model: one slab per layer. The request goes in on the left, the model's own answer comes out on the right. */}
        <div className="px-4 pt-5 sm:px-5">
          <p className="m-0 mb-2 text-xs text-muted">
            {m.name}, frozen · {m.depth} layers · the probe taps layer <span className="num text-accent">{row.layer}</span>
          </p>
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="shrink-0 rounded-[3px] border border-line-strong px-2 py-1 text-xs text-fg-2">Request</span>
            <div className="relative flex h-14 flex-1 items-end gap-[2px]" aria-hidden="true">
              {Array.from({ length: m.depth }, (_, layer) => {
                const i = sampled.get(layer);
                const on = i === pick;
                return (
                  <div
                    key={layer}
                    onClick={i == null ? undefined : () => choose(i)}
                    className={
                      "relative flex-1 rounded-[1px] transition-[height,background-color] duration-300 " +
                      (on ? "h-14 bg-accent" : i == null ? "h-8 bg-line" : "h-11 cursor-pointer bg-line-strong hover:bg-fg-2")
                    }
                  >
                    {on && <span className="absolute top-full left-1/2 h-3 w-px -translate-x-1/2 bg-accent" />}
                  </div>
                );
              })}
            </div>
            <span className="shrink-0 rounded-[3px] border border-line-strong px-2 py-1 text-xs text-fg-2">Answer</span>
          </div>
        </div>

        {/* Inside the tapped layer. */}
        <div className="mx-4 mt-3 rounded-[3px] border border-line bg-bg/40 sm:mx-5">
          <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={`Illustration of layer ${row.layer}: block and allow requests are ${verdict(auroc)}; the probe line separates them.`}>
            <defs>
              <clipPath id="probe-map-clip">
                <rect width={W} height={H} />
              </clipPath>
            </defs>
            <g clipPath="url(#probe-map-clip)">
              <polygon points={`${lx1},${ly1} ${lx2},${ly2} ${bx2},${by2} ${bx1},${by1}`} fill="var(--accent)" opacity={0.06} />
              {DOTS.map((p, i) => {
                const [x, y] = place(p.x + (p.block ? gap / 2 : -gap / 2), p.y);
                return p.block ? (
                  <circle key={i} cx={x} cy={y} r={5.5} fill="var(--fg)" />
                ) : (
                  <circle key={i} cx={x} cy={y} r={4.8} fill="var(--surface)" stroke="var(--fg-2)" strokeWidth={1.4} />
                );
              })}
              <line x1={lx1} y1={ly1} x2={lx2} y2={ly2} stroke="var(--accent)" strokeWidth={2.25} />
            </g>
          </svg>
        </div>

        <ul className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1.5 px-4 pt-3 text-xs text-fg-2 sm:px-5">
          <li className="flex items-center gap-1.5">
            <svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="4.5" fill="var(--fg)" /></svg>
            Should be blocked
          </li>
          <li className="flex items-center gap-1.5">
            <svg width="12" height="12" aria-hidden="true"><circle cx="6" cy="6" r="4" fill="var(--surface)" stroke="var(--fg-2)" strokeWidth="1.4" /></svg>
            Should be allowed
          </li>
          <li className="flex items-center gap-1.5">
            <svg width="16" height="12" aria-hidden="true"><line x1="8" x2="8" y1="0" y2="12" stroke="var(--accent)" strokeWidth="2.25" /></svg>
            The probe: everything on the tinted side is blocked
          </li>
        </ul>

        <div className="mt-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-t border-line px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-2">
            <div role="group" aria-label="Model" className="flex gap-1">
              {(Object.keys(MODELS) as ModelKey[]).map((key) => (
                <button
                  key={key}
                  type="button"
                  aria-pressed={model === key}
                  onClick={() => {
                    touched.current = true;
                    setModel(key);
                    setPick(LAYER_SWEEP[key].rows.findIndex((r) => r.layer === LAYER_SWEEP[key].selected));
                  }}
                  className="min-h-10 cursor-pointer rounded-[3px] border border-line-strong px-3 text-sm aria-pressed:border-fg aria-pressed:bg-fg aria-pressed:text-surface"
                >
                  {MODELS[key].short}
                </button>
              ))}
            </div>
            <div role="group" aria-label={`Layer of ${m.name} to tap`} className="flex flex-wrap gap-1">
              {sweep.rows.map((r, i) => (
                <button
                  key={r.layer}
                  type="button"
                  aria-pressed={pick === i}
                  onClick={() => choose(i)}
                  className="num min-h-10 min-w-10 cursor-pointer rounded-[3px] border border-line px-2 text-sm text-fg-2 aria-pressed:border-accent aria-pressed:bg-selected aria-pressed:text-accent"
                >
                  {r.layer}
                </button>
              ))}
            </div>
          </div>
          <p aria-live="polite" className="m-0 text-right text-sm leading-snug">
            <span className="text-muted">
              Layer {row.layer} of {m.depth}
              {row.layer === sweep.selected ? " · the one the study chose" : ""}
            </span>
            <br />
            <strong className="text-[22px] font-semibold tracking-tight">{verdict(auroc)}</strong>
            <span className="num text-muted"> · AUROC {auroc.toFixed(2)}</span>
          </p>
        </div>
      </div>
      <figcaption className="mx-auto mt-3 max-w-[44rem] text-sm leading-relaxed text-muted">
        An illustration, not the real activations, which have thousands of dimensions. The dots are drawn for the picture;
        how far apart the two groups sit at each layer is set by the linear probe’s real validation AUROC there
        (validation_search.csv), where 1.00 means every validation request landed on the right side of the line.
      </figcaption>
    </figure>
  );
}
