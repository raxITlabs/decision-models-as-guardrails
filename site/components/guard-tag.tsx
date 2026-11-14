import type { SystemMeta } from "@/lib/types";
import { classicType, isClassic } from "@/lib/kind";

/** "Classic guardrail" after the name of a system that is not a decision model: a guardrail service or a safety
 *  classifier. Not a pill: a small shield and a small-caps word in the guard teal (styles in globals.css, .guard-tag),
 *  a lighter teal over a painting. Renders nothing for a decision model. */
export function GuardTag({ m, onArt = false }: { m?: Pick<SystemMeta, "kind">; onArt?: boolean }) {
  if (!isClassic(m)) return null;
  return (
    <span className={onArt ? "guard-tag guard-tag-art" : "guard-tag"} title={`${classicType(m)}, not a decision model`}>
      <svg aria-hidden="true" viewBox="0 0 12 14" className="guard-tag-icon">
        <path d="M6 0.75 11 2.6v3.9c0 3.1-2.1 5.6-5 6.75C3.1 12.1 1 9.6 1 6.5V2.6Z" fill="currentColor" />
      </svg>
      Classic guardrail
    </span>
  );
}
