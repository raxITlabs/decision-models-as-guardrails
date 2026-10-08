"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const path = usePathname();
  const active = href === "/" ? path === "/" : path === href || path.startsWith(href + "/");
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`inline-flex min-h-11 items-center rounded-md px-3 font-medium no-underline transition-colors hover:bg-raised hover:text-fg ${
        active ? "text-fg" : "text-fg-2"
      }`}
    >
      {children}
    </Link>
  );
}
