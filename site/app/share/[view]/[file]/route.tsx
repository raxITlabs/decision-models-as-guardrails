// Share images: /share/<view>/<size>.png for every leaderboard view (overall and each use case) and feed size,
// drawn from the board at build time. The card (title, rows, tiers, footer) comes from lib/share.ts.
import { cloneElement } from "react";
import { ImageResponse } from "next/og";
import { BenchmarksLogo } from "@/components/benchmarks-logo";
import { loadBoard, loadVersions } from "@/lib/data";
import { BRAND, SHARE_SIZES, SHARE_SIZE_IDS, SHARE_VIEWS, isShareView, shareCard, type ShareCard, type ShareRow, type ShareSize } from "@/lib/share";
import { lineageSummaries, supersededBy } from "@/lib/versions";
import { artDataUri, shareFonts } from "../../assets";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return SHARE_VIEWS.flatMap((view) => SHARE_SIZE_IDS.map((size) => ({ view, file: `${size}.png` })));
}

const C = {
  bg: "#f2efea",
  paper: "#f2efea",
  line: "#e3d9cc",
  lineStrong: "#c9bfb3",
  ink: "#14120b",
  fg2: "#33302b",
  muted: "#6b5440",
  accent: "#3457d5",
  rest: "#8a8174",
  onArt: "#f2efea",
  onArtMuted: "rgba(242,239,234,0.78)",
};
const MONO = "Geist Mono";

/** Minimal: the painting carries the brand and the title; the paper carries the ranking, names and scores only.
 *  Royal blue marks the statistically tied top and nothing else. */
const LAYOUT: Record<ShareSize, {
  pad: number; split: boolean; art: number; logoH: number; title: number; sub: number; name: number; rank: number;
  score: number; nameW: number; scoreW: number; small: number; dot: number;
}> = {
  landscape: { pad: 56, split: true, art: 440, logoH: 30, title: 44, sub: 19, name: 25, rank: 17, score: 25, nameW: 300, scoreW: 70, small: 16, dot: 13 },
  square: { pad: 76, split: false, art: 400, logoH: 34, title: 60, sub: 23, name: 28, rank: 18, score: 29, nameW: 380, scoreW: 84, small: 19, dot: 15 },
  portrait: { pad: 76, split: false, art: 470, logoH: 36, title: 64, sub: 24, name: 29, rank: 19, score: 30, nameW: 390, scoreW: 88, small: 19, dot: 16 },
};
type Layout = (typeof LAYOUT)[ShareSize];

function axis(rows: ShareRow[]) {
  if (!rows.length) return { lo: 50, hi: 100 };
  const lo = Math.max(0, 2 * Math.floor((Math.min(...rows.map((r) => r.ciLow)) - 0.5) / 2));
  const hi = Math.min(100, 2 * Math.ceil((Math.max(...rows.map((r) => r.ciHigh)) + 0.5) / 2));
  return { lo, hi: hi - lo < 4 ? Math.min(100, lo + 4) : hi };
}
type Axis = ReturnType<typeof axis>;
const at = (v: number, ax: Axis) => ((Math.min(Math.max(v, ax.lo), ax.hi) - ax.lo) / (ax.hi - ax.lo)) * 100;

function Plot({ row, ax, L }: { row: ShareRow; ax: Axis; L: Layout }) {
  const col = row.tier === 1 ? C.accent : C.rest;
  const bar = Math.max(4, Math.round(L.dot * 0.36));
  const lo = at(row.ciLow, ax);
  const hi = at(row.ciHigh, ax);
  return (
    <div style={{ display: "flex", position: "relative", flexGrow: 1, height: L.dot + 6 }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 1, background: C.line }} />
      <div style={{ position: "absolute", left: `${lo}%`, width: `${Math.max(hi - lo, 0.6)}%`, top: "50%", height: bar, marginTop: -bar / 2, borderRadius: bar, background: col, opacity: 0.25 }} />
      <div style={{ position: "absolute", left: `${at(row.score, ax)}%`, top: "50%", width: L.dot, height: L.dot, marginLeft: -L.dot / 2, marginTop: -L.dot / 2, borderRadius: L.dot, background: col }} />
    </div>
  );
}

