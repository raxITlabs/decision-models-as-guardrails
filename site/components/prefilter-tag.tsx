"use client";

import type { SystemMeta } from "../lib/types";
import { Popover, PopoverContent, PopoverDescription, PopoverHeader, PopoverTitle, PopoverTrigger } from "./ui/popover";

function makerOf(m: SystemMeta): string {
  return m.provider.split(" · ")[0] || "The provider";
}

/** Share of checks the provider refused, as a percentage to one decimal ("0.7%"; "under 0.1%" when smaller). */
export function refusedShare(p: { rows: number; of: number }): string {
  const v = (100 * p.rows) / p.of;
  return v < 0.05 ? "under 0.1%" : `${v.toFixed(1)}%`;
}

/** An "i" after the name of a system scored with a condition: its provider refused some checks before the model
 *  answered (owner ruling 41). A button that opens a short shadcn popover. Never put it inside another button: the
 *  leaderboard row renders it beside its select button. Styles in globals.css. */
export function PrefilterTag({ m, onArt = false }: { m?: SystemMeta; onArt?: boolean }) {
  if (!m?.prefiltered) return null;
  return (
    <Popover>
      <PopoverTrigger
        className={onArt ? "prefilter-tag prefilter-tag-art" : "prefilter-tag"}
        aria-label={`A condition applies to ${m.name}'s score`}
        onClick={(e) => e.stopPropagation()}
      >
        <span aria-hidden="true">i</span>
      </PopoverTrigger>
      <PopoverContent align="start" className="text-[13px] leading-relaxed" onClick={(e) => e.stopPropagation()}>
        <PopoverHeader>
          <PopoverTitle className="text-[14px] font-semibold">A condition applies</PopoverTitle>
          <PopoverDescription>
            {makerOf(m)} runs its own safety filter before the model sees a check. On {refusedShare(m.prefiltered)} of
            checks it returned an error instead of an answer.
          </PopoverDescription>
          <PopoverDescription>
            We count those as wrong, so the score includes them. You can&apos;t configure this filter or see why it fired.
          </PopoverDescription>
        </PopoverHeader>
      </PopoverContent>
    </Popover>
  );
}

/** The longer note for the system's detail panel. */
export function PrefilterNote({ m }: { m?: SystemMeta }) {
  if (!m?.prefiltered) return null;
  return (
    <p className="m-0 border-l-2 border-warn pl-3 text-[13px] leading-relaxed text-fg-2">
      <span className="font-semibold text-warn">A condition applies.</span> {makerOf(m)} puts its own safety filter in
      front of the model. On {refusedShare(m.prefiltered)} of checks it returned an error instead of an answer, with no
      decision and no reason. We count those as wrong, the same as any failed call, so the score above includes them.
      You can&apos;t configure this filter or see why it fired, and your code gets an error, not a verdict.
    </p>
  );
}
