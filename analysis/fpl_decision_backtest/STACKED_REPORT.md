# Stacked Forecast — Mathematical Audit

Date: 2026-08-28

## Corrected verdict

The stacked ridge is a useful **mean-forecast candidate**, but it has not
earned control of lineup, captaincy or transfers.

```text
accepted_for_mean_forecast = true
accepted_for_optimizer = false
accepted_for_transfer_horizon = false
```

It significantly improves MAE and correlation over the odds ridge under a
proper paired week-cluster bootstrap. Its weekly top-five point estimate is
worse, and the uncertainty interval is too wide to establish either
superiority or non-inferiority. The dedicated three-gameweek model also fails
its corrected correlation gate.

## What survived the audit

The model combines lagged form, no-vig opening-market features, and structural
Poisson minutes, goal, assist, clean-sheet and scoring components.

On the 2025/26 evaluation season:

| Quantity | Estimate | Week-cluster 95% CI |
|---|---:|---:|
| MAE gain over odds ridge | +0.0357 | [+0.0211, +0.0528] |
| Correlation gain | about +0.0326 | [+0.0075, +0.0633] |
| Weekly top-five difference | −0.2216 | [−0.6324, +0.1676] |
| 3-GW top-five difference | −0.3458 | [−1.2997, +0.5997] |

The mean-accuracy gain is real under this evaluation. It does not prove that
the ordering of transfer or captain candidates is better.

## Corrections made during audit

### Bootstrap multiplicities

The earlier correlation bootstrap used `isin()` after sampling weeks with
replacement. `isin()` turns the draw into a set and discards repeated weeks,
so it is not a bootstrap sample. The implementation now concatenates each
sampled week, preserving multiplicity.

MAE is also resampled by week rather than treating thousands of correlated
player-weeks as independent. A player-cluster sensitivity check reached the
same conclusion for the mean forecast.

### Absence of significance is not non-inferiority

The earlier gate promoted a model whenever the top-five interval was not
entirely below zero. That is an `absence of detected harm` rule, not evidence
of parity or non-inferiority. The corrected optimizer gate requires a positive
lower confidence bound for the decision utilities. The stacked model does not
meet it.

A future non-inferiority design would require a practical margin fixed before
examining a new holdout season.

### Incomplete three-week targets

GW37 and GW38 previously treated missing future weeks as zero. That changes
the target and gives a separately fitted horizon model a misleading end-season
signal. Incomplete horizons are now censored, and horizon training/evaluation
uses only complete targets.

After that change and the correct cluster bootstrap:

| Three-week quantity | Estimate | 95% CI |
|---|---:|---:|
| Correlation gain over 1-GW stacked | about +0.014 | [−0.0058, +0.0333] |
| 3-GW top-five difference | +0.5578 | [+0.0829, +1.0302] |

The utility point estimate is promising, but the required correlation gain is
not established. Therefore `accepted_for_transfer_horizon = false`.

## Hold replay interpretation

The same-starting-squad hold comparison is more relevant than comparing
directly with a cohort selected because it eventually finished in the top 100.
The reported replay estimates remain:

- GW2 start: median transfer value `+206`, positive on 93/100 paths;
- GW10 start: median transfer value `+27.5`, positive on 60/100 paths.

Call this a **paired internal hold benchmark**, not fully survivorship-free.
The starting squads still come from managers selected ex post by final rank,
and weekly prices are reconstructed rather than archived. The paired design
cancels much of the direct cohort advantage, but it does not create a random,
representative sample of managers.

The replay currently uses `stacked_xp` frozen and fixture-adjusted over three
weeks. It does not use `stacked_3gw_xp` as a separate transfer signal, and it
should not while that model remains unaccepted.

## Haul head

The logistic haul head remains diagnostic. Its ranking differences versus
plain stacked xP are statistically unresolved on the evaluation season. It
must not drive rankings or captaincy.

## Holdout caveat

2025/26 has been inspected repeatedly across the structural and stacked-model
iterations. It is an evaluation season, not a pristine untouched holdout. The
next genuine authority decision needs a newly accumulated season or a
pre-registered rolling-origin protocol whose model and margins are frozen
before results are revealed.

## Research ideas retained

- Mean accuracy and selection quality are different objectives.
- Explicit appearance/start probabilities are valuable.
- Direct multi-week targets are worth developing, but incomplete horizons must
  be censored.
- Transfer engines need paired hold and transfer-cost benchmarks.
- ROI is a budget heuristic, not mathematically equivalent to maximizing total
  FPL points.

## Next step

Keep the current optimizer unchanged. Use the stacked model as a research
candidate and freeze the next protocol around:

1. a complete three-gameweek target;
2. player availability, penalties and set-piece roles;
3. ranking metrics plus a predeclared non-inferiority margin;
4. rolling-origin evaluation and a future untouched acceptance season;
5. a representative or personally archived squad benchmark.
