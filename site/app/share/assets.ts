// Fonts and logos for the share images, read from disk at build time (no network). Inter and Geist Mono are both
// under the SIL Open Font License (fonts/GeistMono-OFL.txt; Inter uses the same licence).
import "server-only";
import fs from "node:fs";
import path from "node:path";

const SITE = process.cwd();
const FONTS = path.join(SITE, "app", "share", "fonts");

type Font = { name: string; data: ArrayBuffer; weight: 400 | 500 | 600; style: "normal" };
let fonts: Font[] | null = null; // read once per build

const buf = (file: string): ArrayBuffer => {
  const b = fs.readFileSync(path.join(FONTS, file));
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer;
};

export function shareFonts(): Font[] {
  fonts ??= [
    { name: "Inter", data: buf("Inter-Regular.otf"), weight: 400, style: "normal" },
    { name: "Inter", data: buf("Inter-Medium.otf"), weight: 500, style: "normal" },
    { name: "Inter", data: buf("Inter-SemiBold.otf"), weight: 600, style: "normal" },
    { name: "Geist Mono", data: buf("GeistMono-Regular.ttf"), weight: 400, style: "normal" },
    { name: "Geist Mono", data: buf("GeistMono-Medium.ttf"), weight: 500, style: "normal" },
  ];
  return fonts;
}

const svgCache = new Map<string, string | undefined>();

/** A public/ SVG (e.g. "/logos/aws.svg") as a data: URI, `currentColor` set to `ink`. Undefined when missing. */
export function svgDataUri(publicPath: string | undefined, ink = "#14120b"): string | undefined {
  if (!publicPath || !publicPath.endsWith(".svg")) return undefined;
  const key = `${publicPath}|${ink}`;
  if (!svgCache.has(key)) {
    const p = path.join(SITE, "public", publicPath.replace(/^\//, ""));
    let uri: string | undefined;
    if (fs.existsSync(p)) {
      const svg = fs.readFileSync(p, "utf8").replace(/currentColor/g, ink);
      uri = `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
    }
    svgCache.set(key, uri);
  }
  return svgCache.get(key);
}

let art: string | null = null;

/** The hero painting (public/plates/hero-fork, see public/plates/NOTICE.md) as a JPEG data: URI; satori reads no WebP. */
export function artDataUri(): string {
  art ??= `data:image/jpeg;base64,${fs.readFileSync(path.join(SITE, "app", "share", "art", "hero-fork.jpg")).toString("base64")}`;
  return art;
}
