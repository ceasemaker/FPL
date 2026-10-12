#!/usr/bin/env python3
"""Captain-pick backtest for the production points model.

The homepage captain card is driven by the RandomForest points regressor in
``django_etl/etl/ml/model.py``. This script replays that model week by week
over past seasons and asks one question: is its top pick a better captain
than simple, defensible alternatives?

Leakage control matches the other backtests: every feature for gameweek G uses
outcomes through G-1 only, and models are refit each week on rows strictly
before the predicted gameweek.

Production parity and its limits:

- Features mirror ``etl/ml/features.py``. ``transfers_balance`` has no weekly
  history in ``fpl_data`` and is dropped; ``value`` uses the season's initial
  price because weekly prices are not stored.
- ``prod_within`` trains only on the current season so far, which is what the
  production database holds. ``prod_history`` also trains on earlier seasons.
- FPL's own weekly projection (``ep_next``) and weekly ownership are not in
  the historical data, so the "most-owned premium" baseline uses the most
  expensive available player as a proxy.
- Injury status is not stored historically either. Every method picks from
  the same pool: players with a fixture who played 60+ minutes the previous
  gameweek.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from run_backtest import SEASON_LABELS, read_initial_prices, read_player_season

POSITION_IDS = {"Goalkeeper": 1, "Defender": 2, "Midfielder": 3, "Forward": 4}
FORM_WINDOW = 3
DEFAULT_FDR = 3
FIRST_SCORED_GAMEWEEK = 4
EARLY_SEASON_LAST_GAMEWEEK = 10
EVALUATION_SEASONS = (2023, 2024, 2025)

# Same order as etl/ml/features.py FEATURE_NAMES minus transfers_balance.
FEATURES = [
    "position",
    "form_3gw",
    "ppg_to_date",
    "xg_3gw",
    "xa_3gw",
    "xgc_3gw",
    "minutes_3gw",
    "games_to_date",
    "fixture_count",
    "home_fixtures",
    "opponent_fdr",
    "value",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("fpl_data"))
    parser.add_argument(
        "--market-dir", type=Path,
        default=Path("analysis/fpl_decision_backtest/data/historical_market"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("analysis/fpl_decision_backtest/output"),
    )
    return parser.parse_args()


def fixture_context(market_dir: Path, season: int) -> pd.DataFrame:
    """fixture_count, home_fixtures and mean FDR per (team name, gameweek)."""
    label = SEASON_LABELS[season].replace("/", "-")  # 2025/26 -> 2025-26
    teams = pd.read_csv(market_dir / f"{label}-teams.csv")[["id", "name"]]
    fixtures = pd.read_csv(market_dir / f"{label}-fixtures.csv")
    fixtures = fixtures.dropna(subset=["event"])
    home = fixtures.assign(team_id=fixtures["team_h"], home=1, fdr=fixtures["team_h_difficulty"])
    away = fixtures.assign(team_id=fixtures["team_a"], home=0, fdr=fixtures["team_a_difficulty"])
    sides = pd.concat([home, away])[["event", "team_id", "home", "fdr"]]
    context = (
        sides.groupby(["team_id", "event"])
        .agg(fixture_count=("home", "size"), home_fixtures=("home", "sum"), opponent_fdr=("fdr", "mean"))
        .reset_index()
        .merge(teams, left_on="team_id", right_on="id")
        .rename(columns={"name": "team", "event": "gameweek"})
    )
    context["gameweek"] = context["gameweek"].astype(int)
    return context[["team", "gameweek", "fixture_count", "home_fixtures", "opponent_fdr"]]


def build_season(data_root: Path, market_dir: Path, season: int) -> pd.DataFrame:
    frame = read_player_season(data_root, season)
    frame = frame.merge(read_initial_prices(data_root, season), on="player_id", how="left")
    frame = frame.sort_values(["player_id", "gameweek"]).reset_index(drop=True)

    grouped = frame.groupby("player_id")
    lagged = lambda column: grouped[column].shift(1)  # noqa: E731

    def window_sum(column: str) -> pd.Series:
        return (
            lagged(column)
            .groupby(frame["player_id"])
            .rolling(FORM_WINDOW, min_periods=1)
            .sum()
            .reset_index(level=0, drop=True)
            .fillna(0.0)
        )

    frame["form_3gw"] = window_sum("total_points")
    frame["xg_3gw"] = window_sum("expected_goals")
    frame["xa_3gw"] = window_sum("expected_assists")
    frame["xgc_3gw"] = window_sum("expected_goals_conceded")
    frame["minutes_3gw"] = window_sum("minutes")
    frame["games_to_date"] = grouped.cumcount()
    prior_points = grouped["total_points"].cumsum() - frame["total_points"]
    frame["ppg_to_date"] = np.where(frame["games_to_date"] > 0, prior_points / frame["games_to_date"].clip(lower=1), 0.0)
    frame["prev_minutes"] = lagged("minutes").fillna(0.0)
    frame["position"] = frame["position"].map(POSITION_IDS).fillna(0).astype(int)
    frame["value"] = (frame["initial_price"].fillna(0.0) * 10).round()

    frame = frame.merge(fixture_context(market_dir, season), on=["team", "gameweek"], how="left")
    frame["fixture_count"] = frame["fixture_count"].fillna(0).astype(int)
    frame["home_fixtures"] = frame["home_fixtures"].fillna(0).astype(int)
    frame["opponent_fdr"] = frame["opponent_fdr"].fillna(DEFAULT_FDR)
    return frame


def production_regressor() -> RandomForestRegressor:
    # Hyperparameters copied from etl/ml/model.py; the StandardScaler there is
    # a no-op for tree models and is omitted.
    return RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42, n_jobs=-1)


def score_production(all_rows: pd.DataFrame, season: int, gameweek: int, with_history: bool) -> pd.Series:
    """Fit on rows strictly before (season, gameweek); score that gameweek."""
    same_season_before = (all_rows["season"] == season) & (all_rows["gameweek"].between(2, gameweek - 1))
    mask = same_season_before
    if with_history:
        mask = mask | ((all_rows["season"] < season) & (all_rows["gameweek"] >= 2))
    train = all_rows[mask]
    target = all_rows[(all_rows["season"] == season) & (all_rows["gameweek"] == gameweek)]
    model = production_regressor().fit(train[FEATURES], train["total_points"])
    return pd.Series(model.predict(target[FEATURES]), index=target.index)


def load_stacked_scores(output_dir: Path) -> pd.DataFrame:
    path = output_dir / "stacked_player_predictions.csv"
    if not path.exists():
        return pd.DataFrame(columns=["season", "gameweek", "player_id", "stacked_xp"])
    return pd.read_csv(path)[["season", "gameweek", "player_id", "stacked_xp"]]


def main() -> None:
    args = parse_args()
    seasons = sorted(SEASON_LABELS)
    all_rows = pd.concat(
        [build_season(args.data_root, args.market_dir, s).assign(season=s) for s in seasons],
        ignore_index=True,
    )
    stacked = load_stacked_scores(args.output_dir)

    picks: list[dict] = []
    for season in EVALUATION_SEASONS:
        last_gw = int(all_rows.loc[all_rows["season"] == season, "gameweek"].max())
        for gameweek in range(FIRST_SCORED_GAMEWEEK, last_gw + 1):
            week = all_rows[(all_rows["season"] == season) & (all_rows["gameweek"] == gameweek)].copy()
            week["prod_within"] = score_production(all_rows, season, gameweek, with_history=False)
            week["prod_history"] = score_production(all_rows, season, gameweek, with_history=True)
            week["form_baseline"] = week["form_3gw"]
            week["premium_baseline"] = week["value"] + week["form_3gw"] / 1000  # price, form breaks ties
            week = week.merge(stacked, on=["season", "gameweek", "player_id"], how="left")

            pool = week[(week["fixture_count"] > 0) & (week["prev_minutes"] >= 60)]
            if pool.empty:
                continue
            best = float(pool["total_points"].max())
            for method in ("prod_within", "prod_history", "form_baseline", "premium_baseline", "stacked_xp"):
                scored = pool.dropna(subset=[method])
                if scored.empty:
                    continue
                pick = scored.loc[scored[method].idxmax()]
                picks.append({
                    "season": SEASON_LABELS[season],
                    "gameweek": gameweek,
                    "method": method,
                    "player": pick["web_name"],
                    "position": int(pick["position"]),
                    "predicted": float(pick[method]),
                    "points": float(pick["total_points"]),
                    "regret": best - float(pick["total_points"]),
                })
        print(f"scored {SEASON_LABELS[season]}", flush=True)

    picks_frame = pd.DataFrame(picks)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    picks_frame.to_csv(args.output_dir / "captain_backtest_picks.csv", index=False)

    summary = summarize(picks_frame)
    (args.output_dir / "captain_backtest_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


def summarize(picks: pd.DataFrame) -> dict:
    def stats(frame: pd.DataFrame) -> dict:
        return {
            "weeks": int(len(frame)),
            "mean_captain_points": round(float(frame["points"].mean()), 3),
            "mean_regret": round(float(frame["regret"].mean()), 3),
            "gk_def_pick_share": round(float((frame["position"] <= 2).mean()), 3),
        }

    def paired(a: pd.DataFrame, b: pd.DataFrame) -> dict:
        joined = a.merge(b, on=["season", "gameweek"], suffixes=("_a", "_b"))
        diff = joined["points_a"] - joined["points_b"]
        se = float(diff.std(ddof=1) / np.sqrt(len(diff))) if len(diff) > 1 else float("nan")
        return {"weeks": int(len(diff)), "mean_diff": round(float(diff.mean()), 3), "se": round(se, 3)}

    result: dict = {"by_method": {}, "vs_premium_baseline": {}, "vs_form_baseline": {}}
    for window, frame in (
        ("all", picks),
        ("early_season_gw4_10", picks[picks["gameweek"] <= EARLY_SEASON_LAST_GAMEWEEK]),
    ):
        result["by_method"][window] = {m: stats(g) for m, g in frame.groupby("method")}
        for baseline in ("premium_baseline", "form_baseline"):
            base = frame[frame["method"] == baseline]
            result[f"vs_{baseline}"][window] = {
                m: paired(g, base) for m, g in frame.groupby("method") if m != baseline
            }
    return result


if __name__ == "__main__":
    main()
