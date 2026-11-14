import type { SystemMeta } from "./types";

/** A classic guardrail: a managed guardrail service (Bedrock) or a safety classifier (Llama Guard, gpt-oss-safeguard).
 *  Everything else on the board is a decision model. */
export function isClassic(m?: Pick<SystemMeta, "kind">): boolean {
  return m?.kind === "service" || m?.kind === "classifier";
}

/** What kind of classic guardrail it is, in a few words. */
export function classicType(m?: Pick<SystemMeta, "kind">): string {
  return m?.kind === "service" ? "Managed guardrail service" : "Safety classifier";
}
