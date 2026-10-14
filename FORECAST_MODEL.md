# Points forecast (v2) and the captain gate

The forecast predicts each player's FPL points for the next gameweek. It trains
on four seasons of gameweek data and has to pass a fixed backtest before the
homepage may show its captain pick. Results and the live record are on
**/model-lab**.

## Data

| Table | What | Source |
|---|---|---|
| `gameweek_history` | One row per player per gameweek, 2022/23 onwards | Past seasons: `etl/data/gameweek_history.csv.gz`. This season: mirrored from `AthleteStat` on every ETL pass |
| `fixture_history` | Fixtures with club codes | `etl/data/fixture_history.csv.gz` + live `Fixture` |
| `deadline_snapshots` | FPL's `ep_next`, ownership and availability before each deadline | Every ETL pass, and every 3 hours within 36h of a deadline |
| `gameweek_summaries` | Deadlines and FPL's most-captained player | Bootstrap `events` |
| `forecast_predictions` | Forecasts for the next three gameweeks | `run_forecast` |
| `shadow_picks` | Each strategy's captain, logged before the deadline, scored after | `run_forecast` |
| `model_artifacts`, `model_evaluations` | The trained model (in Postgres, because Render's disk is wiped) and backtest verdicts | `run_forecast`, `backtest_forecast` |

Players and clubs are keyed by FPL `code` (the Opta id), which is stable across
seasons; element and team ids are not. `etl/data/elite_squads.csv.gz` holds the
weekly squads and captains of each season's eventual top-100 managers
(2023/24 onwards), used only by the backtest.

The history files are built from the raw weekly exports (not in git) with:

```bash
python django_etl/etl/ml/build_history_file.py \
  --data-root ~/Desktop/personal/FPL/fpl_data \
  --fixtures-dir ~/Desktop/personal/FPL/analysis/fpl_decision_backtest/data/historical_market
```

## Model

`etl/forecast/`: gradient-boosted trees (`HistGradientBoostingRegressor`) on
deadline-safe features. A row for gameweek G only sees weeks before G.

- **Player form:** minutes and starts over the last 1, 3 and 6 fixtures; points; xG, xA, bonus and saves per 90.
- **Season so far:** this season's rates.
- **Prior:** last season's rates, which carry the early weeks.
- **Fixtures:** the club's and its opponents' rolling xG for and against; home share; double and blank gameweeks.
- **Static:** position, start price, and the DefCon scoring era.

## Backtest and gate

```bash
python manage.py backtest_forecast              # weekly retraining, ~2 min
```

The backtest walks forward through 2023/24–2025/26, retraining each week on
earlier weeks only. The rule was fixed before the first run. Captain picks are
accepted only if the 95% interval of the model's weekly advantage sits above
zero against every baseline:

- the eventual top-100 managers' most-captained player;
- the priciest attacker who started last week;
- the best last-six form.

Intervals come from a bootstrap over gameweeks.

### First result (v2.0, 2026-10-14)

| Captain points per week | 2023/24–2025/26 |
|---|---|
| Model | 6.82 |
| Top-100 managers' captain | 8.20 |
| Priciest attacker who started | 5.20 |
| Best last-six form | 5.31 |
| Best possible | 17.79 |

- **Against "priciest attacker":** +1.61 (95% interval +0.52 to +2.68).
- **Against "last-six form":** +1.51 (+0.22 to +2.80).
- **Against the top-100 consensus:** −1.39 (−2.43 to −0.40).
- **Verdict: not accepted.** The homepage shows no captain.

The top-100 baseline is survivorship-biased: those managers are in the sample
because their choices worked. They also had team news, which the model lacks.

**Lineups:** the model picks the XI and captain from the top-100 managers' real
squads, all scored with ordinary autosubs and no chips. It beats form by +2.45
(+1.18 to +3.73) and trails the managers' own choices by −2.10 (−2.91 to −1.35).

**Forecast accuracy over 58,682 player-weeks:**

| | Average miss (points) | Correlation |
|---|---|---|
| Model | 1.42 | 0.51 |
| Last-six form | 1.50 | 0.41 |

## Production

`run_forecast` runs as step 9 of the daily pipeline, and through
`refresh_before_deadline` every 3 hours near a deadline. Each run:

1. Trains on every finished week.
2. Stores the model.
3. Writes forecasts.
4. Logs shadow picks for the next deadline: the model, FPL `ep_next`, and the priciest attacker. Live picks skip players FPL flags as out, or below a 75% chance.
5. Scores finished weeks, adding FPL's most-captained player.

`backtest_forecast` re-runs every Monday at 04:30. The optimiser uses these
forecasts when they cover its horizon. Players with no history fall back to FPL
`ep_next`.

## Next candidates

These would mean changing the model after seeing the test seasons. Judge them on
the live shadow record, or on a season the model hasn't seen.

- Bookmaker odds: they are already collected daily in `FixtureOdds`.
- Penalty and set-piece duty.
- Team-news history from `deadline_snapshots`, once a season of it has built up.
