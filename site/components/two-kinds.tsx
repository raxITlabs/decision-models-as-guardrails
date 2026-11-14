import type { Board, SystemMeta } from "@/lib/types";
import { listNames, oneLine } from "@/lib/format";
import { KIND_LABEL } from "@/lib/kind";
import { GuardTag } from "./guard-tag";

type Kind = SystemMeta["kind"];
const KINDS: Kind[] = ["decision", "classifier", "service"];
/** Makers named in the intro when they have a hosted decision model on the board, in this order. */
const NAMED_MAKERS = ["Perplexity", "OpenAI", "Google", "HeyGen"];
/** The three-column grid from lg up: question, then one column per kind. */
const GRID = "lg:grid-cols-[minmax(0,10rem)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]";

/**
 * Three kinds of system share this board, and buyers need to know which is which: decision models answer policy
 * questions you write; safety classifiers and the guardrail service are classic guardrails. This is the one place the
 * kinds are named in full; the glyphs beside the column heads are the ones GuardTag prints after names elsewhere.
 * Facts on Bedrock follow docs/research/early-2026-09-18/09-bedrock-guardrails-feature-inventory.md; facts on the
 * safety classifiers follow docs/benchmark/36-classic-guardrails-proposal.md.
 */
export function TwoKinds({ board }: { board: Board }) {
  const of = (k: Kind) => board.systems.filter((s) => s.kind === k);
  const decision = of("decision");
  const classifiers = of("classifier");
  const service = of("service");
  const hosted = decision.filter((s) => s.hosting === "managed");
  const selfHosted = decision.length - hosted.length;
  const makers = new Set(hosted.map((s) => s.provider.split(" · ")[0]));
  const named = NAMED_MAKERS.filter((m) => makers.has(m));
  const unranked = classifiers.filter((s) => s.unranked);
  const kinds = KINDS.filter((k) => of(k).length > 0);

  const rows: { label: string; text: Record<Kind, string> }[] = [
    {
      label: "How you set the policy",
      text: {
        decision: "You write it as plain yes/no questions, such as \"Does this message ask for investment advice?\". One model answers any policy you can put into words.",
        classifier: "The model checks content against a safety policy. Llama Guard 4 uses Meta's fixed list of 14 harm categories. gpt-oss-safeguard-20b reads a policy you write.",
        service: "You configure the service's own safeguards: content filters by category, denied topics as short definitions, word lists, 31 built-in personal-data types and grounding checks.",
      },
    },
    {
      label: "What comes back",
      text: {
        decision: "A probability for each question (or the vendor's yes/no flag). You decide where to draw the line.",
        classifier: "A verdict, safe or unsafe. The hosted APIs we called return no probability. Llama Guard 4 also names the categories it matched.",
        service: "A verdict per safeguard, intervene or not, with a confidence level or score behind it.",
      },
    },
    {
      label: "How you tune it",
      text: {
        decision: "Move the threshold, or reword the question. Nothing to retrain.",
        classifier: "Choose which of its categories count, or rewrite the policy text. There is no threshold to move.",
        service: "Change a filter's strength (low, medium, high) or edit a topic definition, within the categories the service offers.",
      },
    },
    {
      label: "How we ran it here",
      text: {
        decision: `Every model blocks at a probability of ${board.stats.threshold} or more. No threshold is tuned.`,
        classifier:
          "We score each model's own verdict as it comes. A model that reads a written policy got our policy text as written." +
          unranked
            .map((s) => ` ${oneLine(s, s.id)} offers ${suites(s.unranked!.suites.length)} of ${board.stats.suites}, so we do not rank it overall.`)
            .join(""),
        service: "One documented configuration, set up with Terraform before any row was sent.",
      },
    },
  ];

  return (
    <section id="kinds" aria-labelledby="kinds-h" className="flex scroll-mt-24 flex-col gap-8">
      <div className="flex max-w-[760px] flex-col gap-2.5">
        <h2 id="kinds-h" className="m-0 text-[clamp(1.75rem,3.4vw,2.5rem)] font-semibold leading-[1.1] tracking-[-0.02em] text-balance">
          A decision model is not a classic guardrail
        </h2>
        <p className="m-0 text-[16px] leading-relaxed text-fg-2">
          {decision.length} of the {board.systems.length} systems are decision models. {hosted.length} are hosted APIs from {makers.size} makers
          {named.length ? `, among them ${listNames(named)}` : ""}
          {selfHosted ? `, and ${selfHosted} are open-weights models we ran on our own GPUs` : ""}. The other{" "}
          {classifiers.length + service.length} are classic guardrails, marked in teal across the site.
          {classifiers.length ? ` ${listNames(classifiers.map((s) => oneLine(s, s.id)))} ${classifiers.length === 1 ? "is a safety classifier" : "are safety classifiers"}.` : ""}
          {service.length ? ` ${listNames(service.map((s) => oneLine(s, s.id)))} ${service.length === 1 ? "is a guardrail service" : "are guardrail services"}.` : ""}{" "}
          All of them block harmful traffic, but you set them up and tune them in different ways.
        </p>
      </div>

      {/* One ruled comparison, read across: the same question, answered for each kind. No boxes. From lg up the two
          classic kinds sit under one teal rule; below lg each answer carries its kind's name and glyph. */}
      <div className="border-t border-line-strong">
        <div className={`hidden gap-x-8 border-b border-line pb-4 pt-3 lg:grid ${GRID}`}>
          <span />
          <span />
          <span className="col-span-2 border-b-2 border-guard pb-1.5 text-[13px] font-semibold text-guard">Classic guardrails</span>
          <span />
          <ColHead kind="decision" tag="Your questions, a probability back" />
          {kinds.includes("classifier") && <ColHead kind="classifier" tag="A safety policy, a verdict back" rule />}
          {kinds.includes("service") && <ColHead kind="service" tag="The service's safeguards, configured" rule />}
        </div>
        <dl className="m-0">
          {rows.map((r) => (
            <div key={r.label} className={`grid gap-x-8 gap-y-3 border-b border-line py-5 ${GRID}`}>
              <dt className="text-[15px] font-semibold">{r.label}</dt>
              {kinds.map((k) => (
                <Cell key={k} kind={k}>
                  {r.text[k]}
                </Cell>
              ))}
            </div>
          ))}
          <div className={`grid gap-x-8 gap-y-3 py-5 ${GRID}`}>
            <dt className="text-[15px] font-semibold">On this board</dt>
            {kinds.map((k) => (
              <Cell key={k} kind={k} small>
                {names(of(k))}
              </Cell>
            ))}
          </div>
        </dl>
      </div>
    </section>
  );
}

