import type { Metadata, Viewport } from "next";
import { pageOpenGraph, pageTwitter } from "@/lib/og";
import { Geist_Mono, Inter } from "next/font/google";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { loadBoard } from "@/lib/data";
import { isClassic } from "@/lib/kind";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

// Counted from the board, so the description never goes stale: decision models and classic guardrails (safety
// classifiers and guardrail services) separately, since only the first answer with a probability.
const systems = loadBoard().systems;
const classic = systems.filter((s) => isClassic(s)).length;
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export const metadata: Metadata = {
  metadataBase: new URL("https://dm-as-guardrails.raxitlabs.com"),
  openGraph: pageOpenGraph("/"),
  twitter: pageTwitter(),
  title: { default: "decision-models-as-guardrails", template: "%s · decision-models-as-guardrails" },
  description: `Can a decision model replace your guardrail? raxIT Labs runs ${plural(systems.length - classic, "decision model", "decision models")}${classic ? ` and ${plural(classic, "classic guardrail", "classic guardrails")}` : ""} on the same guardrail checks and compares them on accuracy and cost.`,
};

// Matches --bg in globals.css; the site has one light theme.
export const viewport: Viewport = { themeColor: "#f2efea", colorScheme: "light" };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable} antialiased`}>
      <body className="flex min-h-dvh flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-ink"
        >
          Skip to content
        </a>
        <SiteHeader />
        <main id="main" className="flex-1">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
