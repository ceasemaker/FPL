# AeroFPL redesign plan: Apple calm, our colours

Status: shipped site-wide, 26 Oct 2026. The mockups of Players and the
Transfer planner (`.impeccable/mocks/apple-redesign/`) were signed off, then
steps 2 to 5 were applied to every route. Run `node scripts/design-audit.mjs`
in `frontend/` for the current counts.

## 1. What is actually wrong

Measured in `frontend/src` today:

| Problem | Count now | Target |
| --- | --- | --- |
| Distinct font sizes | 126 (0.55rem to 3rem; 0.70, 0.72, 0.74, 0.75, 0.76, 0.78 and 0.80rem all in use) | 7 |
| Font weights | 500, 600, 700, 750, 800, 900, bold | 400, 500, 600 |
| Letter-spacing values | 43 | 3, set by the type scale |
| All-caps labels | 62 | 0 |
| Raw hex colours | 139 | 0 outside the token file |
| Corner radii | 43 | 4 |
| Breakpoints | 9 (480, 600, 640, 700, 720, 768, 900, 1050, 1051) | 2 |
| Colour token systems | 2 (`theme.css` `--bg-*`/`--accent-*`, 293 uses; `design-system.css` `--aero-*`, 1012 uses) | 1 |
| Inline `style={{}}` in TSX | 51 | Data-driven widths only |

The things in your screenshots, traced to code:

- **Mini-league table, team names centred and too big.** The team cell is a
  `<th scope="row">` and inherits the centred, bold header style
  (`PlannerPage.tsx:560`). Nothing tells it to sit left.
- **Mini-league row spills wider than the card above it.** The planner has no
  shared content width, so the four-column grid runs to the window edge while
  the squad card stops at about 1,040px.
- **"Transfer planner" wraps onto two lines in the sidebar.** The rail is 196px
  and the active state is a solid lime slab, so the eye lands there before the
  page.
- **The "+91.5%" pill beside player names.** `PriceChangeBadge` is a solid lime
  fill at 9px, sits flush against the name, and does not say what it measures
  (progress towards a price rise).
- **The select box with the thick lime glow.** The focus ring is a 3px halo, so
  a plain dropdown looks like an alert.
- **Ugly fonts.** Inter is loaded in five weights and used at 800 and 900 with
  tight tracking everywhere, plus a stray Space Grotesk and SF Mono. Everything
  shouts at once, so nothing leads.

## 2. Direction

**Apple Sports in AeroFPL colours.** Two Apple references, each for a
different job:

- **apple.com** for type, spacing and calm: big quiet headings, generous
  space, one clear action per area, sentence case everywhere.
- **Apple's own data apps** (Apple Sports, Stocks, Settings, Music on the Mac)
  for the screens with data: a translucent sidebar, inset grouped lists,
  segmented controls, right-aligned tabular numbers, hairline separators.

What stays: the graphite ground and the lime. What changes is how much lime
there is and where it goes.

## 3. Tokens

### Colour: same palette, stricter roles

