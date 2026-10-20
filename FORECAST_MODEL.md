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

### Current result (v2.0, every registered player, production run 2026-10-15)

The full write-up, with every number generated from production result files, is
`analysis/points_forecast_report/points_forecast.pdf` (two-page brief: `brief.pdf`).
In short:

- **Accuracy:** MAE 0.996, correlation 0.575 over 84,200 player-weeks. That beats recent form
  (1.052, 0.493), form × fixtures (1.053) and a ridge regression (1.046, 0.547).
- **Captain:** 6.61 points per week.
  - Against the priciest attacker: +1.46 (+0.42 to +2.49), almost all from 2024/25.
  - Against unadjusted form: +1.37 (+0.22 to +2.48).
  - Against form × fixtures (+0.43, −0.81 to +1.62) and the ridge regression (+0.87, −0.21 to +1.93): no detectable difference.
  - Against the top-100 consensus: −1.59 (−2.50 to −0.73).
  - Verdict: not accepted.
- **Lineups:**
  - Beats form by +2.25 and form × fixtures by +1.61.
  - No detectable difference from the ridge regression.
  - Trails the managers' own choices by −2.29 (−1.28 from the eleven, −1.01 from the armband).

Earlier figures (6.75 etc.) came from a history that dropped players who never played
that season. That is hindsight, and an independent review caught it, so they are superseded.

### Squad changes, tested and not adopted (local run 2026-10-15)

`analysis/points_forecast_report/squad_changes_eval.py` added two ideas from Sincere FC's videos to v2.0 and reran the same
walk-forward backtest (results in `squad_changes_eval.json`). Gains are paired by gameweek, with 95% bootstrap ranges.

- **Defensive turnover** (the share of last season's goalkeeper and defender minutes that left the club, own and opponents'):
  - Error fell by 0.004 points (0.002 to 0.006), and by 0.007 for goalkeepers and defenders in GW1-8.
  - Captain −0.07 (−0.72 to +0.64) and lineup +0.19 (−0.36 to +0.78): no detectable change in decisions.
- **Made the leap** (season-to-date xG + xA and minutes share against last season, plus last season's same-club rise in usage and xG + xA):
  - No accuracy gain: −0.001 (−0.002 to 0.000).
  - Captain +0.50 (−0.29 to +1.32): within noise.

Neither changes picks, and both were tested on seasons already used to build the model, so production stays on v2.0.
Turnover is the stronger candidate to re-test on a season the model hasn't seen. Both measures are in Chart Lab's Changes mode.

## Production

`run_forecast` runs as step 9 of the daily pipeline, and through
`refresh_before_deadline` every 3 hours near a deadline. Each run:

1. Trains on every finished week.
2. Stores the model.
3. Writes forecasts.
4. Logs shadow picks for the next deadline: the model, FPL `ep_next`, and the priciest attacker. Live picks skip players FPL flags as out, or below a 75% chance.
5. Scores finished weeks, adding FPL's most-captained player.

**Memory and Render jobs (October 2026).**
- The web service and the Celery worker share one 512 MB instance and use about 400 MB at rest.
- Forecast training peaks at about 450 MB on Render; the backtest needs more.
- Running these inside the instance caused the October crash loop and suspension.

Heavy scheduled work now runs as **Render one-off jobs**:
- The worker only calls the Render API: `start_render_job` in `etl/tasks.py`, using `RENDER_API_KEY` and Render's own `RENDER_SERVICE_ID`.
- Each job runs on its own instance and is billed per second.
- Jobs run `python manage.py run_job <name>`. Pipeline steps run as child `manage.py` processes inside the job.
- The forecast always gets a job of its own (`run_forecast`; `run_forecast --sync` near a deadline).
- Each task is capped at two jobs a day (`claim_attempt`, with counts kept in Redis).
- On Render without `RENDER_API_KEY`, heavy tasks skip and log why instead of running in the web instance.
- `backtest_forecast` is not scheduled. Run it as a one-off job: `cd django_etl && python manage.py backtest_forecast`.

## Next candidates

These would mean changing the model after seeing the test seasons. Judge them on
the live shadow record, or on a season the model hasn't seen.

- Bookmaker odds: they are already collected daily in `FixtureOdds`.
- Penalty and set-piece duty.
- Team-news history from `deadline_snapshots`, once a season of it has built up.
