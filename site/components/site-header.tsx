"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { HF_URL, REPO_URL } from "@/lib/format";
import { External } from "./icons";
import { NavLink } from "./nav-link";

/** On the home page the header sits on the hero painting, transparent with paper ink, until the reader scrolls
 *  (the raxIT site's own behaviour). Everywhere else, and once scrolled, it is solid paper. */
export function SiteHeader() {
  const path = usePathname();
  const [scrolled, setScrolled] = useState(false);
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
        <Link href="/" prefetch={false} className="flex min-h-11 shrink-0 items-center gap-2 text-fg no-underline hover:text-fg">
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, one small SVG */}
          <img src={overArt ? "/brand/raxit-wordmark-light.svg" : "/brand/raxit-wordmark.svg"} alt="raxIT" width={75} height={30} className="h-[30px] w-auto" />
          <span className="hidden text-[14px] text-muted md:inline">/ Labs / decision-models-as-guardrails</span>
        </Link>
        <nav aria-label="Main" className="ml-auto flex min-w-0 items-center">
          <ul className="flex items-center gap-0.5 overflow-x-auto text-[14px] [scrollbar-width:none]">
            <li><NavLink href="/">Results</NavLink></li>
            <li><NavLink href="/reproduce">Reproduce</NavLink></li>
            <li><NavLink href="/data">Data</NavLink></li>
            <li className="hidden sm:block">
              <a href={HF_URL} className="inline-flex min-h-11 items-center gap-1 rounded-md px-2.5 text-fg-2 no-underline hover:bg-raised hover:text-fg">
                Dataset<span className="sr-only"> on Hugging Face</span> <External />
              </a>
            </li>
            <li className="hidden sm:block">
              <a href={REPO_URL} className="inline-flex min-h-11 items-center gap-1 rounded-md px-2.5 text-fg-2 no-underline hover:bg-raised hover:text-fg">
                GitHub <External />
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
