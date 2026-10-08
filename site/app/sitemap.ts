import type { MetadataRoute } from "next";
import { loadBoard } from "@/lib/data";

export const dynamic = "force-static";

const SITE = "https://decision-models-as-guardrails.raxitlabs.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date(loadBoard().release.date);
  return ["/", "/reproduce", "/data", "/changelog"].map((p) => ({ url: `${SITE}${p}`, lastModified }));
}
