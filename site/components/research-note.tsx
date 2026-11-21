import Link from "next/link";
import { ArrowRight } from "@/components/icons";

/**
 * A one-line announcement over the hero painting: the site's "New" marker, one concrete result, and a link.
 * Not a banner or a pill; it reads as a line of type with a hairline under it, so the headline stays the first read.
 */
export function ResearchNote({ href, label, children }: { href: string; label: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="research-note group over-art inline-flex max-w-full flex-wrap items-center gap-x-3 gap-y-1.5 self-start border-b border-[color-mix(in_srgb,var(--over-art)_28%,transparent)] pb-2.5 text-[15px] leading-snug no-underline hover:border-[color-mix(in_srgb,var(--over-art)_70%,transparent)] hover:text-[var(--over-art)]"
    >
      <span className="new-tag new-tag-art">
        <span aria-hidden="true" className="new-tag-dot" />
        {label}
      </span>
      <span className="over-art-86 group-hover:text-[var(--over-art)]">{children}</span>
      <span className="inline-flex items-center gap-1.5 font-medium whitespace-nowrap">
        Read the study
        <span className="transition-transform duration-200 ease-out group-hover:translate-x-0.5">
          <ArrowRight className="size-3.5" />
        </span>
      </span>
    </Link>
  );
}
