"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { JOB_BY_ID } from "@/lib/jobs";
import { shardUrl } from "@/lib/shard";
import type { Board, RowDetail, RowResult } from "@/lib/types";
import { Check, Cross, Lock } from "./icons";

function rowIdFromLocation(): string {
  const parts = window.location.pathname.replace(/\/+$/, "").split("/");
  const last = decodeURIComponent(parts.at(-1) ?? "").replace(/\.html$/, "");
  if (last && last !== "view") return last;
  return new URLSearchParams(window.location.search).get("id") ?? "";
}

function verdict(r: RowResult, label: "yes" | "no") {
  if (r.outcome === "missing") return { text: "Not run", right: null as boolean | null };
  if (r.outcome === "failed" || r.decision === null) return { text: "Failed", right: false };
  return { text: r.decision ? "Blocked" : "Passed", right: r.decision === (label === "yes") };
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="m-0 text-[12px] font-medium text-muted">{title}</h3>
      <div className="max-h-[32rem] overflow-y-auto whitespace-pre-wrap rounded-lg border border-line bg-surface px-4 py-3 text-[14px] leading-relaxed text-fg [overflow-wrap:anywhere]">
        {children}
      </div>
    </div>
  );
}

type State = { kind: "loading" } | { kind: "missing"; id: string } | { kind: "error" } | { kind: "ok"; row: RowDetail };

export function RowView({ board }: { board: Board }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const id = rowIdFromLocation();
    if (!id) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState({ kind: "missing", id: "" });
      return;
    }
    fetch(shardUrl(id))
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((shard: Record<string, RowDetail>) => {
        const row = shard[id];
        setState(row ? { kind: "ok", row } : { kind: "missing", id });
        if (row) document.title = `Row ${id} · decision-models-as-guardrails`;
      })
      .catch(() => setState({ kind: "error" }));
  }, []);

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-10 px-4 pt-10 sm:px-6 sm:pt-14">
      {state.kind === "loading" && (
        <div className="flex flex-col gap-6" aria-busy="true" aria-label="Loading row">
          <div className="h-5 w-48 animate-pulse rounded bg-surface" />
          <div className="h-9 w-80 max-w-full animate-pulse rounded bg-surface" />
          <div className="h-40 animate-pulse rounded-lg bg-surface" />
          <div className="h-72 animate-pulse rounded-lg bg-surface" />
        </div>
      )}
      {state.kind === "missing" && (
        <div className="flex flex-col gap-4">
          <h1 className="m-0 text-[32px] font-semibold tracking-[-0.02em]">Row not found</h1>
          <p className="m-0 max-w-[60ch] text-[16px] text-fg-2">
            {state.id ? <><span className="num">{state.id}</span> is not a public test row.</> : "No row id was given."} Rows from the
            held-back slice are never listed.
          </p>
          <p className="m-0"><Link href="/data">Browse the data</Link></p>
        </div>
      )}
      {state.kind === "error" && (
        <p role="alert" className="m-0 rounded-lg border border-warn/50 px-4 py-3 text-[14px] text-warn">
          This row did not load. Reload the page, or find it on the <Link href="/data">Data</Link> page.
        </p>
      )}
      {state.kind === "ok" && <RowBody board={board} row={state.row} />}
    </div>
  );
}

