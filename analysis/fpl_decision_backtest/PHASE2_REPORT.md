# Phase Two — Personalized Squad and Rank-Risk Optimization

## Current personalized result

Public FPL entry `576154` (“Didier Drogon”) was evaluated immediately before
the 2026/27 Gameweek 2 deadline using the last publicly revealed squad.

| State | Value |
|---|---:|
| Overall points after GW1 | 74 |
| Overall rank after GW1 | 279,827 |
| Bank | £0.0m |
| Team purchase/sale value | £100.0m |
| Chip already used | Bench Boost, GW1 |
| Planning horizon | GW2–GW4 |

Calafiori and João Pedro had each risen by £0.1m, but FPL's half-profit rule
means both still sold for their opening price at this snapshot.

## Decision

All three objectives recommend **rolling the free transfer**.

| Objective | Best screened move | Three-GW expected gain | Risk-adjusted gain | Decision |
|---|---|---:|---:|---|
| Protect rank | Maguire → De Cuyper | +1.17 | +1.08 | Roll |
| Balanced | Maguire → De Cuyper | +1.17 | +1.18 | Roll |
| Chase upside | Mbeumo → Gakpo | +0.98 | +1.45 | Roll |

The system currently requires at least 1.5 risk-adjusted points over the
three-gameweek weighted horizon before spending a free transfer. This is a
modest opportunity-cost threshold, not a claim that a transfer literally costs
1.5 points. Banking raises next week's option set, particularly with £0.0m
currently available.

The transfer names above are watchlist outputs, not recommendations. The
underlying evidence after one gameweek is too weak to justify those moves.

## Provisional GW2 lineup

The Balanced projection selects:

- Goalkeeper: Kinsky
- Defenders: Calafiori, Maguire, Rodon
- Midfielders: Bruno Fernandes, Mbeumo, Szoboszlai, Tzolis
- Forwards: Haaland, João Pedro, Calvert-Lewin
- Bench: Verbruggen, Gomez, Ajer, Diop

Kinsky and Verbruggen are tied at 1.9 projected points. Rodon and Ajer are tied
at 1.7, so their ordering should not be treated as a confident distinction.

Bruno Fernandes and Haaland are both on 4.0 official `ep_next`:

- Protect mode captains Haaland because his overall ownership proxy is 67.9%.
- Chase mode captains Bruno because his ownership proxy is lower at 48.4%.
- Balanced mode is mathematically indifferent on the current point input; its
  Bruno selection is a tie-break, not evidence of a higher mean.

Overall ownership is not captain effective ownership. A production captain
decision needs projected deadline EO for the manager's rank tier.

## What was added to the application

The existing MILP optimizer now supports personalized and rank-aware decisions:

- exact starting squad and free-transfer state;
- cash-flow constraints rather than treating market squad value as cash;
- inferred FPL selling prices, including the half-profit rule;
- retention of unavailable players who are already owned;
- Protect, Balanced and Chase rank-risk objectives;
- explicit opt-in for wildcard use;
- correct transfer, chip, bank and captain-point response fields;
- a frontend rank-strategy selector; and
- a dependency-free live evaluator for current public teams.

For player mean \(\mu\), variance \(v\), ownership benchmark \(e\), and manager
multiplier \(m\), the risk-aware optimizer uses the relative variance:

\[
v(m-e)^2
\]

The non-owner term is constant across decisions. Starting a player changes
variance by \(v(1-2e)\), and captaining them adds \(v(3-2e)\). Protect mode
penalizes relative variance; Chase mode rewards it. Balanced mode maximizes
expected points without an ownership adjustment.

This preserves the crucial result from phase one: ownership does not alter
expected-points value. It changes exposure around that expectation.

## Current limitations

This is a sound decision layer over provisional inputs, not yet a production
recommendation engine.

1. Only one 2026/27 gameweek has been played. GW2 uses official FPL `ep_next`;
   GW3–GW4 use a strongly shrunk price/form/PPG and fixture-difficulty heuristic.
2. The local Django database is not yet synchronized to the 2026/27 player ID
   set, so the direct live evaluator is currently more reliable than the local
   database-backed endpoint for this team.
3. The project's prediction-population command still generates randomized dummy
   values. It must be replaced before deployment.
4. The ownership input is current overall ownership, not projected effective
   ownership at the user's rank tier.
5. Player covariance, bookmaker probabilities and team tactical changes are not
   yet represented.
6. Public manager data may not reveal transfers made since the last deadline.

## Next technical step

The next implementation should synchronize current-season IDs and fixtures,
replace randomized predictions with the calibrated historical model plus odds,
store prediction intervals and projected EO, then run scenario-based squad
simulation. At that point the system can compare Hold, one-transfer, hits and
wildcard paths by expected points and probability of reaching a specified rank.
