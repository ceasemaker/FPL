# Historical Odds Backtest

## Result

Opening bookmaker probabilities added a modest, repeatable improvement to the
player model across the two requested evaluation seasons. On 13,286 likely-
starter player-gameweeks, weighted MAE fell from 2.331 to 2.306 points, an
improvement of 1.1%.

The weekly top-five screen improved more visibly: selected players averaged
5.85 points with the odds layer versus 5.38 without it. This is a screening
result, not a legal 15-player squad simulation.

| Season | Player-weeks | Base MAE | Odds MAE | MAE lift | Base top-five | Odds top-five |
|---|---:|---:|---:|---:|---:|---:|
| 2024/25 | 6,613 | 2.301 | 2.268 | 1.4% | 5.81 | 6.53 |
| 2025/26 | 6,673 | 2.361 | 2.342 | 0.8% | 4.94 | 5.18 |

## Walk-forward design

- 2024/25 was trained only on 2022/23 and 2023/24.
- 2025/26 was trained only on 2022/23 through 2024/25.
- Player form features stop at the preceding gameweek.
- All 380 league matches in every source season matched an FPL gameweek.
- The market inputs are no-vig home/draw/away and over-2.5 probabilities.
- Only Football-Data's opening average prices are used. Closing columns are
  excluded because a closing price may occur after the FPL deadline.

## Interpretation

The odds should calibrate fixture difficulty, not replace the player model.
They improved both seasons but the MAE gain is small, so claims that odds reveal
a player's “true value” on their own would be too strong. Their best use is as
one independent signal alongside minutes, role, form, price and ownership.

The top-five lift is promising but noisier than the all-player MAE result. The
next validation should run the full constrained 15-player selection and
transfer strategy, including captaincy and opportunity cost, before treating
the 0.48-point screen lift as achievable team gain.