function RowBody({ board, row }: { board: Board; row: RowDetail }) {
  const sys = Object.fromEntries(board.systems.map((s) => [s.id, s]));
  const job = JOB_BY_ID[row.job];
  const results = board.overall.map((o) => row.results.find((r) => r.system === o.system)).filter(Boolean) as RowResult[];
  const judged = results.map((r) => verdict(r, row.label));
  const answered = judged.filter((v) => v.right !== null).length;
  const right = judged.filter((v) => v.right).length;
  const roleName: Record<string, string> = { user: "user message", assistant: "assistant reply", tool: "retrieved content" };
  const t = board.stats.threshold;

  return (
    <>
      <nav aria-label="Breadcrumb" className="text-[13px] text-muted">
        <ol className="m-0 flex list-none flex-wrap items-center gap-1.5 p-0">
          <li><Link href="/data">Data</Link></li>
          <li aria-hidden="true">/</li>
          <li><Link href={`/data?job=${row.job}#rows`}>{job.title}</Link></li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" className="num text-fg-2">{row.id}</li>
        </ol>
      </nav>

      <header className="flex flex-col gap-5">
        <h1 className="num m-0 text-[clamp(1.25rem,3.5vw,2rem)] font-medium tracking-[-0.02em] [overflow-wrap:anywhere]">{row.id}</h1>
        <dl className="m-0 grid grid-cols-2 gap-x-8 gap-y-3 text-[14px] sm:grid-cols-4">
          <div><dt className="text-[12px] text-muted">Job</dt><dd className="m-0 mt-0.5">{job.title}</dd></div>
          <div><dt className="text-[12px] text-muted">Source</dt><dd className="num m-0 mt-0.5 [overflow-wrap:anywhere]">{row.source}</dd></div>
          <div><dt className="text-[12px] text-muted">Licence</dt><dd className="num m-0 mt-0.5">{row.licence ?? "see source"}</dd></div>
          <div>
            <dt className="text-[12px] text-muted">Label</dt>
            <dd className={`m-0 mt-0.5 font-medium ${row.label === "yes" ? "text-warn" : "text-good"}`}>{row.label === "yes" ? "Should block" : "Should pass"}</dd>
          </div>
        </dl>
      </header>

      <section aria-labelledby="text-h" className="flex flex-col gap-4">
        <h2 id="text-h" className="m-0 text-[20px] font-semibold tracking-[-0.01em]">What the systems saw</h2>
        {row.withheld ? (
          <div className="flex flex-col gap-2 rounded-lg border border-dashed border-line-strong bg-surface px-5 py-5 text-[14px] text-fg-2">
            <p className="m-0 inline-flex items-center gap-2 font-medium text-fg"><Lock /> Text withheld (licence)</p>
            <p className="m-0 max-w-[68ch] leading-relaxed">
              This source&apos;s licence does not let us republish its text. The dataset ships the row&apos;s id, label and pinned source
              revision. Rebuild the text from the original publisher with the dataset scripts.{" "}
              <Link href="/reproduce#withheld">How to rebuild it</Link>
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {row.context && row.context.length > 0 && (
              <Block title="Earlier turns">
                {row.context.map((c, i) => (
                  <span key={i} className="block [&:not(:first-child)]:mt-3">
                    <span className="num text-[12px] text-muted">{c.role}</span>
                    <br />
                    {c.text}
                  </span>
                ))}
              </Block>
            )}
            {row.document && <Block title="Source document">{row.document}</Block>}
            {row.query && <Block title="Query">{row.query}</Block>}
            {row.toolCall && <Block title="Tool call"><code className="num text-[13px]">{row.toolCall}</code></Block>}
            {row.text && <Block title={`Text under review${row.role ? `, ${roleName[row.role] ?? row.role}` : ""}`}>{row.text}</Block>}
          </div>
        )}
      </section>

      <section aria-labelledby="answers-h" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 id="answers-h" className="m-0 text-[20px] font-semibold tracking-[-0.01em]">Every system&apos;s answer</h2>
          <p className="m-0 text-[14px] text-muted">
            <span className="num text-fg">{right}</span> of {answered} right · a score of {t} or more blocks
          </p>
        </div>
        <div className="-mx-4 overflow-x-auto sm:mx-0">
          <table className="w-full min-w-[560px] border-collapse text-[14px]">
            <caption className="sr-only">Each system&apos;s score, decision and whether it matched the label for this row.</caption>
            <thead>
              <tr className="border-b border-line text-left text-[12px] text-muted">
                <th scope="col" className="py-2.5 pl-4 pr-3 font-medium sm:pl-2">System</th>
                <th scope="col" className="py-2.5 pr-3 font-medium">Score</th>
                <th scope="col" className="py-2.5 pr-3 font-medium">Decision</th>
                <th scope="col" className="py-2.5 pr-4 font-medium sm:pr-2">Against the label</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => {
                const v = judged[i];
                const m = sys[r.system];
                const p = r.score;
                return (
                  <tr key={r.system} className="border-t border-line">
                    <th scope="row" className="py-2.5 pl-4 pr-3 text-left font-normal sm:pl-2">
                      <span className="block font-semibold">{m?.name ?? r.system}</span>
                      <span className="block text-[12px] text-muted">{m?.hosting === "managed" ? "Managed API" : "Self-hosted"}</span>
                    </th>
                    <td className="py-2.5 pr-3">
                      {p === null ? (
                        <span className="text-muted">none</span>
                      ) : (
                        <span className="flex items-center gap-3">
                          <span className="relative h-1.5 w-24 rounded-full bg-raised" aria-hidden="true">
                            <span className="absolute inset-y-0 left-0 rounded-full bg-fg-2" style={{ width: `${Math.min(1, Math.max(0, p)) * 100}%` }} />
                            <span className="absolute -top-1 h-3.5 w-px bg-muted" style={{ left: `${t * 100}%` }} />
                          </span>
                          <span className="num">{p.toFixed(3)}</span>
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 pr-3">{v.text}</td>
                    <td className="py-2.5 pr-4 sm:pr-2">
                      {v.right === null ? (
                        <span className="text-muted">n/a</span>
                      ) : v.right ? (
                        <span className="inline-flex items-center gap-1.5 text-good"><Check /> Right</span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-warn"><Cross /> Wrong</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="m-0 max-w-[72ch] text-[13px] text-muted">
          A decision model&apos;s score is its highest probability across the job&apos;s questions. Bedrock Guardrails reports a severity
          or confidence step instead, and verdict APIs report their own flag. A failed call counts as wrong.
        </p>
      </section>
    </>
  );
}
