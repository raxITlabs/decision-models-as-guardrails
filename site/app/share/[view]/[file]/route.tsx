// Share images: /share/<view>/<size>.png for every leaderboard view (overall and each use case) and feed size,
// drawn from the board at build time. The card (title, rows, tiers, footer) comes from lib/share.ts.
import { cloneElement } from "react";
import { ImageResponse } from "next/og";
import { BenchmarksLogo } from "@/components/benchmarks-logo";
import { loadBoard, loadVersions } from "@/lib/data";
import { SHARE_SIZES, SHARE_SIZE_IDS, SHARE_VIEWS, isShareView, shareCard, type ShareCard, type ShareRow, type ShareSize } from "@/lib/share";
import { lineageSummaries, supersededBy } from "@/lib/versions";
import { shareFonts, svgDataUri } from "../../assets";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return SHARE_VIEWS.flatMap((view) => SHARE_SIZE_IDS.map((size) => ({ view, file: `${size}.png` })));
}

const C = {
  bg: "#f2efea",
  line: "#e3d9cc",
  lineStrong: "#c9bfb3",
  ink: "#14120b",
  fg2: "#33302b",
  muted: "#6b5440",
  accent: "#3457d5",
  rest: "#6f675c",
};
const MONO = "Geist Mono";

/** One calm frame: few rows, names only, the tie said once. Royal blue marks the statistically tied top tier and
 *  nothing else. */
const LAYOUT: Record<ShareSize, {
  pad: number; split: boolean; logoH: number; title: number; sub: number; name: number; rank: number; score: number;
  logo: number; nameW: number; scoreW: number; small: number; dot: number; gap: number;
}> = {
  landscape: { pad: 64, split: true, logoH: 32, title: 48, sub: 20, name: 25, rank: 18, score: 26, logo: 28, nameW: 330, scoreW: 74, small: 17, dot: 14, gap: 36 },
  square: { pad: 80, split: false, logoH: 38, title: 64, sub: 24, name: 28, rank: 19, score: 30, logo: 32, nameW: 380, scoreW: 86, small: 20, dot: 16, gap: 56 },
  portrait: { pad: 80, split: false, logoH: 40, title: 68, sub: 25, name: 29, rank: 20, score: 31, logo: 34, nameW: 390, scoreW: 90, small: 20, dot: 17, gap: 64 },
};
type Layout = (typeof LAYOUT)[ShareSize];

/** Axis over the rows shown: whole points, padded, never past 100; labelled at its two ends and middle only. */
function axis(rows: ShareRow[]) {
  if (!rows.length) return { lo: 50, hi: 100 };
  const lo = Math.max(0, 2 * Math.floor((Math.min(...rows.map((r) => r.ciLow)) - 0.5) / 2));
  const hi = Math.min(100, 2 * Math.ceil((Math.max(...rows.map((r) => r.ciHigh)) + 0.5) / 2));
  return { lo, hi: hi - lo < 4 ? Math.min(100, lo + 4) : hi };
}
type Axis = ReturnType<typeof axis>;
const at = (v: number, ax: Axis) => ((Math.min(Math.max(v, ax.lo), ax.hi) - ax.lo) / (ax.hi - ax.lo)) * 100;

function Mark({ row, L }: { row: ShareRow; L: Layout }) {
  const logo = svgDataUri(row.logo);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: L.logo, height: L.logo, flexShrink: 0 }}>
      {logo ? (
        // eslint-disable-next-line @next/next/no-img-element -- next/og renders <img>, not next/image
        <img src={logo} alt="" width={L.logo} height={L.logo} style={{ objectFit: "contain" }} />
      ) : (
        <div style={{ display: "flex", fontSize: Math.round(L.logo * 0.5), fontWeight: 600, color: C.muted }}>{row.mono}</div>
      )}
    </div>
  );
}

function Plot({ row, ax, L }: { row: ShareRow; ax: Axis; L: Layout }) {
  const col = row.tier === 1 ? C.accent : C.rest;
  const bar = Math.max(5, Math.round(L.dot * 0.4));
  const lo = at(row.ciLow, ax);
  const hi = at(row.ciHigh, ax);
  return (
    <div style={{ display: "flex", position: "relative", flexGrow: 1, height: L.dot + 6 }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 1, background: C.line }} />
      <div style={{ position: "absolute", left: `${lo}%`, width: `${Math.max(hi - lo, 0.6)}%`, top: "50%", height: bar, marginTop: -bar / 2, borderRadius: bar, background: col, opacity: 0.28 }} />
      <div style={{ position: "absolute", left: `${at(row.score, ax)}%`, top: "50%", width: L.dot, height: L.dot, marginLeft: -L.dot / 2, marginTop: -L.dot / 2, borderRadius: L.dot, background: col }} />
    </div>
  );
}

