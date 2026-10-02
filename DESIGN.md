---
name: jev-as-a-guardrails
description: A research datasheet that measures decision-model guardrails against Amazon Bedrock Guardrails on quality, cost and latency.
colors:
  paper: "#f5f6f4"
  raise: "#ffffff"
  ink: "#14161a"
  ink-2: "#474c54"
  ink-3: "#676d76"
  rule: "#d8dbdf"
  grid: "#e7e9ec"
  dm: "#2140c9"
  dm-soft: "rgba(33, 64, 201, 0.34)"
  dm-faint: "rgba(33, 64, 201, 0.14)"
  br: "#a0560a"
  base: "#7b8089"
  focus: "#2140c9"
  paper-dark: "#101215"
  raise-dark: "#181b1f"
  ink-dark: "#eceef1"
  ink-2-dark: "#b4bac2"
  ink-3-dark: "#8e959e"
  rule-dark: "#2b2f35"
  grid-dark: "#1f2226"
  dm-dark: "#86a0ff"
  dm-soft-dark: "rgba(134, 160, 255, 0.4)"
  dm-faint-dark: "rgba(134, 160, 255, 0.16)"
  br-dark: "#f0a552"
  base-dark: "#8f959e"
  focus-dark: "#86a0ff"
typography:
  display:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "clamp(2rem, 1.2rem + 3.2vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.04
    letterSpacing: "-0.03em"
  lede:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "clamp(1.06rem, 1rem + 0.35vw, 1.3rem)"
    fontWeight: 400
    lineHeight: 1.5
  headline:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 680
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 650
    letterSpacing: "-0.01em"
  figure:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.03em"
    fontFeature: "tnum"
  body:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tnum"
  data:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    fontFeature: "tnum"
  label:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    fontFeature: "tnum"
  tick:
    fontFamily: "Public Sans, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    fontFeature: "tnum"
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "13px"
    lineHeight: 1.4
rounded:
  track: "3px"
  sm: "4px"
  card: "14px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "16px"
  panel: "22px"
  md: "28px"
  gutter: "32px"
  lg: "56px"
  section: "64px"
components:
  segment-button:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
    typography: "{typography.data}"
  segment-button-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  tool-button:
    backgroundColor: "{colors.raise}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "8px 14px"
    typography: "{typography.data}"
  ledger-row:
    textColor: "{colors.ink}"
    padding: "18px 0"
  chart-panel:
    textColor: "{colors.ink}"
    padding: "22px 22px 18px 0"
  chart-panel-lit:
    backgroundColor: "{colors.dm-faint}"
  detail-card:
    backgroundColor: "{colors.raise}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "22px 22px 18px"
    width: "min(420px, calc(100vw - 32px))"
  table-header-cell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-3}"
    typography: "{typography.label}"
    padding: "9px 12px"
  table-cell:
    textColor: "{colors.ink}"
    typography: "{typography.data}"
    padding: "9px 12px"
  table-row-hover:
    backgroundColor: "{colors.dm-faint}"
  bias-bar-track:
    backgroundColor: "{colors.grid}"
    rounded: "{rounded.track}"
    height: "6px"
  inline-code:
    backgroundColor: "{colors.grid}"
    typography: "{typography.code}"
    rounded: "{rounded.sm}"
    padding: "1px 5px"
---

# Design System: jev-as-a-guardrails

## Overview

**Creative North Star: "The Research Datasheet"**

jev-as-a-guardrails reads like a printed datasheet from a measurement lab. It has a near-white paper ground, near-black ink, and one sans family set with tabular figures everywhere. Structure comes from hairline rules, never from boxes. The page asks one question and answers it in three passes of rising detail: a verdict ledger, a grid of same-scale small multiples, and a table of every number. Each pass uses the same two hues for the same two parties.

Color is information here and nothing else. Cobalt means a decision model. Ochre means Amazon Bedrock Guardrails. Grey means a baseline, or something unscored. A reader who learns that in the headline can read every later chart, dot, swatch and label without a legend. Uncertainty gets drawn as a first-class mark: interval bars sit behind every main score, and anything missing is written out in words in the tertiary ink, never plotted at zero.

Density is high but calm. Type stays in a narrow band from 11px to 16px below the headings, and hierarchy comes from weight and ink tone more than size. Only one object ever floats, the detail card that opens when a reader selects a point.

**Key Characteristics:**
- Paper ground, ink text, hairline rules; content sits on the page, not in cards.
- Two committed hues, cobalt and ochre, each bound to one party; everything else is grey.
- Public Sans throughout, including chart text, with tabular numerals on by default.
- Same axes across every small multiple, so panels compare by eye.
- Pill shapes for controls only; data marks carry shape as a second identity channel.
- A full dark scheme through `prefers-color-scheme`, with lighter, less saturated hues.

