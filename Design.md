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
  side-us: "#e8e8e8"
  side-them: "#8f8f8f"
  comp-europe: "#7aa7ff"
  comp-cup: "#c59bff"
  negative: "#ff4c5e"
  warn: "#e2b75b"
  fdr-2: "#b8e986"
  fdr-3: "#95ae67"
typography:
  scoreboard:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "clamp(3rem, 5.4vw, 4.6rem)"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "-0.05em"
    fontFeature: "tnum"
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
  section:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  summary:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "0.98rem"
    fontWeight: 400
    lineHeight: 1.55
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
  micro: "3px"
  badge: "5px"
  segment: "7px"
  sm: "10px"
  panel: "12px"
  overlay: "14px"
  md: "16px"
  sheet: "18px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "14px"
  gutter: "16px"
  lg: "18px"
  xl: "24px"
  section: "36px"
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
  tool-pill:
    backgroundColor: "transparent"
    textColor: "{colors.text-dim}"
    rounded: "{rounded.pill}"
    height: "32px"
    padding: "0 13px"
  tool-pill-pressed:
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
  filter-segment:
    backgroundColor: "transparent"
    textColor: "{colors.text-dim}"
    rounded: "{rounded.segment}"
    padding: "6px 12px"
  filter-segment-pressed:
    backgroundColor: "{colors.lime}"
    textColor: "{colors.ink}"
  view-switch-current:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.segment}"
    padding: "7px 14px"
  provenance-badge:
    backgroundColor: "transparent"
    textColor: "{colors.warn}"
    rounded: "{rounded.badge}"
    padding: "1px 6px"
  competition-tag:
    backgroundColor: "transparent"
    textColor: "{colors.text-dim}"
    rounded: "{rounded.badge}"
    padding: "2px 6px"
  competition-tag-europe:
    textColor: "{colors.comp-europe}"
  competition-tag-cup:
    textColor: "{colors.comp-cup}"
  result-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-dim}"
    rounded: "{rounded.segment}"
    size: "30px"
  result-chip-win:
    textColor: "{colors.lime}"
  result-chip-loss:
    textColor: "{colors.negative}"
  chip-accent:
    backgroundColor: "{colors.lime-wash}"
    textColor: "{colors.lime}"
    rounded: "{rounded.pill}"
    padding: "4px 9px"
  card:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.md}"
    padding: "18px"
  content-sheet:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.md}"
    padding: "16px 18px"
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

AeroFPL is a dark graphite instrument for weekly FPL decisions and for reading the football behind them. The ground is near-black ink, surfaces step up in small tonal increments, and one lime voice lights only what matters: the current selection, the primary action, the best numbers, the minute or day you are standing on, and a win. Everything else stays grey so that lime always means something.

Density is high and earned. Data surfaces are sheets, not dashboards of tiles: tight rows, 1px hairlines, tabular figures, frozen identity columns. The football pages (Match, Matches, Team, Player) open with words before charts: a plain-language summary paragraph sits under every header, and every section title carries a one-line note on what the section counts and what it cannot. The product's honesty commitment is visual too: provenance and limits ("PL only", "Estimate", "Full-match totals") are first-class amber components, never hidden. Colour never carries meaning alone; position, weight, written tags and accessible labels travel with it.

The tokens and shared primitives live in `frontend/src/styles/design-system.css` (the `--aero-*` custom properties and `.aero-*` classes). The football pages share a second, page-scoped layer: the `.mp-*` classes in `frontend/src/pages/MatchPage.css`, which the Team and Player pages reuse by carrying `mp-page` on their root. The live navigation rail (`.command-nav*`) lives at the top and end of `frontend/src/theme.css`; the rest of `theme.css` (pure black, iOS grey, blue tertiary, pill buttons) is legacy, not the system.

**Key Characteristics:**
- Graphite ink ground with tonal surface steps, no pure black.
- One accent, lime, reserved for selection, primary action, the "now" marker, wins and top-band data.
- Us light above the line, them grey below: position, not hue, says which side.
- Inter throughout; tabular numerals on every data surface.
- 10px controls, 16px sheets, 7px chips and segments, pills only for toggles, chips and tags.
- Authored SVG icons on a 20px grid; never glyphs.
- Amber provenance badges wherever a number has a source caveat.

