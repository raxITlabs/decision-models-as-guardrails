"""Charts for the edition 2 full run, from ``benchmark/results/edition2-full/leaderboard.json``.

    uv run --with matplotlib python benchmark/runs/e2_full_plots.py

The dev-split sample's charts (``e2_sample_plots``) pointed at the full run's folder, plus ``unpublished-slice``: each
system's overall score on the public test rows against the unpublished slice (owner ruling 15, a contamination
check). Writes PNG and SVG to ``benchmark/results/edition2-full/plots/``. No row text or row id is read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_sample_plots as P  # noqa: E402

P.RES = P.REPO / "benchmark" / "results" / "edition2-full"
P.PLOTS = P.RES / "plots"
P.TAG = "edition 2 test split"


def slice_chart(doc):
    v = doc["unpublished_slice_view"]
    order = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    rows = [(s, (v["public"].get(s) or {}).get("overall") or {}, (v["unpublished"].get(s) or {}).get("overall") or {})
            for s in order]
    rows = [r for r in rows if r[1].get("balanced_accuracy") is not None and r[2].get("balanced_accuracy") is not None]
    fig, ax = P.plt.subplots(figsize=(9.6, 0.45 * len(rows) + 1.9))
    ys = list(range(len(rows)))[::-1]
    for y, (s, a, b) in zip(ys, rows):
        pa, pb = a["balanced_accuracy"], b["balanced_accuracy"]
        ax.plot([pa, pb], [y + 0.13, y - 0.13], color=P.AXIS, lw=1, zorder=1)
        ax.scatter([pa], [y + 0.13], s=56, color=P.S1, edgecolor=P.SURFACE, linewidth=2, zorder=3,
                   label=f"Public test rows ({v['rows']['public']:,})" if y == ys[0] else None)
        ax.scatter([pb], [y - 0.13], s=56, color=P.S2, edgecolor=P.SURFACE, linewidth=2, zorder=3,
                   label=f"Unpublished slice ({v['rows']['unpublished']:,})" if y == ys[0] else None)
        ax.text(max(pa, pb) + 0.5, y, f"{pb - pa:+.1f}", va="center", fontsize=9, color=P.INK)
    ax.set_yticks(ys, [P.name(r[0]) for r in rows])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Overall balanced accuracy x 100 (diagnostic re-score of each slice, never ranked)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5, labelcolor=P.INK2)
    P.title(fig, f"Public test rows vs the unpublished slice ({P.TAG})",
            "A system much better on public rows than on the unpublished slice may have seen them. Label: unpublished "
            "minus public, in points.")
    P.save(fig, "unpublished-slice")


def main():
    doc = json.loads((P.RES / "leaderboard.json").read_text(encoding="utf-8"))
    fr = doc["full_run"]
    P.SPLIT_NOTE = f"Edition 2 test split and unpublished slice, {fr['rows_total']:,} rows"
    P.overall_chart(doc)
    P.heatmap(doc)
    P.catch_vs_block(doc)
    P.score_cost_latency(doc)
    slice_chart(doc)
    print(sorted(p.name for p in P.PLOTS.iterdir()))


if __name__ == "__main__":
    main()
