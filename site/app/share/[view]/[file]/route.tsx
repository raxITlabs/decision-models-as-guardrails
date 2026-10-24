// Share images: /share/<view>/<size>.png for every leaderboard view (overall and each use case) and feed size,
// drawn from the board at build time. The card (title, rows, tiers, footer) comes from lib/share.ts.
import { cloneElement } from "react";
import { ImageResponse } from "next/og";
import { BenchmarksLogo } from "@/components/benchmarks-logo";
import { loadBoard, loadVersions } from "@/lib/data";
import { BRAND, SHARE_SIZES, SHARE_SIZE_IDS, SHARE_VIEWS, isShareView, shareCard, type ShareCard, type ShareRow, type ShareSize, type ShareView } from "@/lib/share";
import { lineageSummaries, supersededBy } from "@/lib/versions";
import { artDataUri, shareFonts } from "../../assets";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return SHARE_VIEWS.flatMap((view) => SHARE_SIZE_IDS.flatMap((size) => [`${size}.png`, `${size}@2x.png`].map((file) => ({ view, file }))));
}

const C = {
  paper: "#f2efea",
  line: "#e3d9cc",
  ink: "#14120b",
  fg2: "#33302b",
  muted: "#6b5440",
  accent: "#3457d5",
  rest: "#8a8174",
  onArt: "#f2efea",
  onArtMuted: "rgba(242,239,234,0.8)",
};
const MONO = "Geist Mono";
/** The benchmark's name as an eyebrow over the title: plain words, no hyphens, spaced capitals. */
const BRAND_CAPS = BRAND.replace(/-/g, " ").toUpperCase();

/** Minimal: the painting carries the brand and the title; the paper carries names, scores and intervals. The tied
 *  top is drawn as one group (a royal-blue rule and a faint band), so the image cannot read as a single winner. */
const LAYOUT: Record<ShareSize, {
  pad: number; split: boolean; art: number; mark: number; brand: number; title: number; sub: number; name: number;
  score: number; half: number; nameW: number; scoreW: number; small: number; dot: number; rowGap: number;
}> = {
  landscape: { pad: 52, split: true, art: 450, mark: 46, brand: 13, title: 38, sub: 18, name: 24, score: 25, half: 15, nameW: 300, scoreW: 118, small: 16, dot: 13, rowGap: 0 },
  square: { pad: 72, split: false, art: 410, mark: 52, brand: 15, title: 52, sub: 22, name: 28, score: 29, half: 17, nameW: 370, scoreW: 132, small: 19, dot: 15, rowGap: 0 },
  portrait: { pad: 72, split: false, art: 500, mark: 56, brand: 16, title: 56, sub: 23, name: 29, score: 30, half: 18, nameW: 380, scoreW: 138, small: 19, dot: 16, rowGap: 0 },
};
type Layout = (typeof LAYOUT)[ShareSize];
const RULE = 4; // the tie rule's width; every row keeps the same inset so names line up

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
      <div style={{ position: "absolute", left: `${lo}%`, width: `${Math.max(hi - lo, 0.6)}%`, top: "50%", height: bar, marginTop: -bar / 2, borderRadius: bar, background: col, opacity: 0.28 }} />
      <div style={{ position: "absolute", left: `${at(row.score, ax)}%`, top: "50%", width: L.dot, height: L.dot, marginLeft: -L.dot / 2, marginTop: -L.dot / 2, borderRadius: L.dot, background: col }} />
    </div>
  );
}

