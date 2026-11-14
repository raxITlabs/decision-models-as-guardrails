import type { SystemMeta } from "./types";

type Kind = SystemMeta["kind"];
type HasKind = Pick<SystemMeta, "kind"> | undefined;

/** A classic guardrail: a managed guardrail service (Bedrock) or a safety classifier (Llama Guard, gpt-oss-safeguard).
 *  Everything else on the board is a decision model. */
export function isClassic(m?: HasKind): boolean {
  return m?.kind === "service" || m?.kind === "classifier";
}

/** The one name for each kind, in sentence case. Every component says a system's kind with these words. */
export const KIND_LABEL: Record<Kind, string> = {
  decision: "Decision model",
  classifier: "Safety classifier",
  service: "Guardrail service",
};

/** What each kind does, in one line, for titles, tooltips and screen-reader text. */
export const KIND_GLOSS: Record<Kind, string> = {
  decision: "answers the yes/no questions you write with a probability",
  classifier: "labels content against a safety policy and returns a verdict, not a probability",
  service: "a managed service that applies safeguards you configure from a fixed set",
};

/** The kind's name, for a system that may be missing from the metadata (treated as a decision model). */
export function kindLabel(m?: HasKind): string {
  return KIND_LABEL[m?.kind ?? "decision"];
}

/** What kind of classic guardrail it is: "Safety classifier" or "Guardrail service". */
export function classicType(m?: HasKind): string {
  return m?.kind === "service" ? KIND_LABEL.service : KIND_LABEL.classifier;
}
