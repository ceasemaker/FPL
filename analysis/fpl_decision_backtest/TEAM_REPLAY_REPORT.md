# Three-Gameweek Team-Path Replay

## Verdict

The revised replay now tests the intended decision process: a frozen
three-gameweek view, ordinary XI points, normal autosubs, and exactly one normal
captain. It still rejects the current model.

The three-gameweek philosophy is not the problem. The underlying player and
captain forecasts are not yet strong enough to beat this exceptionally hard
benchmark, and the policy still recommends too many transfers.

## Headline: base points on every week

All chip multipliers are stripped. Bench Boost scores as an ordinary XI, Triple
Captain scores as a normal captain, and every other week also uses one normal
captain.

| Starting squad | Decisions scored | Model wins | Median model - human | Mean model - human | Best | Worst |
|---|---:|---:|---:|---:|---:|---:|
| After GW2 | GW3-GW38 | 0 / 100 | -330.0 | -330.10 | -171 | -504 |
| After GW10 | GW11-GW38 | 0 / 100 | -239.5 | -250.21 | -116 | -403 |

For the GW10 start, the archived teams averaged 64.06 base points per week and
the model teams averaged 55.12. From GW2, the corresponding averages were 64.78
and 55.62.

## Chip-week sensitivity

Free Hit and Wildcard do not multiply points, but they can change which squad
produced those normal points. As a sensitivity check, removing every human chip
week gives:

| Starting squad | Median model - human | Mean model - human | Model wins |
|---|---:|---:|---:|
| After GW2 | -209.5 | -213.11 | 0 / 100 |
| After GW10 | -147.0 | -152.74 | 0 / 100 |

This shows that chip-enabled squad selection enlarges the headline deficit, but
does not explain the model's failure.

## Decision method

- Player form is frozen at the decision deadline. Later realized player form is
  never borrowed for the second or third projected week.
- The immediate forecast uses the walk-forward player model plus the cached
  bookmaker calibration.
- That frozen forecast is moved across the next three known fixtures and
  weighted `1.00`, `0.90`, and `0.81`.
- The model may hold, use one transfer, or use two transfers.
- Every transfer must recover a 1.5-point option cost over the three-week view.
  Transfers beyond the banked allowance must additionally recover a four-point
  hit.
- Legal formations, club limits, normal captains and normal autosubs are
  reconstructed week by week.

## What is going wrong

The GW10 replay made 3,033 transfers across 2,800 team-weeks and incurred an
average of 14.2 hit points per team. The GW2 replay made 3,936 transfers across
3,600 team-weeks and incurred 17.16 hit points per team. A three-week view
reduced the worst one-week churning behaviour, but the policy remains too eager
to act.

More importantly, the loss is not mainly transfer cost. On ordinary non-chip
weeks, the model averaged 54.77 points from GW10 while the elite humans averaged
61.72. Its captain was Haaland in 1,758 of the 2,800 GW10-start team-weeks. The
current forecast is too sticky around highly owned historical performers and
is not adapting to changes in role, minutes and team attack quickly enough.

## Interpretation limits

1. These are the eventual season-end top 100 reconstructed backwards. This is
   a strongly survivorship-biased benchmark, not a typical manager cohort.
2. Weekly prices were not archived, so the replay uses reconstructed opening
   prices rather than exact purchase and sale values.
3. Future fixture difficulty is taken from the archived schedule. The player's
   form is frozen correctly, but historical FDR snapshots were not retained.
4. The transfer search uses a pruned candidate beam rather than an exhaustive
   whole-squad solver.
5. Human Wildcard improvements continue into later weeks even in the
   chip-excluded sensitivity.

These limitations affect the size of the deficit; they do not support claiming
that a 0/100 result is validated.

## Next model phase

1. Replace the current point forecast with a minutes-first model: probability
   of starting, expected minutes conditional on starting, then per-90 attacking,
   clean-sheet and bonus components.
2. Add rolling team attack/defence strength and role changes rather than relying
   heavily on lagged player points.
3. Calibrate captaincy separately because captain error is doubled and currently
   accounts for a large part of path divergence.
4. Benchmark the policy against Hold, fixture ticker, recent xGI, and simple
   consensus picks before comparing it with humans.
5. Validate on a contemporaneous random or rank-tier cohort; retain this
   eventual-top-100 cohort as the final stress test.
6. Tune no thresholds on this cohort. Use a separate validation season, then
   return once to these 100 paths for a clean test.

Detailed audit trails are saved in `output/team_replay_gw2_weekly.csv` and
`output/team_replay_gw10_weekly.csv`. The summary JSON files feed the local
Decision Lab dashboard.
