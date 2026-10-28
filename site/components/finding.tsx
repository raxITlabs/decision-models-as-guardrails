import type { Board, SystemMeta } from "@/lib/types";
import { int, listNames, oneLine, score1 } from "@/lib/format";

/** A quiet statement band: one finding in plain words, placed just above the section that shows the evidence. */
function Band({ label, statement, children }: { label: string; statement: string; children: React.ReactNode }) {
  return (
    <aside aria-label={label} className="grid gap-x-12 gap-y-3 border-t border-line pt-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] md:items-baseline">
      <p className="m-0 max-w-[24ch] text-[clamp(1.5rem,2.6vw,2rem)] font-medium leading-[1.15] tracking-[-0.02em] text-balance">{statement}</p>
      <p className="m-0 max-w-[52ch] text-[15px] leading-relaxed text-fg-2">{children}</p>
    </aside>
  );
}

/** ``hide``: earlier versions of a model, so each model counts once, at its newest version. */
function facts(board: Board, hide: Record<string, string> = {}) {
  const sys = Object.fromEntries(board.systems.map((s) => [s.id, s])) as Record<string, SystemMeta>;
  const overall = [...board.overall].filter((s) => !hide[s.system]).sort((a, b) => a.rank - b.rank);
  const ref = overall.find((s) => sys[s.system]?.kind === "service");
  const decisions = overall.filter((s) => sys[s.system]?.kind === "decision");
  const best = (job: keyof Board["jobs"]) => [...board.jobs[job]].filter((s) => !hide[s.system]).sort((a, b) => a.rank - b.rank)[0];
  return { sys, overall, ref, decisions, best, name: (id: string) => oneLine(sys[id], id) };
}

const N = ({ children }: { children: React.ReactNode }) => <span className="num font-medium text-fg">{children}</span>;

export function BedrockFinding({ board, hide = {} }: { board: Board; hide?: Record<string, string> }) {
  const { overall, ref, decisions } = facts(board, hide);
  if (!ref) return null;
  const beat = decisions.filter((s) => s.score > ref.score);
  const top = overall.slice(0, 4);
  return (
    <Band label="Finding: decision models against Amazon Bedrock Guardrails" statement={`${beat.length} of ${decisions.length} decision models beat Amazon Bedrock Guardrails.`}>
      The top four score <N>{score1(Math.min(...top.map((s) => s.score)))}</N> to <N>{score1(Math.max(...top.map((s) => s.score)))}</N> overall.
      Amazon Bedrock Guardrails scores <N>{score1(ref.score)}</N>. Scores are balanced accuracy across all {board.stats.jobs} use cases, where 50 is a coin
      flip.
    </Band>
  );
}

export function CostFinding({ board, hide = {} }: { board: Board; hide?: Record<string, string> }) {
  const { sys, overall, ref, name } = facts(board, hide);
  if (!ref?.cost) return null;
  // Decision models that cost less than Bedrock and score higher, cheapest first.
  const cheaper = overall
    .filter((s) => sys[s.system]?.kind === "decision" && sys[s.system]?.hosting === "managed" && s.cost !== null)
    .filter((s) => (s.cost as number) < (ref.cost as number) && s.score > ref.score)
    .sort((a, b) => (a.cost as number) - (b.cost as number))
    .slice(0, 2);
  if (cheaper.length === 0) return null;
  const perMillion = (c: number) => `$${int(Math.round(c * 1000))}`;
  return (
    <Band label="Finding: cost" statement="Cheaper is not worse.">
      Per million checks at list price,{" "}
      {listNames(cheaper.map((s) => `${name(s.system)} costs ${perMillion(s.cost as number)}`))}. {cheaper.length === 1 ? "It scores" : "Both score"} higher than Amazon Bedrock Guardrails,
      which costs <N>{perMillion(ref.cost)}</N>.
    </Band>
  );
}

export function AttacksFinding({ board, hide = {} }: { board: Board; hide?: Record<string, string> }) {
  const { best, name } = facts(board, hide);
  const direct = best("direct");
  const indirect = best("indirect");
  return (
    <Band label="Finding: prompt attacks" statement="Attacks typed into the chat are still hard for everyone.">
      The best score on jailbreaks and injection typed into the chat is <N>{score1(direct.score)}</N>, by {name(direct.system)}. Attacks hidden
      in documents and tool output go better, with a best score of <N>{score1(indirect.score)}</N>, by {name(indirect.system)}.
    </Band>
  );
}
