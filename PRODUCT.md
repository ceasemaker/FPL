# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Engaged Fantasy Premier League managers: they play every gameweek, know what xG
and fixture difficulty mean, and want depth, but not raw Opta jargon. They use
AeroFPL to make weekly decisions about who to buy, sell, captain and bench. They
use it on desktop and on phones about equally, so phone layouts are designed as
carefully as desktop ones.

## Product Purpose

AeroFPL helps managers make better FPL decisions by putting deep, honest data in
front of them: official FPL data plus Opta-depth stats (xG on target, big
chances, defensive actions, Champions League minutes) from the Premier League's
own stats feeds. Success is a manager who can answer "who should I bring in?"
or "who do I captain?" from evidence they understand and trust.

## Positioning

Honest depth. AeroFPL goes deeper than FPL's own data (Opta stats, Champions
League context) and shows every number's source and limits. It never presents a
modelled number as a prediction unless that model has been validated. When data
is missing, stale or estimated, the interface says so instead of filling the gap
with something plausible.

## Operating Context

- Weekly rhythm: gameweek deadlines, price changes, injury news, midweek
  Champions League fixtures that cause rotation.
- Managers compare players, build custom views (Chart Lab formulas, Stats
  Explorer columns) and share links with friends.
- No accounts: views are shared by URL, and saved views live in the browser.

## Capabilities and Constraints

- Data: FPL API (prices, ownership, per-gameweek points, xG/xA/xGC); Premier
  League stats APIs (`PREMIER_LEAGUE_DATA_API.md`): season sheets for the Premier
  League (~130 SDP stats incl. xG/xGOT, ~260 classic stats) and Champions League
  (classic, no xG). The Championship has no 2026/27 stats yet. There are no x/y
  coordinates.
- Per-match stats are not loaded yet. Recent-form windows (last 3/6 gameweeks)
  are designed but ship after season totals.
- The homepage captain pick is switched off until the prediction model beats
  simple baselines (`analysis/fpl_decision_backtest/run_captain_backtest.py`).
- Stack: Django (API, Celery ETL) and React + TypeScript (Vite), served as one
  Render web service. Do not add Render services without approval.

## Brand Commitments

- Name: AeroFPL.
- Voice: plain, direct and evidence-first. Label provenance ("Official FPL",
  "Estimated", "PL only"), never hype.
- The incumbent interface (dark surfaces, lime accent, Inter) lives in
  `frontend/src/styles/design-system.css`. The root `DESIGN.md` predates it and
  is stale.

## Evidence on Hand

- Real data in production: FPL (all players, gameweeks 1–6+), `player_season_stats`
  (2025/26 PL SDP: 790 players; 2026/27 PL SDP: 511, PL classic: 436, UCL
  classic: 623).
- Backtest results: `analysis/fpl_decision_backtest/output/captain_backtest_summary.json`.
- No testimonials, user counts or accuracy claims exist; do not invent them.

## Product Principles

1. Every number earns its place by moving an FPL decision.
2. Show provenance and limits: source badges, estimate labels, sample sizes.
   Showing nothing beats showing a plausible guess.
3. Fair comparison: per-90 with minimum minutes, percentiles within position.
4. Let managers build their own view, and make it shareable by link.

## Accessibility & Inclusion

WCAG 2.2 AA. Colour (e.g. percentile shading) is never the only carrier of
meaning; tables are keyboard-navigable; contrast meets AA on the dark theme.
