"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { HF_URL, REPO_URL } from "@/lib/format";
import { BenchmarksLogo } from "./benchmarks-logo";
import { ContactLink } from "./contact";
import { External } from "./icons";

const PAGES = [
  { href: "/", label: "Results", blurb: "Accuracy and cost for every system" },
  { href: "/reproduce", label: "Reproduce", blurb: "Run the benchmark yourself" },
  { href: "/data", label: "Data", blurb: "Every public row and every system's answer" },
  { href: "/versions", label: "Versions", blurb: "How each new model version compares with the last" },
  { href: "/research", label: "Research", blurb: "Work that goes past the leaderboard" },
] as const;

const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** The header the raxIT landing site uses, cut to the benchmark's needs: the logo, Contact and one Menu button.
 *  It sits on the hero painting, transparent with paper ink, until the reader scrolls past 10px or opens the menu;
 *  everywhere else it is solid paper. The menu wipes down from under the bar (clip-path, never height) with its
 *  items settling in on a 55ms stagger; on desktop the page behind it blurs, on a phone it fills the screen.
 *  Escape, a click outside and following a link all close it, and focus goes back to the Menu button. */
export function SiteHeader() {
  const path = usePathname();
  const [scrolled, setScrolled] = useState(false);
  // The menu remembers the page it was opened on, so arriving anywhere else closes it without an effect.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === path;
  const setOpen = (next: boolean) => setOpenOn(next ? path : null);
  const zone = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // A sentinel at the top of the hero says whether the page is still at rest; scroll events back it up.
    const on = () => setScrolled(window.scrollY > 10);
    on();
    window.addEventListener("scroll", on, { passive: true });
    const sentinel = document.getElementById("hero-sentinel");
    const io = sentinel ? new IntersectionObserver(([e]) => setScrolled(!e.isIntersecting)) : null;
    if (sentinel && io) io.observe(sentinel);
    return () => {
      window.removeEventListener("scroll", on);
      io?.disconnect();
    };
  }, [path]);

  // While open: Escape closes and hands focus back to the button, Tab cycles inside the bar and the menu, and on a
  // phone (where the menu covers the page) the page behind stops scrolling.
  useEffect(() => {
    const node = zone.current;
    if (!open || !node) return;
    node.querySelector<HTMLElement>("#site-menu a")?.focus();
    const lock = window.matchMedia("(max-width: 1023px)").matches;
    const previous = document.body.style.overflow;
    if (lock) document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpenOn(null);
        toggle.current?.focus();
        return;
      }
      if (e.key !== "Tab") return;
      const items = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => el.offsetWidth > 0);
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      if (lock) document.body.style.overflow = previous;
    };
  }, [open]);

  const overArt = path === "/" && !scrolled && !open;
  const current = PAGES.find((p) => (p.href === "/" ? path === "/" : path === p.href || path.startsWith(p.href + "/")));
  const close = () => setOpen(false);

  return (
    <>
      <div ref={zone} className="sticky top-0 z-40">
        <header data-over-art={overArt ? "true" : undefined} className="site-header relative bg-bg">
          <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-2 pl-4 pr-2 sm:pl-6 sm:pr-4">
            <Link
              href="/"
              prefetch={false}
              aria-label="raxIT Benchmarks: decision-models-as-guardrails, home"
              className="mr-auto flex h-11 shrink-0 items-center text-fg no-underline hover:text-fg"
            >
              <BenchmarksLogo className="h-[30px] w-auto" />
            </Link>
            {/* With the pages behind the menu, a quiet label says where the reader is. */}
            {current && (
              <span aria-hidden="true" className="mr-3 hidden text-[13px] text-muted sm:inline">
                {current.label}
              </span>
            )}
            <ContactLink className="header-cta inline-flex h-8 items-center rounded-full bg-fg px-3.5 text-[13px] font-medium text-bg no-underline hover:bg-fg-2 hover:text-bg">
              Contact us
            </ContactLink>
            <button
              ref={toggle}
              type="button"
              aria-expanded={open}
              aria-controls="site-menu"
              aria-label={open ? "Close menu" : "Open menu"}
              onClick={() => setOpen(!open)}
              className="menu-toggle inline-flex h-11 min-w-11 items-center justify-center gap-2 px-2 text-[14px] font-medium text-fg"
            >
              <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
                <path className="menu-icon-a" d="M3 7h14" />
                <path className="menu-icon-b" d="M3 13h14" />
              </svg>
              <span className="hidden sm:inline">{open ? "Close" : "Menu"}</span>
            </button>
          </div>
          {/* The landing site's horizon: a hairline that fades out at both ends, shown only on solid paper. */}
          <div aria-hidden="true" className="header-horizon pointer-events-none absolute inset-x-0 bottom-0 h-px" />
        </header>

        <div
          id="site-menu"
          role="region"
          aria-label="Site menu"
          data-open={open ? "" : undefined}
          inert={!open}
          className="menu-panel fixed inset-x-0 bottom-0 top-14 z-40 overflow-y-auto overscroll-none bg-bg lg:bottom-auto"
        >
          <nav aria-label="Main" className="mx-auto max-w-[1200px] px-4 pb-8 pt-2 sm:px-6 lg:pb-9 lg:pt-7">
            <ul className="m-0 grid list-none grid-cols-1 p-0 lg:grid-cols-4 lg:gap-x-6">
              {PAGES.map((p, i) => {
                const here = current?.href === p.href;
                return (
                  <li key={p.href} className="menu-item" style={{ "--i": i } as React.CSSProperties}>
                    <Link
                      href={p.href}
                      prefetch={p.href === "/" ? false : undefined}
                      aria-current={here ? "page" : undefined}
                      onClick={close}
                      className={`flex min-h-14 flex-col justify-center gap-1 border-b py-3 text-fg no-underline hover:text-fg lg:min-h-0 lg:border-b-0 lg:border-t lg:pb-0 lg:pt-3.5 ${
                        here ? "border-line lg:border-t-2 lg:border-t-fg" : "border-line lg:border-t-line-strong"
                      }`}
                    >
                      <span className="flex items-center justify-between text-[19px] font-semibold tracking-[-0.01em] lg:text-[22px]">
                        {p.label}
                        {here && <span aria-hidden="true" className="size-1.5 rounded-full bg-accent lg:hidden" />}
                      </span>
                      <span className="text-[13px] leading-snug text-muted">{p.blurb}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
            <div className="menu-item mt-4 flex flex-wrap gap-x-6 text-[14px] lg:mt-5" style={{ "--i": PAGES.length } as React.CSSProperties}>
              <a href={HF_URL} onClick={close} className="inline-flex min-h-11 items-center gap-1.5 text-muted no-underline hover:text-fg">
                Dataset on Hugging Face <External className="size-3" />
              </a>
              <a href={REPO_URL} onClick={close} className="inline-flex min-h-11 items-center gap-1.5 text-muted no-underline hover:text-fg">
                GitHub <External className="size-3" />
              </a>
            </div>
          </nav>
          <div aria-hidden="true" className="header-horizon absolute inset-x-0 bottom-0 h-px" />
        </div>
      </div>

      {/* Desktop only: the page recedes behind a faint tint and a blur, and a click on it closes the menu. */}
      <div aria-hidden="true" data-open={open ? "" : undefined} onClick={close} className="menu-scrim fixed inset-x-0 bottom-0 top-14 z-30 hidden lg:block" />
    </>
  );
}
