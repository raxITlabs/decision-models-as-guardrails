"""Charts for the edition 2 results, from ``benchmark/results/edition2-final/leaderboard.json``.

    uv run --with matplotlib python benchmark/runs/e2_final_plots.py

The full run's charts (``e2_full_plots``) for the final document, without latency (owner ruling 22): overall score,
the subtask heatmap (direct and indirect prompt attacks included), catch against false-block rate, score against
cost, the public-versus-unpublished check, and prompt attacks per row tag beside the full-text n-gram baseline.
Writes PNG and SVG to ``benchmark/results/edition2-final/plots/``. No row text or row id is read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e2_sample_plots as P  # noqa: E402
import e2_full_plots as FP  # noqa: E402

P.RES = P.REPO / "benchmark" / "results" / "edition2-final"
P.PLOTS = P.RES / "plots"
P.TAG = "edition 2 test split"
P.SUITE_NAME["prompt_attacks"] = "Prompt attacks"


def score_cost(doc):
    cost = doc["run"]["cost"]
    rank = doc["overall"]["ranking"]
    pts = [((cost.get(e["name"]) or {}).get("usd_per_1000"), e["balanced_accuracy"], e["name"]) for e in rank]
    pts = [p for p in pts if p[0]]
    fig, ax = P.plt.subplots(figsize=(9.6, 5.4))
    ax.set_xscale("log")
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=56, color=P.S1, edgecolor=P.SURFACE, linewidth=2, zorder=3)
    ax.set_xlim(min(p[0] for p in pts) / 1.6, max(p[0] for p in pts) * 4)
    ax.set_ylim(min(p[1] for p in pts) - 2, max(p[1] for p in pts) + 1.5)
    P.label_points(ax, [p[0] for p in pts], [p[1] for p in pts], [P.name(p[2]) for p in pts], fontsize=8)
    ax.set_xlabel("USD per 1,000 checks (log scale)")
    ax.set_ylabel("Overall balanced accuracy x 100")
    ax.xaxis.set_major_locator(P.matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 5)))
    ax.xaxis.set_major_formatter(P.matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}"))
    ax.xaxis.set_minor_formatter(P.matplotlib.ticker.NullFormatter())
    P.title(fig, f"Score vs cost ({P.TAG})",
            "Hosted: measured tokens or text units x list price. VM models: VM up-to-paused time x dated "
            "g2-standard-24 rate, split by run time.")
    P.save(fig, "score-vs-cost")


def attack_tags(doc):
    pa = doc["prompt_attacks"]
    tags = ["injection", "jailbreak", "leakage", "indirect"]
    order = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    order = [s for s in order if s in pa["by_tag"]]
    fig, axs = P.plt.subplots(1, 4, figsize=(13, 0.42 * len(order) + 2.2), sharey=True)
    ys = list(range(len(order)))[::-1]
    for ax, t in zip(axs, tags):
        vals = [pa["by_tag"][s][t]["balanced_accuracy"] for s in order]
        ax.barh(ys, vals, color=P.S1, height=0.6, zorder=2)
        base = pa["ngram_baseline"]["by_tag"].get(t, {}).get("best")
        if base is not None:
            ax.axvline(base, color=P.S2, lw=1.6, zorder=3)
            ax.text(base, len(order) - 0.35, f"n-gram {base:.1f}", color=P.INK2, fontsize=8, ha="center")
        ax.set_xlim(40, 100)
        ax.set_title(t.capitalize(), loc="left", fontsize=10, color=P.INK, fontweight="bold")
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(ys, [P.name(s) for s in order])
    P.title(fig, f"Prompt attacks by row tag, with the full-text n-gram baseline ({P.TAG})",
            "Balanced accuracy x 100 at the fixed rule over test and unpublished rows. Orange line: best word or "
            "character n-gram classifier (grouped CV), a reference, not a system.")
    P.save(fig, "prompt-attacks-by-tag")


def main():
    doc = json.loads((P.RES / "leaderboard.json").read_text(encoding="utf-8"))
    fr = doc["full_run"]
    P.SPLIT_NOTE = f"Edition 2 test split and unpublished slice, {fr['rows_total']:,} rows"
    P.overall_chart(doc)
    P.heatmap(doc)
    P.catch_vs_block(doc)
    score_cost(doc)
    FP.slice_chart(doc)
    attack_tags(doc)
    print(sorted(p.name for p in P.PLOTS.iterdir()))


if __name__ == "__main__":
    main()
