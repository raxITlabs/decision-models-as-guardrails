"use client";

export interface SegOption<T extends string> {
  value: T;
  label: string;
  /** shown instead of label on phones */
  short?: string;
}

/** A group of toggle buttons; exactly one is pressed. Plain words on the paper: the pressed one is in black ink with a
 *  blue rule under it. No pill, no box. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: SegOption<T>[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex max-w-full flex-wrap gap-x-5 gap-y-1">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={`min-h-11 whitespace-nowrap border-b-2 text-[14px] transition-colors ${
              on ? "border-accent font-medium text-fg" : "border-transparent text-muted hover:text-fg"
            }`}
          >
            {o.short ? (
              <>
                <span className="sm:hidden">{o.short}</span>
                <span className="hidden sm:inline">{o.label}</span>
              </>
            ) : (
              o.label
            )}
          </button>
        );
      })}
    </div>
  );
}

export function Select<T extends string>({
  id,
  label,
  options,
  value,
  onChange,
  hideLabel = false,
}: {
  id: string;
  label: string;
  options: SegOption<T>[];
  value: T;
  onChange: (v: T) => void;
  hideLabel?: boolean;
}) {
  return (
    <label htmlFor={id} className="inline-flex items-center gap-2 text-[13px] text-muted">
      <span className={hideLabel ? "sr-only" : ""}>{label}</span>
      <span className="relative inline-flex">
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value as T)}
          className="min-h-11 appearance-none rounded-none border-0 border-b border-line-strong bg-transparent py-1.5 pl-0 pr-7 text-[15px] text-fg hover:border-fg/60 focus-visible:border-accent"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <svg viewBox="0 0 16 16" aria-hidden="true" className="pointer-events-none absolute right-1 top-1/2 size-3.5 -translate-y-1/2 text-muted" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 6l4 4 4-4" />
        </svg>
      </span>
    </label>
  );
}