function Row({ row, ax, L }: { row: ShareRow; ax: Axis; L: Layout }) {
  return (
    <div style={{ display: "flex", alignItems: "center", flexGrow: 1, flexBasis: 0, gap: 24 }}>
      <div style={{ display: "flex", flexDirection: "column", width: L.nameW, flexShrink: 0, whiteSpace: "nowrap", overflow: "hidden" }}>
        <div style={{ display: "flex", fontSize: L.name, fontWeight: 500, color: C.ink, letterSpacing: -0.4 }}>{row.name}</div>
        {row.service ? <div style={{ display: "flex", fontSize: L.small, color: C.muted, marginTop: 2 }}>Not a decision model</div> : null}
      </div>
      <Plot row={row} ax={ax} L={L} />
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "flex-end", gap: 6, width: L.scoreW, flexShrink: 0, fontFamily: MONO, color: C.ink }}>
        <span style={{ fontSize: L.score, fontWeight: 500, letterSpacing: -0.5 }}>{row.score.toFixed(1)}</span>
        <span style={{ fontSize: L.half, color: C.muted }}>{`±${row.half.toFixed(1)}`}</span>
      </div>
    </div>
  );
}

function Ranking({ card, L }: { card: ShareCard; L: Layout }) {
  const ax = axis(card.rows);
  const tied = card.rows.filter((r) => r.tier === 1);
  const rest = card.rows.filter((r) => r.tier !== 1);
  const inset = RULE + 18;
  const plotLeft = inset + L.nameW + 24;
  return (
    <div style={{ display: "flex", flexDirection: "column", flexGrow: 1 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: L.small, marginBottom: 8, marginLeft: inset, marginRight: 12 }}>
        <span style={{ color: C.accent, fontWeight: 500 }}>{tied.length > 1 ? `Statistically tied at the top: ${card.topTier}` : "The leader is clear of the rest"}</span>
        <span style={{ color: C.muted }}>Bars: 95% intervals</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", flexGrow: tied.length, flexBasis: 0, borderLeft: `${RULE}px solid ${C.accent}`, paddingLeft: 18, paddingRight: 12 }}>
        {tied.map((r) => <Row key={r.system} row={r} ax={ax} L={L} />)}
      </div>
      {rest.length ? (
        <div style={{ display: "flex", flexDirection: "column", flexGrow: rest.length, flexBasis: 0, borderLeft: `${RULE}px solid transparent`, paddingLeft: 18, paddingRight: 12 }}>
          {rest.map((r) => <Row key={r.system} row={r} ax={ax} L={L} />)}
        </div>
      ) : null}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, marginLeft: plotLeft, marginRight: L.scoreW + 24 + 12, fontFamily: MONO, fontSize: L.small, color: C.muted }}>
        <span>{ax.lo}</span>
        <span>{ax.hi}</span>
      </div>
    </div>
  );
}

/** The raxIT Benchmarks logo (components/benchmarks-logo.tsx), viewBox 125.6 x 48.3. */
function Mark({ h, fill }: { h: number; fill: string }) {
  const el = BenchmarksLogo({});
  return cloneElement(el, { width: Math.round((h * 125.6) / 48.3), height: h, fill, className: undefined } as Record<string, unknown>);
}

/** The painting under a smoky scrim, the raxIT hero-plate treatment. Drawn at the output's own pixels (satori does
 *  not scale images under a CSS transform), so a 2x image gets a sharp painting too. */
function Painting({ view, split }: { view: ShareView; split: boolean }) {
  return (
    <div style={{ display: "flex", position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}>
      {/* eslint-disable-next-line @next/next/no-img-element -- next/og renders <img>, not next/image */}
      <img src={artDataUri(view)} alt="" style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: split ? "60% 50%" : "50% 58%" }} />
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, backgroundImage: "linear-gradient(180deg, rgba(16,12,8,0.5) 0%, rgba(16,12,8,0.06) 36%, rgba(16,12,8,0.7) 100%)" }} />
    </div>
  );
}

