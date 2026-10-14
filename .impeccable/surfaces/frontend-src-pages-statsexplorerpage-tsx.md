---
version: 1
slug: "frontend-src-pages-statsexplorerpage-tsx"
primary_target: "frontend/src/pages/StatsExplorerPage.tsx"
related_targets: []
---

# Stats Explorer surface brief

Scope: new route `/stats` (`frontend/src/pages/StatsExplorerPage.tsx`), Operate mode,
inside the established AeroFPL world (`frontend/src/styles/design-system.css`).
Mockup phase: built on a static snapshot of real 2026/27 data, not yet wired to an API.

Audience and job: engaged FPL managers deciding who to buy, sell, captain or bench,
on desktop and phone equally (PRODUCT.md).

Agreed requirements (grill-me interview, 14 Oct 2026): Players + Teams tabs; lenses
Attacking threat, Creativity, Defence & keepers, Market & rotation; 'Stats from'
(PL / PL + UCL) and 'Club in Europe' (all / only / exclude); ~50 curated stats plus an
All-stats search; per 90 default with minimum minutes and a totals toggle; xG-family
columns badged 'PL only' when UCL is included; time window Season / Last 6 / Last 3 /
custom (only Season live); URL state plus named saved views (browser); cells shaded
by percentile within position, never colour alone; row actions: drawer, select to
compare, send to Chart Lab, watchlist.

## Direction contract

THESIS: The table is the instrument. One dense, sortable sheet carries the whole
decision. It refuses the dashboard-of-cards and the stat-card hero: no
summary tiles, no chart above the fold.

OWN-WORLD: Ink ground #101011, sheet #151616, hairlines #2e2f30/#3a3b3c, lime #a5ff01
reserved for selection, primary action and the top percentile band; four darker
lime steps for lower bands. Inter with tabular numerals, 13px data, 10px control
radius, pill lens tabs, 1px rules, authored SVG icons at 1.5px stroke.

STORY: The manager picks a lens, flips Stats from to PL + UCL and Club in Europe to
exclude, scans shaded columns, opens a player's drawer to see the PL vs UCL split,
ticks two to compare or chart, stars one, and copies the link.

FIRST VIEWPORT: Desktop 1440: title row (Stats Explorer, Players/Teams tabs,
Saved views, Share). One control bar: lens pills, Stats from segmented, Club in
Europe select, window segmented (Last 6 and Last 3 marked 'soon'), Per 90/Totals,
min minutes, Columns. Then the sheet: grouped column header, frozen identity
column (player, club, position, price, minutes), ~22 rows visible, shaded cells.
Phone 390: title row, lens chip scroller, Filters button showing a count (bottom
sheet), sheet with a frozen name column and the lens's 5–6 columns, and a sticky
compare bar. Signature: percentile shading that explains itself on focus or hover
(rank within position), plus 'PL only' badges that appear the moment UCL is
included.

FORM: Spreadsheet workbench, position 1 of 7 on the ordered structure list; surface
seed key a8ed8efd.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