## Colors

A graphite neutral ramp under a single high-chroma Spring Bud lime, a light-grey/mid-grey pair for the two sides of a match, two competition tints, and amber and coral reserved for caveats and losses.

### Primary
- **Spring Bud Lime** (lime): selection, pressed segment and tool pill, active nav row, sorted column header, focus outlines, the Match page's minute cursor and captain mark, today's date in the calendar, a win in a result, link hover on player and club names, and the top percentile band. Text on lime is always ink.
- **Pressed Lime** (lime-dim): the far end of lime gradients (primary button, signal bars).
- **Lime Wash** (lime-wash): tinted backgrounds for accent chips, quiet positive tags and the club's own row in the league table.

### Secondary
- **Olive Band** (band-olive) and **Moss Band** (band-moss): the two darker steps of the percentile ramp. They exist only for data shading; never use them as UI chrome.
- **Us Light** (side-us, `--mp-home`): the home side on a match, "for" on a team page, a player's middle-band percentile bar. Bars rise above an axis.
- **Them Grey** (side-them, `--mp-away`): the away side, "against", the low percentile bar. Bars hang below the axis. Same value as muted text by design: the other side recedes.

### Tertiary
- **Europe Blue** (comp-europe): Champions League, Europa League, Conference League and Super Cup games.
- **Cup Violet** (comp-cup): League Cup, FA Cup and Community Shield games.
- The Premier League is neutral graphite: no tint. Tints appear only on competition tags and calendar cells, as a 12–13% fill with a 40–50% border, never as text colour elsewhere.

### Neutral
- **Ink** (ink): page ground and text-on-lime.
- **Graphite Surface / Raised / Hover** (surface, surface-raised, surface-hover): controls, segment tracks, chips and their hover state, each one step lighter.
- **Sheet** (sheet): data containers, control bars and the resting tone of the sheet gradient.
- **Row / Row Alt / Row Hover / Row Selected** (row, row-alt, row-hover, row-selected): table body zebra, hover and the faint lime-tinted selected row.
- **Hairline / Strong Hairline** (line, line-strong): internal dividers and container borders respectively.
- **White / Dim / Muted text** (text, text-dim, text-muted): primary, secondary and tertiary copy.
- **Paper** (paper): the light inverse surface for the hover tooltip and toast.

### Status
- **Coral** (negative): losses, red cards, a player sent off, price falls, injured news, errors.
- **Amber** (warn): caveats, provenance badges, doubtful news, VAR, "soon" markers, short-rest dots in the calendar, stale-data notes.
- **Fixture difficulty ramp**: lime, fdr-2, fdr-3, amber, coral for FDR 1 to 5, as solid 6px-radius tags with the number written in them.
- Match event icons use real card colours (yellow card, coral red card); those colours live only in the icons.

### Named Rules
**The One Voice Rule.** Lime marks selection, the primary action, "now" (cursor, today), a win, and the best data only. If more than one non-data element per region is lime, one of them is wrong.

**The Us Above, Them Below Rule.** Whenever two sides are compared (home and away, for and against), the subject is the light bar above the axis or on the left, the other side the grey bar below or on the right. Position carries the meaning; the two greys only reinforce it, and a legend or key names both.

**The Written Tag Rule.** A competition is always named by its short written tag (PL, UCL, UEL, UECL, USC, EFL, FAC, CS). Europe blue and cup violet help the eye group games; the tag carries the meaning. The league is the default and stays untinted.

**The Result Rule.** Results read W, D, L in words or letters first; W is lime, L is coral, D stays dim. On chips the colour sits on a 60% border and the letter, never on a filled background.

**The Percentile Ramp Rule.** Data cells are shaded by percentile within the player's position (or among the 20 clubs): top fifth lime with ink text at weight 700, next fifth olive with ink text at weight 600, middle fifth moss with white text, fourth fifth unshaded dim text, bottom fifth unshaded muted text. Colour plus weight, never colour alone; every shaded cell carries its percentile and cohort in its accessible label and in a hover/focus tooltip.

**The Amber Caveat Rule.** Amber means "read this number with care". It is never decoration and never a second accent.

## Typography

