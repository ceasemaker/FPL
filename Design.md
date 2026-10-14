---
name: AeroFPL
description: Honest-depth Fantasy Premier League decision tools on a dark graphite ground with a single lime voice.
colors:
  lime: "#a5ff01"
  lime-dim: "#78c800"
  lime-wash: "rgba(165, 255, 1, 0.12)"
  band-olive: "#6f9e1c"
  band-moss: "#33461a"
  ink: "#101011"
  surface: "#191919"
  surface-raised: "#1f2020"
  surface-hover: "#242424"
  sheet: "#151616"
  row: "#171818"
  row-alt: "#1a1b1b"
  row-hover: "#212222"
  row-selected: "#1e2615"
  line: "#2e2f30"
  line-strong: "#3a3b3c"
  text: "#ffffff"
  text-dim: "#b7b7b7"
  text-muted: "#8f8f8f"
  paper: "#f4f4f2"
  negative: "#ff4c5e"
  warn: "#e2b75b"
  fdr-2: "#b8e986"
  fdr-3: "#95ae67"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "clamp(1.8rem, 2.6vw, 2.5rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.045em"
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.88rem"
    fontWeight: 400
    lineHeight: 1.55
  data:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.82rem"
    fontWeight: 400
    lineHeight: 1.2
    fontFeature: "tnum"
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.04em"
rounded:
  badge: "5px"
  segment: "7px"
  sm: "10px"
  overlay: "14px"
  md: "16px"
  sheet: "18px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "14px"
  lg: "18px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    height: "42px"
    padding: "0 18px"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    height: "42px"
    padding: "0 18px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-hover}"
  button-tool:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    height: "38px"
    padding: "0 13px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    height: "42px"
    padding: "0 12px"
  lens-pill:
    backgroundColor: "transparent"
    textColor: "{colors.text-dim}"
    rounded: "{rounded.pill}"
    height: "36px"
    padding: "0 16px"
  lens-pill-active:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.ink}"
  segmented-option:
    backgroundColor: "transparent"
    textColor: "{colors.text-dim}"
    rounded: "{rounded.segment}"
    height: "28px"
    padding: "0 11px"
  segmented-option-active:
    backgroundColor: "{colors.surface-hover}"
    textColor: "{colors.text}"
  provenance-badge:
    backgroundColor: "transparent"
    textColor: "{colors.warn}"
    rounded: "{rounded.badge}"
    padding: "1px 5px"
  chip-accent:
    backgroundColor: "{colors.lime-wash}"
    textColor: "{colors.lime}"
    rounded: "{rounded.pill}"
    padding: "4px 9px"
  card:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.md}"
    padding: "18px"
  data-cell-top:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.ink}"
  data-cell-high:
    backgroundColor: "{colors.band-olive}"
    textColor: "{colors.ink}"
  data-cell-mid:
    backgroundColor: "{colors.band-moss}"
    textColor: "{colors.text}"
---

# Design System: AeroFPL

## Overview

**Creative North Star: "The Lit Instrument Panel"**

AeroFPL is a dark graphite instrument for weekly FPL decisions. The ground is near-black ink, surfaces step up in small tonal increments, and one lime voice lights only what matters: the current selection, the primary action, and the best numbers on the sheet. Everything else stays grey so that lime always means something.

Density is high and earned. Data surfaces are sheets, not dashboards of tiles: tight 34px rows, 1px hairlines, tabular figures, frozen identity columns. The system's honesty commitment from the product is visual too: provenance and limits ("PL only", "Estimate", stale-snapshot notes) are first-class components drawn in a warm amber, never hidden. Colour never carries meaning alone; weight, text and accessible labels travel with it.

The tokens and shared primitives live in `frontend/src/styles/design-system.css` (the `--aero-*` custom properties and `.aero-*` classes). `frontend/src/theme.css` still carries an older palette (pure black, iOS grey, blue tertiary, pill buttons); it is legacy, not the system.

