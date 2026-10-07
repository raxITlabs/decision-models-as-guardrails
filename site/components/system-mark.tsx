import type { SystemMeta } from "@/lib/types";

const SIZES = { sm: "size-6 rounded-md text-[12px]", md: "size-8 rounded-lg text-[13px]", lg: "size-11 rounded-lg text-[14px]" };
const IMG = { sm: "size-4", md: "size-5", lg: "size-7" };

/** The maker's logo, or a monogram when there is none. Decorative: the name is always printed beside it. */
export function SystemMark({ m, size = "sm" }: { m?: SystemMeta; size?: keyof typeof SIZES }) {
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center border border-line bg-surface font-semibold text-fg-2 ${SIZES[size]}`}
    >
      {m?.logo ? (
        // eslint-disable-next-line @next/next/no-img-element -- static export, tiny SVGs
        <img src={m.logo} alt="" className={IMG[size]} />
      ) : (
        <span className="num">{m?.mono ?? "?"}</span>
      )}
    </span>
  );
}
