---
target: Stats Explorer page
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 5
target_identity: "file:/Users/nyashamutseta/Desktop/personal/FPL/.claude/worktrees/render-service-url-migration-2a5463/frontend/src/pages/StatsExplorerPage.tsx"
target_fingerprint: "sha256:203f705580e6810fd1d80ec0e8e89c41be7ba81aa5b8f25a64db6ab51ea8b7bb"
target_path: /Users/nyashamutseta/Desktop/personal/FPL/.claude/worktrees/render-service-url-migration-2a5463/frontend/src/pages/StatsExplorerPage.tsx
timestamp: 2026-10-14T09-32-40Z
slug: frontend-src-pages-statsexplorerpage-tsx
---
Method: dual-agent (A: design review sub-agent · B: detector/browser sub-agent), plus a parent technical audit.

## Design Health Score (Nielsen)
| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | Row count and cohort size ("19 forwards") are only in the screen-reader caption |
| 2 | Match real world | 2 | Colour shows rank within position, not size; Starts/90 is meaningless; CBIT/CBIRT jargon |
| 3 | User control | 2 | The phone drawer can't be closed; lens columns can't be removed |
| 4 | Consistency | 3 | The UCL controls use different widgets; Max £ and Watchlist move between the bar and the sheet |
| 5 | Error prevention | 2 | PL-only stats get round the minimum-minutes rule; missing data shows as 0.00 |
| 6 | Recognition | 3 | The legend names 3 of 5 bands; cells never say which cohort they rank against |
| 7 | Flexibility | 3 | Lenses, columns, views, links and an arrow-key grid exist; no search shortcut, no export |
| 8 | Aesthetic / minimal | 2 | Lime floods 42–49% of the first screen of cells |
| 9 | Error recovery | 3 | Good empty and retry states; the Teams empty state shows a management command |
| 10 | Help | 2 | Header help is in `title` only; per 90, minimum minutes and cohort are never explained |
| **Total** | | **25/40** | **Acceptable** |

## Technical audit
Accessibility 2, Performance 3, Responsive 2, Theming 3, Implementation integrity 3 = 13/20 (Acceptable).

## Priority issues
- **P0 The phone drawer sits under the fixed nav** (z-index 1000 vs 50). The name is hidden, and tapping close hits the nav. It is full-width, so there's no scrim to tap. Back leaves /stats. Verified with elementFromPoint.
- **P1 Five-band within-position shading encodes rank, not size.**
  - Big chances 2.32 and 1.08 share full lime, while 1.08 vs 1.06 differ.
  - Lime covers 42–49% of the first screen.
  - With Position = All, colour contradicts the sort.
  - Band 2 is 1.74:1 against the row, and bands 1/0 differ only in grey text.
  - The legend names 3 bands, and "20–40%" is ambiguous.
- **P1 Honesty leaks.**
  - Minimum minutes is checked on combined minutes while PL-only stats divide by PL minutes. Foden: 219 PL min, ranked top 5 for xG/90 under PL+UCL.
  - Absent feed keys read as 0.00. Foden shows xGOT 0.00 despite a shot on target.
- **P1 The drawer is aria-modal, but Tab escapes into the page behind it** (WCAG 2.4.3). Verified.
- **P1 The focus ring on top-band cells is invisible** (white on lime, 1.24:1).
- **P1 At tablet widths (721–1050px) only one of four lenses is visible.** The rest are clipped with no cue. Verified at 900px.
- **P2** About 17 controls above the table; Position (which defines every colour) is buried.
- **P2** The API JSON is 475 KB and uncompressed (no GZip middleware).
- **P2** Sub-11px text: UCL 8.8–9.6px, status, "soon", PL only, group headers.
- **P2** No visible result or cohort count; column help only in `title`.
- **P2** Phone table: truncated names, "O" reads as zero, 16px checkbox (passes 2.5.8 on spacing only), no tap-to-see percentile.
- **P2** Price and ownership are shaded lower-is-better; Starts/90; price appears twice in the Market lens; the Teams empty state shows a CLI command.

## Detector
- The CLI scan is clean (0 findings in 6 files).
- In-page injection: about 1,800 low-contrast hits, all false positives. The detector reads background-color, not the cells' band gradients; the real fills give 15.3:1 and 6.0:1.
- edge-flush-cards and table-wrap cramped-padding are false positives.
- Real signals: undersized badge text, line length about 90ch, a subtle lime glow on the active nav, Inter used for 100% of text (deliberate).

## Strengths
- The provenance system ("PL only", Estimate, the drawer's PL/UCL/Both split, "soon" with a reason).
- The view-as-URL architecture.
- Table craft: sticky header and column, aria-sort, roving grid, per-cell percentile labels, focus returns to the opener.
- Fast recompute (6–15ms per control change).

## Persona red flags
- **Casey (phone):** the drawer is a dead end, names are truncated, Position is two taps deep, no result count.
- **Sam (keyboard/SR):** about 670 Tab stops through the table with no skip link; help only in title; drawer focus escapes; focus ring invisible on lime.
- **Alex (power):** can't remove or reorder lens columns, no "/" shortcut, no CSV, colour contradicts the sort under Position = All.

## Questions
1. Should lime be rarer than a goal?
2. Should colour show the gap (2.32 vs 1.08) rather than the fifth?
3. Should DefCon columns shade against FPL's 10/12 thresholds?
4. Should the page shade at all before the sample can bear it (19 forwards after 6 GWs)?