**Key Characteristics:**
- Graphite ink ground with tonal surface steps, no pure black.
- One accent, lime, reserved for selection, primary action and top-band data.
- Inter throughout; tabular numerals on every data surface.
- 10px controls, 16px containers, pills only for toggles, chips and tags.
- Authored 1.5px-stroke SVG icons on a 20px grid, currentColor.
- Provenance badges in amber wherever a number has a source caveat.

## Colors

A graphite neutral ramp under a single high-chroma Spring Bud lime, with amber and coral reserved for caveats and losses.

### Primary
- **Spring Bud Lime** (lime): selection, active lens pill, active nav item, sorted column header, focus outlines, checkbox and caret accent, and the top percentile band. Text on lime is always ink.
- **Pressed Lime** (lime-dim): the far end of lime gradients (primary button, signal bars).
- **Lime Wash** (lime-wash): tinted backgrounds for accent chips and quiet positive tags.

### Secondary
- **Olive Band** (band-olive) and **Moss Band** (band-moss): the two darker steps of the percentile ramp. They exist only for data shading; never use them as UI chrome.

### Neutral
- **Ink** (ink): page ground and text-on-lime.
- **Graphite Surface / Raised / Hover** (surface, surface-raised, surface-hover): controls, menus and their hover state, each one step lighter.
- **Sheet** (sheet): data containers, control bars and the card gradient's resting tone.
- **Row / Row Alt / Row Hover / Row Selected** (row, row-alt, row-hover, row-selected): table body zebra, hover and the faint lime-tinted selected row.
- **Hairline / Strong Hairline** (line, line-strong): internal dividers and container borders respectively.
- **White / Dim / Muted text** (text, text-dim, text-muted): primary, secondary and tertiary copy.
- **Paper** (paper): the light inverse surface for the hover tooltip and toast, so transient feedback reads apart from the dark sheet.

### Status
- **Coral** (negative): losses, price falls, unavailable status.
- **Amber** (warn): caveats, provenance badges, doubtful status, "soon" markers, stale-data notes.
- **Fixture difficulty ramp**: lime, fdr-2, fdr-3, amber, coral for FDR 1 to 5.

### Named Rules
**The One Voice Rule.** Lime marks selection, the primary action and the best data only. If more than one non-data element per region is lime, one of them is wrong.

**The Percentile Ramp Rule.** Data cells are shaded by percentile within the player's position (or among the 20 clubs): top fifth lime with ink text at weight 700, next fifth olive with ink text at weight 600, middle fifth moss with white text, fourth fifth unshaded dim text, bottom fifth unshaded muted text. Colour plus weight, never colour alone; every shaded cell carries its percentile and cohort in its accessible label and in a hover/focus tooltip.

**The Amber Caveat Rule.** Amber means "read this number with care". It is never decoration and never a second accent.

## Typography

**Display Font:** Inter (with -apple-system, BlinkMacSystemFont, sans-serif)
**Body Font:** Inter
**Label Font:** Inter

**Character:** One family, worked through weight and tight negative tracking at the top of the scale. Headings are compact and confident; data is small, even and aligned.

### Hierarchy
- **Display** (700, clamp(1.8rem, 2.6vw, 2.5rem), 1.05, -0.045em): page titles. Data surfaces may run slightly smaller (1.9rem desktop, 1.55rem phone) to give rows the viewport.
- **Headline** (700, 1.4rem, -0.02em): drawer and sheet titles, player names in a profile.
- **Title** (700, 1.1rem, -0.02em): card and section titles.
- **Body** (400, 0.88rem, 1.55): descriptions and notes, capped near 62ch.
- **Data** (400, 0.82rem, tabular numerals): table cells and split tables; numbers right-aligned.
- **Label** (600, 0.7rem, 0.04em, sentence case): control legends, column group headers, sub-lines.

### Named Rules
**The Tabular Rule.** Every surface that shows comparable numbers sets `font-variant-numeric: tabular-nums` and right-aligns numeric columns.

**The Sentence Case Control Rule.** Button and control text is sentence case with no extra tracking. The legacy global `button` style in `theme.css` uppercases with 0.3em tracking; aero surfaces override it, and new surfaces must too.

