# FPL Quantitative Decision System — Session Handover

Last updated: 2026-08-28

## 1. User goal and decision philosophy

Build a local, personalized FPL decision system that can:

- estimate a player's true expected points;
- quantify player and rank risk;
- identify differentials, dangerous fades, undervalued and overvalued players;
- optimize transfers over a primarily three-gameweek horizon;
- replay historical decisions week by week, starting from GW2 or GW10;
- compare the model's transfer path with the manager's actual or reconstructed
  path using ordinary FPL scoring;
- eventually display the results in the local Decision Lab dashboard.

The user's current FPL entry ID is `576154`. A suspected previous-season entry
ID is `2074090`, but it was not possible to confirm or reconstruct a complete
personal historical squad from it. Anonymous stable squad paths from the
archived eventual top-100 cohort were therefore used for the historical replay.

The user normally makes decisions over three gameweeks. Use weights of `1.00`,
`0.90`, and `0.81` unless later evidence supports something better. Do not
factor Wildcard, Free Hit, Triple Captain or other chips into the primary
comparison. Use an ordinary starting XI, autosubs and one ordinary captain.
Chip-week-excluded sensitivity can remain supplementary.

The central governing principle is: **we are the authority**. Papers, betting
markets and individual metrics are useful inputs, but a model is promoted only
when it improves the actual FPL decision objective on unseen data.

## 2. Repository and local application

Repository:

```text
/Users/nyashamutseta/Desktop/personal/FPL
```

Main areas:

- `analysis/fpl_decision_backtest/`: quantitative research and replays.
- `django_etl/`: Django backend and dashboard services.
- `frontend/`: Vite/React frontend.
- `fpl_data/`: four seasons of archived player and team data.

The Decision Lab page has been available locally at:

```text
http://127.0.0.1:5173/decision-lab
```

At the end of the prior session, Vite and a Django development server had been
running, but a new session should verify rather than assume they are still
alive.

Important repository rule: the worktree already contains many unrelated user
changes and untracked files. Preserve them. Do not reset, clean or overwrite
unrelated work.

## 3. Data and odds policy

Historical player data exists for 2022/23 through 2025/26. It includes minutes,
starts, FPL events, xG, xA, saves, cards, bonus and BPS. The 2025/26 data also
contains defensive-contribution events.

Historical odds are cached under:

```text
analysis/fpl_decision_backtest/data/historical_market/
```

They come from Football-Data.co.uk E0 CSV files and are matched to the archived
FPL fixtures. Opening average 1X2 and over/under 2.5 prices are used. Closing
odds are deliberately excluded because they may contain information arriving
after the FPL deadline.

For current/future odds collection:

- use the free Football-Data downloads when possible;
- download or refresh no more than once per day;
- cache everything locally;
- if multiple remote calls are required, remain at or below roughly five calls
  per minute;
- the same limits must remain true if the application is later run in Docker.

Source page:

```text
https://www.football-data.co.uk/englandm.php
```

## 4. Mathematical decisions already made

The original adapted Black–Scholes player-value equation was rejected. FPL
points are not a tradable underlying asset, no replicating portfolio exists,
and the proposed terms mixed incompatible units. Volatility can inform a
manager's risk utility, but it does not create intrinsic player value.

Ownership affects rank exposure, not raw player expected points. If a player
has points `X`, effective ownership `e`, and the manager multiplier is `m`, the
relative return is:

```text
R = (m - e) X
E[R] = (m - e) E[X]
Var(R) = (m - e)^2 Var(X)
```

The balanced optimizer should maximize expected points rather than force
ownership shields. Protect/chase modes may add an explicitly labelled risk
utility later.

The current mathematical specification is:

```text
analysis/fpl_decision_backtest/MATH_SPEC.md
```

## 5. Completed empirical models

### Ridge player forecast

Implemented in:

```text
analysis/fpl_decision_backtest/run_backtest.py
```

Features are shifted so GW `G` uses results only through `G-1`. Each evaluation
season is trained only on earlier seasons.

### Odds-enhanced ridge forecast

Implemented in:

```text
analysis/fpl_decision_backtest/run_odds_backtest.py
```

It adds no-vig opening-market win, draw, loss and over-2.5 context. On the
2025/26 decision-player population its approximate correlation was `0.223` and
MAE was `2.3423`.

### Structural Poisson/event forecast

Implemented in:

```text
analysis/fpl_decision_backtest/run_structural_backtest.py
```

Tests:

```text
analysis/fpl_decision_backtest/test_structural_backtest.py
```