function Row({ row, ax, L }: { row: ShareRow; ax: Axis; L: Layout }) {
  const gap = Math.round(L.logo * 0.55);
  return (
    <div style={{ display: "flex", alignItems: "center", flexGrow: 1, flexBasis: 0, gap }}>
      <div style={{ display: "flex", width: L.rank * 1.4, flexShrink: 0, fontFamily: MONO, fontSize: L.rank, color: C.muted }}>{row.rank}</div>
      <Mark row={row} L={L} />
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

function Board({ card, L }: { card: ShareCard; L: Layout }) {
  const ax = axis(card.rows);
  const gap = Math.round(L.logo * 0.55);
  const off = L.rank * 1.4 + L.logo + L.nameW + 3 * gap;
  const mid = Math.round((ax.lo + ax.hi) / 2);
  return (
    <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
      <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
        {card.rows.map((r) => <Row key={r.system} row={r} ax={ax} L={L} />)}
      </div>
      <div style={{ display: "flex", position: "relative", height: L.small + 6, marginTop: 8, marginLeft: off, marginRight: L.scoreW + gap, fontFamily: MONO, fontSize: L.small, color: C.muted }}>
        {[ax.lo, mid, ax.hi].map((t) => (
          <div key={t} style={{ position: "absolute", top: 0, left: `${at(t, ax)}%`, width: 60, marginLeft: -30, display: "flex", justifyContent: "center" }}>{t}</div>
        ))}
      </div>
    </div>
  );
}

/** The one thing a reader must not miss: the top of the board is a statistical tie. */
function Tie({ card, L }: { card: ShareCard; L: Layout }) {
  const d = Math.round(L.small * 0.6);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: L.small, color: C.muted, lineHeight: 1.4 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, color: C.fg2 }}>
        <div style={{ display: "flex", width: d, height: d, borderRadius: d, background: C.accent }} />
        {card.topTier > 1 ? `The top ${card.topTier} are statistically tied` : "The leader is clear of the rest"}
      </div>
      <div style={{ display: "flex" }}>Dot: score. Bar: 95% interval.</div>
    </div>
  );
}

function Logo({ h }: { h: number }) {
  const el = BenchmarksLogo({});
  // viewBox 125.6 x 48.3
  return cloneElement(el, { width: Math.round((h * 125.6) / 48.3), height: h, fill: C.ink, className: undefined } as Record<string, unknown>);
}

function Card({ card }: { card: ShareCard }) {
  const L = LAYOUT[card.size];
  const f = card.footer;
  const title = (
    <div style={{ display: "flex", flexDirection: "column", gap: Math.round(L.sub * 0.5) }}>
      <div style={{ display: "flex", fontSize: L.title, fontWeight: 600, color: C.ink, letterSpacing: -L.title * 0.035, lineHeight: 1.02 }}>{card.title}</div>
      <div style={{ display: "flex", fontSize: L.sub, color: C.muted, lineHeight: 1.35 }}>{card.subtitle}</div>
    </div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", padding: L.pad, background: C.bg, color: C.ink, fontFamily: "Inter" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <Logo h={L.logoH} />
        <div style={{ display: "flex", fontFamily: MONO, fontSize: L.small, color: C.muted }}>{f.date}</div>
      </div>
      {L.split ? (
        <div style={{ display: "flex", flexGrow: 1, gap: 56, marginTop: L.gap, marginBottom: L.gap * 0.75 }}>
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: 270, flexShrink: 0 }}>
            {title}
            <Tie card={card} L={L} />
          </div>
          <Board card={card} L={L} />
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", flexGrow: 1, marginTop: L.gap, marginBottom: L.gap * 0.75, gap: L.gap * 0.8 }}>
          {title}
          <Tie card={card} L={L} />
          <Board card={card} L={L} />
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${C.lineStrong}`, paddingTop: Math.round(L.small * 0.9), fontSize: L.small, color: C.muted, flexShrink: 0 }}>
        <span style={{ color: C.fg2, fontWeight: 500 }}>{f.site}</span>
        <span>{`${f.checks} · ${f.version}`}</span>
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