## Layout

A fixed 196px navigation rail on the left; pages sit beside it with 22px/24px padding and a faint lime radial glow high on the ink ground. At 1050px and below the rail collapses to an 86px icon rail; at 720px and below it becomes a 64px top bar with a menu button and the page takes the full width with 14px side padding.

Spacing runs in a tight 6 / 8 / 14 / 18 / 24px rhythm. Data surfaces stack title row, one control bar and the sheet with 14px gaps; the sheet scrolls inside its own container with a sticky two-row header (group row 24px, label row 38px) and a frozen identity column (290px desktop, 124px phone). Body rows are 34px on desktop and grow to 48px on phones for touch.

On phones, secondary filters leave the bar for a bottom sheet behind a Filters button that shows an active count, lens pills become a horizontally scrolling strip with a fade mask, and the compare tray docks to the bottom edge.

## Elevation & Depth

Hybrid. Resting data surfaces are flat and separated by tone and hairlines; general content cards carry one soft ambient shadow; overlays (menus, tray, drawer, toast) lift with deeper, darker shadows. There are no hard offset shadows and no glows on data.

### Shadow Vocabulary
- **Card ambient** (`box-shadow: 0 14px 38px rgba(0, 0, 0, 0.22)`): `.aero-card` content cards.
- **Menu** (`box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5)`): dropdown panels such as Saved views and Columns.
- **Tray** (`box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55)`): the floating compare tray.
- **Drawer** (`box-shadow: -18px 0 50px rgba(0, 0, 0, 0.5)`): the right-side profile drawer.
- **Segment lift** (`box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4)`): the active option in a tab switch.

### Named Rules
**The Flat Sheet Rule.** Tables and control bars never cast shadows; depth there comes from the surface ramp and 1px lines. Shadow is for things that float.

## Shapes

Two radii do almost all the work: 10px for controls (buttons, inputs, selects, segmented tracks) and 16px for containers (cards, control bars, the table container). Overlays sit between at 14px; the phone bottom sheet rounds only its top corners at 18px. Full pills (999px) are reserved for toggles and tokens: lens pills, chips, compare-tray chips. Small inline badges use 4–5px. Borders are always 1px; dashed 1px marks an empty or no-results state.

## Components