## Colors

A cool neutral ink scale on a near-neutral paper, plus two saturated hues that each belong to one party in the comparison.

### Primary
- **Cobalt** (`dm`): decision models, led by Jev. It colors "decision models" in the headline, Jev's dot, interval bar and label in every chart, the "Jev ahead" verdict, and the swatch beside every decision-model row. It doubles as the link color and the focus ring. Its soft variant (`dm-soft`) draws the other decision models as thin ticks on the ledger scale; its faint variant (`dm-faint`) is the only tint used for highlight: row hover, the lit panel, text selection.

### Secondary
- **Ochre** (`br`): Amazon Bedrock Guardrails. It colors "Amazon Bedrock Guardrails" in the headline, the Bedrock diamond and interval in every chart, the "Bedrock ahead" verdict and Bedrock's swatch.

### Neutral
- **Paper** (`paper`): the page ground. It also knocks out behind chart marks and sticky table cells so they read cleanly over grid lines. The light value carries a barely visible warm-green cast; the inks are cool blue-grey.
- **Raise** (`raise`): the one lifted surface color, for the detail card, the segmented control track and the download buttons.
- **Ink** (`ink`): primary text, the 1px rule that opens each data block, and the active segment fill.
- **Ink 2** (`ink-2`): secondary text such as sub-headings, cost values, method prose, chart labels for minor points.
- **Ink 3** (`ink-3`): tertiary text such as column headers, tick labels, descriptions, and every "not scored", "n/a" or "not applicable" note.
- **Rule** (`rule`): hairline row dividers, panel separators and control borders.
- **Grid** (`grid`): chart grid lines, the bias bar track, inline code ground and the close button hover.
- **Baseline grey** (`base`): code baselines and other reference implementations, drawn as hollow triangles.

### Dark scheme
Every neutral and hue has a `-dark` twin, applied under `prefers-color-scheme: dark`. Paper drops to a blue-black, inks invert, and the hues lift: cobalt becomes a periwinkle (`dm-dark`), ochre becomes an amber (`br-dark`). The soft and faint alphas rise slightly (0.4 and 0.16) to hold contrast on the dark ground.

### Named Rules
**The Two Parties Rule.** Cobalt belongs to decision models and ochre belongs to Bedrock, on every mark, label, swatch and verdict. Neither hue is ever used for decoration, for status, or for a third party.

**The Unknown Is Grey Rule.** Missing, unscored, unpriced and not-applicable values are written in words in `ink-3`. They never take a hue and are never drawn as zero.

## Typography

**Display Font:** Public Sans (with system-ui, sans-serif)
**Body Font:** Public Sans (with system-ui, sans-serif)
**Label/Mono Font:** ui-monospace, SFMono-Regular, Menlo, for hashes and file names only

**Character:** One neutral grotesque loaded as a variable font (weights 300 to 800), used at intermediate weights like 550, 620, 650 and 680 to build hierarchy without extra sizes. Tabular figures are set on `body` and on SVG text, so every column of numbers aligns.

### Hierarchy
- **Display** (700, `clamp(2rem, 1.2rem + 3.2vw, 3.5rem)`, 1.04): the page question only. Tight tracking (-0.03em), balanced wrap, capped at 17ch. The two party names inside it take their hues.
- **Lede** (400, `clamp(1.06rem, 1rem + 0.35vw, 1.3rem)`, 1.5): the computed answer under the question, capped at 62ch.
- **Headline** (680, 1.5rem, 1.2): section headings, tracked -0.02em.
- **Title** (650, 16px): chart panel names and method sub-heads (15px there).
- **Figure** (700, 34px, 1): the single large score at the top of the detail card.
- **Body** (400, 16px, 1.55): prose, with sub-heads and method text at 15px in `ink-2`, capped at 62 to 72ch.
- **Data** (400, 14px): table cells, cost values, status items, controls.
- **Label** (400, 13px): column headers, descriptions, secondary lines under a name or verdict, footer.
- **Tick** (400, 11px): chart axis ticks and axis titles; point labels sit at 11.5px, and at 12px and 650 for Jev and Bedrock.

### Named Rules
**The Tabular Figures Rule.** Every number on the page, in HTML or SVG, uses tabular numerals so values line up in columns and do not shift when the axis toggles.

**The Weight Before Size Rule.** Below the headings, rank comes from weight (400, 550, 600, 650) and ink tone (`ink`, `ink-2`, `ink-3`), not from new font sizes.

## Layout

A single centered column, 1180px maximum, with a 32px side gutter that becomes 16px at 640px and below. The page runs top to bottom in fixed order: masthead line, question, answer, status line, verdict ledger, small multiples, full table, method notes, footer. Sections open 64px below the previous one; the masthead sits 56px above the question.

