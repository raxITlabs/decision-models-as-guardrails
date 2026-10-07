// A small, consistent stroke icon set (1.6px, round caps).
type P = { className?: string };
const base = {
  viewBox: "0 0 16 16",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};
export const ArrowRight = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M3 8h10M9 4l4 4-4 4" /></svg>
);
export const ArrowDown = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M8 3v10M4 9l4 4 4-4" /></svg>
);
export const ArrowUpLeft = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M12 12L4 4M4 4h6M4 4v6" /></svg>
);
export const External = ({ className = "size-3.5" }: P) => (
  <svg {...base} className={className}><path d="M6 3H3.5A.5.5 0 0 0 3 3.5v9a.5.5 0 0 0 .5.5h9a.5.5 0 0 0 .5-.5V10M9 3h4v4M13 3L7.5 8.5" /></svg>
);
export const Chevron = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M6 3l5 5-5 5" /></svg>
);
export const Sun = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><circle cx="8" cy="8" r="3" /><path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1" /></svg>
);
export const Moon = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7z" /></svg>
);
export const Copy = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><rect x="5.5" y="5.5" width="8" height="8" rx="1.5" /><path d="M10.5 5.5V3.5a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2" /></svg>
);
export const Check = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M3 8.5l3 3 7-7" /></svg>
);
export const Cross = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><path d="M4 4l8 8M12 4l-8 8" /></svg>
);
export const Lock = ({ className = "size-4" }: P) => (
  <svg {...base} className={className}><rect x="3" y="7" width="10" height="7" rx="1.5" /><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" /></svg>
);
