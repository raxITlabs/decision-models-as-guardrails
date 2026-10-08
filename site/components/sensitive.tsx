"use client";

import { useEffect, useRef, useState } from "react";
import { Lock } from "./icons";

/** Hides a harmful example until the reader asks to see it (ruling 34). */
export function Sensitive({ children, hide = true, compact = false }: { children: React.ReactNode; hide?: boolean; compact?: boolean }) {
  const [shown, setShown] = useState(false);
  const revealed = useRef<HTMLDivElement>(null);
  // After "Show text", keyboard focus moves to the text instead of falling back to the page.
  useEffect(() => {
    if (shown) revealed.current?.focus();
  }, [shown]);
  if (!hide) return <>{children}</>;
  if (shown)
    return (
      <div ref={revealed} tabIndex={-1} className="outline-none focus-visible:outline-2">
        {children}
      </div>
    );
  return (
    <div className={`flex flex-wrap items-center gap-x-3 gap-y-1 ${compact ? "text-[14px]" : "rounded-lg border border-dashed border-line-strong bg-surface px-5 py-4 text-[14px]"}`}>
      <span className="inline-flex items-center gap-1.5 text-muted">
        <Lock className="size-3.5 shrink-0" />
        Harmful example hidden.
      </span>
      <button type="button" onClick={() => setShown(true)} className="inline-flex min-h-11 items-center font-medium text-link hover:text-link-hover sm:min-h-6">
        Show text
      </button>
    </div>
  );
}

/** The notice at the top of every page that shows dataset rows. */
export function ContentWarning() {
  return (
    <p role="note" className="m-0 rounded-lg border border-warn/40 bg-surface px-4 py-3 text-[14px] leading-relaxed text-fg-2">
      <strong className="font-semibold text-warn">Content warning.</strong> The rows are real examples, and many are harmful:
      violence, hate, self-harm, crime, attacks and profanity. We show the full text of 100 example rows only. Harmful examples
      stay hidden until you choose to show them, and we never show sexual or adult content. Every other row links to its
      original source.
    </p>
  );
}
