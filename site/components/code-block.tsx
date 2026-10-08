"use client";

import { useState } from "react";
import { Check, Copy } from "./icons";

/** A shell snippet with a copy button. Lines starting with # are comments and are not copied. */
export function CodeBlock({ code, label }: { code: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copyText = code
    .split("\n")
    .filter((l) => !l.trim().startsWith("#"))
    .map((l) => l.replace(/\s+#\s.*$/, ""))
    .join("\n")
    .trim();
  return (
    <div className="overflow-hidden border-y border-line bg-code">
      <div className="flex items-center justify-between gap-3 border-b border-line py-1 pl-4 pr-1">
        <span className="text-[12px] text-muted first-letter:uppercase">{label}</span>
        <button
          type="button"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(copyText);
              setCopied(true);
              setTimeout(() => setCopied(false), 1600);
            } catch {}
          }}
          className="inline-flex min-h-11 items-center gap-1.5 px-3 text-[13px] text-fg-2 underline-offset-4 hover:text-fg hover:underline"
          aria-label={copied ? "Copied" : `Copy: ${label}`}
        >
          {copied ? <Check /> : <Copy />}
          <span aria-hidden="true">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      {/* Focusable so keyboard users can scroll long lines sideways. */}
      <pre
        tabIndex={0}
        role="region"
        aria-label={`Code: ${label}`}
        className="mono m-0 overflow-x-auto px-4 py-4 text-[13px] leading-[1.7] text-fg"
      >
        {code.split("\n").map((l, i) => {
          const c = l.indexOf(" #");
          const comment = l.trim().startsWith("#") ? 0 : c >= 0 ? c : -1;
          return (
            <span key={i} className="block">
              {comment === -1 ? l : (
                <>
                  {l.slice(0, comment)}
                  <span className="text-muted">{l.slice(comment)}</span>
                </>
              )}
            </span>
          );
        })}
      </pre>
      <span className="sr-only" aria-live="polite">{copied ? "Copied to clipboard" : ""}</span>
    </div>
  );
}
