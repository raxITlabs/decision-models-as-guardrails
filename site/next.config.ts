import type { NextConfig } from "next";

// Static export: every page is prerendered at build time, so Vercel or any static host can serve `out/`.
const nextConfig: NextConfig = {
  output: "export",
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