Method:

1. Normalize opening bookmaker odds to remove the overround.
2. Invert the no-vig over-2.5 probability to obtain the total Poisson goal rate.
3. Fit the home share so independent home/away Poisson rates best reproduce the
   no-vig 1X2 probabilities.
4. Estimate player minutes, xG and xA using six lagged matches and positional
   priors built only from earlier seasons.
5. Allocate the market-implied team goal rate to players by their expected xG
   shares. Allocate assisted goals by xA share.
6. Translate appearances, goals, assists, clean sheets, concessions, saves,
   cards, bonus, penalties and applicable defensive contributions through
   ordinary FPL scoring.
7. Simulate player outcomes to produce blank probability, haul probability and
   10th/90th percentile estimates.

Official 2025/26 defensive-contribution thresholds used:

- defenders: 10 qualifying contributions for 2 points;
- midfielders/forwards: 12 for 2 points;
- maximum 2 defensive-contribution points per match.

The archived 2024/25 data unexpectedly contains the discontinued FPL Challenge
`Manager` position. The structural model explicitly filters it out.

## 6. Structural backtest result and authority gate

Summary output:

```text
analysis/fpl_decision_backtest/output/structural_backtest_summary.json
analysis/fpl_decision_backtest/output/structural_model_summary.csv
analysis/fpl_decision_backtest/output/structural_weekly_summary.csv
analysis/fpl_decision_backtest/output/structural_player_predictions.csv
```

Research report:

```text
analysis/fpl_decision_backtest/STRUCTURAL_REPORT.md
```

Results:

| Season | Model | MAE | RMSE | Correlation | Weekly top-five points |
|---|---|---:|---:|---:|---:|
| 2024/25 | Odds ridge | 2.268 | 3.073 | 0.299 | 6.530 |
| 2024/25 | Structural | **2.071** | 3.111 | **0.314** | **6.578** |
| 2025/26 | Odds ridge | 2.342 | **3.154** | 0.223 | **5.178** |
| 2025/26 | Structural | **2.217** | 3.270 | **0.226** | 4.941 |

The blend was selected on 2024/25 only. Validation selected a 100% structural
weight. The untouched 2025/26 season therefore remained a clean test.

The structural model reduced 2025/26 MAE by about 5.3% and slightly improved
correlation, but its weekly top-five selections scored worse. The final
authority gate is therefore:

```text
accepted_for_optimizer = false
```

Do not silently replace the optimizer forecast with structural xP. The current
model appears good at predicting ordinary/low-scoring player-weeks but
underestimates the upper tail, which matters disproportionately for transfers
and captaincy.

The simulated blank/haul probabilities are currently diagnostic rather than
fully calibrated. In a quick check, haul probability was materially too low.

## 7. Historical squad replay

Implemented in:

```text
analysis/fpl_decision_backtest/run_team_replay.py
```

Current reports and outputs:

```text
analysis/fpl_decision_backtest/TEAM_REPLAY_REPORT.md
analysis/fpl_decision_backtest/output/team_replay_gw2_summary.json
analysis/fpl_decision_backtest/output/team_replay_gw2_weekly.csv
analysis/fpl_decision_backtest/output/team_replay_gw10_summary.json
analysis/fpl_decision_backtest/output/team_replay_gw10_weekly.csv
```

Current replay results for the earlier odds/ridge projection were poor:

- GW2 start: median model-path difference about `-330`; `0/100` paths won.
- GW10 start: median model-path difference about `-239.5`; `0/100` paths won.
- Excluding chip weeks improved the medians but did not reverse the result.

This does not demonstrate an optimizer algebra error by itself. It mainly shows
that the projection/ranking inputs and possibly the hand-set transfer rules
were not decision-grade.

The replay uses reconstructed season-start prices because reliable historical
weekly prices were not archived. Treat it as a model diagnostic, not a perfect
cash-flow reconstruction.

The squad cohort consists of managers who eventually finished in the top 100,
reconstructed across the whole season. This is survivorship-biased and must not
be described as the contemporaneous top 100.

## 8. Dashboard state

The Django/React Decision Lab already displays earlier live/replay analysis.
Relevant files include:

```text
django_etl/etl/services/decision_dashboard.py
django_etl/etl/api_views.py
frontend/src/pages/DecisionDashboardPage.tsx
frontend/src/pages/DecisionDashboardPage.css
```

The structural forecast was deliberately not wired in as the optimizer's main
forecast because it failed the top-five authority criterion. If exposing it in
the dashboard, label it clearly as a structural/risk diagnostic and show both
the MAE improvement and selection failure.