function Row({ row, ax, L }: { row: ShareRow; ax: Axis; L: Layout }) {
  return (
    <div style={{ display: "flex", alignItems: "center", flexGrow: 1, flexBasis: 0, gap: 22 }}>
      <div style={{ display: "flex", width: L.rank * 1.3, flexShrink: 0, fontFamily: MONO, fontSize: L.rank, color: C.muted }}>{row.rank}</div>
      <div style={{ display: "flex", flexDirection: "column", width: L.nameW, flexShrink: 0, whiteSpace: "nowrap", overflow: "hidden" }}>
        <div style={{ display: "flex", fontSize: L.name, fontWeight: 500, color: C.ink, letterSpacing: -0.4 }}>{row.name}</div>
        {row.service ? <div style={{ display: "flex", fontSize: L.small, color: C.muted, marginTop: 2 }}>Not a decision model</div> : null}
      </div>
      <Plot row={row} ax={ax} L={L} />
      <div style={{ display: "flex", justifyContent: "flex-end", width: L.scoreW, flexShrink: 0, fontFamily: MONO, fontSize: L.score, fontWeight: 500, color: C.ink, letterSpacing: -0.5 }}>
        {row.score.toFixed(1)}
      </div>
    </div>
  );
}

function Ranking({ card, L }: { card: ShareCard; L: Layout }) {
  const ax = axis(card.rows);
  const off = L.rank * 1.3 + L.nameW + 2 * 22;
  const d = Math.round(L.small * 0.55);
  return (
    <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: L.small, color: C.fg2, marginBottom: 6 }}>
        <div style={{ display: "flex", width: d, height: d, borderRadius: d, background: C.accent }} />
        {card.topTier > 1 ? `The top ${card.topTier} are statistically tied` : "The leader is clear of the rest"}
      </div>
      <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
        {card.rows.map((r) => <Row key={r.system} row={r} ax={ax} L={L} />)}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginLeft: off, marginRight: L.scoreW + 22, fontFamily: MONO, fontSize: L.small, color: C.muted }}>
        <span>{ax.lo}</span>
        <span>{ax.hi}</span>
      </div>
    </div>
  );
}

function Logo({ h, fill }: { h: number; fill: string }) {
  const el = BenchmarksLogo({});
  // viewBox 125.6 x 48.3
  return cloneElement(el, { width: Math.round((h * 125.6) / 48.3), height: h, fill, className: undefined } as Record<string, unknown>);
}

/** The painting with the brand and title over a smoky scrim, the raxIT hero-plate treatment. */
function Art({ card, L, w, h }: { card: ShareCard; L: Layout; w: number | string; h: number | string }) {
  return (
    <div style={{ display: "flex", position: "relative", width: w, height: h, flexShrink: 0, overflow: "hidden" }}>
      {/* eslint-disable-next-line @next/next/no-img-element -- next/og renders <img>, not next/image */}
      <img src={artDataUri()} alt="" style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: L.split ? "62% 50%" : "50% 55%" }} />
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundImage: "linear-gradient(180deg, rgba(16,12,8,0.42) 0%, rgba(16,12,8,0.08) 38%, rgba(16,12,8,0.62) 100%)" }} />
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", position: "relative", width: "100%", height: "100%", padding: L.pad }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Logo h={L.logoH} fill={C.onArt} />
          <div style={{ display: "flex", fontSize: Math.round(L.small * 1.1), fontWeight: 500, color: C.onArt, letterSpacing: -0.1 }}>{BRAND}</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: Math.round(L.sub * 0.45) }}>
          <div style={{ display: "flex", fontSize: L.title, fontWeight: 600, color: C.onArt, letterSpacing: -L.title * 0.035, lineHeight: 1.02 }}>{card.title}</div>
          <div style={{ display: "flex", fontSize: L.sub, color: C.onArtMuted, lineHeight: 1.35 }}>{card.subtitle}</div>
        </div>
      </div>
    </div>
  );
}

function Footer({ card, L }: { card: ShareCard; L: Layout }) {
  const f = card.footer;
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: Math.round(L.small * 0.9), borderTop: `1px solid ${C.line}`, fontSize: L.small, color: C.muted, flexShrink: 0 }}>
      <span style={{ color: C.fg2, fontWeight: 500 }}>{f.site}</span>
      <span>{`Bars: 95% intervals · ${f.checks} · ${f.date}`}</span>
    </div>
  );
}

function Card({ card }: { card: ShareCard }) {
  const L = LAYOUT[card.size];
  const paper = { display: "flex", flexDirection: "column", flexGrow: 1, background: C.paper, padding: L.pad, gap: Math.round(L.pad * 0.5) } as const;
  return (
    <div style={{ display: "flex", flexDirection: L.split ? "row" : "column", width: "100%", height: "100%", background: C.paper, fontFamily: "Inter", color: C.ink }}>
      <Art card={card} L={L} w={L.split ? L.art : "100%"} h={L.split ? "100%" : L.art} />
      <div style={paper}>
        <Ranking card={card} L={L} />
        <Footer card={card} L={L} />
      </div>
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
  return new ImageResponse(<Card card={card} />, {
    width,
    height,
    fonts: shareFonts(),
    headers: { "Cache-Control": "public, max-age=3600" },
  });
}
