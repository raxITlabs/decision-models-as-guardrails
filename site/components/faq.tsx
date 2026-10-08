import { Chevron } from "./icons";

export interface QA {
  q: string;
  a: React.ReactNode;
}

export function Faq({ items }: { items: QA[] }) {
  return (
    <div className="border-t border-line-strong">
      {items.map((it) => (
        <details key={it.q} className="group border-b border-line-strong">
          <summary className="flex min-h-14 items-center gap-3.5 py-4 pr-1 text-[16px] font-semibold text-fg hover:text-link sm:text-[17px]">
            <Chevron className="chev size-4 shrink-0 text-link transition-transform duration-150 ease-out" />
            <span>{it.q}</span>
          </summary>
          <div className="max-w-[72ch] pb-6 pl-[30px] text-[15px] leading-[1.65] text-fg-2">{it.a}</div>
        </details>
      ))}
    </div>
  );
}
