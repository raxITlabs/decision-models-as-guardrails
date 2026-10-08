"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const path = usePathname();
  const active = href === "/" ? path === "/" : path === href || path.startsWith(href + "/");
  return (
    <Link
      href={href}
      // Prefetching / pulls in its hero-image preload on every page.
      prefetch={href === "/" ? false : undefined}
      aria-current={active ? "page" : undefined}
      className={`inline-flex min-h-11 items-center px-3 font-medium underline-offset-[6px] transition-colors hover:text-fg hover:underline ${
        active ? "text-fg underline decoration-accent decoration-2" : "text-fg-2 no-underline"
      }`}
    >
      {children}
    </Link>
  );
}
