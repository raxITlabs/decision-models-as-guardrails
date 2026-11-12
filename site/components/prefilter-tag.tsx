import type { SystemMeta } from "../lib/types";

/** "Pre-filtered" after the name of a system whose provider refused some inputs before the model answered (owner
 *  ruling 41). The refused rows are scored as wrong; this says so where the score is read. Styles in globals.css. */
export function PrefilterTag({ m, onArt = false }: { m?: SystemMeta; onArt?: boolean }) {
  if (!m?.prefiltered) return null;
  const { rows, of } = m.prefiltered;
  return (
    <span
      className={onArt ? "prefilter-tag prefilter-tag-art" : "prefilter-tag"}
      title={`${makerOf(m)}'s safety filter returned an error instead of an answer on ${rows.toLocaleString("en-US")} of ${of.toLocaleString("en-US")} checks. Counted as wrong.`}
    >
      Pre-filtered
    </span>
  );
}

function makerOf(m: SystemMeta): string {
  return m.provider.split(" · ")[0] || "The provider";
}

/** The longer note for the system's detail panel. */
export function PrefilterNote({ m }: { m?: SystemMeta }) {
  if (!m?.prefiltered) return null;
  const { rows, of } = m.prefiltered;
  return (
    <p className="m-0 border-l-2 border-warn pl-3 text-[13px] leading-relaxed text-fg-2">
      <span className="font-semibold text-warn">Pre-filtered.</span> {makerOf(m)} puts its own safety filter in front of
      the model. On {rows.toLocaleString("en-US")} of {of.toLocaleString("en-US")} checks it returned an error instead of
      an answer, with no decision and no reason. We count those as wrong, the same as any failed call, so the score above
      includes them. You can&apos;t configure this filter or see why it fired, and your code gets an error, not a verdict.
    </p>
  );
}
