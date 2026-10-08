"use client";

import { useMemo, useState } from "react";
import type { Board } from "@/lib/types";
import { score1 } from "@/lib/format";
import { Segmented } from "./segmented";
import { SystemMark } from "./system-mark";

const PRESETS = [100_000, 1_000_000, 10_000_000, 100_000_000];

const compact = (n: number) =>
  n >= 1e9 ? `${+(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${+(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${+(n / 1e3).toFixed(1)}K` : `${n}`;
const usd = (v: number) =>
  v >= 100 ? `$${Math.round(v).toLocaleString("en-US")}` : v >= 1 ? `$${v.toFixed(2)}` : `$${v.toFixed(3)}`;

/**
 * Monthly and yearly cost at a chosen volume, from each system's measured cost per check (list prices, 7 Oct 2026).
 * A check is one message or document screened against one use case's policy.
 */
export function CostCalculator({ board }: { board: Board }) {
  const [volume, setVolume] = useState(1_000_000);
  const [scope, setScope] = useState<"managed" | "all">("managed");
  const sys = useMemo(() => Object.fromEntries(board.systems.map((s) => [s.id, s])), [board]);
  const ref = board.overall.find((s) => sys[s.system]?.kind === "service");
  const rows = board.overall
    .filter((s) => s.cost !== null && (scope === "all" || sys[s.system]?.hosting === "managed"))
    .map((s) => ({ s, month: ((s.cost as number) / 1000) * volume }))
    .sort((a, b) => a.month - b.month);
  const max = Math.max(...rows.map((r) => r.month), 1e-9);
  const refMonth = ref?.cost ? (ref.cost / 1000) * volume : null;

  return (
    <section id="cost" aria-labelledby="cost-h" className="flex scroll-mt-24 flex-col gap-6">
      <div className="flex max-w-[760px] flex-col gap-2.5">
        <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Cost at your volume</span>
        <h2 id="cost-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-balance">
          What it costs in production
        </h2>
        <p className="m-0 text-[16px] leading-relaxed text-fg-2">
          Pick how many checks you run a month. A check is one message or document screened against one use case.
        </p>
      </div>

      <div className="flex flex-col gap-5 rounded-xl border border-line bg-surface p-4 sm:p-6">
        <div className="flex flex-wrap items-end gap-x-4 gap-y-3">
          <div role="group" aria-label="Checks a month" className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p}
                type="button"
                aria-pressed={volume === p}
                onClick={() => setVolume(p)}
                className={`min-h-11 rounded-full border px-4 text-[14px] font-medium lg:min-h-[38px] ${
                  volume === p ? "border-fg bg-fg text-bg" : "border-line-strong text-fg-2 hover:border-fg/40 hover:text-fg"
                }`}
              >
                {compact(p)}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2 text-[14px] text-fg-2">
            <span>or</span>
            <input
              type="number"
              inputMode="numeric"
              min={1}
              step={1000}
              value={volume}
              onChange={(e) => setVolume(Math.max(1, Math.round(Number(e.target.value) || 1)))}
              className="num min-h-11 w-36 rounded-full border border-line-strong bg-bg px-4 text-[14px] text-fg lg:min-h-[38px]"
              aria-label="Checks a month"
            />
            <span>checks a month</span>
          </label>
          <div className="sm:ml-auto">
            <Segmented
              label="Systems in the calculator"
              value={scope}
              onChange={setScope}
              options={[
                { value: "managed", label: "Managed APIs", short: "Managed" },
                { value: "all", label: "All systems", short: "All" },
              ]}
            />
          </div>
        </div>

        <ol className="m-0 flex list-none flex-col p-0" aria-label={`Cost at ${volume.toLocaleString("en-US")} checks a month`}>
          {rows.map(({ s, month }) => {
            const m = sys[s.system];
            const isRef = m?.kind === "service";
            const diff = refMonth !== null && !isRef ? month - refMonth : null;
            return (
              <li
                key={s.system}
                className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1.5 border-t border-line px-2 py-3 first:border-t-0 sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)_auto] ${
                  isRef ? "rounded-md bg-raised" : ""
                }`}
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <SystemMark m={m} />
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate text-[14px] font-semibold">
                      <span className="sm:hidden">{m?.short ?? m?.name ?? s.system}</span>
                      <span className="hidden sm:inline">{m?.name ?? s.system}</span>
                    </span>
                    <span className="text-[12px] text-muted">
                      score {score1(s.score)}
                      {m?.hosting === "self-hosted" ? " · our GPU time" : ""}
                    </span>
                  </span>
                </span>
                <span className="col-span-2 row-start-2 h-1.5 overflow-hidden rounded-full bg-raised sm:col-span-1 sm:row-start-1 sm:col-start-2" aria-hidden="true">
                  <span className="block h-full rounded-full bg-fg/70" style={{ width: `${Math.max(1.5, (month / max) * 100)}%` }} />
                </span>
                <span className="flex flex-col items-end text-right">
                  <span className="num text-[16px] font-semibold">
                    {usd(month)}
                    <span className="text-[12px] font-normal text-muted"> /mo</span>
                  </span>
                  <span className="num hidden text-[12px] text-muted sm:block">
                    {usd(month * 12)} a year
                    {diff !== null && Math.abs(diff) >= 0.005 ? (
                      <span className={diff < 0 ? "text-good" : "text-warn"}>
                        {" "}· {usd(Math.abs(diff))} {diff < 0 ? "less" : "more"} than Bedrock
                      </span>
                    ) : null}
                  </span>
                </span>
                {/* Phones: the yearly figure and the Bedrock comparison get their own line, so names are not cut. */}
                <span className="num col-span-2 text-[12px] text-muted sm:hidden">
                  {usd(month * 12)} a year
                    {diff !== null && Math.abs(diff) >= 0.005 ? (
                      <span className={diff < 0 ? "text-good" : "text-warn"}>
                        {" "}· {usd(Math.abs(diff))} {diff < 0 ? "less" : "more"} than Bedrock
                      </span>
                    ) : null}
                </span>
              </li>
            );
          })}
        </ol>

        <p className="m-0 text-[13px] leading-relaxed text-muted">
          Measured on our test rows and priced at each vendor&apos;s list price on 7 October 2026. Our checks averaged about 1,100 to
          1,400 input tokens, including the policy questions, so longer messages cost more. Cloudflare also needs its Workers Paid plan
          ($5 a month). Self-hosted figures are our shared GPU time and do not scale in a straight line with volume.
        </p>
      </div>
    </section>
  );
}