/** The art panel: the painting (unless drawn underneath already) with the brand and title over it. */
function Art({ card, L, w, h, bare = false }: { card: ShareCard; L: Layout; w: number | string; h: number | string; bare?: boolean }) {
  return (
    <div style={{ display: "flex", position: "relative", width: w, height: h, flexShrink: 0, overflow: "hidden" }}>
      {bare ? null : <Painting view={card.view} split={L.split} />}
      <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", position: "relative", width: "100%", height: "100%", padding: L.pad }}>
        {bare ? <div style={{ display: "flex", height: L.mark }} /> : <Mark h={L.mark} fill={C.onArt} />}
        <div style={{ display: "flex", flexDirection: "column", gap: Math.round(L.sub * 0.5) }}>
          <div style={{ display: "flex", fontSize: L.brand, fontWeight: 500, color: C.onArtMuted, letterSpacing: L.brand * 0.2, marginBottom: Math.round(L.sub * 0.35) }}>
            {BRAND_CAPS}
          </div>
          <div style={{ display: "flex", fontSize: L.title, fontWeight: 600, color: C.onArt, letterSpacing: -L.title * 0.03, lineHeight: 1.06 }}>{card.title}</div>
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
      <span>
        Source: <span style={{ color: C.fg2, fontWeight: 500, marginLeft: 6 }}>{f.site}</span>
      </span>
      <span>{`${f.checks} · ${f.date}`}</span>
    </div>
  );
}

function Card({ card, bare = false }: { card: ShareCard; bare?: boolean }) {
  const L = LAYOUT[card.size];
  return (
    <div style={{ display: "flex", flexDirection: L.split ? "row" : "column", width: "100%", height: "100%", background: bare ? "transparent" : C.paper, fontFamily: "Inter", color: C.ink }}>
      <Art card={card} L={L} w={L.split ? L.art : "100%"} h={L.split ? "100%" : L.art} bare={bare} />
      <div style={{ display: "flex", flexDirection: "column", flexGrow: 1, padding: L.pad, paddingTop: Math.round(L.pad * (L.split ? 1 : 0.8)), gap: Math.round(L.pad * 0.45) }}>
        <Ranking card={card} L={L} />
        <Footer card={card} L={L} />
      </div>
    </div>
  );
}

/** The card at ``scale`` times its pixels: the layout is drawn once at 1x and scaled, so 2x is the same image, sharper. */
function Scaled({ card, scale, width, height }: { card: ShareCard; scale: number; width: number; height: number }) {
  if (scale === 1) return <Card card={card} />;
  const L = LAYOUT[card.size];
  return (
    <div style={{ display: "flex", position: "relative", width: width * scale, height: height * scale, background: C.paper }}>
      <div style={{ display: "flex", position: "absolute", top: 0, left: 0, width: L.split ? L.art * scale : width * scale, height: L.split ? height * scale : L.art * scale, overflow: "hidden" }}>
        <Painting view={card.view} split={L.split} />
      </div>
      <div style={{ display: "flex", position: "absolute", top: 0, left: 0, width, height, transform: `scale(${scale})`, transformOrigin: "top left" }}>
        <Card card={card} bare />
      </div>
      <div style={{ display: "flex", position: "absolute", top: L.pad * scale, left: L.pad * scale }}>
        <Mark h={L.mark * scale} fill={C.onArt} />
      </div>
    </div>
  );
}

export async function GET(_req: Request, ctx: RouteContext<"/share/[view]/[file]">) {
  const { view, file } = await ctx.params;
  const m = /^([a-z]+)(@2x)?\.png$/.exec(file);
  const size = m?.[1] as ShareSize | undefined;
  if (!isShareView(view) || !m || !size || !(size in SHARE_SIZES)) return new Response("Not found", { status: 404 });
  const scale = m[2] ? 2 : 1;
  const board = loadBoard();
  const older = supersededBy(lineageSummaries(loadVersions()));
  const card = shareCard(board, older, view, size);
  const { width, height } = SHARE_SIZES[size];
  return new ImageResponse(<Scaled card={card} scale={scale} width={width} height={height} />, {
    width: width * scale,
    height: height * scale,
    fonts: shareFonts(),
    headers: { "Cache-Control": "public, max-age=3600" },
  });
}
