"use client";

import { useEffect, useState } from "react";
import { ContactLink } from "./contact";

const KEY = "contact-prompt-dismissed";
const AT = 0.55;

/** A quiet invitation to get in touch. It appears once the reader is about 55% of the way down the page, never before,
 *  and stays away for good once they close it or open the contact form. */
export function ContactPrompt() {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      if (localStorage.getItem(KEY)) return;
    } catch {}
    const check = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      if (max > 0 && window.scrollY / max >= AT) {
        setShow(true);
        window.removeEventListener("scroll", check);
      }
    };
    window.addEventListener("scroll", check, { passive: true });
    return () => window.removeEventListener("scroll", check);
  }, []);
  const dismiss = () => {
    setShow(false);
    try {
      localStorage.setItem(KEY, "1");
    } catch {}
  };
  if (!show) return null;
  return (
    <aside
      aria-label="Contact raxIT Labs"
      className="prompt-in fixed inset-x-4 bottom-[max(16px,env(safe-area-inset-bottom))] z-30 flex flex-col gap-3 border border-line-strong bg-bg p-5 shadow-[0_16px_40px_-20px_rgb(var(--smoky)/0.45)] sm:inset-x-auto sm:right-6 sm:w-[360px]"
    >
      <div className="flex items-start justify-between gap-4">
        <p className="m-0 text-[17px] font-medium leading-snug tracking-[-0.01em]">Want us to test your guardrail?</p>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Close"
          className="-mr-2 -mt-2 grid size-11 shrink-0 place-items-center text-[20px] leading-none text-muted hover:text-fg"
        >
          ×
        </button>
      </div>
      <p className="m-0 text-[14px] leading-relaxed text-fg-2">
        Ask about the results, or have raxIT Labs run your system through the same checks.
      </p>
      <span className="flex">
        {/* Opening the form counts as an answer: the prompt goes once the form is closed, and does not come back. */}
        <ContactLink
          onOpen={() => {
            try {
              localStorage.setItem(KEY, "1");
            } catch {}
          }}
          onClose={() => setShow(false)}
          className="inline-flex min-h-11 items-center gap-2 rounded-full bg-fg px-5 text-[15px] font-medium text-bg no-underline hover:bg-fg-2 hover:text-bg">
          Contact us
        </ContactLink>
      </span>
    </aside>
  );
}
