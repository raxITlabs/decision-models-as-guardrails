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
    <div className="relative rounded-xl border border-line bg-code">
      <pre className="num m-0 overflow-x-auto px-4 py-4 pr-14 text-[13px] leading-[1.7] text-fg">
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
      <button
        type="button"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(copyText);
            setCopied(true);
            setTimeout(() => setCopied(false), 1600);
          } catch {}
        }}
        className="absolute right-2 top-2 inline-flex size-9 items-center justify-center rounded-md text-muted hover:bg-raised hover:text-fg"
        aria-label={copied ? "Copied" : `Copy: ${label}`}
      >
        {copied ? <Check /> : <Copy />}
      </button>
      <span className="sr-only" aria-live="polite">{copied ? "Copied to clipboard" : ""}</span>
    </div>
  );
}
