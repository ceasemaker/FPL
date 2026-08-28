# FPL Quantitative Decision Backtest — Initial Report

## Executive conclusion

The repository data supports a useful empirical decision system, but it does
not support Black–Scholes pricing or a universal ownership threshold.

The strongest first-pass framework is:

- estimate next-gameweek expected points and an outcome interval;
- measure value relative to positional replacement and a position-specific
  expected-points/price curve;
- treat effective ownership as an exposure multiplier, not as player value;
- treat volatility as risk, not as free expected value; and
- use differentials only when their expected-points sacrifice is acceptable
  for the manager's rank objective.

Across 111 out-of-sample decision gameweeks, the model improved likely-starter
MAE by 13.3% versus a three-game rolling-points baseline. Its point forecasts
remain noisy: likely-starter MAE was 2.32 points and week-level correlation was
only 0.17–0.26. The system is therefore a screening and risk tool, not a source
of a single observable “true value.”

## Data and backtest design

The backtest uses four complete player seasons:

| Repository folder | Interpreted season | Role |
|---|---:|---|
| `fpl_data/2022` | 2022/23 | Initial training season |
| `fpl_data/2023` | 2023/24 | Out-of-sample evaluation |
| `fpl_data/2024` | 2024/25 | Out-of-sample evaluation |
| `fpl_data/2025` | 2025/26 | Out-of-sample evaluation |

There are 87,025 evaluated player-gameweeks in the three test seasons. The
decision-focused sample contains 20,212 player-gameweeks with a prior
three-game average of at least 60 minutes. Gameweek 1 is not used for weekly
screens because no same-season player history exists, leaving 111 screened
gameweeks (37 per evaluation season).

The model for each season is trained only on previous seasons. Every gameweek
feature uses data through the preceding gameweek. Features include rolling
points, minutes, appearances, starts, xGI per 90, xGC per 90, ICT per 90, BPS
per 90, position and initial price.

Initial price is recovered as `final now_cost - full-season cost change`. This
recovers the published opening price without using final performance, but it
does not capture in-season price movements.

Effective ownership is calculated directly from the manager-pick multiplier:

\[
EO_{i,t}=\frac{\sum_j multiplier_{i,j,t}}{N_t}
\]

The ownership files reconstruct the eventual season-end top 100 managers. This
creates survivorship bias: the results describe exposure among eventual elite
managers, not the managers who occupied the top 100 at each historical deadline.

## Metric definitions

For player points \(P\), projected mean \(\mu\), predicted standard deviation
\(\sigma\), effective ownership \(e\), and the manager's multiplier \(m\):

\[
E[relative\ points]=(m-e)\mu
\]

\[
relative\ risk=|m-e|\sigma
\]

The exported data reports these scenarios:

- non-owner: \(m=0\);
- normal owner: \(m=1\);
- captain: \(m=2\).

“Value” is represented in two complementary ways:

1. projected points above the position's 25th-percentile likely-starter baseline,
   divided by the price premium over the cheapest likely starter;
2. projected points minus a weekly position-specific expected-points/price curve.

The second measure can be inverted into an approximate `fair_price`. It is a
relative squad-allocation estimate, not a market-clearing financial price.

A differential candidate has lagged elite EO below 10%, projected minutes of
at least 60, and expected points in the week's top quartile. “Undervalued” and
“overvalued” refer to positive and negative deviations from the price curve.

## Forecast performance

| Season | Likely-starter rows | Model MAE | Rolling-3 MAE | Improvement | Correlation | 10–90% coverage |
|---|---:|---:|---:|---:|---:|---:|
| 2023/24 | 6,729 | 2.33 | 2.66 | 12.2% | 0.247 | 82.8% |
| 2024/25 | 6,707 | 2.27 | 2.60 | 12.6% | 0.258 | 82.2% |
| 2025/26 | 6,776 | 2.36 | 2.78 | 15.0% | 0.168 | 79.7% |
| Weighted | 20,212 | 2.32 | 2.68 | 13.3% | — | 81.5% |

The risk interval is well calibrated in aggregate: a nominal central 80%
interval captured 79.7–82.8% of likely-starter results. The low correlations
show why the interval is as important as the point estimate.

## Weekly-screen results

Each `top_5` screen selects up to five players per gameweek. These are player
screens rather than legal 15-player squads, so totals must not be interpreted
as a complete FPL strategy.

| Screen | Selections | Actual pts/GW-player | Haul rate | Blank rate | Actual edge vs price curve |
|---|---:|---:|---:|---:|---:|
| Highest projected points | 555 | 5.36 | 27.7% | 44.5% | +0.76 |
| EO ≥70% template | 504 | 5.55 | 30.0% | 44.0% | +1.44 |
| Top differentials | 555 | 4.01 | 17.5% | 54.6% | +0.31 |
| Top undervalued | 555 | 3.59 | 14.1% | 60.0% | +0.72 |
| Top replacement value | 555 | 3.03 | 9.0% | 61.4% | +0.56 |
| Most overvalued | 555 | 1.64 | 5.0% | 79.8% | −1.09 |

