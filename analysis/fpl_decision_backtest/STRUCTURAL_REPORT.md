# Structural Poisson Backtest

## Verdict

The structural model is mathematically coherent and materially improves
average player-week error, but it does not yet improve the actual top-player
selection objective. It has therefore **not** replaced the existing ranking
forecast in the transfer optimizer.

## Results

| Season | Model | MAE | RMSE | Correlation | Mean weekly top-five points |
|---|---|---:|---:|---:|---:|
| 2024/25 | Odds ridge | 2.268 | 3.073 | 0.299 | 6.530 |
| 2024/25 | Structural Poisson | **2.071** | 3.111 | **0.314** | **6.578** |
| 2025/26 | Odds ridge | 2.342 | **3.154** | 0.223 | **5.178** |
| 2025/26 | Structural Poisson | **2.217** | 3.270 | **0.226** | 4.941 |

The blend weight was selected on 2024/25 only. Validation chose a 100%
structural forecast. The 2025/26 result was initially out-of-sample, but later
iterations have now inspected it; treat it as evaluation evidence rather than
a pristine future authority holdout.

The structural model beat ridge MAE in all 37 evaluated weeks of each season.
That is a strong calibration result. The 2025/26 top-five shortfall is still a
hard failure for an optimizer whose job is to choose the best players, and it
overrides the MAE win at the authority gate.

## What is modelled

- Opening 1X2 and over/under 2.5 odds are normalized to no-vig probabilities.
- Independent home and away Poisson goal rates are fitted to those markets.
- Player minutes, xG, xA, saves, bonus and disciplinary events use only data
  available through the previous gameweek.
- Player rates are shrunk toward positional priors built only from earlier
  seasons.
- Player goal and assist intensities are scaled back to the market team total.
- Ordinary FPL scoring is applied, including 2025/26 defensive contributions.
- A deterministic-seeded simulation emits blank probability, haul probability,
  and 10th/90th percentile outcomes.

## Current weaknesses

The model underpredicts the upper tail: its simulated haul probability is too
low, and top-five ranking deteriorated in the evaluation season. Likely causes
are the simple assisted-goal constant, a crude minutes-state distribution,
independent player goal/assist events, and empirical rather than match-state
bonus modelling. These affect stars and captain candidates more than ordinary
players, which explains why MAE can improve while selection worsens.

## Next acceptance work

The next version should separately calibrate starter minutes, penalty/set-piece
shares, FPL assists, and bonus; evaluate probability calibration by position;
and optimize the validation rule for three-gameweek squad value rather than
one-week MAE alone. The structural forecast can become the optimizer authority
only if it preserves its error improvement while matching or beating ridge on
unseen top-player and three-gameweek transfer outcomes.

## Update 2026-08-28: three-state minutes model

The minutes model was upgraded from two shrunk probabilities (`p_play`, `p_60`)
to an explicit three-state model per fixture: start, substitute appearance, or
no appearance. Each state probability is a six-match lagged frequency shrunk
toward earlier-season positional priors. Expected minutes are now
`p_start * minutes_per_start + p_sub * minutes_per_sub`, with both conditional
minutes estimated per player (league-wide these are roughly 85 and 18 minutes).
The 60-minute probability is `p_start * P(60 | start)`, with `P(60 | start)`
also player-specific and prior-shrunk (positional prior about 0.93). The Monte
Carlo simulation now draws the three states directly and gates clean-sheet and
second appearance points on a Bernoulli 60-minute draw rather than a fixed
75-minute assumption.

Effect on the 2025/26 evaluation season:

| Metric | Before | After |
|---|---:|---:|
| Structural MAE | 2.217 | 2.218 |
| Correlation | 0.226 | 0.223 |
| Weekly top-five realized points | 4.941 | 5.011 |

The tail-selection metric that gates optimizer authority improved by about
+0.07 points per week while MAE held, but it remains below the odds-ridge
baseline (5.178). The authority gate therefore remains
`accepted_for_optimizer = false`. The 2024/25 validation season also improved
slightly (MAE 2.071 to 2.068). Remaining next steps are unchanged: penalty and
set-piece shares, FPL-assist versus xA separation, match-state bonus modelling,
and blank/haul calibration.