| Name | Value | Use |
| --- | --- | --- |
| Ink | `#101011` | Page background (unchanged) |
| Graphite | `#1b1b1d` | Grouped lists, panels. Replaces `#151616`, `#171818`, `#191919`, `#1b1c1c`, `#1f2020` |
| Raised | `#262628` | Controls, hover, the selected sidebar row |
| Hairline | `rgba(255,255,255,0.09)` | Separators and outlines. Replaces `#2e2f30` / `#3a3b3c` borders |
| Text | `#f5f5f7` | Primary text (Apple's off-white, softer than `#fff`) |
| Secondary | `#a1a1a6` | Labels, meta, column headers |
| Tertiary | `#86868b` | Footnotes only (5.3:1 on Ink, passes AA) |
| Lime | `#a5ff01` | See the lime rule below |
| Red / Amber | `#ff4c5e` / `#e2b75b` | Data only: drops, flags, hard fixtures |

**The lime rule: one lime thing per screen area.** Lime marks either the
primary action ("Select to compare", "Save plan") or where you are (your row
in a league, the current gameweek). The sidebar's active row is no longer a
lime slab: it gets a Raised fill with a lime icon. Gradients on buttons and
cards go. Positive numbers in tables use lime text, never lime fills.

### Type

**Family:** the system stack, so Macs and iPhones get Apple's real SF Pro
with its optical sizes, and Inter is the fallback everywhere else:

```css
--font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Segoe UI", Roboto, sans-serif;
```

SF Pro cannot be self-hosted for Windows and Android: Apple's licence only
allows it on Apple platforms. Inter is the closest match and is loaded as a
variable font with its optical-size axis, so headings use the Display cut.
Space Grotesk and SF Mono go.

**Scale:** seven steps on Apple's own sizes. Nothing smaller than 12px.

| Role | Size / line | Weight | Tracking | Where |
| --- | --- | --- | --- | --- |
| Large title | 48 / 52 | 600 | -0.025em | Home only |
| Title | 32 / 38 | 600 | -0.02em | Page titles ("Players") |
| Section | 22 / 28 | 600 | -0.01em | "Your mini-leagues" |
| Headline | 17 / 22 | 600 | 0 | Card titles, player names |
| Body | 15 / 22 | 400 | 0 | Copy, table cells (numbers at 500) |
| Footnote | 13 / 18 | 400 | 0 | Meta, notes, column headers, field labels |
| Caption | 12 / 16 | 500 | 0 | Chips, FDR, price-change text |

All numbers use `font-variant-numeric: tabular-nums`. Sentence case only:
"Search", not "SEARCH". Intro paragraphs stop at 68 characters a line.

### Layout and shape

- **One column, one left edge.** Content sits in a 1,200px column inside the
  space beside the sidebar, with 32px gutters (24px tablet, 16px phone). Every
  heading, card and table starts on that edge. Nothing runs wider than it.
- **Spacing:** 4, 8, 12, 16, 24, 32, 48, 64. Sections 48 apart, panels padded
  20 to 24, rows at least 44 tall (Apple's touch minimum).
- **Radii:** 6 (chips), 10 (inputs, segmented controls), 18 (panels), pill
  (buttons). Four values in place of 43.
- **No card shadows.** Panels are Graphite on Ink, separated by contrast, not
  shadow.
- **Breakpoints:** Apple's own, 1068px and 734px.
- **Tables:** text left, numbers right, never centred. Separators are inset
  hairlines that start at the text edge, iOS style. No zebra stripes. Your
  row gets a lime wash and a lime rank number.

```
Desktop, 1440px
┌──────────┬───────────────────────────────────────────────────┐
│ AeroFPL  │   Players                                [Select] │ Title 32
│          │   Browse the squad pool, then compare.            │ Body, secondary
│ Home     │                                                   │
│ Matches  │   [ Search…        ] [All|GK|DEF|MID|FWD] [Team ▾]│ segmented control
│ Teams    │                                                   │
│▸Players  │   Name               Team  Pos  Cost  Owned  Pts  │ Footnote headers
│ Chart Lab│   ─────────────────────────────────────────────── │
│          │   Haaland  ▲92%      MCI   FWD  15.7  77.9%   66  │ hairline, inset
│ My FPL   │   De Cuyper          BHA   DEF   5.3  42.5%   60  │
│ …        │                                                   │
└──────────┴───────────────────────────────────────────────────┘
  220px      ← one 1,200px column, one left edge →
```

### Components

- **Sidebar:** 220px so labels never wrap, translucent material
  (`backdrop-filter: saturate(180%) blur(20px)`), 15px labels, 36px rows,
  group headings in Footnote secondary. On phones: a 52px blurred top bar with
  the same menu.
- **Buttons:** pills. Primary is solid lime with Ink text, no gradient.
  Secondary is Raised with Text. One primary per screen area.
- **Segmented control** for anything with five options or fewer (position,
  grid/list view, gameweek ranges). Selects only for long lists such as teams
  and leagues.
- **Focus:** 2px lime outline, 2px offset. No glow.
- **Grouped list:** the iOS Settings pattern for the mini-league lists, rivals
  and captains: Graphite panel, inset hairlines, name left, value right.
- **FDR chips:** 26 × 20, radius 6, Caption number. The colour ramp stays.
- **Price change:** quiet text, not a pill: `▲ 92%` in lime Caption, 8px from
  the name, with the tooltip "92% of the way to a price rise tonight".

### Motion

One kind only: the selection indicator slides in the sidebar and in
segmented controls (200ms, ease-out). No entrance fades and no hover lifts.
All of it turns off under `prefers-reduced-motion`.

## 4. Checked against the brief

- **"Feel like an Apple website" against a tool you open every week.** My first
  idea copied apple.com's centred hero headings onto every page. I dropped it:
  that pushes the data below the fold on a tool you check every week. Pages
  are left-aligned like Apple's own apps, and only Home gets a Large title.
- **"I love our colours."** A dark ground with one acid-green accent is a
  common default look, but it is your brand, so it stays. What makes it feel
  Apple is the discipline: lime goes from roughly every third element to one
  per area.
- **Pure black like Apple's dark mode?** No. `#101011` stays: it is part of
  the palette you like, and Graphite panels read better on it.
- **The one bold thing:** the lime rule. Everything else is quiet on purpose.

## 5. Rollout

Each step is its own commit, with screenshots at 1440px and 375px.

1. **Mockups.** Players list and Transfer planner (with mini-leagues) in the
   new system, for your sign-off.
2. **Foundation.** New tokens in `design-system.css`. Point the legacy
   `--bg-*`, `--text-*` and `--accent-*` variables at them so every old page
   moves at once. Font stack, global table rules, no global uppercase. Add a
   small `frontend/scripts/design-audit.mjs` that prints the counts in
   section 1, so progress is measurable.
3. **Shell.** Sidebar, phone top bar, page container, and a `PageHeader` and
   `Section` component used by every page.
4. **Primitives.** Button, SegmentedControl, Select, GroupedList, DataTable,
   FdrChip, PriceChange text. Shown together on a hidden `/design` route for
   review.
5. **Pages, most-used first.** Players, Planner, Home, Player page, Team page,
   Matches, then Stats Explorer (the largest stylesheet, 1,409 lines), Chart
   Lab, Analyze Manager, Price Monitor, DEFCON, Model Lab, Decision Lab, Rate
   my team, Watchlist.
6. **Clean-up.** Delete the leftovers in `theme.css` (1,117 lines, still
   headed "Fotmob-inspired") once nothing uses them. Rewrite `Design.md` from
   what shipped.

Done means the audit script shows at most 7 font sizes, no raw hex outside the
token file, 4 radii and 0 all-caps labels, and the per-page alignment scan
from 26 Oct comes back clean at 1440px and 375px.

Where it stands (26 Oct, second pass): every target is met. The audit reads
7 font sizes, 3 weights, 3 tracking values, 4 radii, 2 breakpoints, 0 raw
hex colours outside the token files (`design-system.css` and its JavaScript
mirror `styles/tokens.ts`) and 0 all-caps labels. `theme.css` is gone: its
base rules live in `design-system.css`, and 26 unused components and pages
were deleted with it. Every route was checked at 1440px and 375px: no
sideways scroll, nothing under 12px, no all-caps text.
