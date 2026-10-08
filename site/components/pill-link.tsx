import Link from "next/link";

const VARIANTS = {
  /** Ink pill on the paper ground: the one primary button. */
  ink: "bg-fg text-bg hover:bg-fg-2 hover:text-bg",
  /** Paper pill over a painting. */
  paper: "bg-[var(--over-art)] text-fg hover:bg-white hover:text-fg",
  /** Outlined pill over a painting. */
  ghost: "over-art border border-[color-mix(in_srgb,var(--over-art)_55%,transparent)] hover:bg-white/10 hover:text-[var(--over-art)]",
};

/** The site's button-styled link, in the raxIT pill shape. Internal paths use next/link; anything else is a plain anchor. */
export function PillLink({
  href,
  variant = "ink",
  children,
}: {
  href: string;
  variant?: keyof typeof VARIANTS;
  children: React.ReactNode;
}) {
  const className = `inline-flex min-h-12 items-center gap-2 rounded-full px-6 text-[16px] font-medium no-underline ${VARIANTS[variant]}`;
  return href.startsWith("/") ? (
    <Link href={href} className={className}>
      {children}
    </Link>
  ) : (
    <a href={href} className={className}>
      {children}
    </a>
  );
}
