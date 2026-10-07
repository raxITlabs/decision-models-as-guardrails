"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { JOBS, type JobId } from "@/lib/jobs";
import { int, score1 } from "@/lib/format";
import type { Board, RowLite, RowsIndex, Score } from "@/lib/types";
import { Lock } from "./icons";
import { SystemMark } from "./system-mark";
import { Segmented, Select } from "./segmented";

type Colour = "score" | "catch" | "fbr";
type Mode = "wrong" | "missed" | "blocked";
const PAGE = 50;

interface Filters {
  job: JobId | "";
  source: string;
  label: "" | "yes" | "no";
  hard: boolean;
  text: boolean;
  system: string;
  mode: Mode;
}
const EMPTY: Filters = { job: "", source: "", label: "", hard: false, text: false, system: "", mode: "wrong" };

function readUrl(): Filters {
  const q = new URLSearchParams(window.location.search);
  const job = q.get("job") ?? "";
  const label = q.get("label") ?? "";
  const mode = q.get("mode") ?? "wrong";
  return {
    job: JOBS.some((j) => j.id === job) ? (job as JobId) : "",
    source: q.get("source") ?? "",
    label: label === "yes" || label === "no" ? label : "",
    hard: q.get("hard") === "1",
    text: q.get("text") === "1",
    system: q.get("system") ?? "",
    mode: mode === "missed" || mode === "blocked" ? mode : "wrong",
  };
}