**Display Font:** Inter (with -apple-system, BlinkMacSystemFont, sans-serif)
**Body Font:** Inter
**Label Font:** Inter

**Character:** One family, worked through weight and tight negative tracking at the top of the scale. Headings are compact and confident; data is small, even and aligned.

### Hierarchy
- **Scoreboard** (800, clamp(3rem, 5.4vw, 4.6rem), 0.95, -0.05em, tabular): the Match page score only; a kick-off time drops to clamp(2rem, 3.6vw, 3rem), phones 2.6rem.
- **Display** (700, clamp(1.8rem, 2.6vw, 2.5rem), 1.05, -0.045em): page titles. Football pages tune within the same range: club name clamp(1.8rem, 3vw, 2.6rem), player name clamp(1.7rem, 2.8vw, 2.5rem), the two match team names clamp(1.5rem, 2.2vw, 2.1rem) and 1rem on phones.
- **Headline** (700, 1.4rem, -0.02em): drawer and sheet titles.
- **Section** (700, 1.3rem, -0.025em): section titles on the football pages, with a muted 0.8rem note line beneath.
- **Title** (700, 1.1rem, -0.02em): card titles and the momentum band heading (1.05rem).
- **Summary** (400, 0.98rem, 1.55–1.6): the plain-language paragraph under a header, 68–80ch; the calendar takeaway runs at 1rem.
- **Body** (400, 0.88rem, 1.55): descriptions and notes, capped near 62ch.
- **Data** (400, 0.8–0.82rem, tabular numerals): table cells; numbers right-aligned. Key figures in compare rows and fact lists rise to 0.95–1.05rem at 700–800.
- **Label** (600–700, 0.64–0.72rem, sentence case): column headers, fact terms, legends, sub-lines.

### Named Rules
**The Tabular Rule.** Every surface that shows comparable numbers, scores, minutes or dates sets `font-variant-numeric: tabular-nums` and right-aligns numeric columns.

**The Sentence Case Control Rule.** Button and control text is sentence case with no extra tracking. The legacy global `button` style in `theme.css` uppercases with 0.3em tracking; every aero page root resets it (`text-transform: none; letter-spacing: 0`), and new surfaces must too. Uppercase tracked text appears only as structural dividers: nav group titles, calendar month marks, and competition separator rows in a match log.

## Layout

A fixed 196px navigation rail on the left; pages sit beside it with 22px/24px padding and a faint lime radial glow high on the ink ground. Football pages cap their content at 1340px. At 1050px and below the rail collapses to an 86px icon rail; at 720px and below it becomes a 64px top bar with a menu button and the page takes the full width.

Spacing runs in a tight 6 / 8 / 14 / 16 / 18 / 24px rhythm; sections on the football pages are separated by a 36px section-title gap, and sheets in a row sit 16–18px apart. Every football page follows the same spine: breadcrumb (0.76rem, muted, slash-separated), header, summary paragraph, filters if any, then titled sections of sheets, ending in a muted 0.72rem source footnote naming the feeds and their limits.

Per page:
- **Match** (`/matches/:id`): three-column header (home, score, away) with crests and scorers; summary centred under it; the full-width momentum sheet; a 7/12 + 5/12 split of pitch and "now" panel; "The full match" (two sheets: team compare and shot zones); "Every player" (sortable table); "Going into the match" (three context sheets: form, meetings, FPL or odds; two for cup games). Phones stack everything to one column and move scorers under the score.
- **Matches** (`/matches`): title with a view switch (Calendar / Fixture planner), takeaway line, a tool row (date stepper, competition filter, Calendar/List filter), a legend, then either the calendar grid (frozen 92px club column, 46px day columns, 44px rows, today lime, weekends faintly lifted) or the list (day headings over sheets of five-column match rows).
- **Team** (`/teams/:id`): crest, name, a line of league facts and the last-five result chips, a season select; summary; three filter segments (competition, venue, games) with a written count line; "Game by game" xG strip; "Per game, for and against" (compare + shot zones); "Every game" log; then a 1.6fr / 1fr pair of Squad and Premier League table. The `/teams` index is a 240px-min auto-fill grid of 12px-radius club tiles.
- **Player** (`/players/:id`): 96×116 portrait tile with the club crest in its corner, name, position and club, a fact list, price panel; injury or doubt news as a coral or amber panel; summary; then a two-column grid of sheets: season by competition, how he compares, every game, what's next, FPL this gameweek, where he played.