const suites = (n: number) => (n === 1 ? "one suite" : `${n} suites`);

/** The kind's name with its glyph (none for a decision model): the same glyph GuardTag prints after names elsewhere. */
function KindName({ kind, className }: { kind: Kind; className: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 ${kind === "decision" ? "" : "text-guard"} ${className}`}>
      {KIND_LABEL[kind]}
      <span aria-hidden="true" className="inline-flex">
        <GuardTag m={{ kind }} />
      </span>
    </span>
  );
}

function ColHead({ kind, tag, rule = false }: { kind: Kind; tag: string; rule?: boolean }) {
  return (
    <span className={`flex flex-col ${rule ? "border-l border-line pl-8" : ""}`}>
      <KindName kind={kind} className="text-[18px] font-semibold tracking-[-0.01em]" />
      <span className="text-[14px] text-muted">{tag}</span>
    </span>
  );
}

function Cell({ kind, small = false, children }: { kind: Kind; small?: boolean; children: React.ReactNode }) {
  return (
    <dd className={`m-0 leading-relaxed text-fg-2 ${small ? "text-[14px]" : "text-[15px]"} ${kind === "decision" ? "" : "lg:border-l lg:border-line lg:pl-8"}`}>
      <KindName kind={kind} className="mb-0.5 text-[13px] font-medium lg:hidden" />
      <span className="block">{children}</span>
    </dd>
  );
}

const names = (xs: { id: string; name: string; label?: string }[]) => listNames(xs.map((s) => oneLine(s, s.id))) + ".";
