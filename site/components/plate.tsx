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
    <div className={`relative grid overflow-hidden rounded-[4px] ${minH} ${className}`}>
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
      <div aria-hidden="true" className="col-start-1 row-start-1 bg-black/[0.05]" />
      <div className="relative col-start-1 row-start-1 flex min-w-0 flex-col gap-4 p-3 sm:gap-5 sm:p-8 lg:p-12">{children}</div>
    </div>
  );
}
