import type { SystemMeta } from "@/lib/types";

const SIZES = { sm: "size-6 rounded-md", md: "size-8 rounded-lg", lg: "size-11 rounded-lg" };
const IMG = { sm: "size-4", md: "size-5", lg: "size-7" };

/** Generic marks for makers without a published logo: a shield for a managed API, a cube for open weights. */
function Generic({ hosting, className }: { hosting?: SystemMeta["hosting"]; className: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" className={className}>
      {hosting === "managed" ? (
        <>
          <path d="M12 3l7 3v5.5c0 4.2-2.9 7.9-7 9.5-4.1-1.6-7-5.3-7-9.5V6l7-3z" />
          <path d="M9 12l2 2 4-4" />
        </>
      ) : (
        <>
          <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" />
          <path d="M4 7.5l8 4.5 8-4.5M12 12v9" />
        </>
      )}
    </svg>
  );
}

/** The maker's logo, or a generic mark when there is none. Decorative: the name is always printed beside it. */
export function SystemMark({ m, size = "sm" }: { m?: SystemMeta; size?: keyof typeof SIZES }) {
  return (
    <span aria-hidden="true" className={`grid shrink-0 place-items-center border border-line bg-surface text-muted ${SIZES[size]}`}>
      {m?.logo ? (
        // eslint-disable-next-line @next/next/no-img-element -- static export, tiny SVGs
        <img src={m.logo} alt="" className={IMG[size]} />
      ) : (
        <Generic hosting={m?.hosting} className={IMG[size]} />
      )}
    </span>
  );
}
