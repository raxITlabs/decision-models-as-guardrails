"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { JOBS, JOB_BY_ID, type JobId } from "@/lib/jobs";
import { int, oneLine, score1 } from "@/lib/format";
import type { Board, RowLite, RowsIndex, Score, SystemMeta } from "@/lib/types";
import { Chevron, External, Lock } from "./icons";
import { SOURCES } from "@/lib/sources";
import { Sensitive } from "./sensitive";
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

function readUrl(systems: Set<string>): Filters {
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
    system: systems.has(q.get("system") ?? "") ? (q.get("system") as string) : "",
    mode: mode === "missed" || mode === "blocked" ? mode : "wrong",
  };
}

function writeUrl(f: Filters, page: number) {
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
  if (page > 0) q.set("page", String(page + 1));
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
  const [filtersOpen, setFiltersOpen] = useState(false);
  const rowsRef = useRef<HTMLElement>(null);
  const sys = useMemo(() => Object.fromEntries(board.systems.map((s) => [s.id, s])), [board]);

  useEffect(() => {
    // Sync filters from the URL once on mount (static export: no server-side search params).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setF(readUrl(new Set(board.systems.map((s) => s.id))));
    setPage(Math.max(0, (Number(new URLSearchParams(window.location.search).get("page")) || 1) - 1));
    fetch("/data/rows-index.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setIndex)
      .catch(() => setError(true));
  }, [board]);

  const update = useCallback((patch: Partial<Filters>) => {
    setF((prev) => ({ ...prev, ...patch }));
    setPage(0);
  }, []);

  // Mirror the filters into the URL after React commits them. Writing history inside the state updater runs during
  // render and makes Next's router update mid-render. The first run is skipped: the filters still hold their defaults
  // until the mount effect above has read the URL.
  const urlReady = useRef(false);
  useEffect(() => {
    if (!urlReady.current) {
      urlReady.current = true;
      return;
    }
    writeUrl(f, page);
  }, [f, page]);

  const filtered = useMemo(() => {
    if (!index) return [];
    const jobIdx = f.job ? index.jobs.indexOf(f.job) : -1;
    const srcIdx = f.source ? index.sources.indexOf(f.source) : -1;
    const sysIdx = f.system ? index.systems.indexOf(f.system) : -1;
    return index.rows.filter((r) => {
      if (jobIdx >= 0 && r[1] !== jobIdx) return false;
      if (srcIdx >= 0 && r[2] !== srcIdx) return false;
      if (f.label && (r[3] === 1) !== (f.label === "yes")) return false;
      if (f.text && r[5] !== 0) return false;
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
    }).sort((a, b) => (a[5] === 0 ? 0 : 1) - (b[5] === 0 ? 0 : 1));
  }, [index, f]);

  const activeCount = [f.job, f.source, f.label, f.hard, f.text, f.system].filter(Boolean).length;
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const current = Math.min(page, pages - 1);
  const slice = filtered.slice(current * PAGE, current * PAGE + PAGE);

  const pickCell = (job: JobId, system: string) => {
    update({ job, system, mode: colour === "score" ? "wrong" : colour === "catch" ? "missed" : "blocked", hard: false, label: "" });
    rowsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    rowsRef.current?.focus({ preventScroll: true });
  };

  const sysName = (id: string) => oneLine(sys[id], id);
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

        {/* Phones: the filters fold behind one button, so the rows are on the first screen. */}
        <button
          type="button"
          aria-expanded={filtersOpen}
          aria-controls="row-filters"
          onClick={() => setFiltersOpen((o) => !o)}
          className="inline-flex min-h-11 w-fit items-center gap-2 text-[15px] font-medium text-link sm:hidden"
        >
          Filters
          {activeCount > 0 && <span className="num text-fg">({activeCount} on)</span>}
          <Chevron className={`size-3.5 transition-transform ${filtersOpen ? "-rotate-90" : "rotate-90"}`} />
        </button>
        <div id="row-filters" className={`${filtersOpen ? "flex" : "hidden"} flex-wrap items-end gap-x-8 gap-y-3 border-y border-line py-4 sm:flex`}>
          <Select
            id="f-job"
            label="Use case"
            value={f.job}
            onChange={(v) => update({ job: v as JobId | "" })}
            options={[{ value: "", label: "All use cases" }, ...JOBS.map((j) => ({ value: j.id, label: j.title }))]}
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
          <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 text-[14px] text-fg">
            <input type="checkbox" checked={f.hard} onChange={(e) => update({ hard: e.target.checked })} className="size-5 accent-[var(--accent)]" />
            Most systems got it wrong
          </label>
          <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 text-[14px] text-fg">
            <input type="checkbox" checked={f.text} onChange={(e) => update({ text: e.target.checked })} className="size-5 accent-[var(--accent)]" />
            Only the 100 example rows
          </label>
          {(f.job || f.source || f.label || f.hard || f.text || f.system) && (
            <button type="button" onClick={() => update(EMPTY)} className="min-h-11 text-[14px] text-link underline underline-offset-4 hover:text-link-hover">
              Clear filters
            </button>
          )}
        </div>

        {f.system && (
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 bg-selected px-4 py-3 text-[14px]">
            <span>
              This list shows the {modeText} for <strong className="font-semibold">{sysName(f.system)}</strong>
              {f.job ? ` on ${JOBS.find((j) => j.id === f.job)?.title.toLowerCase()}` : ""}.
            </span>
            <Segmented
              label="Mistake type"
              value={f.mode}
              onChange={(mode) => update({ mode })}
              options={[
                { value: "wrong", label: "All mistakes", short: "All" },
                { value: "missed", label: "Missed harmful", short: "Missed" },
                { value: "blocked", label: "Blocked safe", short: "Blocked safe" },
              ]}
            />
            <button type="button" onClick={() => update({ system: "", mode: "wrong" })} className="inline-flex min-h-11 items-center text-[13px] text-link hover:text-link-hover">
              Show every system
            </button>
          </div>
        )}

        <p className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-muted">
          <span>
            Each row splits the {board.systems.length} systems by what they did: let it through on the left, blocked on the right.
            An orange line under a logo marks a wrong call.
            {f.system ? ` ${sysName(f.system)} has a black ring.` : ""} Hover a logo for its name, or open the row.
          </span>
        </p>

        {error && (
          <p role="alert" className="m-0 border-y border-warn/50 py-3 text-[14px] text-warn">
            The row index did not load. Reload the page. If the error continues, get the rows from Hugging Face.
          </p>
        )}

        {!index && !error && (
          <ul className="m-0 flex list-none flex-col p-0" aria-hidden="true">
            {Array.from({ length: 6 }, (_, i) => (
              <li key={i} className="h-[92px] animate-pulse border-b border-line bg-surface/60" />
            ))}
          </ul>
        )}

        {index && filtered.length === 0 && (
          <div className="border-y border-line py-8 text-[15px] text-fg-2">
            No public rows match these filters. Select a different job or source, or{" "}
            <button type="button" onClick={() => update(EMPTY)} className="text-link underline underline-offset-[3px]">
              clear them
            </button>
            .
          </div>
        )}

        {index && slice.length > 0 && (
          <ol className="m-0 flex list-none flex-col border-t border-line-strong p-0">
            {slice.map((r) => (
              <RowItem key={r[0]} r={r} index={index} sys={sys} sysName={sysName} highlight={f.system} />
            ))}
          </ol>
        )}

        {index && pages > 1 && (
          <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-3 text-[14px] text-muted">
            <span>
              Rows {int(current * PAGE + 1)} to {int(Math.min(filtered.length, current * PAGE + PAGE))} of {int(filtered.length)}
            </span>
            <span className="flex items-center gap-5">
              <button
                type="button"
                disabled={current === 0}
                onClick={() => {
                  setPage(current - 1);
                  rowsRef.current?.scrollIntoView({ block: "start" });
                }}
                className="min-h-11 font-medium text-link underline underline-offset-4 enabled:hover:text-link-hover disabled:text-muted disabled:no-underline"
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
                className="min-h-11 font-medium text-link underline underline-offset-4 enabled:hover:text-link-hover disabled:text-muted disabled:no-underline"
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

function RowItem({
  r,
  index,
  sys,
  sysName,
  highlight,
}: {
  r: RowLite;
  index: RowsIndex;
  sys: Record<string, SystemMeta>;
  sysName: (id: string) => string;
  highlight: string;
}) {
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
    <li className="grid gap-x-8 gap-y-3 border-b border-line py-4 transition-colors hover:bg-surface/70 md:grid-cols-[minmax(0,1fr)_auto]">
      <div className="flex min-w-0 flex-col gap-1.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-muted">
          <Link href={`/data/rows/${id}`} className="mono inline-flex min-h-11 items-center text-[13px] font-medium sm:min-h-6">
            {id}
          </Link>
          <span>{job?.title}</span>
          <span className="mono">{index.sources[srcI]}</span>
          <span className={label === 1 ? "text-warn" : "text-good"}>{label === 1 ? "Should block" : "Should pass"}</span>
        </div>
        {highlight && (() => {
          const d = decisions[index.systems.indexOf(highlight)];
          if (d === undefined || d === ".") return null;
          const did = d === "1" ? "blocked it" : d === "0" ? "let it through" : "failed to answer";
          const ok = !isWrong(d, label);
          return (
            <p className={`m-0 text-[13px] font-medium ${ok ? "text-good" : "text-warn"}`}>
              {sysName(highlight)} {did}
              {ok ? "" : label === 1 ? ", but it should block" : ", but it should pass"}.
            </p>
          );
        })()}
        {withheld ? (
          <p className="m-0 flex flex-wrap items-center gap-x-1.5 text-[14px] text-muted">
            <Lock className="size-3.5 shrink-0" />
            {withheld === 2 ? "Sexual or adult content, not shown here." : "Text not shown here."}
            {SOURCES[index.sources[srcI]] ? (
              <a href={SOURCES[index.sources[srcI]].url} className="inline-flex min-h-11 items-center gap-1 sm:min-h-6">
                View it at {SOURCES[index.sources[srcI]].name} <External className="size-3" />
              </a>
            ) : null}
          </p>
        ) : (
          <Sensitive hide={label === 1} compact>
            {/* The index carries at most 200 characters of each row, so the whole snippet is shown, never clamped. */}
            <p className="m-0 text-[14px] leading-snug text-fg-2 [overflow-wrap:anywhere]">
              {snippet}
              {snippet?.endsWith("…") && (
                <>
                  {" "}
                  <Link href={`/data/rows/${id}`} className="whitespace-nowrap">
                    Full text<span className="sr-only"> of row {id}</span>
                  </Link>
                </>
              )}
            </p>
          </Sensitive>
        )}
      </div>
      <div className="flex flex-col gap-1.5 md:items-end">
        <span className="text-[12px] text-muted">
          <span className="num text-fg">{right}</span> of {answered} right
        </span>
        <Split decisions={decisions} label={label} index={index} sys={sys} sysName={sysName} highlight={highlight} right={right} answered={answered} />
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
  const [phoneJob, setPhoneJob] = useState<JobId>(JOBS[0].id);
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
          <h2 id="heat-h" className="m-0 text-[24px] font-semibold tracking-[-0.02em]">Systems by use case</h2>
          <p className="m-0 max-w-[62ch] text-[14px] text-muted">
            <span className="sm:hidden">Pick a use case, then tap a system to list the {what}.</span>
            <span className="hidden sm:inline">Select a cell to list the {what} for that system and use case.</span>
          </p>
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
      {/* Phones: one use case at a time, systems ranked, instead of an eight-column grid that runs off-screen. */}
      <div className="flex flex-col gap-3 sm:hidden">
        <Select
          id="heat-job"
          label="Use case"
          value={phoneJob}
          onChange={(v) => setPhoneJob(v as JobId)}
          options={JOBS.map((j) => ({ value: j.id, label: j.title }))}
        />
        <ol className="m-0 flex list-none flex-col border-t border-line-strong p-0">
          {board.overall
            .map((o) => ({ o, v: cellValue(lookup[o.system]?.[phoneJob], colour) }))
            .filter((x): x is { o: Score; v: number } => x.v !== null)
            .sort((a, b) => (colour === "fbr" ? a.v - b.v : b.v - a.v))
            .map(({ o, v }) => {
              const m = board.systems.find((s) => s.id === o.system);
              const a = Math.max(0.05, Math.min(1, intensity(v)));
              return (
                <li key={o.system}>
                  <button
                    type="button"
                    onClick={() => onPick(phoneJob, o.system)}
                    aria-label={`${oneLine(m, o.system)}, ${JOB_BY_ID[phoneJob].title}: ${fmt(v)}. List the ${what}.`}
                    className="grid min-h-12 w-full grid-cols-[minmax(0,1fr)_4rem] items-center gap-3 border-b border-line py-2 text-left"
                  >
                    <span className="flex min-w-0 items-center gap-2.5">
                      <SystemMark m={m} />
                      <span className="flex min-w-0 flex-col">
                        <span className="truncate text-[14px] font-semibold text-fg">{m?.name ?? o.system}</span>
                        <span className="truncate text-[12px] text-muted">{m?.provider}</span>
                      </span>
                    </span>
                    <span
                      className="num grid h-9 place-items-center rounded-md text-[14px]"
                      style={{ background: `color-mix(in oklab, ${hue} calc(var(--heat-max) * ${Math.round(a * 100)}%), var(--surface))`, color: "var(--heat-ink)" }}
                    >
                      {fmt(v)}
                    </span>
                  </button>
                </li>
              );
            })}
        </ol>
      </div>
      <div className="-mx-4 hidden overflow-x-auto px-4 sm:mx-0 sm:block sm:px-0">
        <table className="w-full min-w-[880px] border-separate border-spacing-1 text-[13px]">
          <caption className="sr-only">
            {colour === "score" ? "Score" : colour === "catch" ? "Catch rate" : "False-block rate"} for every system on every use case. Each cell is a button that lists the {what}.
          </caption>
          <thead>
            <tr>
              <th scope="col" className="sticky left-0 z-10 bg-bg pb-2 pl-1 text-left text-[12px] font-medium text-muted sm:w-44">System</th>
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
                        <span className="block max-w-[9rem] font-semibold leading-tight text-fg sm:max-w-none">{m?.name ?? o.system}</span>
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
                          aria-label={`${oneLine(m, o.system)}, ${j.title}: ${fmt(v)}. List the ${what}.`}
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
          ? "Balanced accuracy on each use case. 50 is a coin flip. Darker is better."
          : colour === "catch"
            ? "Share of harmful rows that the system blocked. Darker is better."
            : "Share of safe rows that the system blocked. Your users see these as refusals. Darker is worse."}{" "}
        We score personal data per entity type.
      </p>
    </section>
  );
}

/** One row's decisions as a split: systems that let it through on the left of a rule, systems that blocked it on the
 *  right, each by logo, in leaderboard order. A wrong call gets an orange line under its logo. */
function Split({
  decisions,
  label,
  index,
  sys,
  sysName,
  highlight,
  right,
  answered,
}: {
  decisions: string;
  label: 0 | 1;
  index: RowsIndex;
  sys: Record<string, SystemMeta>;
  sysName: (id: string) => string;
  highlight: string;
  right: number;
  answered: number;
}) {
  const all = decisions.split("").map((d, i) => ({ d, s: index.systems[i] }));
  const pass = all.filter((x) => x.d === "0");
  const block = all.filter((x) => x.d === "1");
  const failed = all.filter((x) => x.d === "x");
  const wrongNames = all.filter((x) => x.d !== "." && isWrong(x.d, label)).map((x) => sysName(x.s));
  const mark = ({ d, s }: { d: string; s: string }) => {
    const m = sys[s];
    const wrong = isWrong(d, label);
    return (
      <span
        key={s}
        title={`${sysName(s)}: ${d === "1" ? "blocked" : d === "0" ? "let through" : "no answer"}${wrong ? ", wrong" : ", right"}`}
        className={`grid size-6 place-items-center border-b-2 ${wrong ? "border-warn" : "border-transparent"} ${s === highlight ? "rounded-sm ring-2 ring-fg ring-offset-1 ring-offset-[var(--bg)]" : ""}`}
      >
        {m?.logo ? (
          // eslint-disable-next-line @next/next/no-img-element -- static export, tiny SVGs
          <img src={m.logo} alt="" className="size-4" />
        ) : (
          <span className="text-[9px] font-semibold text-fg-2">{m?.mono}</span>
        )}
      </span>
    );
  };
  return (
    <span
      role="img"
      aria-label={`${right} of ${answered} systems right. ${pass.length} let it through, ${block.length} blocked it${failed.length ? `, ${failed.length} gave no answer` : ""}.${wrongNames.length ? ` Wrong: ${wrongNames.join(", ")}.` : ""}`}
      className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 md:w-[23rem]"
    >
      <span className="flex flex-wrap justify-end gap-0.5">{pass.map(mark)}</span>
      <span className="h-6 w-px bg-line-strong" aria-hidden="true" />
      <span className="flex flex-wrap gap-0.5">
        {block.map(mark)}
        {failed.map(mark)}
      </span>
    </span>
  );
}
