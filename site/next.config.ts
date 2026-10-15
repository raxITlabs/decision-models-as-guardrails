import type { NextConfig } from "next";

// Static export: every page is prerendered at build time, so Vercel or any static host can serve `out/`.
const nextConfig: NextConfig = {
  output: "export",
  // posthog-js posts to /ingest/e/ and /ingest/flags/; vercel.json strips trailing slashes everywhere else.
  skipTrailingSlashRedirect: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