The verdict ledger is a four-column grid (200px name, flexible scale, 148px verdict, 200px cost) with 28px column gaps. At 900px it restacks: name and verdict share the first line, the scale takes a full-width second line with its own 40, 70 and 100 ticks, and cost drops to a third line.

The small multiples are a three-column grid of chart panels separated by vertical hairlines, with the bias panel spanning the full width at the end. They drop to two columns at 1000px and one at 640px. All six capability panels share the same y range (40 to 100) and the same log-scale x domain, computed across every suite.

The full table scrolls horizontally inside its wrapper (minimum 860px) with a sticky header row and a sticky first column. Below 900px a right-edge mask fades the overflow to signal more columns. Method notes sit in two columns with a 56px gap, collapsing to one at 800px.

**The Same Axes Rule.** Every capability panel shares its x domain and its 40 to 100 quality scale. A new panel joins that shared domain; it never gets an axis fitted to its own points.

## Elevation & Depth

The page is flat. Depth comes from rules and ink weight: a 1px `ink` rule opens each data block, 1px `rule` hairlines divide rows and panels, and `grid` lines sit quietest inside charts. The only shadow belongs to the floating detail card.

### Shadow Vocabulary
- **Detail lift** (`box-shadow: 0 1px 2px rgba(20, 22, 26, 0.06), 0 12px 32px -8px rgba(20, 22, 26, 0.18)`; dark: `0 1px 2px rgba(0, 0, 0, 0.4), 0 16px 40px -8px rgba(0, 0, 0, 0.6)`): the detail card only.

Chart dots on the verdict ledger carry a 2px paper-colored ring (`0 0 0 2px var(--paper)`). That ring is a knockout that separates the dot from the interval bar under it, not elevation.

### Named Rules
**The One Lifted Thing Rule.** Only the detail card casts a shadow. Everything else lies on the paper and is separated by rules.

**The Opening Ink Rule.** Each data block (ledger, chart grid, table) starts with a full-width 1px `ink` rule; rows inside it divide with `rule` hairlines.

## Shapes

Data is square and controls are round. Rows, panels and the table have no corner radius at all; they are defined by the rules between them. Controls that a reader presses (the segmented axis switch, the CSV and JSON buttons) are full pills (999px). The detail card rounds at 14px, the close button and status markers are circles, and small inline pieces (code, bias bar buttons) round at 4px, with bar tracks and fills at 3px.

Chart marks carry identity by shape as well as hue, so the charts survive greyscale printing and color-blind reading:
- **Filled circle, 6px radius**: Jev.
- **Hollow circle, 4.2px radius**: other decision models.
- **Filled diamond** (an 11px square rotated 45 degrees): Bedrock.
- **Hollow triangle**: baselines.

Main marks carry a 1.5px paper stroke to separate them from grid lines. Interval bars use round caps at reduced opacity (0.45 for main points, 0.3 for others, 0.32 on the ledger).

## Components

### Buttons
Quiet and round, with no fill until pressed.
- **Shape:** full pill (999px).
- **Segmented axis switch:** a pill track in `raise` with a 1px `rule` border and 3px inner padding. Segments sit at 6px by 14px in 14px `ink-2`. The pressed segment fills with `ink` and its text turns `paper`. Unpressed segments darken to `ink` on hover. State lives in `aria-pressed`. Background and color transition over 180ms ease-out.
- **Tool button (CSV, JSON):** `raise` fill, 1px `rule` border, 8px by 14px padding, 14px text, with a 15px stroked SVG download icon at 1.5px stroke. Hover darkens the border to `ink-3` over 160ms.
- **Close:** a 32px transparent circle holding a 16px stroked cross; hover fills it with `grid` and darkens the icon to `ink`.

### Verdict ledger
The signature component. One row per capability, answering "who is ahead here, how sure are we, and at what cost" in a single line.
- **Name cell:** capability in 600 `ink`, description below in 13px `ink-3`.
- **Scale cell:** a 40 to 100 strip with `grid` tick lines at every ten points. Jev's interval bar and dot sit above the center line in cobalt, Bedrock's below it in ochre, with each score printed at 11.5px and 650 in its hue. Other decision models appear as thin `dm-soft` ticks. An unscored capability shows a sentence in `ink-3` instead of marks.
- **Verdict cell:** "Jev ahead" in cobalt, "Bedrock ahead" in ochre, "Level" in `ink`, "Awaiting review" in `ink-3` at weight 500. A 13px `ink-3` line under it gives the gap or says the intervals overlap. A win requires intervals that do not overlap.
- **Cost cell:** both prices in 600 `ink`, the ratio beneath in `ink-3`.
- **Behavior:** the whole row is focusable; hover or focus turns the name cobalt over 160ms. Activating it scrolls to the matching chart panel and tints it `dm-faint` for 1.4 seconds.

