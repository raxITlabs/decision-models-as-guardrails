import posthog from "posthog-js";

// PostHog runs only when a project key is set at build time, so local builds and forks send nothing.
// Events go through /ingest (proxied to PostHog in vercel.json) so ad blockers don't drop them.
const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;

if (key) {
  posthog.init(key, {
    api_host: "/ingest",
    ui_host: "https://us.posthog.com",
    defaults: "2025-05-24",
    capture_exceptions: true,
  });
}
