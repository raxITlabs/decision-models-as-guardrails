// The link-preview image for every page: the overall share card (/share/overall/landscape.png), the same picture the
// leaderboard's Share button gives. X and LinkedIn cache a preview by its URL, so the query carries a hash of what
// the card shows: a new release, ranking or headline gives a new URL and they fetch the image again.
import "server-only";
import { createHash } from "node:crypto";
import type { Metadata } from "next";
import { loadBoard, loadVersions } from "@/lib/data";
import { SHARE_REV, SHARE_SIZES, shareCard, shareFile } from "@/lib/share";
import { lineageSummaries, supersededBy } from "@/lib/versions";

let cached: { url: string; width: number; height: number; alt: string } | null = null;

export function previewImage() {
  if (!cached) {
    const card = shareCard(loadBoard(), supersededBy(lineageSummaries(loadVersions())), "overall", "landscape");
    const v = createHash("sha256").update(`${SHARE_REV}|${card.alt}`).digest("hex").slice(0, 10);
    const { width, height } = SHARE_SIZES.landscape;
    cached = { url: `${shareFile("overall", "landscape")}?v=${v}`, width, height, alt: card.alt };
  }
  return cached;
}

/** openGraph for a page, with the preview image (Next replaces a parent's openGraph whole, so each page sets it). */
export function pageOpenGraph(url: string): NonNullable<Metadata["openGraph"]> {
  return { url, siteName: "decision-models-as-guardrails", type: "website", images: [previewImage()] };
}

export function pageTwitter(): NonNullable<Metadata["twitter"]> {
  return { card: "summary_large_image", images: [previewImage()] };
}
