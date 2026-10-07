/** raxIT mark: a gate with one bar lowered. Drawn, not a glyph. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true" fill="none">
      <rect x="2.5" y="2.5" width="19" height="19" rx="5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M7.5 8.5h9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M7.5 12h9" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M7.5 15.5h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
