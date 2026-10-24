// Share images: /share/<view>/<size>.png for every leaderboard view (overall and each use case) and feed size,
// drawn from the board at build time. The card (title, rows, tiers, footer) comes from lib/share.ts.
import { cloneElement, type ReactElement } from "react";
import { ImageResponse } from "next/og";
import { BenchmarksLogo } from "@/components/benchmarks-logo";
import { loadBoard, loadVersions } from "@/lib/data";
import { SHARE_SIZES, SHARE_SIZE_IDS, SHARE_VIEWS, isShareView, shareCard, type ShareCard, type ShareRow, type ShareSize, type ShareView } from "@/lib/share";
import type { Board as BoardData } from "@/lib/types";
import { lineageSummaries, supersededBy } from "@/lib/versions";
import { shareFonts, svgDataUri } from "../../assets";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return SHARE_VIEWS.flatMap((view) => SHARE_SIZE_IDS.map((size) => ({ view, file: `${size}.png` })));
}

const C = {
  bg: "#f2efea",
  surface: "#faf8f4",
  line: "#e3d9cc",
  lineStrong: "#c9bfb3",
  ink: "#14120b",
  fg2: "#33302b",
  muted: "#6b5440",
  warn: "#a8461a",
};
const TIER = ["#3457d5", "#8a6fb8", "#a8742f", "#6f675c"];
const tierColour = (t: number) => TIER[t - 1] ?? "#9a9184";

/** Type and spacing per size. Names stay at 26px or more at 1080 wide. */
const LAYOUT: Record<ShareSize, {
  pad: number; split: boolean; logoH: number; date: number; title: number; sub: number; name: number; provider: number;
  rank: number; score: number; mark: number; nameW: number; scoreW: number; small: number; dot: number; gapTitle: number;
}> = {
  landscape: { pad: 60, split: true, logoH: 34, date: 18, title: 46, sub: 20, name: 26, provider: 18, rank: 19, score: 27, mark: 38, nameW: 330, scoreW: 76, small: 18, dot: 13, gapTitle: 0 },
  square: { pad: 72, split: false, logoH: 40, date: 21, title: 62, sub: 25, name: 27, provider: 20, rank: 19, score: 28, mark: 46, nameW: 392, scoreW: 84, small: 20, dot: 15, gapTitle: 40 },
  portrait: { pad: 72, split: false, logoH: 42, date: 22, title: 66, sub: 26, name: 28, provider: 20, rank: 20, score: 30, mark: 48, nameW: 400, scoreW: 88, small: 20, dot: 16, gapTitle: 48 },
};
type Layout = (typeof LAYOUT)[ShareSize];
/** {tier: how many newest-version systems the view's board puts in it} */
type TierCounts = Record<number, number>;

function tierCounts(board: BoardData, older: Record<string, string>, view: ShareView): TierCounts {
  const counts: TierCounts = {};
  for (const s of view === "overall" ? board.overall : board.jobs[view]) {
    if (!older[s.system]) counts[s.tier] = (counts[s.tier] ?? 0) + 1;
  }
  return counts;
}

const MONO = "Geist Mono";

/** A shared axis over the rows shown, hugging their intervals: 1, 2, 5 or 10 points a step, never past 100. */
function axis(rows: ShareRow[]) {
  if (!rows.length) return { lo: 50, hi: 100, ticks: [50, 75, 100] };
  const minLow = Math.min(...rows.map((r) => r.ciLow));
  const maxHigh = Math.max(...rows.map((r) => r.ciHigh));
  const step = [1, 2, 5, 10, 20].find((s) => (maxHigh - minLow + 1) / s <= 6) ?? 25;
  const hi = Math.min(100, Math.ceil((maxHigh + 0.4) / step) * step);
  let lo = Math.max(0, Math.floor((minLow - 0.4) / step) * step);
  if (hi - lo < 2 * step) lo = Math.max(0, hi - 2 * step);
  const ticks: number[] = [];
  for (let t = lo; t <= hi + 1e-9; t += step) ticks.push(t);
  return { lo, hi, ticks };
}

function Mark({ row, L }: { row: ShareRow; L: Layout }) {
  const logo = svgDataUri(row.logo);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: L.mark, height: L.mark, flexShrink: 0, borderRadius: 8, border: `1px solid ${C.line}`, background: C.surface }}>
      {logo ? (
        // eslint-disable-next-line @next/next/no-img-element -- next/og renders <img>, not next/image
        <img src={logo} alt="" width={Math.round(L.mark * 0.6)} height={Math.round(L.mark * 0.6)} style={{ objectFit: "contain" }} />
      ) : (
        <div style={{ display: "flex", fontSize: Math.round(L.mark * 0.36), fontWeight: 600, color: C.fg2, letterSpacing: -0.4 }}>{row.mono}</div>
      )}
    </div>
  );
}

