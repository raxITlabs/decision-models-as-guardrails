import type { Board } from "@/lib/types";
import { listNames, oneLine } from "@/lib/format";

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
        <h2 id="kinds-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-balance">
          A decision model is not a guardrail service
        </h2>
        <p className="m-0 text-[16px] leading-relaxed text-fg-2">
          {decision.length} of the {board.systems.length} systems are decision models, including the hosted Decisions APIs from
          Perplexity and OpenAI. Bedrock Guardrails is a managed guardrail service. Both block harmful traffic, but you set them up and tune them in different ways.
        </p>
      </div>

      {/* One ruled comparison, read across: the same question, answered for each kind. No boxes. */}
      <div className="border-t border-line-strong">
        <div className="hidden grid-cols-[minmax(0,13rem)_minmax(0,1fr)_minmax(0,1fr)] gap-x-10 border-b border-line py-4 md:grid">
          <span />
          <ColHead title="Decision model" tag="Your policy, in your words" />
          <span className="border-l border-line pl-10">
            <ColHead title="Guardrail service" tag="The service's safeguards, configured" />
          </span>
        </div>
        <dl className="m-0">
          {rows.map((r) => (
            <div key={r.label} className="grid gap-x-10 gap-y-2 border-b border-line py-5 md:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_minmax(0,1fr)]">
              <dt className="text-[15px] font-semibold">{r.label}</dt>
              <dd className="m-0 text-[15px] leading-relaxed text-fg-2">
                <span className="mb-0.5 block text-[13px] font-medium text-muted md:hidden">Decision model</span>
                {r.model}
              </dd>
              <dd className="m-0 text-[15px] leading-relaxed text-fg-2 md:border-l md:border-line md:pl-10">
                <span className="mb-0.5 block text-[13px] font-medium text-muted md:hidden">Guardrail service</span>
                {r.svc}
              </dd>
            </div>
          ))}
          <div className="grid gap-x-10 gap-y-2 py-5 md:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_minmax(0,1fr)]">
            <dt className="text-[15px] font-semibold">On this board</dt>
            <dd className="m-0 text-[14px] leading-relaxed text-fg-2">{names(decision)}</dd>
            <dd className="m-0 text-[14px] leading-relaxed text-fg-2 md:border-l md:border-line md:pl-10">{names(service)}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}

function ColHead({ title, tag }: { title: string; tag: string }) {
  return (
    <span className="flex flex-col">
      <span className="text-[18px] font-semibold tracking-[-0.01em]">{title}</span>
      <span className="text-[14px] text-muted">{tag}</span>
    </span>
  );
}

const names = (xs: { id: string; name: string; label?: string }[]) => listNames(xs.map((s) => oneLine(s, s.id))) + ".";
