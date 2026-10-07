import { ImageResponse } from "next/og";
import { loadBoard } from "@/lib/data";

export const dynamic = "force-static";
export const alt = "decision-models-as-guardrails: guardrail systems compared on accuracy and cost";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const board = loadBoard();
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#f7f4ef", color: "#14120b", padding: 72 }}>
        <div style={{ display: "flex", fontSize: 28, color: "#645d53" }}>raxIT Labs</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ fontSize: 76, fontWeight: 700, letterSpacing: -2, lineHeight: 1.05 }}>decision-models-as-guardrails</div>
          <div style={{ fontSize: 40, color: "#3b372f" }}>Can a decision model replace your guardrail?</div>
        </div>
        <div style={{ display: "flex", gap: 40, fontSize: 28, color: "#3f5bc8" }}>
          <span>{board.stats.systems} systems</span>
          <span>{board.stats.checks.toLocaleString("en-US")} checks</span>
          <span>accuracy and cost</span>
        </div>
      </div>
    ),
    size,
  );
}
