---
version: 1
slug: "frontend-src-pages-matchpage-tsx"
primary_target: "frontend/src/pages/MatchPage.tsx"
related_targets: []
---

# Match page

Scope: the Match page (route `/matches/:id`), opened from Matches, a Team page, a Player page or the homepage; looks the same wherever it is opened. Mode: Operate (analysis). Desktop and phone designed equally.

Audience and job: engaged FPL managers reviewing a finished match (or previewing an upcoming one) to judge players and teams: who was involved, who was dangerous, what changed the game, who earned FPL points.

Content: score and scorers; timeline (goals, cards with reasons, subs, VAR); Opta minute-by-minute momentum; team stats side by side incl. xG and shot zones (inside/outside box, left/centre/right, goal-mouth placement); lineups on a pitch by formation (captain, subs with minutes on/off); every player's match sheet plus FPL points; head-to-head and form going in; FPL angle.

Constraints: per-minute data exists only for goals, cards, subs, VAR and momentum; shot and pass counts are full-match totals. No x/y coordinates. Plain-language takeaways first; simple readable visuals, one encoding per chart.

## Direction contract

THESIS: The match is a timeline you can drag. One minute cursor drives the page: the momentum band, the event list, the scoreline and the pitch all show the match as it stood at that minute. Refuses the category default of a tab strip (Overview / Stats / Lineups) where each tab is a separate silo.

OWN-WORLD: The Aero instrument panel: ink #101011 ground, graphite sheets, 1px hairlines, Inter with tabular numerals, one lime voice for the cursor and the leading side; coral for red cards and the trailing side's goals only where meaning needs it; amber provenance badges ("Opta momentum", "Full-match totals").

STORY: Read the one-line summary and the score; drag across the momentum band to see when the game turned; watch the pitch lose a player at the red card; then read full-match stats, shot zones and every player's sheet; close with the form going in and the FPL points.

FIRST VIEWPORT: Full-width header: teams, score, scorers with minutes, one plain sentence of what happened. Directly beneath, the momentum band spanning the width (home above the axis, away below), goals/cards/subs pinned on it, a lime cursor with a minute readout. Under it, left 7/12: the pitch at the cursor minute; right 5/12: the scoreline at that minute and the events so far.

FORM: Minute scrubber, candidate 6 of 7 on the ranked list; surface seed key 595dc355.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
