import { int, listNames, maxTier, money, pct, tierVar } from "@/lib/format";
import type { Board, SystemMeta } from "@/lib/types";
import { ScoreBar } from "./leaderboard";
import { NewTag } from "./new-tag";
import { SystemMark } from "./system-mark";

/** Every system on the public test rows alone, with the systems that were sent only those rows. Not the ranked board:
 *  its rows leave out the held-back slice, so its ranks and tiers stand on their own. */
export function PublicRows({ board }: { board: Board }) {
  const pr = board.publicRows;
  if (!pr || !pr.publicOnly.length) return null;
  const sys = Object.fromEntries([...board.systems, ...pr.publicOnly].map((s) => [s.id, s])) as Record<string, SystemMeta>;
  const only = new Set(pr.publicOnly.map((s) => s.id));
  const names = listNames(pr.publicOnly.map((s) => s.name));
  const tiers = maxTier(pr.overall);

  return (
    <section id="public-rows" aria-labelledby="pr-h" className="flex scroll-mt-24 flex-col gap-6">
      <div className="flex flex-col gap-2.5">
        <span className="text-[12px] font-medium uppercase tracking-[0.2em] text-muted">Public rows only</span>
        <h2 id="pr-h" className="m-0 text-[clamp(1.375rem,2.6vw,1.75rem)] font-semibold leading-[1.15] tracking-[-0.02em]">
          {names} on the public rows
        </h2>
      </div>
      <div className="flex max-w-[72ch] flex-col gap-3 text-[15px] leading-relaxed text-fg-2">
        <p className="m-0">
          We sent {names} the {int(pr.rows)} public test rows and not the held-back slice, so it is not on the ranked board
          above.
        </p>
        <p className="m-0">
          This table scores every system on those same public rows, under the same rule and with the same 95% intervals.
          Its ranks and tiers come from this table alone and can differ from the main board, which also counts the
          held-back rows.
        </p>
      </div>

      <div className="overflow-x-auto border-t border-line-strong">
        <table className="w-full sm:min-w-[760px] border-collapse text-[14px]">
          <caption className="sr-only">
            Public test rows only: rank, score with 95% interval, tier, catch rate, false-block rate and cost for every system.
          </caption>
          <thead>
            <tr className="border-b border-line text-left text-[12px] text-muted">
              <th scope="col" className="hidden w-10 py-3 pl-5 font-medium sm:table-cell">#</th>
              <th scope="col" className="sticky left-0 z-[1] bg-bg py-2.5 pl-3 pr-3 font-medium sm:static sm:pl-0">System</th>
              <th scope="col" className="py-2.5 pr-3 text-right font-medium sm:text-left">Score <span className="font-normal">±95% CI</span></th>
              <th scope="col" className="hidden py-2.5 pr-3 font-medium sm:table-cell">Tier</th>
              <th scope="col" className="hidden py-2.5 pr-3 text-right font-medium sm:table-cell">Catch rate</th>
              <th scope="col" className="hidden py-2.5 pr-3 text-right font-medium sm:table-cell">False-block rate</th>
              <th scope="col" className="hidden py-2.5 pr-4 text-right font-medium sm:table-cell sm:pr-5">$ per 1,000 checks</th>
            </tr>
          </thead>
          <tbody>
            {pr.overall.map((s, i) => {
              const m = sys[s.system];
              const mine = only.has(s.system);
              const newTier = i > 0 && pr.overall[i - 1].tier !== s.tier;
              return (
                <tr key={s.system} className={`${newTier ? "border-t border-line-strong" : "border-t border-line"} ${mine ? "bg-selected" : ""}`}>
                  <td className="num hidden py-2.5 pl-5 text-muted sm:table-cell">{s.rank}</td>
                  <th scope="row" className={`sticky left-0 z-[1] py-2.5 pl-3 pr-3 text-left font-normal sm:static sm:pl-0 ${mine ? "bg-selected" : "bg-bg"}`}>
                    <span className="flex min-h-11 items-center gap-3">
                      <SystemMark m={m} size="md" />
                      <span className="flex flex-col items-start">
                        <span className="flex items-center gap-2">
                          <span className="font-semibold text-fg">{m?.name ?? s.system}</span>
                          {mine && m?.isNew && <NewTag />}
                        </span>
                        <span className="text-[12px] text-muted">{m?.provider}</span>
                      </span>
                    </span>
                  </th>
                  <td className="py-2.5 pr-3 text-right sm:text-left">
                    <ScoreBar s={s} />
                    <span className={`num mt-0.5 block whitespace-nowrap text-[12px] sm:hidden ${s.falseBlockRate >= 0.25 ? "text-warn" : "text-muted"}`}>
                      {money(s.cost)} · {pct(s.falseBlockRate)} blocked
                    </span>
                  </td>
                  <td className="hidden py-2.5 pr-3 sm:table-cell">
                    <span className="inline-flex items-center gap-2 whitespace-nowrap">
                      <span className="size-2.5 rounded-full" style={{ background: tierVar(s.tier) }} aria-hidden="true" />
                      <span className="num text-[13px]">{s.tier}</span>
                    </span>
                  </td>
                  <td className="num hidden py-2.5 pr-3 text-right sm:table-cell">{pct(s.catchRate)}</td>
                  <td className={`num hidden py-2.5 pr-3 text-right sm:table-cell ${s.falseBlockRate >= 0.25 ? "text-warn" : ""}`}>{pct(s.falseBlockRate)}</td>
                  <td className="num hidden py-2.5 pr-4 text-right sm:table-cell sm:pr-5">{money(s.cost)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-[13px] leading-relaxed text-muted">
        Shaded: sent the public rows only. {tiers} tiers on these rows. Cost for the other systems is from the full run.
      </p>
    </section>
  );
}
