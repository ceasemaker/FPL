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

## Update 2026-08-28: replays rerun with the stacked candidate forecast

The stacked forecast candidate was fed to both replays via
`--odds-predictions output/stacked_replay_predictions.csv`:

| Start | Old median delta | New median delta | Paths won |
|---|---:|---:|---:|
| GW2 | −330.0 | −318.5 | 0/100 |
| GW10 | −239.5 | −232.5 | 0/100 |

A forecast improvement of proven statistical significance at the player-week
level moved the replay deficit by under 3%. The deficit is therefore not a
forecast-quality signal. The dominant cause is the benchmark itself:

**The comparison cohort is an extreme order statistic.** The cohort is the
eventual top ~100 of roughly 11 million managers, selected ex post on the
very outcome being compared. For n ≈ 1.1e7, the top-100 threshold sits
approximately 4.4 standard deviations above the mean season score. With a
plausible inter-manager season standard deviation of 100–150 points in this
base-points view, selection bias alone accounts for roughly 450–650 points —
more than the entire observed deficit (model paths average ~2011 points over
GW2–38 vs the cohort's ~2332). An unbiased ex-ante strategy is *expected* to
lose to this cohort by a wide margin even if it is better than nearly every
manager ex ante.

Conclusion: this replay, as constructed, cannot validate or reject a
forecast. To make it informative it needs an unbiased benchmark, e.g. a
random sample of manager IDs archived at season start (not conditioned on
finish), a template/most-owned-squad baseline, or the user's own historical
entry. Until such a benchmark exists, model promotion should rest on the
statistical gate, and the replay should be read only as "how far behind the
luckiest 100 finishers an ex-ante strategy lands."

## Update 2026-08-28 (later): paired internal hold benchmark added

The replay now scores every model path against the identical starting squad
held with zero transfers, with lineup and captain chosen by the same
predictions. This paired comparison isolates transfer-path value much better
than the direct eventual-top-100 score comparison. It is not fully
survivorship-free: the starting squads still belong to a cohort selected ex
post by final rank, and weekly prices are reconstructed.

| Start | Median transfer value | Mean | Paths positive | Worst | Best |
|---|---:|---:|---:|---:|---:|
| GW2 | +206.0 | +195.2 | 93/100 | −133 | +611 |
| GW10 | +27.5 | +39.5 | 60/100 | −145 | +255 |

Interpretation: from an early-season start the transfer engine adds roughly
+200 points per season over holding — strong, consistent positive value
(compare Pokharel et al. 2022, whose transfer engine *destroyed* 264 points
against the same kind of baseline). From a GW10 start the edge is small and
noisy: with only 28 remaining gameweeks and already-settled squads, transfer
value is thinner and roughly 40% of paths would have done better holding.
This suggests the confidence buffer on mid-season transfers should be larger
than the early-season one.

These transfer-value numbers are more decision-relevant than the direct
top-100 cohort deltas, but still require confirmation on a representative or
personally archived squad sample.
