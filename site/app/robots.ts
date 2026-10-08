import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    // Row pages are noindex; crawlers must be allowed to fetch them to see that.
    rules: { userAgent: "*", allow: "/" },
    sitemap: "https://decision-models-as-guardrails.raxitlabs.com/sitemap.xml",
  };
}