/** The provider line, without repeating what the name already says. */
function providerLine(row: ShareRow) {
  const p = row.provider.replace(/\s*·\s*not a decision model/i, "").trim();
  if (p && !row.name.includes(p)) return p;
  return row.hosting === "self-hosted" ? "Self-hosted" : "Managed API";
}

function Plot({ row, ax, L }: { row: ShareRow; ax: ReturnType<typeof axis>; L: Layout }) {
  const pct = (v: number) => `${(Math.min(Math.max(v, ax.lo), ax.hi) - ax.lo) / (ax.hi - ax.lo) * 100}%`;
  const col = tierColour(row.tier);
  const barH = Math.max(6, Math.round(L.dot * 0.5));
  const lowPct = (Math.max(row.ciLow, ax.lo) - ax.lo) / (ax.hi - ax.lo) * 100;
  const highPct = (Math.min(row.ciHigh, ax.hi) - ax.lo) / (ax.hi - ax.lo) * 100;
  return (
    <div style={{ display: "flex", position: "relative", flexGrow: 1, height: L.dot + 8, alignSelf: "center" }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 1, background: C.lineStrong }} />
      {ax.ticks.map((t) => (
        <div key={t} style={{ position: "absolute", left: pct(t), top: "50%", width: 1, height: 7, marginTop: -3, background: C.lineStrong }} />
      ))}
      <div style={{ position: "absolute", left: `${lowPct}%`, width: `${Math.max(highPct - lowPct, 0.6)}%`, top: "50%", height: barH, marginTop: -barH / 2, borderRadius: barH, background: col, opacity: 0.45 }} />
      <div style={{ position: "absolute", left: pct(row.score), top: "50%", width: L.dot, height: L.dot, marginLeft: -L.dot / 2, marginTop: -L.dot / 2, borderRadius: L.dot, background: col, border: `2px solid ${C.bg}` }} />
    </div>
  );
}

function Row({ row, ax, L }: { row: ShareRow; ax: ReturnType<typeof axis>; L: Layout }) {
  return (
    <div style={{ display: "flex", alignItems: "center", flexGrow: 1, flexBasis: 0, gap: Math.round(L.mark * 0.36) }}>
      <div style={{ display: "flex", width: L.rank * 1.6, flexShrink: 0, fontFamily: MONO, fontSize: L.rank, color: C.muted }}>{row.rank}</div>
      <Mark row={row} L={L} />
      <div style={{ display: "flex", flexDirection: "column", width: L.nameW, flexShrink: 0 }}>
        <div style={{ display: "flex", fontSize: L.name, fontWeight: 500, color: C.ink, letterSpacing: -0.4, lineHeight: 1.15, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{row.name}</div>
        <div style={{ display: "flex", gap: 7, fontSize: L.provider, color: C.muted, lineHeight: 1.3, marginTop: 2, whiteSpace: "nowrap" }}>
          <span>{providerLine(row)}</span>
          {row.service ? <span style={{ color: C.warn }}>· not a decision model</span> : null}
        </div>
      </div>
      <Plot row={row} ax={ax} L={L} />
      <div style={{ display: "flex", justifyContent: "flex-end", width: L.scoreW, flexShrink: 0, fontFamily: MONO, fontSize: L.score, fontWeight: 500, color: C.ink, letterSpacing: -0.5 }}>
        {row.score.toFixed(1)}
      </div>
    </div>
  );
}

/** The plot column's offset from the row's left edge, so the axis labels line up under it. */
const plotOffset = (L: Layout) => L.rank * 1.6 + L.mark + L.nameW + 3 * Math.round(L.mark * 0.36);

/** A tier heading, worded as the site's TierHeading: only the dot carries the tier colour. */
function TierRule({ tier, count, shown, L }: { tier: number; count: number; shown: number; L: Layout }) {
  const dot = Math.round(L.small * 0.5);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, height: L.small + 10, flexShrink: 0, fontSize: L.small, whiteSpace: "nowrap" }}>
      <div style={{ display: "flex", width: dot, height: dot, borderRadius: dot, background: tierColour(tier) }} />
      <div style={{ display: "flex", fontWeight: 500, color: C.ink }}>{`Tier ${tier}`}</div>
      <div style={{ display: "flex", color: C.muted }}>{count === 1 ? "on its own" : shown < count ? `the tests cannot separate ${count} systems, ${shown} shown` : `the tests cannot separate these ${count}`}</div>
      <div style={{ display: "flex", flexGrow: 1, height: 1, background: C.line }} />
    </div>
  );
}

