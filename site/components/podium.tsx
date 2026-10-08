import type { Board } from "@/lib/types";
import { money, score1, tierVar } from "@/lib/format";
import { ArrowRight } from "./icons";
import { SystemMark } from "./system-mark";

/** The top of the overall board, set on paper over the hero painting: the answer next to the question. */
export function Podium({ board }: { board: Board }) {
  const sys = Object.fromEntries(board.systems.map((s) => [s.id, s]));
  const top = [...board.overall].sort((a, b) => a.rank - b.rank).slice(0, 3);
  return (
    <div className="rise rise-2 w-full rounded-xl bg-surface/95 p-5 text-fg shadow-[0_24px_60px_-28px_rgb(16_12_8/0.55)] sm:p-6">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Top of the board</span>
        <span className="text-[12px] text-muted">overall score</span>
      </div>
      <ol className="m-0 flex list-none flex-col p-0">
        {top.map((s) => {
          const m = sys[s.system];
          return (
            <li key={s.system} className="flex items-center gap-3 border-t border-line py-3 first:border-t-0">
              <span className="num w-4 text-[13px] text-muted">{s.rank}</span>
              <SystemMark m={m} size="md" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="text-[15px] font-semibold leading-snug">{m?.name ?? s.system}</span>
                <span className="truncate text-[12px] text-muted">
                  <span className="hidden sm:inline">{m?.provider.split(" · ")[0]} · </span>
                  {money(s.cost)} per 1,000
                </span>
              </span>
              <span className="flex items-center gap-2">
                <span className="size-2 rounded-full" style={{ background: tierVar(s.tier) }} aria-hidden="true" />
                <span className="num text-[24px] font-semibold tracking-[-0.02em]">{score1(s.score)}</span>
              </span>
            </li>
          );
        })}
      </ol>
      <a href="#leaderboard" className="mt-2 inline-flex min-h-11 items-center gap-1.5 text-[14px] font-medium">
        All {board.stats.systems} systems <ArrowRight />
      </a>
    </div>
  );
}
