# FPL Decision Backtest

This analysis replaces the proposed Black–Scholes heuristic with an empirical,
week-by-week framework for four related questions:

1. What is the player's next-gameweek expected points value?
2. How uncertain is that outcome?
3. How much relative-rank exposure follows from owning, captaining, or fading the player?
4. Is the player attractive relative to alternatives at the same position and price?

## Leakage controls

- Features for gameweek `G` use player outcomes through `G-1` only.
- The 2023/24 model is trained on 2022/23, the 2024/25 model on the two earlier
  seasons, and the 2025/26 model on the three earlier seasons.
- Final-season price data is used only to algebraically recover the published
  initial price (`now_cost - cost_change_start`). Price changes within the
  season are deliberately not reconstructed from incomplete transfer samples.
- Current-week realized effective ownership is used only for retrospective
  rank-impact measurement. The actionable ownership estimate is the prior
  week's effective ownership.

## Metric interpretation

- `predicted_points`: model estimate of next-gameweek points.
- `points_p10`, `points_p90`: estimated 10th and 90th outcome percentiles.
- `predictive_sd`: percentile range converted to an approximate standard deviation.
- `forecast_eo`: prior-week effective ownership among the eventual season-end top 100.
- `nonowner_expected_drag`: expected relative points from fading the player.
- `*_rank_sd`: outcome uncertainty scaled by the ownership/captain multiplier gap.
- `value_above_replacement_per_m`: projected points above a positional replacement
  baseline per extra £1m of initial price.
- `valuation_edge`: projected points minus a weekly, position-specific expected-points
  price curve. `fair_price` inverts that curve to express the forecast as a price.

## Run

Use the bundled analysis Python environment from the Codex desktop workspace.
The model is a self-contained regularized regression and does not require
scikit-learn:

```bash
/Users/nyashamutseta/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  analysis/fpl_decision_backtest/run_backtest.py
```

Outputs are written to `analysis/fpl_decision_backtest/output/`.

## Personalized live phase

The live evaluator accepts a public FPL entry ID and evaluates legal lineups and
all affordable same-position one-transfer moves under three rank objectives:

```bash
python analysis/fpl_decision_backtest/live_team_analysis.py 576154 \
  --horizon 3 \
  --output analysis/fpl_decision_backtest/output/team_576154_live.json
```

- `protect` penalizes relative-rank variance.
- `balanced` maximizes expected points.
- `chase` accepts more relative-rank variance for upside.

Public FPL data can lag transfers made since the most recent deadline. The live
evaluator is a transparent bridge until current-season database synchronization,
bookmaker-calibrated projections, and deadline-tier EO are available.

## Historical odds phase

Run the cached Football-Data comparison with:

```bash
python analysis/fpl_decision_backtest/run_odds_backtest.py
```

Historical source files are downloaded once into `data/historical_market/`.
Subsequent runs reuse the cache; current-season collection remains governed by
the separate once-daily downloader.

## Structural Poisson phase

Run the leakage-safe event model with:

```bash
python analysis/fpl_decision_backtest/run_structural_backtest.py
```

It infers home and away goal intensities from cached, no-vig opening odds,
allocates team goal and assist expectations using lagged player xG/xA and
minutes, applies ordinary FPL scoring, and generates blank/haul risk estimates.
The acceptance gate compares both general forecast error and weekly selection
quality on the untouched 2025/26 season. See `STRUCTURAL_REPORT.md` for the
current verdict.

## Anonymous team-path replay

The archived top-100 squad files preserve 100 stable 15-player squad slots for
all 38 gameweeks, although the original export omitted manager IDs. Run the
transfer-only replay from the squad revealed in GW10 with:

```bash
python analysis/fpl_decision_backtest/run_team_replay.py \
  --season 2025 \
  --start-gameweek 10
```

The first counterfactual decision is GW11. Each squad can hold, make one
transfer, or make two transfers, with banked free transfers and ordinary
4-point hit accounting. Decisions use a frozen three-gameweek view with weights
of 1.00, 0.90 and 0.81; later realized form is never borrowed. The replay uses
the cached bookmaker-calibrated player forecast when available. Headline totals
strip chip multipliers and reconstruct an ordinary XI, normal autosubs and one
normal captain on every week. A chip-week-excluded sensitivity is retained.
Detailed weekly results and
the cohort summary are saved as `team_replay_gw10_weekly.csv` and
`team_replay_gw10_summary.json`.

Pass `--start-gameweek 2` for the requested early-season stress test. See
`TEAM_REPLAY_REPORT.md` for the current results and verdict.

Weekly prices were not archived, so this phase uses reconstructed season-start
prices. It is a model diagnostic rather than a fully faithful reconstruction of
FPL cash flows.

## Important limitation

The ownership cohort consists of the managers who ultimately finished in the
top 100, reconstructed across their season. It is therefore survivorship-biased
and must not be described as the contemporaneous top 100. It is useful for
studying elite-manager exposure, but a production model should ingest deadline
EO snapshots for the user's actual comparison tier.