function writeUrl(f: Filters) {
  const q = new URLSearchParams();
  if (f.job) q.set("job", f.job);
  if (f.source) q.set("source", f.source);
  if (f.label) q.set("label", f.label);
  if (f.hard) q.set("hard", "1");
  if (f.text) q.set("text", "1");
  if (f.system) {
    q.set("system", f.system);
    if (f.mode !== "wrong") q.set("mode", f.mode);
  }
  const s = q.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${s ? `?${s}` : ""}${window.location.hash}`);
}

/** wrong for one system's answer: "1" blocked, "0" passed, "x" failed (always wrong), "." no record */
function isWrong(d: string, label: 0 | 1) {
  if (d === "x") return true;
  if (d === ".") return false;
  return (d === "1") !== (label === 1);
}

export function DataExplorer({ board }: { board: Board }) {
  const [index, setIndex] = useState<RowsIndex | null>(null);
  const [error, setError] = useState(false);
  const [f, setF] = useState<Filters>(EMPTY);
  const [page, setPage] = useState(0);
  const [colour, setColour] = useState<Colour>("score");
  const rowsRef = useRef<HTMLElement>(null);
  const sys = useMemo(() => Object.fromEntries(board.systems.map((s) => [s.id, s])), [board]);

  useEffect(() => {
    // Sync filters from the URL once on mount (static export: no server-side search params).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setF(readUrl());
    fetch("/data/rows-index.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setIndex)
      .catch(() => setError(true));
  }, []);

  const update = useCallback((patch: Partial<Filters>) => {
    setF((prev) => {
      const next = { ...prev, ...patch };
      writeUrl(next);
      return next;
    });
    setPage(0);
  }, []);

  const filtered = useMemo(() => {
    if (!index) return [];
    const jobIdx = f.job ? index.jobs.indexOf(f.job) : -1;
    const srcIdx = f.source ? index.sources.indexOf(f.source) : -1;
    const sysIdx = f.system ? index.systems.indexOf(f.system) : -1;
    return index.rows.filter((r) => {
      if (jobIdx >= 0 && r[1] !== jobIdx) return false;
      if (srcIdx >= 0 && r[2] !== srcIdx) return false;
      if (f.label && (r[3] === 1) !== (f.label === "yes")) return false;
      if (f.text && r[5] === 1) return false;
      if (f.hard) {
        let wrong = 0;
        let answered = 0;
        for (const d of r[4]) {
          if (d === ".") continue;
          answered++;
          if (isWrong(d, r[3])) wrong++;
        }
        if (wrong * 2 <= answered) return false;
      }
      if (sysIdx >= 0) {
        const d = r[4][sysIdx];
        if (!isWrong(d, r[3])) return false;
        if (f.mode === "missed" && r[3] !== 1) return false;
        if (f.mode === "blocked" && r[3] !== 0) return false;
      }
      return true;
    });
  }, [index, f]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const current = Math.min(page, pages - 1);
  const slice = filtered.slice(current * PAGE, current * PAGE + PAGE);

  const pickCell = (job: JobId, system: string) => {
    update({ job, system, mode: colour === "score" ? "wrong" : colour === "catch" ? "missed" : "blocked", hard: false, label: "" });
    rowsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    rowsRef.current?.focus({ preventScroll: true });
  };

  const sysName = (id: string) => sys[id]?.name ?? id;
  const modeText = f.mode === "missed" ? "harmful rows it missed" : f.mode === "blocked" ? "safe rows it blocked" : "rows it got wrong";

  return (
    <div className="flex flex-col gap-14">
      <Heatmap board={board} colour={colour} setColour={setColour} onPick={pickCell} active={f.system && f.job ? { system: f.system, job: f.job } : null} />

      <section id="rows" ref={rowsRef} tabIndex={-1} aria-labelledby="rows-h" className="flex flex-col gap-5 outline-none">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 id="rows-h" className="m-0 text-[24px] font-semibold tracking-[-0.02em]">Rows</h2>
          <p className="m-0 text-[13px] text-muted" aria-live="polite">
            {index ? `${int(filtered.length)} of ${int(index.rows.length)} public rows` : error ? "" : "Loading rows"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <Select
            id="f-job"
            label="Job"
            value={f.job}
            onChange={(v) => update({ job: v as JobId | "" })}
            options={[{ value: "", label: "All jobs" }, ...JOBS.map((j) => ({ value: j.id, label: j.title }))]}
          />
          <Select
            id="f-source"
            label="Source"
            value={f.source}
            onChange={(v) => update({ source: v })}
            options={[{ value: "", label: "All sources" }, ...(index?.sources ?? []).map((s) => ({ value: s, label: s }))]}
          />
          <Select
            id="f-label"
            label="Label"
            value={f.label}
            onChange={(v) => update({ label: v as Filters["label"] })}
            options={[
              { value: "", label: "Any label" },
              { value: "yes", label: "Should block" },
              { value: "no", label: "Should pass" },
            ]}
          />
          <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-line bg-surface px-3 text-[13px] text-fg hover:border-line-strong">
            <input type="checkbox" checked={f.hard} onChange={(e) => update({ hard: e.target.checked })} className="size-5 accent-[var(--accent)]" />
            Most systems got it wrong
          </label>
          <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border border-line bg-surface px-3 text-[13px] text-fg hover:border-line-strong">
            <input type="checkbox" checked={f.text} onChange={(e) => update({ text: e.target.checked })} className="size-5 accent-[var(--accent)]" />
            Text available
          </label>
          {(f.job || f.source || f.label || f.hard || f.text || f.system) && (
            <button type="button" onClick={() => update(EMPTY)} className="min-h-11 rounded-lg px-2 text-[13px] text-link hover:text-link-hover">
              Clear filters
            </button>
          )}
        </div>

        {f.system && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-accent/50 bg-selected px-4 py-3 text-[14px]">
            <span>
              Showing the {modeText} for <strong className="font-semibold">{sysName(f.system)}</strong>
              {f.job ? ` on ${JOBS.find((j) => j.id === f.job)?.title.toLowerCase()}` : ""}.
            </span>
            <Segmented
              label="Which mistakes"
              value={f.mode}
              onChange={(mode) => update({ mode })}
              options={[
                { value: "wrong", label: "All mistakes" },
                { value: "missed", label: "Missed" },
                { value: "blocked", label: "Blocked safe" },
              ]}
            />
            <button type="button" onClick={() => update({ system: "", mode: "wrong" })} className="text-[13px] text-link hover:text-link-hover">
              Show every system
            </button>
          </div>
        )}

        <p className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
          <span>Each square is one system, in leaderboard order.</span>
          <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-[3px] border border-line-strong bg-fg-2" aria-hidden="true" />blocked</span>
          <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-[3px] border border-line-strong" aria-hidden="true" />passed</span>
          <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-[3px] border border-warn bg-warn" aria-hidden="true" />wrong</span>
          <span>Open a row for each system&apos;s name, score and decision.</span>
        </p>

        {error && (
          <p role="alert" className="m-0 rounded-lg border border-warn/50 px-4 py-3 text-[14px] text-warn">
            The row index did not load. Reload the page; if it keeps failing, the rows are also on Hugging Face.
          </p>
        )}

        {!index && !error && (
          <ul className="m-0 flex list-none flex-col gap-2 p-0" aria-hidden="true">
            {Array.from({ length: 6 }, (_, i) => (
              <li key={i} className="h-[92px] animate-pulse rounded-lg bg-surface" />
            ))}
          </ul>
        )}

        {index && filtered.length === 0 && (
          <div className="rounded-lg border border-dashed border-line-strong px-5 py-8 text-center text-[14px] text-muted">
            No public rows match these filters. Try another job or source, or{" "}
            <button type="button" onClick={() => update(EMPTY)} className="text-link underline underline-offset-[3px]">
              clear them
            </button>
            .
          </div>
        )}

        {index && slice.length > 0 && (
          <ol className="m-0 flex list-none flex-col gap-2 p-0">
            {slice.map((r) => (
              <RowItem key={r[0]} r={r} index={index} sysName={sysName} highlight={f.system} />
            ))}
          </ol>
        )}

        {index && pages > 1 && (
          <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-3 text-[13px] text-muted">
            <span>
              Rows {int(current * PAGE + 1)} to {int(Math.min(filtered.length, current * PAGE + PAGE))} of {int(filtered.length)}
            </span>
            <span className="flex items-center gap-2">
              <button
                type="button"
                disabled={current === 0}
                onClick={() => {
                  setPage(current - 1);
                  rowsRef.current?.scrollIntoView({ block: "start" });
                }}
                className="min-h-9 rounded-lg border border-line px-3 text-fg enabled:hover:border-line-strong disabled:opacity-40"
              >
                Previous
              </button>
              <span className="num">
                {current + 1} / {pages}
              </span>
              <button
                type="button"
                disabled={current >= pages - 1}
                onClick={() => {
                  setPage(current + 1);
                  rowsRef.current?.scrollIntoView({ block: "start" });
                }}
                className="min-h-9 rounded-lg border border-line px-3 text-fg enabled:hover:border-line-strong disabled:opacity-40"
              >
                Next
              </button>
            </span>
          </nav>
        )}
      </section>
    </div>
  );
}

function RowItem({ r, index, sysName, highlight }: { r: RowLite; index: RowsIndex; sysName: (id: string) => string; highlight: string }) {
  const [id, jobI, srcI, label, decisions, withheld, snippet] = r;
  const job = JOBS.find((j) => j.id === index.jobs[jobI]);
  let right = 0;
  let answered = 0;
  for (const d of decisions) {
    if (d === ".") continue;
    answered++;
    if (!isWrong(d, label)) right++;
  }
  return (
    <li className="grid gap-x-6 gap-y-3 rounded-lg border border-line bg-surface px-4 py-3.5 transition-colors hover:border-line-strong md:grid-cols-[minmax(0,1fr)_auto]">
      <div className="flex min-w-0 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-muted">
          <Link href={`/data/rows/${id}`} className="num -my-2 inline-flex min-h-11 items-center text-[13px] font-medium">
            {id}
          </Link>
          <span>{job?.title}</span>
          <span className="num">{index.sources[srcI]}</span>
          <span className={label === 1 ? "text-warn" : "text-good"}>{label === 1 ? "Should block" : "Should pass"}</span>
        </div>
        {withheld ? (
          <p className="m-0 inline-flex items-center gap-1.5 text-[14px] text-muted">
            <Lock className="size-3.5 shrink-0" />
            Text withheld (licence); rebuild it with the dataset scripts.
          </p>
        ) : (
          <p className="m-0 line-clamp-2 text-[14px] leading-snug text-fg-2 [overflow-wrap:anywhere]">{snippet}</p>
        )}
      </div>
      <div className="flex flex-col gap-1.5 md:items-end">
        <span className="text-[12px] text-muted">
          <span className="num text-fg">{right}</span> of {answered} right
        </span>
        <span className="flex flex-wrap gap-1" role="img" aria-label={`${right} of ${answered} systems answered correctly`}>
          {decisions.split("").map((d, i) => {
            const s = index.systems[i];
            const wrong = isWrong(d, label);
            const verb = d === "1" ? "blocked" : d === "0" ? "passed" : d === "x" ? "failed" : "not run";
            return (
              <span
                key={s}
                title={`${sysName(s)}: ${verb}${d === "." ? "" : wrong ? ", wrong" : ", right"}`}
                className={`size-3 rounded-[3px] border ${s === highlight ? "ring-2 ring-fg ring-offset-1 ring-offset-[var(--surface)]" : ""}`}
                style={{
                  borderColor: d === "." ? "var(--line)" : wrong ? "var(--warn)" : "var(--line-strong)",
                  background: d === "1" ? (wrong ? "var(--warn)" : "var(--fg-2)") : d === "x" ? "repeating-linear-gradient(45deg, var(--warn) 0 2px, transparent 2px 4px)" : "transparent",
                }}
              />
            );
          })}
        </span>
      </div>
    </li>
  );
}

function cellValue(s: Score | undefined, colour: Colour): number | null {
  if (!s) return null;
  return colour === "score" ? s.score : colour === "catch" ? s.catchRate * 100 : s.falseBlockRate * 100;
}

function Heatmap({
  board,
  colour,
  setColour,
  onPick,
  active,
}: {
  board: Board;
  colour: Colour;
  setColour: (c: Colour) => void;
  onPick: (job: JobId, system: string) => void;
  active: { system: string; job: string } | null;
}) {
  const lookup = useMemo(() => {
    const m: Record<string, Record<string, Score>> = {};
    for (const j of JOBS) for (const s of board.jobs[j.id]) (m[s.system] ??= {})[j.id] = s;
    return m;
  }, [board]);
  // intensity 0..1: score from 50 (coin flip) to 100; catch from 0 to 100; false blocks from 0 to 50%
  const intensity = (v: number) => (colour === "score" ? (v - 50) / 50 : colour === "catch" ? v / 100 : v / 50);
  const hue = colour === "fbr" ? "var(--heat-warn)" : "var(--heat-accent)";
  const fmt = (v: number) => (colour === "score" ? score1(v) : `${v.toFixed(colour === "fbr" ? 1 : 0)}%`);
  const what = colour === "score" ? "rows it got wrong" : colour === "catch" ? "harmful rows it missed" : "safe rows it blocked";

  return (
    <section aria-labelledby="heat-h" className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <h2 id="heat-h" className="m-0 text-[24px] font-semibold tracking-[-0.02em]">Systems by job</h2>
          <p className="m-0 max-w-[62ch] text-[14px] text-muted">Select a cell to list the {what} for that system and job.</p>
        </div>
        <Segmented
          label="Colour cells by"
          value={colour}
          onChange={setColour}
          options={[
            { value: "score", label: "Score" },
            { value: "catch", label: "Catch rate" },
            { value: "fbr", label: "False-block rate" },
          ]}
        />
      </div>
      <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <table className="w-full min-w-[880px] border-separate border-spacing-1 text-[13px]">
          <caption className="sr-only">
            {colour === "score" ? "Score" : colour === "catch" ? "Catch rate" : "False-block rate"} for every system on every job. Each cell is a button that lists the {what}.
          </caption>
          <thead>
            <tr>
              <th scope="col" className="sticky left-0 z-10 w-44 bg-bg pb-2 pl-1 text-left text-[12px] font-medium text-muted">System</th>
              {JOBS.map((j) => (
                <th key={j.id} scope="col" className="pb-2 text-center align-bottom text-[12px] font-medium leading-tight text-muted">
                  {j.short}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {board.overall.map((o) => {
              const m = board.systems.find((s) => s.id === o.system);
              return (
                <tr key={o.system}>
                  <th scope="row" className="sticky left-0 z-10 bg-bg py-0.5 pl-1 pr-2 text-left font-normal">
                    <span className="flex items-center gap-2">
                      <SystemMark m={m} />
                      <span>
                        <span className="block font-semibold text-fg">{m?.name ?? o.system}</span>
                        <span className="block text-[12px] text-muted">{m?.provider}</span>
                      </span>
                    </span>
                  </th>
                  {JOBS.map((j) => {
                    const s = lookup[o.system]?.[j.id];
                    const v = cellValue(s, colour);
                    if (v === null) return <td key={j.id} className="rounded-md text-center text-muted">n/a</td>;
                    const a = Math.max(0.05, Math.min(1, intensity(v)));
                    const on = active?.system === o.system && active?.job === j.id;
                    return (
                      <td key={j.id} className="p-0">
                        <button
                          type="button"
                          onClick={() => onPick(j.id, o.system)}
                          aria-label={`${m?.name ?? o.system}, ${j.title}: ${fmt(v)}. List the ${what}.`}
                          className={`num flex h-11 w-full items-center justify-center rounded-md text-[13px] transition-[box-shadow] hover:shadow-[inset_0_0_0_2px_var(--fg-2)] ${
                            on ? "shadow-[inset_0_0_0_2px_var(--fg)]" : ""
                          }`}
                          style={{
                            // capped per theme (--heat-max) so --heat-ink keeps 4.5:1 on every cell
                            background: `color-mix(in oklab, ${hue} calc(var(--heat-max) * ${Math.round(a * 100)}%), var(--surface))`,
                            color: "var(--heat-ink)",
                          }}
                        >
                          {fmt(v)}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="m-0 text-[12px] text-muted">
        {colour === "score"
          ? "Balanced accuracy on each job. 50 is a coin flip; darker is better."
          : colour === "catch"
            ? "Share of rows that should be blocked that the system blocked. Darker is better."
            : "Share of safe rows the system blocked. These are the refusals your users see; darker is worse."}{" "}
        Personal data is scored per entity type.
      </p>
    </section>
  );
}
