import type { Board } from "@/lib/types";
import { oneLine } from "@/lib/format";
import { SystemMark } from "./system-mark";

/**
 * Two kinds of system share this board, and buyers need to know which is which: decision models answer policy
 * questions you write, guardrail services apply safeguards they define. Facts on Bedrock follow the feature inventory
 * in docs/research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md.
 */
export function TwoKinds({ board }: { board: Board }) {
  const decision = board.systems.filter((s) => s.kind === "decision");
  const service = board.systems.filter((s) => s.kind === "service");
  const rows: { label: string; model: string; svc: string }[] = [
    {
      label: "How you set the policy",
      model: "You write it as plain yes/no questions, such as \"Does this message ask for investment advice?\". One model answers any policy you can put into words.",
      svc: "You configure the service's own safeguards: content filters by category, denied topics as short definitions, word lists, 31 built-in personal-data types and grounding checks.",
    },
    {
      label: "What comes back",
      model: "A probability for each question (or the vendor's yes/no flag). You decide where to draw the line.",
      svc: "A verdict per safeguard, intervene or not, with a confidence level or score behind it.",
    },
    {
      label: "How you tune it",
      model: "Move the threshold, or reword the question. Nothing to retrain.",
      svc: "Change a filter's strength (low, medium, high) or edit a topic definition, within the categories the service offers.",
    },
    {
      label: "How we ran it here",
      model: `Every model blocks at a probability of ${board.stats.threshold} or more. No threshold is tuned.`,
      svc: "One documented configuration, set up with Terraform before any row was sent.",
    },
  ];
  return (
    <section id="kinds" aria-labelledby="kinds-h" className="flex scroll-mt-24 flex-col gap-8">
      <div className="flex max-w-[760px] flex-col gap-2.5">
        <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Two kinds of guardrail</span>
        <h2 id="kinds-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-balance">
          A decision model is not a guardrail service
        </h2>
        <p className="m-0 text-[16px] leading-relaxed text-fg-2">
          {decision.length} of the {board.systems.length} systems are decision models, including the hosted Decisions APIs from
          Perplexity and OpenAI. Bedrock Guardrails is a managed guardrail service. Both block harmful traffic, but you set them up and tune them in different ways.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {[
          { title: "Decision model", tag: "Your policy, in your words", systems: decision, key: "model" as const, accent: false },
          { title: "Guardrail service", tag: "The service's safeguards, configured", systems: service, key: "svc" as const, accent: true },
        ].map((col) => (
          <div
            key={col.title}
            className={`flex flex-col gap-5 rounded-xl border bg-surface p-5 sm:p-6 ${col.accent ? "border-line-strong" : "border-line"}`}
          >
            <div className="flex flex-col gap-1">
              <h3 className="m-0 text-[20px] font-semibold tracking-[-0.01em]">{col.title}</h3>
              <span className="text-[14px] text-muted">{col.tag}</span>
            </div>
            <dl className="m-0 flex flex-col">
              {rows.map((r) => (
                <div key={r.label} className="flex flex-col gap-1 border-t border-line py-3.5">
                  <dt className="text-[12px] font-medium uppercase tracking-[0.12em] text-muted">{r.label}</dt>
                  <dd className="m-0 text-[15px] leading-relaxed text-fg-2">{r[col.key]}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-auto flex flex-wrap items-center gap-2 border-t border-line pt-4">
              <span className="sr-only">Systems on this board:</span>
              {col.systems.map((s) => (
                <span key={s.id} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-bg py-1 pl-1 pr-2.5 text-[12px] text-fg-2">
                  <SystemMark m={s} />
                  {oneLine(s, s.id)}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
