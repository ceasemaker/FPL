---
name: AeroFPL
description: Calm, Apple-style Fantasy Premier League decision tools on a graphite ground, with lime for one thing per screen area.
colors:
  lime: "#a5ff01"
  lime-hover: "#b6ff33"
  lime-wash: "rgba(165, 255, 1, 0.10)"
  ink: "#101011"
  surface: "#1b1b1d"
  surface-raised: "#262628"
  surface-hover: "#2e2e31"
  fill: "rgba(118, 118, 128, 0.24)"
  segment-on: "#636366"
  line: "rgba(255, 255, 255, 0.09)"
  line-strong: "rgba(255, 255, 255, 0.14)"
  text: "#f5f5f7"
  text-soft: "#d1d1d6"
  text-dim: "#a1a1a6"
  text-muted: "#86868b"
  negative: "#ff4c5e"
  negative-soft: "#ff7a87"
  warn: "#e2b75b"
  warn-soft: "#f5d06f"
  info: "#64d2ff"
  us: "#e8e8e8"
  them: "#8f8f8f"
  europe: "#7aa7ff"
  cup: "#c59bff"
  fdr-2: "#b8e986"
  fdr-3: "#95ae67"
  fdr-4: "#e2b75b"
  fdr-5: "#ff4c5e"
  pitch-a: "#17241a"
  pitch-b: "#1a291d"
  pitch-line: "#2b3a2d"
typography:
  large-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "3rem"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.19
    letterSpacing: "-0.02em"
  section:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 600
    lineHeight: 1.27
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.47
    letterSpacing: "0"
  data:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 500
    lineHeight: 1.47
    letterSpacing: "0"
    fontFeature: "tnum"
  footnote:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "0"
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, \"SF Pro Text\", \"Inter\", \"Segoe UI\", Roboto, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
    letterSpacing: "0"
rounded:
  chip: "6px"
  sm: "10px"
  panel: "18px"
  pill: "980px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "24px"
  "6": "32px"
  "7": "48px"
  "8": "64px"
  gutter: "32px"
  column: "1200px"
  nav: "220px"
components:
  button-primary:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    height: "36px"
    padding: "0 18px"
  button-primary-hover:
    backgroundColor: "{colors.lime-hover}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    height: "36px"
    padding: "0 18px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-hover}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    height: "36px"
    padding: "0 18px"
  input:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    height: "36px"
    padding: "0 12px"
  select:
    backgroundColor: "{colors.fill}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    height: "36px"
    padding: "0 34px 0 12px"
  segmented-track:
    backgroundColor: "{colors.fill}"
    rounded: "{rounded.sm}"
    padding: "2px"
  segmented-option:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    typography: "{typography.footnote}"
    height: "32px"
    padding: "0 14px"
  segmented-option-selected:
    backgroundColor: "{colors.segment-on}"
    textColor: "{colors.text}"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "20px"
  chip:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text-dim}"
    typography: "{typography.caption}"
    rounded: "{rounded.chip}"
    padding: "2px 8px"
  chip-accent:
    backgroundColor: "{colors.lime-wash}"
    textColor: "{colors.lime}"
  fdr-chip:
    backgroundColor: "rgba(255, 255, 255, 0.08)"
    textColor: "{colors.text-dim}"
    typography: "{typography.caption}"
    rounded: "{rounded.chip}"
    height: "22px"
    padding: "0 6px"
  fdr-chip-easy:
    backgroundColor: "rgba(184, 233, 134, 0.12)"
    textColor: "{colors.fdr-2}"
  fdr-chip-hard:
    backgroundColor: "rgba(226, 183, 91, 0.16)"
    textColor: "{colors.fdr-4}"
  fdr-chip-hardest:
    backgroundColor: "rgba(255, 76, 94, 0.18)"
    textColor: "{colors.negative-soft}"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.text-soft}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    height: "36px"
    padding: "0 12px"
  nav-item-active:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
  table-row-mine:
    backgroundColor: "{colors.lime-wash}"
  error:
    backgroundColor: "rgba(255, 76, 94, 0.08)"
    textColor: "#ffb4bc"
    rounded: "{rounded.sm}"
    padding: "12px 16px"
---

# Design System: AeroFPL

## Overview

**Creative North Star: "Apple Sports in AeroFPL colours"**

