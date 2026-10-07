"""Charts for the published results, from ``benchmark/results/final/leaderboard.json``.

    uv run --with matplotlib python benchmark/runs/e2_final_plots.py

Writes PNG and SVG to ``benchmark/results/final/plots/``: overall score with intervals and tiers, the subtask heatmap,
catch against false-block rate per suite, score against cost, the public-versus-unpublished check, and prompt attacks
per row tag beside the full-text n-gram baseline. No latency (the leaderboard compares accuracy and cost). Colors are
the dataviz reference palette (light surface); text uses ink tokens, never the series color. No row text or row id is
read.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RES = REPO / "benchmark" / "results" / "final"
PLOTS = RES / "plots"
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S1, S2 = "#2a78d6", "#eb6834"   # categorical slots 1 and 2 (validated: adjacent CVD dE 24.7, normal 33.6)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]   # blue 100..700
SUITES = ["content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_info", "grounding"]
SUITE_NAME = {"content": "Content", "prompt_attacks": "Prompt attacks", "denied_topics": "Denied topics",
              "word_filters": "Word filters (profanity)", "sensitive_info": "Sensitive info (PII)",
              "grounding": "Grounding"}
SHORT = {"jev-1.13.0": "Jev 1.13.0", "clef": "Clef", "clef-flash": "Clef-flash", "pplx-decider-v1-27b": "pplx-decider",
         "kev-0-8b": "Kev-0.8B", "kev-4b": "Kev-4B", "kev-9b": "Kev-9B", "open-jev-2b": "Open-Jev-2B", "laya": "Laya",
         "strands-decider-2b": "Strands 2B", "bedrock-guardrails": "Bedrock", "gpt-6-luna": "gpt-6-luna"}
TAG = "test split"
SPLIT_NOTE = "Test split and unpublished slice"   # main() adds the row count

plt.rcParams.update({"font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "font.size": 10,
                     "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2,
                     "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
                     "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none"})


def name(s):
    return SHORT.get(s, s)


def title(fig, main, sub):
    """Title and subtitle at fixed distances (inches) from the top, and the plot area pushed below them."""
    h = fig.get_figheight()
    fig.text(0.01, 1 - 0.22 / h, main, ha="left", va="top", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.01, 1 - 0.50 / h, sub, ha="left", va="top", fontsize=9, color=INK2)
    fig.subplots_adjust(top=1 - 1.05 / h)


def save(fig, stem):
    PLOTS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(PLOTS / f"{stem}.{ext}", dpi=160 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)


def repel(pts, widths, h=0.045, iters=400):
    """Label anchors (axes fractions) for dots at ``pts`` (axes fractions): start just right of each dot, then push
    overlapping label boxes (left-aligned, ``widths`` wide, ``h`` tall) apart vertically until none overlap."""
    pos = [[x + 0.018, y] for x, y in pts]
    for _ in range(iters):
        moved = False
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                (xi, yi), (xj, yj) = pos[i], pos[j]
                if xi < xj + widths[j] and xj < xi + widths[i] and abs(yi - yj) < h:
                    d = (h - abs(yi - yj)) / 2 + 0.002
                    up = i if (yi, -i) >= (yj, -j) else j
                    dn = j if up == i else i
                    pos[up][1] += d
                    pos[dn][1] -= d
                    moved = True
        for q in pos:   # labels stay inside the panel
            q[1] = min(0.97, max(0.03, q[1]))
        for i in range(len(pos)):   # a label never sits on another dot
            for j, (dx, dy) in enumerate(pts):
                if j != i and pos[i][0] - 0.004 < dx + 0.012 and dx - 0.012 < pos[i][0] + widths[i] \
                        and abs(pos[i][1] - dy) < h * 0.7:
                    pos[i][1] += (h * 0.7 - abs(pos[i][1] - dy) + 0.002) * (1 if pos[i][1] >= dy else -1)
                    moved = True
        if not moved:
            break
    return pos


def label_points(ax, xs, ys, labels, fontsize=8, char_w=0.0115, log_x=False):
    """Direct labels beside dots, repelled in axes-fraction space, with a hairline leader when a label moved."""
    to_ax = ax.transAxes.inverted().transform
    disp = ax.transData.transform
    pts = [tuple(to_ax(disp((x, y)))) for x, y in zip(xs, ys)]
    pos = repel(pts, [char_w * len(t) * fontsize / 8 + 0.01 for t in labels])
    for (px, py), (lx, ly), t in zip(pts, pos, labels):
        moved = abs(ly - py) > 0.01
        ax.annotate(t, (px, py), (lx, ly), xycoords="axes fraction", textcoords="axes fraction", fontsize=fontsize,
                    color=INK2, va="center", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.6, shrinkA=0, shrinkB=4) if moved else None)


def _limits(vals, lo_floor, hi_ceil, pad, min_span=0.3):
    """Axis range around ``vals`` with padding, at least ``min_span`` wide (so small gaps are not magnified),
    shifted to stay inside [lo_floor, hi_ceil]."""
    lo, hi = min(vals), max(vals)
    span = hi - lo
    lo, hi = lo - pad * span, hi + pad * span
    if hi - lo < min_span:
        mid = (lo + hi) / 2
        lo, hi = mid - min_span / 2, mid + min_span / 2
    if lo < lo_floor:
        lo, hi = lo_floor, hi + (lo_floor - lo)
    if hi > hi_ceil:
        lo, hi = max(lo_floor, lo - (hi - hi_ceil)), hi_ceil
    return lo, hi


def overall_chart(doc):
    rank = doc["overall"]["ranking"]
    unr = doc["overall"].get("unranked", [])
    n = len(rank)
    fig, ax = plt.subplots(figsize=(8.6, 0.42 * (n + len(unr)) + 1.8))
    ys = list(range(n))[::-1]
    for y, e in zip(ys, rank):
        lo, hi = e["ci"]["low"], e["ci"]["high"]
        ax.plot([lo, hi], [y, y], color=S1, lw=2, solid_capstyle="round", zorder=2)
        ax.scatter([e["balanced_accuracy"]], [y], s=64, color=S1, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(hi + 0.4, y, f"{e['balanced_accuracy']:.1f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(ys, [name(e["name"]) for e in rank])
    lo_all = min(e["ci"]["low"] for e in rank)
    ax.set_xlim(math.floor(lo_all / 5) * 5, 100)
    ax.set_xlabel("Overall balanced accuracy x 100 (equal suite weights), 95% bootstrap interval")
    ax.grid(axis="y", visible=False)
    tx = ax.get_xlim()[1] + 0.5
    ax.text(tx, n - 0.4, "Tier", fontsize=9, color=INK2, fontweight="bold", va="bottom")
    prev = None
    for y, e in zip(ys, rank):
        ax.text(tx, y, str(e["tier"]), va="center", fontsize=9, color=INK)
        if prev is not None and e["tier"] != prev:
            ax.axhline(y + 0.5, color=AXIS, lw=0.8, zorder=1)
        prev = e["tier"]
    if unr:
        ax.text(ax.get_xlim()[0], -1.0, "Not ranked: " + "; ".join(f"{name(e['name'])} ({e.get('reason', '')[:60]})"
                                                                for e in unr), fontsize=8, color=INK2, va="top")
    title(fig, f"Overall score per system ({TAG})",
          f"{SPLIT_NOTE}, fixed 0.5 rule. Tiers: Holm-adjusted paired tests vs the tier "
          "leader.")
    save(fig, "overall")


def heatmap(doc):
    order = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    cols = [k for k in ["content/request", "content/reply", "prompt_attacks/direct", "prompt_attacks/indirect",
                        "denied_topics/topic",
                        "word_filters/profanity", "sensitive_info/entity_detection", "grounding/grounding"]
            if k in doc["subtasks"]]
    vals = {}
    for k in cols:
        for e in doc["subtasks"][k].get("ranking", []):
            vals[(e["name"], k)] = e["balanced_accuracy"]
    words = doc["sanity_checks"]["checks"].get("word_filters/word", {}).get("systems", {})
    cmap = LinearSegmentedColormap.from_list("blue", SEQ)
    vmin, vmax = 50, 100
    fig, ax = plt.subplots(figsize=(10.5, 0.5 * len(order) + 2.4))
    ax.grid(False)
    names = {"content/request": "Content\nrequest", "content/reply": "Content\nreply",
             "prompt_attacks/direct": "Prompt attacks\ndirect",
             "prompt_attacks/indirect": "Prompt attacks\nindirect", "denied_topics/topic": "Denied\ntopics",
             "word_filters/profanity": "Profanity", "sensitive_info/entity_detection": "PII (entity\nmean)",
             "grounding/grounding": "Grounding"}
    labels = [names[k] for k in cols]
    for i, sy in enumerate(order):
        for j, k in enumerate(cols + ["words"]):
            if k == "words":
                w = words.get(sy) or {}
                txt = f"{w.get('result') or 'n/a'}\n{w['balanced_accuracy']:.0f}" if w.get("balanced_accuracy") is not None else "n/a"
                ax.add_patch(plt.Rectangle((j - 0.48, i - 0.46), 0.96, 0.92, facecolor=SURFACE, edgecolor=AXIS, lw=0.8))
                ax.text(j, i, txt, ha="center", va="center", fontsize=8, color=INK2)
                continue
            v = vals.get((sy, k))
            if v is None:
                ax.text(j, i, "n/a", ha="center", va="center", fontsize=8, color=MUTED)
                continue
            f = min(1, max(0, (v - vmin) / (vmax - vmin)))
            ax.add_patch(plt.Rectangle((j - 0.48, i - 0.46), 0.96, 0.92, facecolor=cmap(f), lw=0))
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=9, color="#ffffff" if f > 0.45 else INK)
    ax.set_xlim(-0.5, len(cols) + 0.5)
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_xticks(range(len(cols) + 1), labels[:len(cols)] + ["Custom words\n(sanity, pass >= 95)"], fontsize=8.5)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(order)), [name(s) for s in order])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin, vmax))
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("Balanced accuracy x 100 (scale clipped at 50)", color=INK2, fontsize=8)
    cb.outline.set_visible(False)
    title(fig, f"Balanced accuracy by system and subtask ({TAG})",
          "Fixed 0.5 rule; rows sorted by overall rank. Custom words is a pass/fail check outside the score.")
    save(fig, "heatmap-subtasks")


def catch_vs_block(doc):
    rank = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    num = {n: str(i + 1) for i, n in enumerate(rank)}
    fig, axs = plt.subplots(2, 3, figsize=(13, 9.2))
    for ax, su in zip(axs.flat, SUITES):
        es = doc["suites"].get(su, {}).get("ranking", [])
        xs, ys = [e["false_block_rate"] for e in es], [e["catch_rate"] for e in es]
        ax.scatter(xs, ys, s=56, color=S1, edgecolor=SURFACE, linewidth=2, zorder=3)
        x0, x1 = _limits(xs, -0.01, 1.0, 0.3)
        y0, y1 = _limits(ys, 0.0, 1.02, 0.15)
        ax.set_xlim(x0, x1 + 0.1 * (x1 - x0))
        ax.set_ylim(y0, y1)
        label_points(ax, xs, ys, [num.get(e["name"], "?") for e in es], fontsize=8, char_w=0.012)
        ax.set_title(SUITE_NAME[su], loc="left", fontsize=10, color=INK, fontweight="bold")
        ax.set_xlabel("False-block rate (lower is better)", fontsize=8.5)
        ax.set_ylabel("Catch rate (higher is better)", fontsize=8.5)
    key = "    ".join(f"{num[n]} {name(n)}" for n in rank)
    fig.text(0.01, 0.015, "Key (overall rank): " + key, fontsize=8.5, color=INK2, ha="left")
    title(fig, f"Catch rate vs false-block rate per suite ({TAG})",
          "Suite value = mean over its scored subtasks (PII: mean over entity types). Best corner is top left. "
          "Each panel has its own axis range.")
    fig.subplots_adjust(hspace=0.35, wspace=0.25, bottom=0.09)
    save(fig, "catch-vs-false-block")


def slice_chart(doc):
    v = doc["unpublished_slice_view"]
    order = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    rows = [(s, (v["public"].get(s) or {}).get("overall") or {}, (v["unpublished"].get(s) or {}).get("overall") or {})
            for s in order]
    rows = [r for r in rows if r[1].get("balanced_accuracy") is not None and r[2].get("balanced_accuracy") is not None]
    fig, ax = plt.subplots(figsize=(9.6, 0.45 * len(rows) + 1.9))
    ys = list(range(len(rows)))[::-1]
    for y, (s, a, b) in zip(ys, rows):
        pa, pb = a["balanced_accuracy"], b["balanced_accuracy"]
        ax.plot([pa, pb], [y + 0.13, y - 0.13], color=AXIS, lw=1, zorder=1)
        ax.scatter([pa], [y + 0.13], s=56, color=S1, edgecolor=SURFACE, linewidth=2, zorder=3,
                   label=f"Public test rows ({v['rows']['public']:,})" if y == ys[0] else None)
        ax.scatter([pb], [y - 0.13], s=56, color=S2, edgecolor=SURFACE, linewidth=2, zorder=3,
                   label=f"Unpublished slice ({v['rows']['unpublished']:,})" if y == ys[0] else None)
        ax.text(max(pa, pb) + 0.5, y, f"{pb - pa:+.1f}", va="center", fontsize=9, color=INK)
    ax.set_yticks(ys, [name(r[0]) for r in rows])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Overall balanced accuracy x 100 (diagnostic re-score of each slice, never ranked)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5, labelcolor=INK2)
    title(fig, f"Public test rows vs the unpublished slice ({TAG})",
            "A system much better on public rows than on the unpublished slice may have seen them. Label: unpublished "
            "minus public, in points.")
    save(fig, "unpublished-slice")


def score_cost(doc):
    cost = doc["run"]["cost"]
    rank = doc["overall"]["ranking"]
    pts = [((cost.get(e["name"]) or {}).get("usd_per_1000"), e["balanced_accuracy"], e["name"]) for e in rank]
    pts = [p for p in pts if p[0]]
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ax.set_xscale("log")
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=56, color=S1, edgecolor=SURFACE, linewidth=2, zorder=3)
    ax.set_xlim(min(p[0] for p in pts) / 1.6, max(p[0] for p in pts) * 4)
    ax.set_ylim(min(p[1] for p in pts) - 2, max(p[1] for p in pts) + 1.5)
    label_points(ax, [p[0] for p in pts], [p[1] for p in pts], [name(p[2]) for p in pts], fontsize=8)
    ax.set_xlabel("USD per 1,000 checks (log scale)")
    ax.set_ylabel("Overall balanced accuracy x 100")
    ax.xaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 5)))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:g}"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    title(fig, f"Score vs cost ({TAG})",
            "Hosted: measured tokens or text units x list price. VM models: VM up-to-paused time x dated "
            "g2-standard-24 rate, split by run time.")
    save(fig, "score-vs-cost")


def attack_tags(doc):
    pa = doc["prompt_attacks"]
    tags = ["injection", "jailbreak", "leakage", "indirect"]
    order = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    order = [s for s in order if s in pa["by_tag"]]
    fig, axs = plt.subplots(1, 4, figsize=(13, 0.42 * len(order) + 2.2), sharey=True)
    ys = list(range(len(order)))[::-1]
    for ax, t in zip(axs, tags):
        vals = [pa["by_tag"][s][t]["balanced_accuracy"] for s in order]
        ax.barh(ys, vals, color=S1, height=0.6, zorder=2)
        base = pa["ngram_baseline"]["by_tag"].get(t, {}).get("best")
        if base is not None:
            ax.axvline(base, color=S2, lw=1.6, zorder=3)
            ax.text(base, len(order) - 0.35, f"n-gram {base:.1f}", color=INK2, fontsize=8, ha="center")
        ax.set_xlim(40, 100)
        ax.set_title(t.capitalize(), loc="left", fontsize=10, color=INK, fontweight="bold")
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(ys, [name(s) for s in order])
    title(fig, f"Prompt attacks by row tag, with the full-text n-gram baseline ({TAG})",
            "Balanced accuracy x 100 at the fixed rule over test and unpublished rows. Orange line: best word or "
            "character n-gram classifier (grouped CV), a reference, not a system.")
    save(fig, "prompt-attacks-by-tag")


def main():
    doc = json.loads((RES / "leaderboard.json").read_text(encoding="utf-8"))
    global SPLIT_NOTE
    SPLIT_NOTE = f"{SPLIT_NOTE}, {doc['full_run']['rows_total']:,} rows"
    overall_chart(doc)
    heatmap(doc)
    catch_vs_block(doc)
    score_cost(doc)
    slice_chart(doc)
    attack_tags(doc)
    print(sorted(p.name for p in PLOTS.iterdir()))


if __name__ == "__main__":
    main()