function Board({ card, tiers, L, notes = true }: { card: ShareCard; tiers: TierCounts; L: Layout; notes?: boolean }) {
  const ax = axis(card.rows);
  const parts: ReactElement[] = [];
  card.rows.forEach((r, i) => {
    if (i === 0 || r.tier !== card.rows[i - 1].tier) {
      // the tier's size on the whole board, not just the rows shown
      const count = tiers[r.tier] ?? card.rows.filter((o) => o.tier === r.tier).length;
      parts.push(<TierRule key={`t${i}`} tier={r.tier} count={count} shown={card.rows.filter((x) => x.tier === r.tier).length} L={L} />);
    }
    parts.push(<Row key={r.system} row={r} ax={ax} L={L} />);
  });
  const off = plotOffset(L);
  return (
    <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
      <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>{parts}</div>
      <div style={{ display: "flex", position: "relative", height: L.small + 8, marginTop: 6, marginLeft: off, marginRight: L.scoreW + Math.round(L.mark * 0.36) }}>
        {ax.ticks.map((t) => (
          <div
            key={t}
            style={{ position: "absolute", top: 0, left: `${((t - ax.lo) / (ax.hi - ax.lo)) * 100}%`, width: 64, marginLeft: -32, display: "flex", justifyContent: "center", fontFamily: MONO, fontSize: L.small, color: C.muted }}
          >
            {t}
          </div>
        ))}
      </div>
      {notes ? <Notes card={card} L={L} row /> : null}
    </div>
  );
}

function Notes({ card, L, row }: { card: ShareCard; L: Layout; row?: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: row ? "row" : "column", justifyContent: "space-between", gap: 6, marginTop: row ? 10 : 0, fontSize: L.small, color: C.muted }}>
      <span>Dot: balanced accuracy. Bar: 95% interval.</span>
      <span>{card.more > 0 ? `+${card.more} more on the full board` : "Every system on the board"}</span>
    </div>
  );
}

function Logo({ h }: { h: number }) {
  const el = BenchmarksLogo({});
  // viewBox 125.6 x 48.3
  return cloneElement(el, { width: Math.round((h * 125.6) / 48.3), height: h, fill: C.ink, className: undefined } as Record<string, unknown>);
}

function Footer({ card, L }: { card: ShareCard; L: Layout }) {
  const f = card.footer;
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${C.lineStrong}`, paddingTop: Math.round(L.small * 0.9), fontSize: L.small, color: C.muted, flexShrink: 0 }}>
      <span style={{ color: C.fg2, fontWeight: 500 }}>{f.site}</span>
      <span>{`${f.checks} · ${f.version} · ${f.rule}`}</span>
    </div>
  );
}

function Header({ card, L }: { card: ShareCard; L: Layout }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
      <Logo h={L.logoH} />
      <div style={{ display: "flex", fontFamily: MONO, fontSize: L.date, color: C.muted }}>{card.footer.date}</div>
    </div>
  );
}

function Title({ card, L }: { card: ShareCard; L: Layout }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: Math.round(L.sub * 0.6), flexShrink: 0 }}>
      <div style={{ display: "flex", fontSize: L.title, fontWeight: 600, color: C.ink, letterSpacing: -L.title * 0.035, lineHeight: 1.02 }}>{card.title}</div>
      <div style={{ display: "flex", fontSize: L.sub, color: C.muted, lineHeight: 1.35 }}>{card.subtitle}</div>
    </div>
  );
}

function Card({ card, tiers }: { card: ShareCard; tiers: TierCounts }) {
  const L = LAYOUT[card.size];
  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", padding: L.pad, background: C.bg, color: C.ink, fontFamily: "Inter" }}>
      <Header card={card} L={L} />
      {L.split ? (
        <div style={{ display: "flex", flexGrow: 1, gap: 44, marginTop: 30, marginBottom: 22 }}>
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: 250, flexShrink: 0, paddingTop: 6 }}>
            <Title card={card} L={L} />
            <Notes card={card} L={L} />
          </div>
          <Board card={card} tiers={tiers} L={L} notes={false} />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", flexGrow: 1, marginTop: L.gapTitle, marginBottom: 30, gap: L.gapTitle }}>
          <Title card={card} L={L} />
          <Board card={card} tiers={tiers} L={L} />
        </div>
      )}
      <Footer card={card} L={L} />
    </div>
  );
}

export async function GET(_req: Request, ctx: RouteContext<"/share/[view]/[file]">) {
  const { view, file } = await ctx.params;
  const size = file.replace(/\.png$/, "") as ShareSize;
  if (!isShareView(view) || !file.endsWith(".png") || !(size in SHARE_SIZES)) return new Response("Not found", { status: 404 });
  const board = loadBoard();
  const older = supersededBy(lineageSummaries(loadVersions()));
  const card = shareCard(board, older, view, size);
  const { width, height } = SHARE_SIZES[size];
  return new ImageResponse(<Card card={card} tiers={tierCounts(board, older, view)} />, {
    width,
    height,
    fonts: shareFonts(),
    headers: { "Cache-Control": "public, max-age=3600" },
  });
}