AeroFPL is a weekly FPL decision tool that now reads like one of Apple's own data apps (Sports, Stocks, Settings) set on AeroFPL's graphite ground. Headings are big and quiet, panels are flat graphite on ink with no border or shadow, rows are separated by inset hairlines, and every screen area has at most one lime thing: the primary action, or the marker that says where you are. Everything else is greys of different strengths, so the lime is always the answer to "what do I do here?" or "where am I?".

Density comes from tables and grouped lists, not from tiles. Text sits left and numbers sit right in tabular figures; there are no zebra stripes. Copy is sentence case and British English, labels are plain words ("Search", never "SEARCH"), and status (fixture difficulty, injury, price change) is shown as a soft tint or tinted text, never a solid lime block. The honesty commitment from PRODUCT.md stays visual: notes, empty states and errors are components in their own right, and data that is missing or estimated is labelled, not filled.

Tokens and shared primitives live in `frontend/src/styles/design-system.css` (`--aero-*`, `--fs-*`, `.aero-*`); `frontend/src/styles/tokens.ts` mirrors the colours for SVG and canvas drawing and holds the chart series. `frontend/scripts/design-audit.mjs` measures the system: 7 font sizes, 3 weights, 3 tracking values, 4 radii, 2 breakpoints, no raw hex outside the two token files, no all-caps.

