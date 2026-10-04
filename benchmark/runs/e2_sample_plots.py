"""Charts for the edition 2 tune-split sample, from ``benchmark/results/edition2-tune-sample/leaderboard.json``.

    uv run --with matplotlib python benchmark/runs/e2_sample_plots.py

Writes PNG and SVG to ``benchmark/results/edition2-tune-sample/plots/``: overall score with intervals and tiers,
a systems x subtasks heatmap, catch rate against false-block rate per suite, score against cost and against p95
latency, and pplx-decider-v1-27b with and without the tune rows that match its training data. Every title says
"tune-split sample". Colors are the dataviz reference palette (light surface); text uses ink tokens, never the
series color. No row text is read.
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
RES = REPO / "benchmark" / "results" / "edition2-tune-sample"
PLOTS = RES / "plots"
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S1, S2 = "#2a78d6", "#eb6834"   # categorical slots 1 and 2 (validated: adjacent CVD dE 24.7, normal 33.6)
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]   # blue 100..700
SUITES = ["content", "prompt_attacks", "denied_topics", "word_filters", "sensitive_info", "grounding"]
SUITE_NAME = {"content": "Content", "prompt_attacks": "Prompt attacks (provisional)", "denied_topics": "Denied topics",
              "word_filters": "Word filters (profanity)", "sensitive_info": "Sensitive info (PII)",
              "grounding": "Grounding"}
SHORT = {"jev-1.13.0": "Jev 1.13.0", "clef": "Clef", "clef-flash": "Clef-flash", "pplx-decider-v1-27b": "pplx-decider",
         "kev-0-8b": "Kev-0.8B", "kev-4b": "Kev-4B", "kev-9b": "Kev-9B", "open-jev-2b": "Open-Jev-2B", "laya": "Laya",
         "strands-decider-2b": "Strands 2B", "bedrock-guardrails": "Bedrock"}
TAG = "tune-split sample, not a held-out result"

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
          "Edition 2 public tune split, 1,422 rows, fixed 0.5 rule. Tiers: Holm-adjusted paired tests vs the tier "
          "leader. Prompt attacks provisional.")
    save(fig, "overall")


def heatmap(doc):
    order = [e["name"] for e in doc["overall"]["ranking"]] + [e["name"] for e in doc["overall"].get("unranked", [])]
    cols = [k for k in ["content/request", "content/reply", "prompt_attacks/direct", "denied_topics/topic",
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
    labels = ["Content\nrequest", "Content\nreply", "Prompt attacks\n(provisional)", "Denied\ntopics",
              "Profanity", "PII (entity\nmean)", "Grounding"]
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


def score_cost_latency(doc):
    cost = doc["run"]["cost"]
    runs = doc["run"]["systems"]
    rank = doc["overall"]["ranking"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.4), sharey=True)
    allv = [e["balanced_accuracy"] for e in rank]
    a1.set_ylim(min(allv) - 2, max(allv) + 1.5)
    for ax, key, xl in ((a1, "cost", "USD per 1,000 checks (log scale)"),
                        (a2, "lat", "p95 latency per row, seconds (log scale)")):
        pts, es = [], []
        for e in rank:
            x = (cost.get(e["name"]) or {}).get("usd_per_1000") if key == "cost" else (runs.get(e["name"]) or {}).get("latency_p95_s")
            if x:
                pts.append((x, e["balanced_accuracy"]))
                es.append(e)
        ax.set_xscale("log")
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=56, color=S1, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.set_xlim(min(p[0] for p in pts) / 1.6, max(p[0] for p in pts) * 4)
        label_points(ax, [p[0] for p in pts], [p[1] for p in pts], [name(e["name"]) for e in es], fontsize=8)
        ax.set_xlabel(xl)
        fmt = (lambda v, _: f"${v:g}") if key == "cost" else (lambda v, _: f"{v:g}")
        ax.xaxis.set_major_locator(matplotlib.ticker.LogLocator(base=10, subs=(1, 2, 5)))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(fmt))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    a1.set_ylabel("Overall balanced accuracy x 100")
    title(fig, f"Score vs cost and vs p95 latency ({TAG})",
          "Hosted: measured tokens x list price. VM models: VM up-to-paused time x dated g2-standard-24 rate, split by "
          "run time. Latency recorded under each system's own concurrency; not a load test.")
    fig.subplots_adjust(wspace=0.08)
    save(fig, "score-vs-cost-latency")


def pplx_overlap(doc):
    s = doc["pplx_overlap_sensitivity"]
    w, wo = s.get("pplx_with") or {}, s.get("pplx_without") or {}
    rows = [("Overall", "overall")] + [(SUITE_NAME[su], su) for su in SUITES]
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    ys = list(range(len(rows)))[::-1]
    for y, (lab, k) in zip(ys, rows):
        a, b = (w.get(k) or {}).get("balanced_accuracy"), (wo.get(k) or {}).get("balanced_accuracy")
        if a is None or b is None:
            continue
        ya, yb = y + 0.13, y - 0.13   # offset so equal values stay visible as two marks
        ax.plot([a, b], [ya, yb], color=AXIS, lw=1, zorder=1)
        ax.scatter([a], [ya], s=56, color=S1, edgecolor=SURFACE, linewidth=2, zorder=3,
                   label="All tune rows" if y == ys[0] else None)
        ax.scatter([b], [yb], s=56, color=S2, edgecolor=SURFACE, linewidth=2, zorder=3,
                   label=f"Without the {s['rows_dropped']} overlap rows" if y == ys[0] else None)
        d = b - a
        ax.text(max(a, b) + 0.5, y, "no change" if abs(d) < 0.05 else f"{d:+.1f}", va="center", fontsize=9,
                color=INK)
    ax.set_yticks(ys, [r[0] for r in rows])
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("pplx-decider-v1-27b balanced accuracy x 100")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=8.5, labelcolor=INK2)
    by = ", ".join(f"{k} {v}" for k, v in s["rows_dropped_by_feature"].items())
    title(fig, f"pplx-decider-v1-27b with and without training-overlap rows ({TAG})",
          f"Dropped rows ({by}) match its training or development data (MODEL-TRAINING-OVERLAP.json). "
          "Label: change in points.")
    save(fig, "pplx-overlap")


def main():
    doc = json.loads((RES / "leaderboard.json").read_text(encoding="utf-8"))
    overall_chart(doc)
    heatmap(doc)
    catch_vs_block(doc)
    score_cost_latency(doc)
    pplx_overlap(doc)
    print(sorted(p.name for p in PLOTS.iterdir()))


if __name__ == "__main__":
    main()
