/* eslint-disable @next/next/no-img-element -- static export: plates are pre-sized webp files */

/** Each plate ships at 828, 1280 and 1920 px wide (public/plates/<name>-<w>.webp; the bare name is 1920). */
function srcSet(src: string): string {
  const base = src.replace(/\.webp$/, "");
  return `${base}-828.webp 828w, ${base}-1280.webp 1280w, ${src} 1920w`;
}
const SIZES = "(min-width: 1248px) 1152px, calc(100vw - 32px)";

/**
 * A painted plate with type set over it, the raxIT hero-plate treatment: the painting fills the box,
 * dimmed to 90%, and a smoky-black scrim rises from the bottom under the content so paper ink reads on any part of it.
 */
export function Plate({
  src,
  children,
  className = "",
  minH = "min-h-[480px] sm:min-h-[560px]",
  priority = false,
}: {
  src: string;
  children: React.ReactNode;
  className?: string;
  minH?: string;
  priority?: boolean;
}) {
  return (
    <div className={`relative grid grid-cols-[minmax(0,1fr)] overflow-hidden rounded-[4px] ${minH} ${className}`}>
      <img
        src={src}
        srcSet={srcSet(src)}
        sizes={SIZES}
        alt=""
        loading={priority ? "eager" : "lazy"}
        className="col-start-1 row-start-1 size-full object-cover brightness-90"
      />
      <div className="plate-scrim relative col-start-1 row-start-1 self-end px-5 pb-7 pt-24 sm:px-14 sm:pb-12 sm:pt-40">{children}</div>
    </div>
  );
}

/**
 * The raxIT WallpaperFrame: a painting and the content share one grid cell, so the content sets the height.
 * A 5% ink wash knocks the painting back so the paper cards on top read first.
 */
export function WallpaperFrame({ src, children }: { src: string; children: React.ReactNode }) {
  return (
    <div className="relative grid overflow-hidden rounded-[4px]">
      <img src={src} srcSet={srcSet(src)} sizes={SIZES} alt="" loading="lazy" className="col-start-1 row-start-1 size-full object-cover brightness-90" />
      <div aria-hidden="true" className="relative col-start-1 row-start-1 bg-black/[0.05]" />
      <div className="relative col-start-1 row-start-1 flex min-w-0 flex-col gap-4 p-3 sm:gap-5 sm:p-8 lg:p-12">{children}</div>
    </div>
  );
}

/**
 * The home hero: the painting fills the whole first screen, edge to edge, and slides under the transparent header
 * (the raxIT landing page treatment). A light wash at the top keeps the header ink readable; the bottom scrim carries
 * the title. Content sits on the page's 1200px rail.
 */
export function HeroPlate({ src, children }: { src: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby="hero-h" className="relative -mt-[73px] flex min-h-[100svh] flex-col justify-end overflow-hidden bg-[rgb(var(--smoky))]">
      <span id="hero-sentinel" aria-hidden="true" className="pointer-events-none absolute left-0 top-0 h-6 w-px" />
      {/* The painting is pinned to one screen height. When the hero grows (the names opened on a phone, a long
          example), the extra height is smoky ground below the painting, so the painting never rescales or zooms. */}
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[100svh]">
        <img src={src} srcSet={srcSet(src)} sizes="100vw" alt="" loading="eager" className="hero-painting size-full object-cover" />
        <div className="hero-wash absolute inset-0" />
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-b from-transparent to-[rgb(var(--smoky))]" />
      </div>
      <div className="relative mx-auto w-full max-w-[1200px] px-4 pb-10 pt-28 sm:px-6 sm:pb-12 lg:pb-12">
        {children}
      </div>
    </section>
  );
}
