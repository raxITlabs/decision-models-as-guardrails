import type { SystemMeta } from "@/lib/types";
import { KIND_GLOSS, KIND_LABEL, classicType, isClassic } from "@/lib/kind";

type ClassicKind = "classifier" | "service";

/** The glyph for each classic kind, drawn at text size in the guard teal. A decision model has no glyph.
 *  Safety classifier: a shield. Guardrail service: a cloud (a managed service you configure). */
function Glyph({ kind }: { kind: ClassicKind }) {
  return kind === "classifier" ? (
    <svg aria-hidden="true" viewBox="0 0 12 14" className="guard-tag-icon">
      <path d="M6 0.75 11 2.6v3.9c0 3.1-2.1 5.6-5 6.75C3.1 12.1 1 9.6 1 6.5V2.6Z" fill="currentColor" />
    </svg>
  ) : (
    <svg aria-hidden="true" viewBox="0 0 16 12" className="guard-tag-icon guard-tag-icon-wide">
      <path d="M4.2 11.25a3.45 3.45 0 0 1-.55-6.86A4.6 4.6 0 0 1 12.4 3.6a3.85 3.85 0 0 1-.35 7.65Z" fill="currentColor" />
    </svg>
  );
}

/** After the name of a classic guardrail, a symbol only: a shield for a safety classifier, a cloud for a guardrail
 *  service. The words live in the legend (KindLegend) and in the accessible name and tooltip. Renders nothing for a
 *  decision model. */
export function GuardTag({ m, onArt = false }: { m?: Pick<SystemMeta, "kind">; onArt?: boolean }) {
  if (!isClassic(m)) return null;
  const kind = m!.kind as ClassicKind;
  const label = classicType(m);
  return (
    <span role="img" aria-label={label} title={`${label}: ${KIND_GLOSS[kind]}. Not a decision model.`}
      className={onArt ? "guard-tag guard-tag-art" : "guard-tag"}>
      <Glyph kind={kind} />
    </span>
  );
}

/** The key to the symbols, placed once under a table, chart or list that uses GuardTag. Pass the kinds present so
 *  the legend only explains what the reader can see. */
export function KindLegend({ kinds, onArt = false, className = "" }: { kinds: SystemMeta["kind"][]; onArt?: boolean; className?: string }) {
  const present = new Set(kinds);
  const classic = (["classifier", "service"] as const).filter((k) => present.has(k));
  if (!classic.length) return null;
  return (
    <span className={`kind-legend ${onArt ? "kind-legend-art" : ""} ${className}`}>
      {present.has("decision") && <span className="kind-legend-item">No symbol: {KIND_LABEL.decision.toLowerCase()}</span>}
      {classic.map((k) => (
        <span key={k} className="kind-legend-item">
          <span className={onArt ? "guard-tag guard-tag-art" : "guard-tag"} aria-hidden="true"><Glyph kind={k} /></span>
          {KIND_LABEL[k]}
        </span>
      ))}
    </span>
  );
}

/** A system's name with its kind symbol after it. The name may wrap on a narrow screen, but the symbol stays on the
 *  same line as the name's last word, so it never sits alone on a line. */
export function NameWithKind({ name, m, onArt = false }: { name: string; m?: Pick<SystemMeta, "kind">; onArt?: boolean }) {
  if (!isClassic(m)) return <>{name}</>;
  const cut = name.lastIndexOf(" ") + 1;
  return (
    <>
      {name.slice(0, cut)}
      <span className="whitespace-nowrap">
        {name.slice(cut)}
        <span className="ml-1.5 inline-flex align-[-1px]"><GuardTag m={m} onArt={onArt} /></span>
      </span>
    </>
  );
}