**Key Characteristics:**
- Graphite ink ground (#101011) with flat graphite panels; depth from contrast, not shadow.
- One lime thing per screen area: the primary action or where you are.
- System SF stack with Inter as the fallback, on a seven-step type scale and three weights (400, 500, 600).
- One centred 1200px column beside a 220px translucent sidebar; every heading, panel and table shares its left edge.
- Inset hairlines, text left, numbers right, tabular figures, no zebra.
- Four radii: 6px chips, 10px controls, 18px panels, pill buttons.
- Sentence case, British English, no motion the user did not start.

## Colors

One graphite ramp, Apple's off-white text greys, a single Spring Bud lime, and soft status tints that only ever describe data.

### Primary
- **Spring Bud Lime** (lime): the primary action in an area (a solid pill with ink text), the current-place marker (the active sidebar icon, the selected gameweek's 2px top line in the planner, your rank number in a mini-league), focus outlines, checkbox and range accents, positive numbers as text, and the top cells in Stats Explorer as text on a 20% lime tint. Text on solid lime is always ink.
- **Lime Hover** (lime-hover): the primary button's hover fill only.
- **Lime Wash** (lime-wash): your own row (league standings, the selected player row, the active squad row) and the accent chip ground.

### Secondary
- **Us Light** (us) and **Them Grey** (them): the two sides of a match. The subject side is light and above the axis (or left); the other side is grey and below (or right). Page code reaches them through `--mp-home` / `--mp-away` on `.mp-page`.
- **Europe Blue** (europe) and **Cup Violet** (cup): competition grouping, always beside a written competition tag. The Premier League is untinted.

### Tertiary
- **Info Cyan** (info): information and the second chart series. The categorical chart series (`series` in `tokens.ts`) runs lime, then Apple's dark-mode cyan, yellow, pink, purple and orange.

### Neutral
- **Ink** (ink): page ground, sidebar-adjacent background and text on lime.
- **Graphite** (surface): every panel, grouped list, table container, note and sticky table column.
- **Raised / Hover** (surface-raised, surface-hover): secondary buttons, chips, the active sidebar row, row hover; each one step lighter.
- **Tertiary Fill** (fill): translucent grey fill for search fields, inputs, selects and segmented-control tracks.
- **Selected Segment** (segment-on): the selected option in any segmented control.
- **Hairline / Strong Hairline** (line, line-strong): inset row separators and the sidebar edge; strong hairlines for dashed empty cells and the rare outline.
- **Text / Soft / Secondary / Tertiary** (text, text-soft, text-dim, text-muted): primary copy; sidebar labels; labels, meta and column headers; footnotes and placeholders only.

### Status
- **Coral** (negative, negative-soft): drops, rule breaks, injured or suspended players, the hardest fixtures. `negative` for numbers, `negative-soft` for text on a coral tint.
- **Amber** (warn, warn-soft): warnings, doubtful players, price timing, hard fixtures, caveats.
- **Fixture difficulty** (fdr-2 to fdr-5, via the `--aero-tint-*` tokens): FDR 1 is the pale-lime tint at 20% (`tint-easiest`) and FDR 2 at 12% (`tint-easy`), both with fdr-2 text; 3 is a neutral 8% white wash (`tint-neutral`) with secondary text; 4 is amber at 16% (`tint-warn`); 5 is coral at 18% (`tint-hard`) with soft coral text. FDR is never a solid fill.
- **Pitch** (pitch-a, pitch-b, pitch-line): the mown stripes and outline of the match pitch; nowhere else.

### Named Rules
**The One Lime Rule.** Each screen area gets at most one lime thing: the primary action, or where you are. Positive numbers may be lime text; lime is never a fill on anything except the primary button, the cursor tag on the match timeline and legend dots.

**The Soft Tint Rule.** Fixture difficulty and status are a tinted ground with matching text (12–18% alpha), never a solid block, and never colour alone: the number or word is always written in the chip.

**The Quiet Heat Rule.** Table heat shading is a white wash whose strength follows the value within the position group (up to 16% white); only the top cells (roughly the top 7%) switch to a 20% lime tint with lime text at 600. Weight and the cell's accessible label carry the same information as the shade.

**The Data-Only Status Rule.** Coral and amber describe data (drops, flags, hard fixtures, caveats). They are never decoration or a second accent.

## Typography

**Display Font:** SF Pro via the system stack (`-apple-system, BlinkMacSystemFont, "SF Pro Text"`), with Inter as the fallback
**Body Font:** the same stack
**Label Font:** the same stack

**Character:** Apple's own type on Apple devices and Inter everywhere else, loaded in `frontend/index.html` as a variable font with its optical-size axis (`opsz 14..32`, weights 400–600) so headings pick up the display cut. One family, quiet weights, tight tracking only on the large sizes.

### Hierarchy
- **Large title** (600, 3rem / 48px, line-height 1, -0.02em): the Home heading only.
- **Title** (600, 2rem / 32px, 1.19, -0.02em): every page title, in the page header.
- **Section** (600, 1.375rem / 22px, 1.27, -0.02em): section headings ("Your mini-leagues"), headline figures in fact strips, the sidebar wordmark.
- **Headline** (600, 1.0625rem / 17px, 1.3, 0): panel titles, player names in panels, the phone wordmark.
- **Body** (400, 0.9375rem / 15px, 1.47): copy, table cells, controls and sidebar labels; numbers in tables at 500. Intro paragraphs stop near 62–68ch.
- **Footnote** (400–500, 0.8125rem / 13px): meta, notes, column headers, field labels, segmented-control text, sidebar group headings.
- **Caption** (500–600, 0.75rem / 12px): chips, FDR, price-change text, legends, micro tags. Nothing in the system is smaller than 12px.

### Named Rules
**The Seven Sizes Rule.** Every font size is one of the seven `--fs-*` tokens. Weights are 400, 500 and 600 only; tracking is 0, -0.01em or -0.02em only.

**The Tabular Rule.** Every table sets `font-variant-numeric: tabular-nums` (globally on `table`), and any other figure that lines up with another (facts, tallies, timelines) sets it too.

**The Sentence Case Rule.** All text, including buttons, column headers and group headings, is sentence case with no added tracking. Copy is British English; identifiers and routes stay as they are.

## Layout

One centred column beside a fixed sidebar. The sidebar is 220px wide (200px at 1068px and below); pages sit beside it in a 1200px column with 32px minimum gutters (24px at 1068px, 16px at 734px), padded 48px on top and 96px at the bottom. The page padding is computed so the column stays centred in the space beside the sidebar: `max(gutter, (100% - nav - column) / 2)`. Every heading, panel and table starts on that left edge and nothing runs wider.

At 734px and below the sidebar becomes a 52px top bar, the page takes the full width, and page padding becomes 84px top, 16px sides, 64px bottom. These two breakpoints (1068px and 734px, Apple's own) are the only ones; two-column layouts (the planner's squad plus 320px side column, the mini-league pair, Home's main plus rail) drop to one column at 1068px, and dense rows reflow into grid areas at 734px.

Spacing runs 4, 8, 12, 16, 24, 32, 48, 64. The page header sits 32px above content (24px on phones); sections are 48–64px apart; panels pad 20–24px; table cells pad 10px by 12px with 20px at the row ends. On phones, tap-target rows grow to 44px (the sidebar menu links); segmented options stay at 32px inside their 2px track.

## Elevation & Depth

Flat. Panels are graphite (#1b1b1d) on ink (#101011), separated by contrast; `--aero-shadow` is `none` and `.aero-card`, `.glow-card`, `.mp-sheet` and table containers carry no border and no shadow. Depth comes from four tonal steps (ink, graphite, raised, hover) and from translucency in exactly one place: the sidebar, which is `rgba(24,24,26,0.72)` behind `backdrop-filter: saturate(180%) blur(20px)`. Lines inside panels are drawn as inset box-shadows or 1px backgrounds so they occupy no layout space.

### Shadow Vocabulary
- **Segment lift** (`box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3)`): the selected option in a segmented control, the only resting shadow in the system.
- **Inset hairline** (`box-shadow: inset 0 1px var(--aero-line)`): row separators in tables and fact strips.
- **Lime ring** (`box-shadow: 0 0 0 2px var(--aero-lime) inset`): a selected card in compare mode; a just-on player token.
- **Token lift** (`box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4)`): player tokens on the match pitch, so they read over the stripes.

### Named Rules
**The No Card Shadow Rule.** Panels are separated from the ground by colour alone. A shadow appears only on a selected segment or on an object floating over imagery (pitch tokens).

## Shapes

Four radii and nothing else: chips at 6px (FDR, status tags, micro tags, swatches), controls at 10px (inputs, selects, segmented tracks, sidebar rows, notes, errors), panels at 18px (every graphite panel and table container), and pills at 980px (all buttons). The segmented control's inner option is concentric with its track: `calc(var(--aero-radius-sm) - 2px)` inside a 2px pad. Circles (50%) are shapes, not radii: avatars, player tokens, round step buttons, the phone menu button. Borders are rare: a 1px dashed strong hairline marks a blank fixture or an empty slot; the goal-mouth frame is the one 2px line.

## Components

### Buttons
Pills, quiet by default; the primary is the only lit one.
- **Shape:** full pill (980px), 36px tall (30px for in-row actions such as Sell), 0 18px padding, Body at 500.
- **Primary:** solid lime with ink text, no gradient, hover to lime-hover. One per screen area.
- **Secondary (default):** raised graphite with text colour, hover steps to surface-hover. Toggle buttons that are on (Sell) invert to text-colour fill with ink text.
- **Ghost:** transparent, same shape.
- **Focus:** 2px lime outline at 2px offset, no glow. Disabled at 45% opacity.
- **Base `button`:** sentence case, no tracking, 500 weight, pill radius; page styles and `.aero-button` decide the look.

### Segmented Controls
The control for any choice of five options or fewer (position, view, gameweek range, competition, venue). A translucent fill track (10px radius, 2px pad) holding 32px options at Footnote / 500 in text colour, minimum 44px wide. The selected option (`aria-pressed="true"`) is the selected-segment grey (#636366) with the segment lift, at the concentric inner radius. Never lime: a segment is a filter, not an action or a location. Selects are for long lists only (teams, leagues).

### Chips
- **Neutral chip:** raised graphite, secondary text, Caption / 500, 6px radius, 2px by 8px.
- **Accent chip:** lime wash with lime text, for a quiet positive tag (a chip played, "New").
- **Status tag:** amber or coral tint with matching text at Caption, explained by a tooltip.

### FDR Chips
A 28px-min by 22px chip at 6px radius with the rating written in Caption / 500, shaded per the Soft Tint Rule. In grids the same tints scale up to 42px cells (opponent over a small sub-line), with a 1px white inset ring on hover and a dashed strong hairline for a blank gameweek.

### Cards / Containers
- **Corner Style:** 18px.
- **Background:** graphite (#1b1b1d), on ink.
- **Shadow Strategy:** none; see Elevation & Depth.
- **Border:** none.
- **Internal Padding:** 20px (24px on legacy `.glow-card` panels); 0 when a table or grouped list fills it. Panel titles are Headline over a Footnote tertiary line, 16px above content.

### Grouped Lists and Tables
The iOS Settings pattern, used for standings, rivals, squads and every data table. One graphite panel; header cells in Footnote / 500 secondary text; rows separated by hairlines inset from the text edge (the planner's squad hairline starts at the name, 56px in); text and row headers left, numbers right in tabular figures at 500; no zebra. Hover is a 3% white wash; your own row is lime wash with a lime rank number. Sticky identity columns stay graphite with a 1px strong-hairline edge.

### Heat-Shaded Cells
Stats Explorer cells follow the Quiet Heat Rule: a white wash up to 16% scaled by `--sx-level`, text weight rising to 600 for strong values, the top cells on a 20% lime tint with lime text, and a light tooltip (text-colour ground, ink text, 6px radius) carrying the rank.

### Inputs / Fields
- **Style:** translucent fill, no border, 10px radius, 36px tall, 0 12px padding, Body. Selects add an authored chevron and 34px right padding. Field labels sit 6px above in Footnote secondary, sentence case.
- **Focus:** 2px lime outline at 2px offset; no halo or glow.
- **Placeholder:** tertiary text.

### Navigation
A fixed 220px sidebar of translucent graphite (blur 20px, saturate 180%) with a 1px hairline right edge. The wordmark is Section weight 600 in text colour. Groups are 20px apart under Footnote / 500 tertiary headings; links are 36px rows with a 20px icon slot and a Body label in soft text, 10px radius. Hover is a 5% white wash; the current page (`a.active`) is a raised fill with text-colour label at 500 and a lime icon. That lime icon is the sidebar's one lime thing. At 734px the sidebar becomes a 52px top bar with a 36px round menu button; the menu drops down as a solid graphite sheet (a nested blur would not render) with 44px rows.

### Notes, Empty, Loading and Error States
Honest messaging is a component. Empty and note text is Footnote tertiary. A note panel is the amber tint (`tint-warn`) with secondary text, 10px radius, 12px by 16px, and no side stripe. Loading is Body tertiary with 32px vertical padding. Errors are a coral 8% tint with a 40% coral 1px border and soft pink text, 10px radius.

### Price Change
Quiet text, not a pill: an arrow and percentage in lime (or coral) Caption beside the name, with a tooltip saying what it measures.

### Match Pitch (signature)
A 105:68 striped pitch (68:100 portrait on phones) in the pitch tokens at 10px radius, 16% white line art, and 30px round player tokens (home in us-light with ink numbers, away in hover graphite with a strong hairline ring). A just-on player gets a lime ring; a player sent off is a dashed coral ring at 38% opacity. Tokens glide 0.35s with `cubic-bezier(0.16, 1, 0.3, 1)` only when the user moves the match cursor.

### Motion
Motion only answers the user: colour and background transitions on hover and press (0.15s ease), the segmented selection (0.2s ease-out), the phone bottom sheet rising when opened (0.22s), pitch tokens following the cursor. No entrance fades, no hover lifts. `prefers-reduced-motion` collapses every transition and animation to 0.01ms globally.

## Do's and Don'ts

### Do:
- **Do** take every colour, size, radius and spacing from the `--aero-*` and `--fs-*` tokens; raw hex lives only in `design-system.css` and `tokens.ts`.
- **Do** keep each screen area to one lime thing: the primary action or where you are.
- **Do** put content in the shared 1200px column (`.aero-page` or `.page`) and start every heading, panel and table on its left edge.
- **Do** build panels as flat graphite (#1b1b1d) at 18px radius with no border or shadow.
- **Do** separate rows with inset hairlines, put text left and numbers right, and use tabular figures.
- **Do** use a segmented control for five options or fewer, with the #636366 selected segment at `calc(var(--aero-radius-sm) - 2px)`.
- **Do** show fixture difficulty and status as soft tints with the number or word written in.
- **Do** write sentence case in British English, for buttons and headers too.
- **Do** keep motion to responses to the user and respect `prefers-reduced-motion`.
- **Do** run `node scripts/design-audit.mjs` from `frontend/` before shipping; every count should stay at its target.

### Don't:
- **Don't** fill FDR, status, tabs, segments or the active sidebar row with solid lime.
- **Don't** add card shadows, gradients on buttons or panels, or borders round panels.
- **Don't** use font sizes outside the seven tokens, weights above 600, or text under 12px.
- **Don't** use all-caps or tracked labels anywhere.
- **Don't** add breakpoints beyond 1068px and 734px, or radii beyond the four.
- **Don't** zebra-stripe tables or centre numbers and row headers.
- **Don't** animate anything the user did not trigger: no entrance fades, hover lifts or decorative loops.
- **Don't** let colour alone carry meaning; the number, word or accessible label travels with it.