## 9. Recommended next phase

The next session should improve upper-tail and three-gameweek selection quality
before touching the optimizer authority:

1. Improve the minutes model — **DONE 2026-08-28**:
   - three states (start / substitute appearance / none) from lagged starts,
     shrunk to positional priors; player-specific minutes per start and per
     substitute; `p_60 = p_start * P(60 | start)`; simulation updated to draw
     the states directly.
   - Result on untouched 2025/26: weekly top-five 4.941 → 5.011, MAE held at
     2.218. Gate still fails (ridge top-five 5.178), so
     `accepted_for_optimizer` remains false. See STRUCTURAL_REPORT.md update.
2. Model penalty, direct-set-piece and corner/free-kick shares explicitly.
   **Blocked by data 2026-08-28**: the archive has no penalties-taken or
   set-piece columns; penalty xG is captured implicitly via the xG share
   allocation. Needs an external source (Understat attempts or FPL
   `penalties_order` snapshots).
3. Separate official FPL assists from statistical xA; the simple 75% assisted-
   goal constant is likely too crude. **Partially tested 2026-08-28**: simply
   replacing 0.75 with the earlier-season empirical FPL-assist rate (~0.90)
   worsened top-five selection on both validation and test seasons and was
   reverted; a structural FPL-assist model is still needed.
4. Improve bonus modelling — **DONE 2026-08-28**: per-position event-driven
   least-squares bonus (fit on earlier seasons) blended 50/50 with the rolling
   empirical bonus; validated on 2024/25 (top-five 6.73 → 6.78).
5. Calibrate blank and haul probabilities — **DONE 2026-08-28**: per-position
   Platt scaling fit on 2024/25 only; hauls were understated ~2x; Brier
   improved on unseen 2025/26; calibrated columns exported.
6. Ranking metrics — **DONE 2026-08-28**: NDCG@10, captain regret and realized
   three-gameweek top-five utility added to the weekly summary and manifest.
7. Three-gameweek selection — **DONE 2026-08-28**: blend weight now selected
   on 2024/25 by realized 3-GW top-five utility (weights 1.0/0.9/0.81);
   validation chose a 35% structural / 65% ridge hybrid.
8. Only after passing those checks, rerun both GW2 and GW10 team-path replays and
   expose the accepted forecast in the dashboard. **Not triggered 2026-08-28**:
   the extended gate still fails. On unseen 2025/26 the 35% hybrid beats ridge
   on MAE (2.273 vs 2.342), correlation (0.238 vs 0.223) and NDCG@10, but
   loses one-week top-five (5.049 vs 5.178) and 3-GW top-five utility (11.650
   vs 12.211). `accepted_for_optimizer = false`; replays not rerun; nothing
   promoted. The remaining gap is upper-tail selection — see the 2026-08-28
   second-pass section of STRUCTURAL_REPORT.md for the recommended haul-
   oriented next steps.

A reasonable architecture may ultimately use structural xP for calibrated mean
and risk, plus a residual learner for player-specific effects. That hybrid must
still pass the unseen decision gate; it should not be assumed superior.

## 10. Commands

From the repository root:

```bash
python analysis/fpl_decision_backtest/run_backtest.py
python analysis/fpl_decision_backtest/run_odds_backtest.py
python analysis/fpl_decision_backtest/run_structural_backtest.py --simulation-draws 300
python analysis/fpl_decision_backtest/run_team_replay.py --season 2025 --start-gameweek 2
python analysis/fpl_decision_backtest/run_team_replay.py --season 2025 --start-gameweek 10
python -m unittest discover -s analysis/fpl_decision_backtest -p 'test_*.py'
```

At the final verification, all 13 analysis tests passed.

For local application development:

```bash
cd django_etl && python manage.py runserver 0.0.0.0:8000
cd frontend && npm run dev
```

## 11. Key cautions for the next session

- Preserve all existing dirty-worktree changes.
- Maintain strict GW-1 feature timing and earlier-season-only priors.
- Use opening rather than closing odds for deadline-safe historical testing.
- Do not repeatedly call the free odds source; use the daily local cache.
- Do not introduce chip effects into the primary transfer comparison.
- Do not claim that lower MAE alone makes a better FPL selector.
- Do not promote the structural model until unseen top-player and three-week
  transfer outcomes also improve.
- Keep outputs and explanations understandable to a non-technical user, while
  retaining the full mathematics in the research files.
