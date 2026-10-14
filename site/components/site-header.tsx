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
  return (
    <header
      data-over-art={overArt ? "true" : undefined}
      className="site-header sticky top-0 z-40 border-b border-line bg-bg transition-[background-color,border-color] duration-300 ease-out"
    >
      <div className="mx-auto flex h-[72px] max-w-[1200px] items-center gap-3 px-4 sm:px-6">
        {/* Stacked: the raxIT wordmark, and under it the product line, Benchmark | decision-models-as-guardrails. */}
        <Link href="/" prefetch={false} className="flex min-h-11 min-w-0 shrink-0 flex-col items-start justify-center gap-1.5 text-fg no-underline hover:text-fg">
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, one small PNG (v2 word-only mark from raxitlabs.com) */}
          <img src={overArt ? "/brand/raxit-wordmark-v2-white.png" : "/brand/raxit-wordmark-v2.png"} alt="raxIT" width={60} height={16} className="h-[15px] w-auto sm:h-4" />
          <span className="inline-flex items-center gap-2 whitespace-nowrap text-[12px] leading-none sm:text-[13px]">
            <span className="font-medium text-fg">Benchmark</span>
            <span aria-hidden="true" className="h-3 w-px bg-line-strong" />
            <span className="text-muted">decision-models-as-guardrails</span>
          </span>
        </Link>
        {/* Phones: the stacked name needs the width, so the links fold into a Menu. */}
        <details ref={menu} className="relative ml-auto sm:hidden">
          <summary className="inline-flex min-h-11 items-center px-2 text-[14px] font-medium text-fg-2 underline decoration-line-strong underline-offset-[6px]">
            Menu
          </summary>
          <ul
            onClick={() => menu.current?.removeAttribute("open")}
            className="menu-panel absolute right-0 top-full z-50 m-0 mt-2 flex w-48 list-none flex-col border border-line-strong bg-bg p-2 text-[15px] shadow-[0_16px_40px_-20px_rgb(var(--smoky)/0.45)]"
          >
            <li><NavLink href="/">Results</NavLink></li>
            <li><NavLink href="/reproduce">Reproduce</NavLink></li>
            <li><NavLink href="/data">Data</NavLink></li>
            <li><NavLink href="/research">Research</NavLink></li>
            <li>
              <ContactLink className="inline-flex min-h-11 items-center px-2 font-medium text-fg-2 no-underline">Contact</ContactLink>
            </li>
            <li><a href={HF_URL} className="inline-flex min-h-11 items-center gap-1 px-2 text-fg-2 no-underline">Dataset <External /></a></li>
            <li><a href={REPO_URL} className="inline-flex min-h-11 items-center gap-1 px-2 text-fg-2 no-underline">GitHub <External /></a></li>
          </ul>
        </details>
        <nav aria-label="Main" className="ml-auto hidden min-w-0 items-center sm:flex">
          <ul className="flex items-center gap-0.5 overflow-x-auto text-[14px] [scrollbar-width:none]">
            <li><NavLink href="/">Results</NavLink></li>
            <li><NavLink href="/reproduce">Reproduce</NavLink></li>
            <li><NavLink href="/data">Data</NavLink></li>
            <li><NavLink href="/research">Research</NavLink></li>
            <li>
              <ContactLink className="inline-flex min-h-11 items-center px-2 font-medium text-fg-2 no-underline underline-offset-[6px] hover:text-fg hover:underline sm:px-3">
                Contact
              </ContactLink>
            </li>
            <li>
              <a href={HF_URL} className="inline-flex min-h-11 items-center gap-1 px-2.5 text-fg-2 no-underline underline-offset-[6px] hover:text-fg hover:underline">
                Dataset<span className="sr-only"> on Hugging Face</span> <External />
              </a>
            </li>
            <li>
              <a href={REPO_URL} className="inline-flex min-h-11 items-center gap-1 px-2.5 text-fg-2 no-underline underline-offset-[6px] hover:text-fg hover:underline">
                GitHub <External />
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
