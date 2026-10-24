// Share images: one branded PNG per view (overall or a use case) and size, drawn from the board data at build time
// (app/share/[view]/[file]/route.tsx) and offered by the Share panel (components/share-panel.tsx). Pure, so both sides
// and the tests read the same card. Newest versions only; intervals and tiers on every row, so an image cannot
// overclaim a lead the tests cannot separate.
import { JOBS, JOB_BY_ID, type JobId } from "./jobs";
import type { Board, Hosting } from "./types";

export const SITE_HOST = "dm-as-guardrails.raxitlabs.com";
/** The benchmark's name, written as the site writes it. */
export const BRAND = "decision-models-as-guardrails";
export const SITE_URL = `https://${SITE_HOST}`;

export type ShareView = "overall" | JobId;
export const SHARE_VIEWS: ShareView[] = ["overall", ...JOBS.map((j) => j.id)];

/** Feed sizes: 16:9 for X and LinkedIn link-style posts, 1:1 everywhere, 4:5 for the LinkedIn and Instagram feed.
 *  ``rows``: how many systems fit legibly. */
export const SHARE_SIZES = {
  landscape: { width: 1200, height: 675, rows: 5, label: "Landscape", hint: "16:9 · X, LinkedIn" },
  square: { width: 1080, height: 1080, rows: 6, label: "Square", hint: "1:1 · any feed" },
  portrait: { width: 1080, height: 1350, rows: 8, label: "Portrait", hint: "4:5 · LinkedIn, Instagram" },
} as const;
export type ShareSize = keyof typeof SHARE_SIZES;
export const SHARE_SIZE_IDS = Object.keys(SHARE_SIZES) as ShareSize[];

export interface ShareRow {
  rank: number;
  system: string;
  name: string;
  provider: string;
  hosting: Hosting;
  logo?: string;
  mono: string;
  score: number;
  /** half-width of the 95% interval, as the board's "±" */
  half: number;
  ciLow: number;
  ciHigh: number;
  tier: number;
  /** a guardrail service, not a decision model */
  service: boolean;
}

export interface ShareCard {
  view: ShareView;
  size: ShareSize;
  title: string;
  subtitle: string;
  rows: ShareRow[];
  /** systems ranked below the rows shown */
  more: number;
  /** how many systems share tier 1 (the tests cannot separate them) */
  topTier: number;
  footer: { site: string; checks: string; version: string; date: string; rule: string };
  /** the page a reader should land on, with the view selected */
  url: string;
  alt: string;
}

/** The PNG's path on the site: /share/overall/landscape.png, or landscape@2x.png at twice the pixels (downloads). */
export const shareFile = (view: ShareView, size: ShareSize, scale: 1 | 2 = 1) =>
  `/share/${view}/${size}${scale === 2 ? "@2x" : ""}.png`;
/** The name a downloaded image is saved under: decision-models-as-guardrails-overall-landscape-2026-10-20.png */
export const shareDownloadName = (view: ShareView, size: ShareSize, date: string) => `${BRAND}-${view}-${size}-${date}.png`;
export const shareLink = (view: ShareView) => (view === "overall" ? `${SITE_URL}/#leaderboard` : `${SITE_URL}/?case=${view}#leaderboard`);
export const isShareView = (v: string | null | undefined): v is ShareView => !!v && (SHARE_VIEWS as string[]).includes(v);

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const shortDate = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
};

/** The card for one view and size. ``older``: {earlier version: newest version} (lib/versions supersededBy). */
export function shareCard(board: Board, older: Record<string, string>, view: ShareView, size: ShareSize): ShareCard {
  const sys = Object.fromEntries(board.systems.map((s) => [s.id, s]));
  const scores = [...(view === "overall" ? board.overall : board.jobs[view])]
    .filter((s) => !older[s.system])
    .sort((a, b) => a.rank - b.rank);
  // rank among newest versions, ties sharing a number (as the board shows it)
  const rankOf = (r: number) => 1 + scores.filter((o) => o.rank < r).length;
  const n = SHARE_SIZES[size].rows;
  const rows: ShareRow[] = scores.slice(0, n).map((s) => {
    const m = sys[s.system];
    return {
      rank: rankOf(s.rank), system: s.system, name: m?.label ?? m?.name ?? s.system, provider: m?.provider ?? "",
      hosting: m?.hosting ?? "managed", logo: m?.logo, mono: m?.mono ?? s.system.slice(0, 2), score: s.score,
      half: Math.max(s.score - s.ciLow, s.ciHigh - s.score),
      ciLow: s.ciLow, ciHigh: s.ciHigh, tier: s.tier, service: m?.kind === "service",
    };
  });
  const top = scores.length ? scores[0].tier : 1;
  // The overall image leads with the board's published finding (components/finding.tsx, BedrockFinding).
  const ref = scores.find((s) => sys[s.system]?.kind === "service");
  const decisions = scores.filter((s) => sys[s.system]?.kind === "decision");
  const beat = ref ? decisions.filter((s) => s.score > ref.score).length : 0;
  const title =
    view !== "overall"
      ? JOB_BY_ID[view].title
      : ref
        ? `${beat} of ${decisions.length} decision models beat ${sys[ref.system]?.name ?? "the guardrail service"}`
        : "Overall ranking";
  const subtitle =
    view === "overall"
      ? `Overall ranking, balanced accuracy across ${board.stats.jobs} guardrail use cases`
      : JOB_BY_ID[view].sub;
  const card: ShareCard = {
    view, size, title, subtitle, rows, more: Math.max(0, scores.length - rows.length),
    topTier: scores.filter((s) => s.tier === top).length,
    footer: {
      site: SITE_HOST,
      checks: `${board.stats.checks.toLocaleString("en-US")} checks`,
      version: `v${board.release.version}`,
      date: shortDate(board.release.date),
      rule: `blocked at a probability of ${board.stats.threshold} or more`,
    },
    url: shareLink(view),
    alt: "",
  };
  card.alt = `${BRAND}, ${title}: ${rows.map((r) => `${r.rank}. ${r.name} ${r.score.toFixed(1)}`).join(", ")}. ${card.footer.site}, ${card.footer.date}.`;
  return card;
}
