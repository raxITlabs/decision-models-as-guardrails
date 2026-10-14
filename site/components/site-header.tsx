"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { HF_URL, REPO_URL } from "@/lib/format";
import { External } from "./icons";
import { NavLink } from "./nav-link";
import { ContactLink } from "./contact";

/** On the home page the header sits on the hero painting, transparent with paper ink, until the reader scrolls
 *  (the raxIT site's own behaviour). Everywhere else, and once scrolled, it is solid paper. */
export function SiteHeader() {
  const path = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    // A sentinel at the top of the hero says whether the page is still at rest; scroll events back it up.
    const on = () => setScrolled(window.scrollY > 24);
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
  const overArt = path === "/" && !scrolled;
  const ext = "inline-flex min-h-11 items-center gap-1 px-2.5 text-fg-2 no-underline underline-offset-[6px] hover:text-fg hover:underline";
  return (
    <header
      data-over-art={overArt ? "true" : undefined}
      className="site-header sticky top-0 z-40 border-b border-line bg-bg transition-[background-color,border-color] duration-300 ease-out"
    >
      <div className="mx-auto flex h-[72px] max-w-[1200px] items-center gap-6 px-4 sm:px-6">
        {/* The raxIT wordmark, and under it the product line on a shared left edge. */}
        <Link href="/" prefetch={false} aria-label="Benchmark: decision-models-as-guardrails, by raxIT" className="flex shrink-0 flex-col items-start gap-[7px] py-2 text-fg no-underline hover:text-fg">
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, one small PNG (v2 word-only mark from raxitlabs.com) */}
          <img src={overArt ? "/brand/raxit-wordmark-v2-white.png" : "/brand/raxit-wordmark-v2.png"} alt="" width={60} height={16} className="h-4 w-auto" />
          <span className="flex items-center gap-2 whitespace-nowrap text-[12px] leading-none tracking-[0.005em]">
            <span className="font-medium text-fg">Benchmark</span>
            <span aria-hidden="true" className="h-2.5 w-px bg-line-strong" />
            <span className="text-muted">decision-models-as-guardrails</span>
          </span>
        </Link>

        {/* Desktop: the pages, then the outside links after a hairline, then Contact as the one button. */}
        <nav aria-label="Main" className="ml-auto hidden items-center lg:flex">
          <ul className="m-0 flex list-none items-center p-0 text-[14px]">
            <li><NavLink href="/">Results</NavLink></li>
            <li><NavLink href="/reproduce">Reproduce</NavLink></li>
            <li><NavLink href="/data">Data</NavLink></li>
            <li><NavLink href="/research">Research</NavLink></li>
            <li aria-hidden="true" className="mx-2 h-4 w-px bg-line-strong" />
            <li>
              <a href={HF_URL} className={ext}>
                Dataset<span className="sr-only"> on Hugging Face</span> <External className="size-3" />
              </a>
            </li>
            <li>
              <a href={REPO_URL} className={ext}>
                GitHub <External className="size-3" />
              </a>
            </li>
          </ul>
          <ContactLink className="header-cta ml-4 inline-flex min-h-10 items-center rounded-full bg-fg px-4 text-[14px] font-medium text-bg no-underline transition-colors hover:bg-fg-2 hover:text-bg">
            Contact us
          </ContactLink>
        </nav>

        {/* Phones and tablets: one Menu. It opens a full-width sheet under the header, ruled rows, no card. */}
        <details ref={menu} className="group ml-auto lg:hidden">
          <summary className="flex min-h-11 items-center gap-1.5 text-[14px] font-medium text-fg">
            <span className="group-open:hidden">Menu</span>
            <span className="hidden group-open:inline">Close</span>
          </summary>
          <div
            onClick={(e) => {
              if ((e.target as HTMLElement).closest("a")) menu.current?.removeAttribute("open");
            }}
            className="menu-panel fixed inset-x-0 top-[72px] z-50 border-b border-line-strong bg-bg"
          >
            <ul className="mx-auto m-0 flex max-w-[1200px] list-none flex-col px-4 py-2 text-[17px] sm:px-6">
              {[
                ["/", "Results"],
                ["/reproduce", "Reproduce"],
                ["/data", "Data"],
                ["/research", "Research"],
              ].map(([href, label]) => (
                <li key={href} className="border-b border-line">
                  <Link href={href} prefetch={href === "/" ? false : undefined} className="flex min-h-12 items-center text-fg no-underline">
                    {label}
                  </Link>
                </li>
              ))}
              <li className="border-b border-line">
                <a href={HF_URL} className="flex min-h-12 items-center gap-1.5 text-fg-2 no-underline">
                  Dataset on Hugging Face <External className="size-3" />
                </a>
              </li>
              <li>
                <a href={REPO_URL} className="flex min-h-12 items-center gap-1.5 text-fg-2 no-underline">
                  GitHub <External className="size-3" />
                </a>
              </li>
            </ul>
            <div className="mx-auto max-w-[1200px] px-4 pb-5 pt-2 sm:px-6">
              <ContactLink className="header-cta inline-flex min-h-12 w-full items-center justify-center rounded-full bg-fg text-[16px] font-medium text-bg no-underline">
                Contact us
              </ContactLink>
            </div>
          </div>
        </details>
      </div>
    </header>
  );
}