### Buttons
Quiet and solid; the primary is the only lit one.
- **Shape:** gently rounded (10px), 42px tall (38px in dense toolbars).
- **Primary:** lime gradient (#b8ff37 to #8fe800) with ink text at 700. One per region.
- **Secondary:** raised graphite with a strong hairline border, white text at 600; hover steps to surface-hover.
- **Toggle-on tool button:** graphite with a half-strength lime border and lime text (e.g. Watchlist on).
- **Icon button:** 34px square, transparent, dim icon brightening on hover.
- **Focus:** 2px lime outline at 2px offset on every interactive element. Disabled at 45% opacity.

### Chips
- **Accent chip:** lime wash ground, lime text, pill.
- **Neutral chip:** raised graphite, strong hairline, dim text, pill.
- **Compare chip:** 32px pill on surface-hover with an inline remove icon button.

### Lens Pills
A horizontal row of pill toggles choosing the active view. Unselected: transparent with a strong hairline and dim text. Selected: solid lime with ink text. The same grammar appears in Chart Lab's tag pickers.

### Segmented Controls
A 3px-padded graphite track (10px radius) holding 28px options (7px radius). The active option steps to surface-hover with white text and an inset half-strength lime ring. Disabled options stay visible in muted text with an amber "soon" marker rather than disappearing. The heavier variant (Players / Teams tabs) uses 34px options and the segment-lift shadow instead of the lime ring.

### Cards / Containers
- **Corner Style:** 16px.
- **Background:** sheet tone; content cards use a subtle 145deg gradient from #1b1c1c to the sheet tone.
- **Shadow Strategy:** card ambient for content cards; none for data containers (see Elevation).
- **Border:** 1px strong hairline.
- **Internal Padding:** 18px (control bars 10–14px).

### Inputs / Fields
- **Style:** graphite surface, 1px strong hairline, 10px radius, 42px (36px inside control bars).
- **Search field:** icon plus borderless input inside a bordered shell; the shell border turns 60% lime on focus-within.
- **Focus:** 2px lime outline at 2px offset. Checkboxes use lime as accent colour.

### Navigation
A fixed graphite rail with the wordmark ("Aero" white, "FPL" lime), 48px rows with an authored 20px icon and an 0.86rem label, dim by default and white on hover over #202121. The active row is a lime gradient with ink text. Collapses to an icon rail at 1050px and a top bar with a menu toggle at 720px.

### Icons
Authored inline SVG on a 20px viewBox, 1.5px round-capped, round-joined strokes in currentColor, `aria-hidden`. Shared by the primary nav (`components/navIcons.tsx`) and the Stats Explorer (`components/statsExplorer/icons.tsx`); new icons follow the same drawing rules.

### Provenance Badge
A small amber-outlined tag (5px radius, 0.6rem, 700) that sits beside a column header or stat label: "PL only" when a column counts Premier League matches only, "Estimate" when the number is modelled. It carries a title explaining the limit. It appears the moment the condition is true and never decorates a clean number.

### Data Sheet
The signature component. A sortable table inside a 16px sheet container: sticky grouped header, frozen identity column separated by a 1px strong-hairline edge, 34px zebra rows, tabular right-aligned numbers, and percentile shading per the Percentile Ramp Rule. The sorted header turns lime. Cells are keyboard-navigable; hover or focus shows a paper tooltip with the exact rank and cohort. A one-line key above the sheet shows the three swatches and what shading means.

### Compare Tray
A floating bar fixed to the bottom of the page beside the rail (full width minus 10px on phones), sheet-dark with a 35% lime border, 14px radius and tray shadow. Selected items sit as removable chips with a count and the actions (compare, chart) on the right; on phones it stacks with full-width actions.

### Side Drawer
A right-side panel up to 460px (full width on phones) over a 45% black scrim, with a strong-hairline left edge and drawer shadow. It slides in 28px over 0.22s with cubic-bezier(0.16, 1, 0.3, 1), suppressed under reduced motion. Contents: headline, action buttons, a two-cell minutes grid, a split table with thin percentile bars, and collapsible detail sections.

### Bottom Sheet
On phones, a native `<dialog>` docked to the bottom edge, 18px top corners, max 88vh, 55% black backdrop, rising 24px with the drawer's easing. Header with title and close, a scrolling body of stacked controls, and a footer with full-width actions.

### Notes and States
Honest messaging is a component: muted 0.78rem copy in a bordered graphite panel for stale or partial data, a dashed-border sheet for empty and no-results states, a shimmering row skeleton for loading, and a coral-tinted panel for errors.

## Do's and Don'ts

### Do:
- **Do** take every colour, radius and shadow from the `--aero-*` tokens in `design-system.css` rather than re-declaring hex values.
- **Do** shade comparable numbers by percentile within a fair cohort, and pair each shade with weight and an accessible label carrying the rank.
- **Do** set tabular numerals and right-align numbers on every data surface.
- **Do** badge a number's provenance ("PL only", "Estimate") in amber whenever its source has a limit.
- **Do** draw new icons as 20px, 1.5px-stroke, currentColor SVG.
- **Do** keep control text in sentence case with no added tracking, overriding the legacy global button style.
- **Do** move secondary filters into a bottom sheet on phones and keep the frozen identity column.

### Don't:
- **Don't** use lime for secondary actions, ornaments or non-top data; beyond the faint radial glow on the page ground, it is the single voice.
- **Don't** let colour alone carry meaning in shading, status or difficulty.
- **Don't** use the olive or moss band colours outside data shading.
- **Don't** reach for `theme.css` tokens (pure black, #8E8E93 grey, #007AFF blue) or its pill-shaped buttons and inputs on new surfaces.
- **Don't** put shadows on tables or control bars.
- **Don't** use emoji or text glyphs as icons.