## Negative result 2026-08-28: empirical FPL-assist rate

Replacing the 0.75 assisted-goal constant with the leakage-safe earlier-season
empirical FPL-assist rate (about 0.90 assists per goal) was tested and
rejected. It slightly raised correlation but worsened top-five realized points
on both the 2024/25 validation season (6.73 to 6.66) and the 2025/26
evaluation season (5.01 to 4.90). The lower constant evidently acts as beneficial
shrinkage on assist ceilings. The constant stays at 0.75; a future assist model
should separate FPL assists from xA structurally (set pieces, secondary
assists) rather than only rescaling the aggregate rate.

## Update 2026-08-28 (second pass): bonus, calibration, ranking metrics, 3-GW selection

Four further acceptance-phase items were completed on top of the three-state
minutes model.

**Event-driven bonus model.** A per-position least-squares bonus model
(features: appearance, 60+ minutes, goals, assists, clean sheets, saves) is
fit only on earlier seasons and blended 50/50 with the rolling empirical
bonus. On the 2024/25 validation season this improved weekly top-five realized
points from 6.73 to 6.78 with MAE and correlation flat or better. Fitted
coefficients are plausible (about 0.9-1.4 bonus points per goal declining
GK to FWD is not fit for GK; clean sheets worth about 0.6-0.9 for GK/DEF).

**Blank/haul probability calibration.** Simulated blank and haul probabilities
are now Platt-scaled per position, with parameters fit on 2024/25 only. The
raw simulation understated hauls by roughly half (mean 0.008 vs actual 0.016).
Calibration improved the Brier score on the 2025/26 evaluation season for both
outcomes (blank 0.1079 to 0.1027; haul 0.0172 to 0.0170), so the calibrated
columns `blank_probability_calibrated` / `haul_probability_calibrated` are now
exported alongside the raw ones.

**Ranking metrics.** The weekly summary now reports NDCG@10, captain regret
(best realized score minus the realized score of the model's captain pick),
and realized three-gameweek top-five utility (weights 1.0/0.9/0.81) for every
model, alongside MAE and one-week top-five.

**Three-gameweek selection.** The structural/ridge blend weight is now chosen
on 2024/25 by maximizing realized three-gameweek top-five utility rather than
one-week MAE. Validation selected a 35% structural / 65% ridge hybrid.

**Authority gate (extended and still failing).** The gate now also requires
the hybrid to match ridge on complete-horizon three-gameweek top-five utility.
On the 2025/26 evaluation season:

| Metric | Odds ridge | Hybrid (35% structural) |
|---|---:|---:|
| MAE | 2.342 | **2.273** |
| Correlation | 0.223 | **0.238** |
| Weekly top-five points | **5.178** | 5.049 |
| Three-GW top-five utility | **12.603** | 12.068 |
| NDCG@10 | 0.395 | **0.396** |
| Captain regret | 10.135 | 10.135 (same picks) |

`accepted_for_optimizer` remains **false**: the hybrid is a better estimator
but still a worse selector of the extreme top of the ranking. Team replays
were not rerun and nothing was promoted to the optimizer or dashboard.

**Penalty and set-piece shares (blocked by data).** The archived gameweek data
has no penalties-taken or set-piece columns (only `penalties_missed` and
`penalties_saved`), so an explicit penalty-share model cannot be fit from this
archive. Penalty expectation is partially captured implicitly because player
xG (which includes penalty xG) drives the market goal-share allocation. A
future source (e.g. Understat penalty attempts or FPL `penalties_order`
snapshots) is needed to model it explicitly.

**Remaining gap.** The consistent pattern across all improvements is that the
structural model wins on average error and loses on the extreme upper tail.
Closing the gate likely requires explicit haul-oriented modelling — e.g.
ranking by a calibrated tail objective rather than mean xP, correlated
goal/assist events within a match, or a residual learner for star players on
top of the structural mean.