The valuation screen successfully separated the two tails: undervalued players
beat the price curve by 0.72 points on average, while overvalued players missed
it by 1.09. The cheap replacement-value screen also beat its price curve, but
its raw points were low. This is the correct interpretation: budget-efficient
players are enablers, not automatically the best captain or transfer target.

Examples repeatedly identified by the undervaluation screen include Palmer in
2023/24, Mbeumo in 2024/25 and Semenyo in 2025/26. These examples are descriptive;
the aggregate results above are the actual test.

## Differential result

Low ownership did not create expected value. The differential screen averaged
4.01 points, versus 5.36 for the unrestricted top-projection screen. It also
blanked more often and hauled less often.

This does not make differentials useless. It means a rational rule should be:

> First establish expected points and minutes. Use ownership to choose among
> similarly valued players or to alter variance for a defined rank target.

Choosing a player primarily because EO is below 10% paid an unnecessary
expected-points penalty in this sample.

## Ownership and rank exposure

| Realized elite EO | Player-weeks | Mean points | Haul rate | Blank rate | Non-owner relative points |
|---|---:|---:|---:|---:|---:|
| 0–10% | 5,355 | 3.74 | 13.7% | 54.8% | −0.12 |
| 10–30% | 1,389 | 4.59 | 21.8% | 47.0% | −0.84 |
| 30–50% | 476 | 4.73 | 19.7% | 43.7% | −1.84 |
| 50–70% | 335 | 5.04 | 24.2% | 41.2% | −3.02 |
| 70–100% | 370 | 6.36 | 35.4% | 34.1% | −5.44 |
| Above 100% | 168 | 8.20 | 48.8% | 20.2% | −12.92 |

High-EO players were very costly to fade in this elite cohort. Nevertheless,
34% of the 70–100% observations still blanked. There is no mathematical
discontinuity at 70%; exposure rises continuously with EO and expected outcome.
The lagged EO proxy correlated 0.776 with realized EO and had mean absolute
error of about 7.8 percentage points, but chip and availability changes can
produce much larger weekly errors.

The table is also affected by elite-cohort selection: eventual top managers
were more likely to have selected players who performed well. It demonstrates
exposure mechanics, but it overstates the causal benefit of following ownership.

## Volatility result

Historical point volatility predicted wider future outcomes. The lowest
volatility quartile had subsequent point standard deviation of 2.84, compared
with 3.58 in the highest quartile.

It did not produce a Black–Scholes-style expected-value premium. After the
forecast accounted for player quality, mean forecast residual was +0.06 points
in the lowest quartile and −0.01 in the highest. The high-volatility group had
more hauls, but also had higher expected points before volatility was considered.

Volatility should therefore widen risk ranges and affect goal-dependent rank
strategy. It should not be added to expected value merely because FPL upside is
perceived as asymmetric.

## Haaland case study

Across the three evaluation seasons, Haaland averaged 5.59 actual points versus
a 5.71 forecast. His average estimated fair prices were approximately £14.02m,
£15.01m and £14.24m against opening prices of £14.0m, £15.0m and £14.0m. On this
simple price curve, he was broadly fairly priced over full seasons.

When his realized EO was at least 70% (70 observations), he averaged 7.61 points,
hauled 42.9% of the time and blanked 31.4% of the time. A non-owner lost 12.13
relative points per such observation on average. A normal owner still averaged
−4.52 relative points from his contribution because elite EO often exceeded
100% through captaincy. Owning him reduced the loss relative to fading him;
captaincy was needed to match an EO above 100%.

The 2024/25 GW6–13 run is an important model failure case. Haaland averaged only
2.88 actual points while the model still forecast 6.44. Elite EO fell from 141%
to 2% during that sequence, but the rolling model reacted slowly and its average
valuation edge remained slightly positive. Fixture, injury/news, team-strength,
bookmaker and live price inputs are needed before this system can reliably call
an expensive star overvalued during a regime change.

It is also important to define “net negative” correctly. For one player, owning
instead of not owning always improves relative score by that player's realized
points. A premium player becomes net negative only when the lost points from
the best affordable alternative squad exceed his points. That is a constrained
squad opportunity-cost question, not an EO-only calculation.

## What this first test supports

1. Keep expected points, predictive intervals and expected minutes as the core.
2. Use EO to calculate rank exposure under explicit owner/captain scenarios.
3. Use value residuals to find enablers and flag poor uses of budget.
4. Require a differential to clear a minimum expected-points threshold.
5. Remove Black–Scholes and the mandatory 70% rule.
6. Add a legal-squad optimizer and Monte Carlo rank objective before issuing
   transfer or captain recommendations.

## Next build phase

The highest-value next additions are:

- reconstruct weekly prices rather than relying on opening price;
- add fixtures, opponent strength, home/away status, blanks and doubles;
- include pre-deadline availability/news and bookmaker probabilities;
- ingest contemporaneous EO for the user's rank tier;
- fit a calibrated count/distributional model rather than only a point model;
- simulate correlated player outcomes and complete manager squads;
- compare transfers over multi-gameweek horizons including hits, free-transfer
  opportunity cost and alternative budget allocation.

Until those are added, the outputs should be presented as retrospective player
screens, not an automated transfer engine.
