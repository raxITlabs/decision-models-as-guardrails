"""Re-skin an archify diagram in the raxIT Labs house style (raxitlabs-github/site DESIGN.md).

    uv run python docs/teach/diagrams/raxit_theme.py docs/teach/benchmark-pipeline.html

Archify renders a slate theme in JetBrains Mono. This swaps its theme variables for the raxIT palette (cream
ground, warm ink, byzantine blue for the main data path) and the font for Inter, and opens in the light theme
by default, since the marketing site does not ship dark mode. The dark toggle still works, on the raxIT dark
ground. Only CSS variables and the font change; the diagram geometry is the renderer's.
"""
import re
import sys
from pathlib import Path

LIGHT = {
    "--bg": "#f2efea", "--grid": "#e7e0d6", "--text": "#18120c", "--text-muted": "#6f5237", "--text-dim": "#8a7560",
    "--text-faint": "#6f5f4e", "--panel": "#faf8f5", "--panel-border": "#ddccbb", "--lane-fill": "rgba(231, 224, 214, 0.35)",
    "--lane-stroke": "#d6c7b4", "--arrow": "#a8977f", "--arrow-emphasis": "#3457d5", "--mask": "#faf8f5",
    "--frontend-fill": "rgba(42, 157, 143, 0.12)", "--frontend-stroke": "#2a7d72",
    "--backend-fill": "rgba(52, 87, 213, 0.10)", "--backend-stroke": "#3457d5",
    "--database-fill": "rgba(233, 196, 106, 0.24)", "--database-stroke": "#94701c",
    "--cloud-fill": "rgba(244, 162, 97, 0.18)", "--cloud-stroke": "#a95e25",
    "--security-fill": "rgba(231, 111, 81, 0.14)", "--security-stroke": "#b0472e",
    "--messagebus-fill": "rgba(244, 162, 97, 0.18)", "--messagebus-stroke": "#a95e25",
    "--external-fill": "rgba(158, 185, 212, 0.24)", "--external-stroke": "#4f7396",
    "--toolbar-bg": "rgba(250, 248, 245, 0.92)", "--toolbar-border": "#ddccbb", "--toolbar-text": "#3a2d20",
    "--toolbar-hover": "#faf8f5", "--toolbar-menu-bg": "#faf8f5",
}
DARK = {
    "--bg": "#14120b", "--grid": "#1b1913", "--text": "#f6f2ee", "--text-muted": "#a89c8f", "--text-dim": "#7d7366",
    "--text-faint": "#968a7d", "--panel": "#0a0905", "--panel-border": "#46423a", "--lane-fill": "rgba(27, 25, 19, 0.5)",
    "--lane-stroke": "#46423a", "--arrow": "#7d7366", "--arrow-emphasis": "#7b93e6", "--mask": "#0a0905",
    "--frontend-fill": "rgba(42, 157, 143, 0.18)", "--frontend-stroke": "#4fb8aa",
    "--backend-fill": "rgba(86, 115, 220, 0.18)", "--backend-stroke": "#7b93e6",
    "--database-fill": "rgba(233, 196, 106, 0.14)", "--database-stroke": "#e9c46a",
    "--cloud-fill": "rgba(244, 162, 97, 0.14)", "--cloud-stroke": "#f4a261",
    "--security-fill": "rgba(231, 111, 81, 0.16)", "--security-stroke": "#e76f51",
    "--messagebus-fill": "rgba(244, 162, 97, 0.14)", "--messagebus-stroke": "#f4a261",
    "--external-fill": "rgba(158, 185, 212, 0.14)", "--external-stroke": "#9eb9d4",
    "--toolbar-bg": "rgba(10, 9, 5, 0.85)", "--toolbar-border": "#46423a", "--toolbar-text": "#f6f2ee",
    "--toolbar-hover": "rgba(27, 25, 19, 0.95)", "--toolbar-menu-bg": "#1b1913",
}
PRINT = {k: LIGHT[k] for k in LIGHT}


def block(vars_: dict) -> str:
    return "\n".join(f"      {k}: {v};" for k, v in vars_.items())


def main(path: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    s = re.sub(r'(:root,\s*\[data-theme="dark"\]\s*\{)[^}]*\}', lambda m: m.group(1) + "\n" + block(DARK) + "\n    }", s, count=1)
    s = re.sub(r'(\n    \[data-theme="light"\]\s*\{)[^}]*\}', lambda m: m.group(1) + "\n" + block(LIGHT) + "\n    }", s, count=1)
    s = re.sub(r'(:root, \[data-theme="dark"\], \[data-theme="light"\]\s*\{)[^}]*\}',
               lambda m: m.group(1) + "\n" + block(PRINT) + "\n      }", s, count=1)
    s = s.replace("family=JetBrains+Mono:wght@400;500;600;700", "family=Inter:wght@400;500;600;700")
    # every font stack, including the one the SVG export embeds, becomes Inter
    s = re.sub(r"'JetBrains Mono', ui-monospace[^;\"]*", "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif", s)
    s = s.replace("local('JetBrains Mono'), local('JetBrainsMono-Regular')", "local('Inter'), local('Inter-Regular')")
    s = s.replace("font-family: 'JetBrains Mono'", "font-family: 'Inter'").replace("find JetBrains Mono", "find Inter")
    # legend words in this benchmark's terms (the renderer's defaults describe a PII pipeline)
    for a, b in ((">primary data<", ">main path<"), (">policy / PII<", ">evidence gate<"), (">async batch<", ">publish step<"), (">data store<", ">stored artifact<")):
        s = s.replace(a, b)
    # light by default: the raxIT marketing system does not ship dark mode; the toggle and ?theme= still work
    s = s.replace("theme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';", "theme = 'light';")
    s = s.replace('<html lang="en" data-theme="dark">', '<html lang="en" data-theme="light">')
    assert "JetBrains" not in s and "#020617" not in s and "#f8fafc" not in s, "theme swap incomplete"
    p.write_text(s, encoding="utf-8")
    print(f"raxIT theme applied to {p}")


if __name__ == "__main__":
    main(sys.argv[1])
