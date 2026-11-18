import type { SystemMeta } from "@/lib/types";

const fmt = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/** "Retired" after the name of a hosted system whose provider has shut its endpoint down. Muted, no dot: the score
 *  stands, but nobody can call the model any more (owner ruling 47). Styles in globals.css, .retired-tag. */
export function RetiredTag({ m, onArt = false }: { m?: SystemMeta; onArt?: boolean }) {
  if (!m?.retired) return null;
  const past = m.retired <= new Date().toISOString().slice(0, 10);
  const title = past
    ? `The provider shut this endpoint down on ${fmt(m.retired)}. The score stands; the model can no longer be rerun.`
    : `The provider shuts this endpoint down on ${fmt(m.retired)}. The score stands; after that the model can't be rerun.`;
  return (
    <span className={onArt ? "retired-tag retired-tag-art" : "retired-tag"} title={title}>
      {past ? "Retired" : `Retiring ${fmt(m.retired)}`}
    </span>
  );
}
