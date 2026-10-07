"use client";

export interface SegOption<T extends string> {
  value: T;
  label: string;
}

/** A group of toggle buttons; exactly one is pressed. */
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
    <div role="group" aria-label={label} className="inline-flex rounded-lg border border-line bg-surface p-0.5">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={`min-h-11 whitespace-nowrap rounded-md px-3 text-[13px] transition-colors sm:min-h-9 ${
              on ? "bg-raised font-medium text-fg shadow-[0_1px_2px_color-mix(in_oklab,var(--fg)_10%,transparent)]" : "text-muted hover:text-fg"
            }`}
          >
            {o.label}
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
          className="min-h-11 appearance-none sm:min-h-9 rounded-lg border border-line bg-surface py-1.5 pl-3 pr-8 text-[13px] text-fg hover:border-line-strong"
        >
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <svg viewBox="0 0 16 16" aria-hidden="true" className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 6l4 4 4-4" />
        </svg>
      </span>
    </label>
  );
}
