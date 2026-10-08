"use client";

import { useState } from "react";
import { listNames, oneLine } from "@/lib/format";
import { JOB_BY_ID, type JobId } from "@/lib/jobs";
import type { SystemMeta } from "@/lib/types";

export interface Example {
  id: string;
  job: JobId;
  /** "yes": the right call is to block */
  label: "yes" | "no";
  text: string;
  /** per system: true blocked, false allowed, null no answer (counts as wrong) */
  verdicts: Record<string, boolean | null>;
}

/** The hero's decision space: one real benchmark message, set on the painting, and every system sorted to the side
 *  it chose. The reader steps through the examples; nothing advances on its own. */
export function DecisionSpace({ examples, systems }: { examples: Example[]; systems: SystemMeta[] }) {
  const [i, setI] = useState(0);
  // Phones: the names start open; the reader can fold them away and that choice holds across examples.
  const [namesOpen, setNamesOpen] = useState(true);
  const ex = examples[i];
  const block = ex.label === "yes";
  const allowed = systems.filter((s) => ex.verdicts[s.id] === false);
  const blocked = systems.filter((s) => ex.verdicts[s.id] === true);
  const silent = systems.filter((s) => ex.verdicts[s.id] == null);
  const wrong = systems.filter((s) => ex.verdicts[s.id] !== block);
  const right = systems.length - wrong.length;
  const go = (d: number) => setI((n) => (n + d + examples.length) % examples.length);

  const lists = (
    <>
      <Side title="Allowed" items={allowed} wrong={block} />
      <Side title="Blocked" items={blocked} wrong={!block} border />
    </>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-4 text-[13px]">
        <span className="over-art font-medium">{JOB_BY_ID[ex.job].title}</span>
        <span className="over-art-86 num">
          Example {i + 1} of {examples.length}
        </span>
      </div>
      <p key={ex.id} className="fade over-art m-0 min-h-[2.7em] text-[clamp(1.125rem,2vw,1.3125rem)] font-medium leading-[1.35] tracking-[-0.015em]">
        &ldquo;{ex.text}&rdquo;
      </p>
      <p className="over-art-86 m-0 text-[14px]">
        The right call is to <b className="over-art font-semibold">{block ? "block it" : "let it through"}</b>.
      </p>

      {/* Tablet and up: both sides at once. */}
      <div key={`d${ex.id}`} className="fade hidden grid-cols-2 border-t border-[var(--over-line)] sm:grid">
        {lists}
      </div>
      {/* Phones: the counts, with the names one tap away. */}
      <details
        open={namesOpen}
        onToggle={(e) => setNamesOpen((e.currentTarget as HTMLDetailsElement).open)}
        className="border-t border-[var(--over-line)] sm:hidden"
      >
        <summary className="over-art flex min-h-11 items-center justify-between gap-3 text-[14px]">
          <span className="num">
            {allowed.length} allowed · {blocked.length} blocked
          </span>
          <span className="font-medium underline decoration-[var(--over-line)] underline-offset-4">{namesOpen ? "Hide names" : "Who decided what"}</span>
        </summary>
        <div className="grid grid-cols-1 pb-2 min-[400px]:grid-cols-2">{lists}</div>
      </details>

      <p className="over-art-86 num m-0 border-t border-[var(--over-line)] pt-3 text-[14px]">
        {right} of {systems.length} got it right
        {wrong.length > 0 && (
          <>
            {", "}
            <span className="text-[var(--warn-art)]">
              {wrong.length} wrong {wrong.length === 1 ? "call" : "calls"}
            </span>
          </>
        )}
        {silent.length > 0 && `. ${listNames(silent.map((s) => oneLine(s, s.id)))} gave no answer`}.
      </p>
      <p className="sr-only" aria-live="polite">
        Example {i + 1} of {examples.length}: {right} of {systems.length} systems got it right.
      </p>

      <div className="flex items-center justify-between gap-4">
        <div className="flex gap-1.5" aria-hidden="true">
          {examples.map((e, n) => (
            <span key={e.id} className={`h-0.5 w-4 transition-colors ${n === i ? "bg-[var(--over-art)]" : "bg-[var(--over-line)]"}`} />
          ))}
        </div>
        <div className="flex gap-5 text-[14px] font-medium">
          <button type="button" onClick={() => go(-1)} className="art-link min-h-11">
            Previous
          </button>
          <button type="button" onClick={() => go(1)} className="art-link min-h-11">
            Next example
          </button>
        </div>
      </div>
    </div>
  );
}

function Side({ title, items, wrong, border = false }: { title: string; items: SystemMeta[]; wrong: boolean; border?: boolean }) {
  return (
    <div className={`min-w-0 pt-3 ${border ? "min-[400px]:border-l min-[400px]:border-[var(--over-line)] min-[400px]:pl-4 sm:pl-5" : "pr-4 sm:pr-5"}`}>
      <h3 className="over-art-86 m-0 mb-1.5 flex items-baseline justify-between text-[13px] font-medium">
        {title} <span className="num">{items.length}</span>
      </h3>
      <ul className="m-0 flex list-none flex-col p-0 sm:min-h-[12.5rem]">
        {items.length === 0 && <li className="over-art-86 py-1 text-[14px]">No system</li>}
        {items.map((s) => (
          <li key={s.id} className={`flex items-center gap-2.5 py-[3px] text-[14px] ${wrong ? "text-[var(--warn-art)]" : "over-art"}`}>
            <span className="grid size-[18px] shrink-0 place-items-center" aria-hidden="true">
              {s.logo ? (
                // eslint-disable-next-line @next/next/no-img-element -- static export, tiny SVGs
                <img src={s.logo} alt="" className="logo-on-art size-4" />
              ) : (
                <span className="size-2 rounded-full border border-current opacity-80" />
              )}
            </span>
            <span className="min-w-0 break-words">{oneLine(s, s.id)}</span>
            {wrong && (
              <span className="ml-auto shrink-0 pl-2 text-[12px]">
                <span aria-hidden="true">✕</span>
                <span className="sr-only">, wrong call</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