### Chart panel
- **Frame:** no background, no radius; hairline `rule` borders between panels and along the bottom.
- **Padding:** 22px on the inner sides, 18px at the bottom.
- **Head:** title at 16px and 650, a 13px `ink-3` description held to a two-line minimum height so plots align across a row.
- **Plot:** a 360 by 250 SVG with `grid` lines, 11px `ink-3` ticks, an `ink-3` baseline, and an axis title in the lower right. On the cost axis a dashed gutter labelled "Free" holds documented zero-price policies, which a log axis cannot place.
- **Labels:** placed by a collision pass that tries right, left, above, then below. Jev and Bedrock are always labelled; minor points drop their label before overlapping.
- **Footnote:** points that cannot sit on the current axis are listed in a 12.5px `ink-3` line with the reason.

### Detail card
- **Corner Style:** 14px.
- **Background:** `raise`.
- **Shadow Strategy:** detail lift, the only shadow on the page.
- **Placement:** fixed to the bottom right at 24px, 420px wide, up to 78vh tall with its own scroll. On phones it spans the width with 16px insets.
- **Content:** implementation name at 18px in its party hue, context line in 13px `ink-3`, the score in the figure style with its interval beside it, then a two-column definition list at 14px with `ink-3` terms and right-aligned values.
- **Motion:** enters from 12px below with opacity, 200ms for opacity and 260ms on `cubic-bezier(0.16, 1, 0.3, 1)` for the rise. Escape or an outside click closes it and returns focus to the point that opened it.

### Data table
- **Header:** 13px, weight 500, `ink-3`, sticky to the top on `paper`.
- **Cells:** 14px, right-aligned numbers, 9px by 12px padding, `rule` hairline below; the first column is left-aligned, sticky, and carries an 8px party swatch before the name.
- **Group rows:** capability name at 650 with 26px top padding and an `ink-3` rule under it.
- **Hover:** the whole row tints `dm-faint`; rows are focusable and open the detail card.
- **Missing values:** "n/a" in `ink-3`.

### Bias bars
- **Track:** 6px high, `grid` fill, 3px radius. The fill takes the party hue at the score's width and brightens slightly on hover.
- **Value:** 600 weight, right-aligned in 40px, followed by the sample size in 12px `ink-3`.
- **Not applicable:** written out in 13px `ink-3`, never an empty bar.

### Status line
A wrapping row of 14px `ink-2` items, each led by a 6px dot. Settled facts get a filled `ink-3` dot; warnings (draft contract, interim results) get a hollow ring drawn in `ink`.

### Links and focus
Links are cobalt with a 1px underline offset 3px, thickening to 2px on hover. Every focusable element gets a 2px `focus` outline offset 2px. Chart points show focus as a 2px ring on a 10px halo, and thicken their mark stroke to 2.5px on hover or focus.

### Motion
State changes run 160 to 220ms on ease-out. The one authored moment is the axis toggle: chart points keep their DOM nodes and glide to new positions over 420ms on `cubic-bezier(0.16, 1, 0.3, 1)`, while labels fade in over 360ms. `prefers-reduced-motion: reduce` sets every transition and animation to zero.

## Do's and Don'ts

### Do:
- **Do** bind cobalt (`dm`) to decision models and ochre (`br`) to Bedrock on every mark, label, swatch and verdict, and keep everything else grey.
- **Do** write missing, unscored and not-applicable values out in words in `ink-3`; keep them off the plot and out of the zero position.
- **Do** draw a 95% interval behind every main score, and call two parties level whenever their intervals overlap.
- **Do** give every capability panel the same axes: 40 to 100 on y, the shared log domain on x.
- **Do** separate content with 1px rules: an `ink` rule to open a data block, `rule` hairlines between rows and panels.
- **Do** set every number in Public Sans with tabular figures, in HTML and SVG alike.
- **Do** carry identity by mark shape as well as hue: circle for decision models, diamond for Bedrock, hollow triangle for baselines.
- **Do** keep pills (999px) for small pressable controls.

### Don't:
- **Don't** use cobalt or ochre for decoration, emphasis, warnings or errors; each hue means one party.
- **Don't** wrap content in cards. The only lifted surface is the detail card, and it is the only thing with a shadow.
- **Don't** fit a panel's axes to its own points; per-panel scales break comparison across the grid.
- **Don't** plot a zero cost on the log axis; documented free policies go in the "Free" gutter and anything unpriced goes in the panel footnote.
- **Don't** add a second type family for display or data; monospace is only for hashes and file names.
- **Don't** add new font sizes inside the 11px to 16px data band; use weight and ink tone instead.
