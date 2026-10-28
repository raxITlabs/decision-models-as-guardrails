"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight } from "./icons";
import { follow, podiums } from "@/lib/leaders";
import { int, oneLine, score1, tierVar } from "@/lib/format";
import type { Score, SystemMeta } from "@/lib/types";

const TOP = 5;
const PLACE = ["Leader", "2nd", "3rd", "4th", "5th"];

/** "The leader changes with the use case": per use case, the first five systems as logo squares, the tier colour on the
 *  border. Selecting a square (or hovering one with a mouse) follows that system across every use case. */
export function UseCaseLeaders({
  jobs,
  rankings,
  sys,
  hide,
  rows,
}: {
  jobs: { id: string; title: string; sub: string }[];
  rankings: Record<string, Score[]>;
  sys: Record<string, SystemMeta>;
  hide: Record<string, string>;
  rows: number[];
}) {
  const table = podiums(jobs, rankings, hide, TOP);
  const [picked, setPicked] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const active = hover ?? picked;
  const name = (id: string) => sys[id]?.short ?? oneLine(sys[id], id);
  const f = picked ? follow(table, picked) : null;
  const tier = picked ? table.flatMap((r) => r.top).find((s) => s.system === picked)?.tier ?? 1 : 1;

  return (
    <div className="flex flex-col gap-3">
      {/* Stays under the site header while the reader scrolls the table, so the summary is in view after a tap lower down. */}
      <p className="sticky top-[var(--header-h,56px)] z-[2] m-0 flex min-h-14 items-center gap-3 border-b border-line bg-bg py-2 text-[14px] text-fg-2" aria-live="polite">
        {picked && f ? (
          <>
            <Mark id={picked} tier={tier} sys={sys} on />
            <span className="min-w-0 flex-1">
              <b className="font-semibold text-fg">{oneLine(sys[picked], picked)}</b>
              {f.first ? ` leads ${f.first} of ${f.of} use cases` : " leads none of the use cases"}
              {` and is in the top ${TOP} in ${f.inTop}.`}
            </span>
            <button type="button" onClick={() => setPicked(null)} className="min-h-11 shrink-0 text-[14px] text-muted underline decoration-line-strong underline-offset-[3px] hover:text-fg">
              Clear
            </button>
          </>
        ) : (
          <span>Select a logo to follow one system across all {table.length} use cases.</span>
        )}
      </p>
      <div className="border-t border-line-strong">
        <table className="w-full table-fixed border-collapse">
          <caption className="sr-only">
            The first {TOP} systems in each use case, with their score; the square&apos;s border colour is the system&apos;s tier in that use
            case.
          </caption>
          <colgroup>
            <col className="w-[34%] sm:w-[30%] lg:w-[28%]" />
            {PLACE.map((p) => (
              <col key={p} />
            ))}
          </colgroup>
          <thead>
            <tr className="border-b border-line text-[12px] text-muted">
              <th scope="col" className="py-2.5 pr-3 text-left font-medium">
                Use case
              </th>
              {PLACE.map((p) => (
                <th key={p} scope="col" className="py-2.5 text-center font-medium">
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.map((r, i) => {
              const j = jobs[i];
              return (
                <tr key={r.job} className="border-b border-line">
                  <th scope="row" className="py-3.5 pr-3 text-left align-top font-normal">
                    <span className="block text-[15px] font-semibold leading-snug tracking-[-0.01em] text-fg sm:text-[16px]">{j.title}</span>
                    <span className="mt-0.5 hidden text-[13px] leading-snug text-muted md:block">{j.sub}</span>
                    <Link href={`/data?job=${j.id}#rows`} className="mt-1 inline-flex min-h-9 items-center gap-1 text-[13px]">
                      {int(rows[i])} rows<span className="sr-only"> for {j.title}</span> <ArrowRight className="size-3" />
                    </Link>
                  </th>
                  {PLACE.map((p, n) => {
                    const s = r.top[n];
                    if (!s) return <td key={p} />;
                    const on = active === s.system;
                    const dim = active !== null && !on;
                    return (
                      <td key={p} className="py-3.5 text-center align-top">
                        <button
                          type="button"
                          aria-pressed={picked === s.system}
                          aria-label={`${oneLine(sys[s.system], s.system)}: ${p === "Leader" ? "leads" : p} ${j.title}, score ${score1(s.score)}, tier ${s.tier}. Follow it across the use cases.`}
                          onClick={() => setPicked((v) => (v === s.system ? null : s.system))}
                          onPointerEnter={(e) => e.pointerType === "mouse" && setHover(s.system)}
                          onPointerLeave={(e) => e.pointerType === "mouse" && setHover(null)}
                          className={`group mx-auto flex w-full max-w-[96px] flex-col items-center gap-1.5 rounded-md py-1 transition-opacity duration-200 ease-out motion-reduce:transition-none ${dim ? "opacity-25" : ""}`}
                        >
                          <Mark id={s.system} tier={s.tier} sys={sys} on={on} />
                          <span className={`num text-[13px] leading-none sm:text-[14px] ${n === 0 ? "font-semibold text-fg" : "text-fg-2"}`}>{score1(s.score)}</span>
                          <span className="hidden w-full truncate text-[12px] leading-tight text-muted lg:block">{name(s.system)}</span>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
        <span>Score is balanced accuracy in that use case. Border colour is the tier there:</span>
        {[1, 2, 3, 4, 5].map((t) => (
          <span key={t} className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: tierVar(t) }} aria-hidden="true" />
            Tier {t}
            {t === 5 ? "+" : ""}
          </span>
        ))}
      </p>
    </div>
  );
}

/** One system's logo square, tier colour on the border. `on` marks the followed system with a heavy ring. */
function Mark({ id, tier, sys, on }: { id: string; tier: number; sys: Record<string, SystemMeta>; on: boolean }) {
  return (
    <span
      className="grid size-9 shrink-0 place-items-center rounded-md sm:size-10 lg:size-11"
      style={{
        background: `color-mix(in srgb, ${tierVar(tier)} 14%, var(--bg))`,
        border: `2px solid ${tierVar(tier)}`,
        boxShadow: on ? "0 0 0 2px var(--bg), 0 0 0 5px var(--fg)" : undefined,
      }}
    >
      {sys[id]?.logo ? (
        // eslint-disable-next-line @next/next/no-img-element -- static export, tiny SVGs
        <img src={sys[id]?.logo} alt="" className="size-5 sm:size-[22px] lg:size-6" />
      ) : (
        <span className="text-[12px] font-semibold text-fg-2">{sys[id]?.mono}</span>
      )}
    </span>
  );
}