Grids collapse to one column at 1050px (team and player pairs) or 720px (match splits); phone table rows grow to 44px for touch. On data-room pages, secondary filters leave the bar for a bottom sheet behind a Filters button, lens pills become a horizontally scrolling strip, and the compare tray docks to the bottom edge; on the football pages segment tracks scroll horizontally instead.

## Elevation & Depth

Hybrid. Data-room sheets are flat and separated by tone and hairlines; content sheets and cards carry one soft ambient shadow; overlays (menus, tray, drawer, toast) lift with deeper, darker shadows. There are no hard offset shadows.

### Shadow Vocabulary
- **Card ambient** (`box-shadow: 0 14px 38px rgba(0, 0, 0, 0.22)`): `.aero-card`, every `.mp-sheet`, and the calendar grid container.
- **Menu** (`box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5)`): dropdown panels such as Saved views and Columns.
- **Tray** (`box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55)`): the floating compare tray.
- **Drawer** (`box-shadow: -18px 0 50px rgba(0, 0, 0, 0.5)`): the right-side profile drawer.
- **Segment lift** (`box-shadow: 0 1px 2px rgba(0, 0, 0, 0.4)`): the active option in a heavy tab switch.
- **Token lift** (`box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4)`): player tokens on the match pitch.

### Named Rules
**The Flat Sheet Rule.** Tables that scroll in place inside their own bordered wrapper (the Stats Explorer sheet, the Match page's "Every player" table) never cast shadows; depth comes from the surface ramp and 1px lines. Short tables and lists that sit inside a content sheet ride that sheet's ambient shadow.

## Shapes

Two radii do most of the work: 10px for controls (buttons, inputs, selects, segment tracks, inner panels) and 16px for sheets and containers. Seven pixels is the chip radius: segment options, result chips, calendar cells. Twelve pixels rounds the pitch, error panels and club tiles; overlays sit at 14px (also the calendar's day-list sheets); the phone bottom sheet rounds its top corners at 18px. Full pills (999px) are reserved for toggles and tokens: lens pills, the momentum jump buttons, the player-table team pills, chips. Inline tags use 4–5px; the micro competition tag hung on a chip uses 3px. Borders are always 1px (the goal-mouth frame is the one 2px line); dashed 1px marks an empty, "earlier games" or sent-off state.

## Components

### Buttons
Quiet and solid; the primary is the only lit one.
- **Shape:** gently rounded (10px), 42px tall (38px in dense toolbars, 34px in the calendar date stepper).
- **Primary:** lime gradient (#b8ff37 to #8fe800) with ink text at 700. One per region.
- **Secondary:** raised graphite with a strong hairline border, white text at 600; hover steps to surface-hover.
- **Toggle-on tool button:** transparent or graphite with a half-strength lime border and lime text (Watchlist on, the momentum Play button).
- **Icon button:** 34px square, transparent, dim icon brightening on hover.
- **Focus:** 2px lime outline at 2px offset on every interactive element. Disabled at 45% opacity.

### Chips
- **Accent chip:** lime wash ground, lime text, pill.
- **Neutral chip:** raised graphite, strong hairline, dim text, pill.
- **Compare chip:** 32px pill on surface-hover with an inline remove icon button.

### Lens Pills and Tool Pills
A horizontal row of pill toggles. Unselected: transparent with a strong hairline and dim text. Selected or pressed: solid lime with ink text, border gone. Lens pills (36px) choose the active view on data rooms and Chart Lab; tool pills (32px) choose a team in the Match page's player table and jump the momentum cursor.

### Segmented Controls
A 3px-padded graphite track (10px radius, 2px gap) holding 7px-radius options at 0.78rem / 700.
- **Filter segment** (football pages: competition, venue, last-N, calendar view): the pressed option (`aria-pressed="true"`) is solid lime with ink text. This is the default for new filter rows.
- **Scope segment** (Stats Explorer): 28px options; the active option steps to surface-hover with white text and an inset half-strength lime ring. Unavailable options stay visible in muted text with an amber "soon" marker. The heavier Players / Teams tab variant uses 34px options and the segment-lift shadow.
- **View switch** (a link pair between sibling routes, e.g. Calendar / Fixture planner): same track, the current route on surface-raised with white text; no lime, because it is navigation, not a filter.

### Sheets and Section Titles
The football pages' container. A `.mp-sheet` is a 16px-radius panel with the 145deg gradient from #1b1c1c to the sheet tone, a 1px strong hairline and card-ambient shadow; padding 16–18px, or 0 when a table fills it. Every group of sheets is introduced by a `.mp-sec-title`: a 1.3rem section heading and a muted 0.8rem line saying what the numbers cover, where any provenance badge sits inline. `.aero-card` is the same material for the data-room pages.

### Summary Paragraph
Under every football header: one or two plain sentences generated from the data (who won and how, a club's league position and form, a player's season), at Summary size in dim (Match, centred) or full white (Team, Player, the calendar takeaway). It is never a heading and never decorated.

### Competition Tags
A 0.6–0.62rem / 800 written tag in a 4–5px radius outline: graphite hairline and dim text for the league, Europe blue or cup violet text with a half-strength border for the others. On result chips and calendar cells, non-league games hang a 3px-radius micro tag (0.46–0.48rem) off the bottom edge; league games carry none.

### Result Chips
Square chips linking to the match: 30px on the Match page form rows (result over score), 38×36px on the Team header (result over opponent code). Graphite surface, strong hairline, dim text; W turns border and letter lime, L coral, D stays neutral; hover turns the border white. In tables and the xG strip, results are bold letters coloured by the same rule.

### Calendar Cell
A 38px-tall, 7px-radius graphite cell in a 46px day column: opponent code at 0.68rem / 800 over a sub-line (result and score once played, home/away plus the bookmakers' win chance before). Europe and cup cells take their tint as fill and border. Played cells sit at 82% opacity. An amber 6px dot marks short rest. Hover lifts 1px with a white border.

### Us-vs-Them Bars
Momentum (Match page): an SVG band with home bars above the axis and away bars below, future minutes at 16% opacity, event pins on the axis, a lime cursor line and lime minute tag, draggable and keyboard-focusable. Team compare rows: value, label and a 4px split bar (us light, them grey), the losing value muted at 500. Team xG strip: per-game columns, ours rising from the line, theirs hanging below at 75% opacity, the result letter beneath. Player compare rows: one 6px bar per stat in us light, lime for the top fifth, them grey for the low end, with the percentile written beside it.

### Match Pitch
A 105:68 striped green-graphite pitch (portrait 68:100 on phones) with 16% white line art. Players are 30px round tokens: home light with ink numbers, away dark graphite with a hairline ring; a lime captain dot, a lime ring for a player just on, a dashed coral ring at 38% opacity for a player off. Tokens glide over 0.35s with cubic-bezier(0.16, 1, 0.3, 1), suppressed under reduced motion.

### Crest
Club crests come only through the `Crest` component (`components/match/icons.tsx`): the Premier League's SVG badge first, the older PNG badge for cup and European opponents, and a hidden image (layout kept) when neither exists. Never a placeholder glyph or initials. Sizes: 16–24px inline, 34px on club tiles, 58px (42px phone) in the match header, 76px (54px phone) on the team header, 24px on the player portrait corner.

### Inputs / Fields
- **Style:** graphite surface, 1px strong hairline, 10px radius, 42px (36px inside control bars).
- **Search field:** icon plus borderless input inside a bordered shell; the shell border turns 60% lime on focus-within.
- **Focus:** 2px lime outline at 2px offset. Checkboxes use lime as accent colour.

### Navigation
A fixed graphite rail (gradient #171818 to #111212, 1px right edge) with the wordmark ("Aero" white, "FPL" lime). Three groups: the five sections (Home, Matches, Teams, Players, Chart Lab) as 48px rows with an authored 20px icon and an 0.86rem label; then "My FPL" (Decision Lab, Analyze Manager, Price Monitor) and "Data rooms" (Stats Explorer, Model Lab) as smaller 38px / 0.8rem rows under a top hairline and a 0.64rem uppercase group title. Rows are dim by default, white on #202121 hover; the active row (including routes that belong to a section, such as the fixture planner under Matches and compare under Players) is a lime gradient with ink text and `aria-current="page"`. Collapses to an icon rail at 1050px (group titles hidden) and a top bar with a menu toggle at 720px.

### Icons
Authored inline SVG on a 20px viewBox, `aria-hidden`. Interface icons use 1.5px round-capped, round-joined strokes in currentColor (`components/navIcons.tsx`, `components/statsExplorer/icons.tsx`). Match event icons (`components/match/icons.tsx`) are drawn in fixed meaning colours: ball, yellow and red cards, a lime-on / coral-off substitution pair, an amber VAR screen.

### Provenance Badge
A small amber-outlined tag (5px radius, 0.6–0.62rem, 700) beside a column header, stat label or section note: "PL only", "Estimate", "Opta momentum", "Full-match totals". It carries a title explaining the limit and appears only when the condition is true.

### Data Sheet
The data-room signature. A sortable table inside a 16px sheet container: sticky grouped header, frozen identity column separated by a 1px strong-hairline edge, 34–36px zebra rows, tabular right-aligned numbers, and percentile shading per the Percentile Ramp Rule. The sorted header turns lime. The Match page's player table follows the same build, with the single best FPL score lit lime.

### Compare Tray
A floating bar fixed to the bottom of the page beside the rail (full width minus 10px on phones), sheet-dark with a 35% lime border, 14px radius and tray shadow. Selected items sit as removable chips with a count and the actions on the right.

### Side Drawer
A right-side panel up to 460px (full width on phones) over a 45% black scrim, with a strong-hairline left edge and drawer shadow. It slides in 28px over 0.22s with cubic-bezier(0.16, 1, 0.3, 1), suppressed under reduced motion.

### Bottom Sheet
On phones, a native `<dialog>` docked to the bottom edge, 18px top corners, max 88vh, 55% black backdrop, rising 24px with the drawer's easing.

### Notes and States
Honest messaging is a component: muted 0.78–0.8rem copy for partial data (or in a bordered graphite panel on data rooms), a dashed-border sheet or button for empty and "earlier games" states, a shimmering skeleton block (1.4s, off under reduced motion) for loading, a coral-tinted 12px panel for errors, and coral or amber news panels for injured or doubtful players.

## Do's and Don'ts

### Do:
- **Do** take every colour, radius and shadow from the `--aero-*` tokens in `design-system.css` rather than re-declaring hex values.
- **Do** build football pages from the shared spine: breadcrumb, header, summary paragraph, `.mp-sec-title` plus `.mp-sheet` sections, source footnote.
- **Do** put the subject side light and above (or left), the other side grey and below (or right), and name both in a key.
- **Do** write the competition tag on every non-league game; tint is a helper, not the label.
- **Do** colour results W lime and L coral on the border and letter only, with the letter always present.
- **Do** use solid lime for the pressed option in filter segments and tool pills.
- **Do** load crests through the `Crest` component so cup and European opponents fall back cleanly.
- **Do** shade comparable numbers by percentile within a fair cohort, and pair each shade with weight and an accessible label carrying the rank.
- **Do** set tabular numerals and right-align numbers on every data surface.
- **Do** badge a number's provenance ("PL only", "Estimate", "Full-match totals") in amber whenever its source has a limit.
- **Do** draw new icons as 20px SVG: 1.5px currentColor strokes for interface icons.
- **Do** keep control text in sentence case with no added tracking, overriding the legacy global button style.

### Don't:
- **Don't** use lime for secondary actions or ornaments; beyond the faint radial glow on the page ground, it is the single voice.
- **Don't** let colour alone carry meaning in shading, status, side, result, competition or difficulty.
- **Don't** use the olive or moss band colours outside data shading, or the competition tints outside competition tags and calendar cells.
- **Don't** reach for `theme.css` tokens (pure black, #8E8E93 grey, #007AFF blue) or its pill-shaped buttons and inputs on new surfaces.
- **Don't** put shadows on tables that scroll in their own wrapper or on control bars.
- **Don't** use emoji or text glyphs as icons, markers or crest stand-ins.
