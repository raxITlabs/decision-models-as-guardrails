"use client";

import { useState } from "react";
import { Check, Copy, External } from "./icons";

/** A short prompt a reader pastes into their coding agent. It points at /reproduce.md rather than inlining the steps. */
export function AgentPrompt({ prompt, mdUrl }: { prompt: string; mdUrl: string }) {
  const [copied, setCopied] = useState(false);
  const q = encodeURIComponent(prompt);
  const link = "inline-flex min-h-11 items-center gap-1.5 text-[15px] font-medium text-link underline underline-offset-4 hover:text-link-hover";
  return (
    <div className="flex flex-col gap-4 border-y border-line-strong py-5">
      <p className="m-0 max-w-[68ch] text-[17px] leading-relaxed text-fg">{prompt}</p>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <button
          type="button"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(prompt);
              setCopied(true);
              setTimeout(() => setCopied(false), 1600);
            } catch {}
          }}
          className="inline-flex min-h-11 items-center gap-2 rounded-full bg-fg px-5 text-[14px] font-medium text-bg hover:bg-fg-2"
        >
          {copied ? <Check /> : <Copy />} {copied ? "Copied" : "Copy prompt"}
        </button>
        <a href={`https://claude.ai/new?q=${q}`} className={link}>
          Open in Claude <External />
        </a>
        <a href={`https://cursor.com/link/prompt?text=${q}`} className={link}>
          Open in Cursor <External />
        </a>
        <a href={mdUrl} className={link}>
          Open the guide as Markdown
        </a>
      </div>
      <span className="sr-only" aria-live="polite">{copied ? "Prompt copied to clipboard" : ""}</span>
    </div>
  );
}
