#!/usr/bin/env python3
"""Measure the incremental value of pre-match bookmaker context.

Historical inputs are downloaded once and cached locally. Football-Data's
opening average 1X2 and over/under prices are used; closing prices are
deliberately excluded because they can move after an FPL deadline.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from run_backtest import (
    FEATURE_COLUMNS,
    SEASON_LABELS,
    RidgeModel,
    add_historical_features,
    read_initial_prices,
    read_player_season,
)


MARKET_FEATURES = [
    "market_win_probability",
    "market_draw_probability",
    "market_loss_probability",
    "market_over25_probability",
    "market_home",
]
EVALUATION_SEASONS = (2024, 2025)
USER_AGENT = "FPL-Decision-System/1.0 historical-backtest"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("fpl_data"))
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("analysis/fpl_decision_backtest/data/historical_market"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis/fpl_decision_backtest/output"),
    )
    return parser.parse_args()


def season_slug(season: int) -> str:
    return f"{season}-{str(season + 1)[-2:]}"


def football_data_code(season: int) -> str:
    return f"{str(season)[-2:]}{str(season + 1)[-2:]}"


def download_once(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
    path.write_bytes(content)
    return path


def normalize_team(value: object) -> str:
    name = re.sub(r"[^a-z0-9]", "", str(value).lower())
    aliases = {
        "tottenham": "spurs",
        "nottinghamforest": "nottmforest",
        "sheffieldunited": "sheffutd",
        "sheffieldutd": "sheffutd",
        "manchesterunited": "manutd",
        "manunited": "manutd",
        "manchestercity": "mancity",
        "newcastleunited": "newcastle",
        "leedsunited": "leeds",
        "leicestercity": "leicester",
        "norwichcity": "norwich",
    }
    return aliases.get(name, name)


def no_vig_probabilities(*odds: object) -> list[float]:
    numeric = np.array([float(value) for value in odds], dtype=float)
    inverse = 1.0 / numeric
    return (inverse / inverse.sum()).tolist()


def load_team_gameweek_market(season: int, cache_dir: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    slug = season_slug(season)
    code = football_data_code(season)
    github_root = (
        "https://raw.githubusercontent.com/vaastav/"
        f"Fantasy-Premier-League/master/data/{slug}"
    )
    odds_path = download_once(
        f"https://www.football-data.co.uk/mmz4281/{code}/E0.csv",
        cache_dir / f"{code}-E0.csv",
    )
    fixtures_path = download_once(
        f"{github_root}/fixtures.csv", cache_dir / f"{slug}-fixtures.csv"
    )
    teams_path = download_once(
        f"{github_root}/teams.csv", cache_dir / f"{slug}-teams.csv"
    )

    odds = pd.read_csv(odds_path)
    fixtures = pd.read_csv(fixtures_path)
    teams = pd.read_csv(teams_path)[["id", "name"]]
    fixtures = fixtures[fixtures["event"].notna()].copy()
    team_names = teams.set_index("id")["name"]
    fixtures["home_team"] = fixtures["team_h"].map(team_names)
    fixtures["away_team"] = fixtures["team_a"].map(team_names)
    fixtures["home_key"] = fixtures["home_team"].map(normalize_team)
    fixtures["away_key"] = fixtures["away_team"].map(normalize_team)
    odds["home_key"] = odds["HomeTeam"].map(normalize_team)
    odds["away_key"] = odds["AwayTeam"].map(normalize_team)

    required = ["AvgH", "AvgD", "AvgA", "Avg>2.5", "Avg<2.5"]
    odds = odds.dropna(subset=required)
    matches = fixtures.merge(
        odds[["home_key", "away_key", *required]],
        on=["home_key", "away_key"],
        how="inner",
        validate="one_to_one",
    )
    if len(matches) != 380:
        missing = fixtures.merge(
            odds[["home_key", "away_key"]],
            on=["home_key", "away_key"],
            how="left",
            indicator=True,
        )
        missing = missing.loc[missing["_merge"] == "left_only", ["home_team", "away_team"]]
        raise ValueError(f"Only matched {len(matches)}/380 {slug} matches: {missing.to_dict('records')}")

    team_rows: list[dict[str, object]] = []
    for match in matches.to_dict("records"):
        home, draw, away = no_vig_probabilities(match["AvgH"], match["AvgD"], match["AvgA"])
        over, _ = no_vig_probabilities(match["Avg>2.5"], match["Avg<2.5"])
        shared = {"season": season, "gameweek": int(match["event"]), "market_draw_probability": draw,
                  "market_over25_probability": over}
        team_rows.append({**shared, "team_key": match["home_key"], "market_win_probability": home,
                          "market_loss_probability": away, "market_home": 1.0})
        team_rows.append({**shared, "team_key": match["away_key"], "market_win_probability": away,
                          "market_loss_probability": home, "market_home": 0.0})

    team_market = pd.DataFrame(team_rows).groupby(
        ["season", "gameweek", "team_key"], as_index=False
    )[MARKET_FEATURES].mean()
    return team_market, {
        "season": season,
        "matches": len(matches),
        "team_gameweeks": len(team_market),
        "double_gameweek_team_rows": len(team_rows) - len(team_market),
    }


def model_comparison(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    season_rows: list[dict[str, object]] = []
    weekly_rows: list[dict[str, object]] = []
    player_rows: list[pd.DataFrame] = []
    for season in EVALUATION_SEASONS:
        train = data[(data["season"] < season) & (data["history_games"] >= 1)].dropna(
            subset=MARKET_FEATURES
        )
        test = data[data["season"] == season].dropna(subset=MARKET_FEATURES).copy()
        decision_train = train[train["minutes_mean_3"].fillna(0) >= 60]
        decision_test = test[test["minutes_mean_3"].fillna(0) >= 60].copy()
        y_train = decision_train["total_points"].clip(-5, 25)

        base_model = RidgeModel().fit(decision_train[FEATURE_COLUMNS], y_train)
        odds_model = RidgeModel().fit(decision_train[FEATURE_COLUMNS + MARKET_FEATURES], y_train)
        decision_test["base_prediction"] = np.clip(
            base_model.predict(decision_test[FEATURE_COLUMNS]), 0, 18
        )
        decision_test["odds_prediction"] = np.clip(
            odds_model.predict(decision_test[FEATURE_COLUMNS + MARKET_FEATURES]), 0, 18
        )
        player_rows.append(
            decision_test[["season", "gameweek", "player_id", "odds_prediction"]].copy()
        )
        if not np.isfinite(decision_test[["base_prediction", "odds_prediction"]].to_numpy()).all():
            raise ValueError(f"Non-finite model output for {SEASON_LABELS[season]}")
        actual = decision_test["total_points"]
        base_error = np.abs(actual - decision_test["base_prediction"])
        odds_error = np.abs(actual - decision_test["odds_prediction"])

        base_picks = []
        odds_picks = []
        for gameweek, week in decision_test.groupby("gameweek"):
            base = week.nlargest(5, "base_prediction")
            market = week.nlargest(5, "odds_prediction")
            base_picks.append(base["total_points"].mean())
            odds_picks.append(market["total_points"].mean())
            week_actual = week["total_points"]
            weekly_rows.append({
                "season": SEASON_LABELS[season],
                "gameweek": int(gameweek),
                "base_mae": float(np.abs(week_actual - week["base_prediction"]).mean()),
                "odds_mae": float(np.abs(week_actual - week["odds_prediction"]).mean()),
                "base_top5_points": float(base["total_points"].mean()),
                "odds_top5_points": float(market["total_points"].mean()),
            })

        base_mae = float(base_error.mean())
        odds_mae = float(odds_error.mean())
        season_rows.append({
            "season": SEASON_LABELS[season],
            "player_gameweeks": len(decision_test),
            "base_mae": base_mae,
            "odds_mae": odds_mae,
            "mae_improvement_pct": 100.0 * (base_mae - odds_mae) / base_mae,
            "base_correlation": float(actual.corr(decision_test["base_prediction"])),
            "odds_correlation": float(actual.corr(decision_test["odds_prediction"])),
            "base_top5_points": float(np.mean(base_picks)),
            "odds_top5_points": float(np.mean(odds_picks)),
        })
    return pd.DataFrame(season_rows), pd.DataFrame(weekly_rows), pd.concat(player_rows, ignore_index=True)


def rounded_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    output = frame.copy()
    numeric = output.select_dtypes(include=[np.number]).columns
    output[numeric] = output[numeric].round(4)
    return output.to_dict("records")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    player_frames = []
    market_frames = []
    coverage = []
    for season in SEASON_LABELS:
        players = read_player_season(args.data_root, season)
        prices = read_initial_prices(args.data_root, season)
        player_frames.append(players.merge(prices, on="player_id", how="left"))
        market, season_coverage = load_team_gameweek_market(season, args.cache_dir)
        market_frames.append(market)
        coverage.append(season_coverage)

    players = add_historical_features(pd.concat(player_frames, ignore_index=True))
    players["team_key"] = players["team"].map(normalize_team)
    markets = pd.concat(market_frames, ignore_index=True)
    joined = players.merge(markets, on=["season", "gameweek", "team_key"], how="left")
    comparison, weekly, player_predictions = model_comparison(joined)

    weighted_base = float(np.average(comparison["base_mae"], weights=comparison["player_gameweeks"]))
    weighted_odds = float(np.average(comparison["odds_mae"], weights=comparison["player_gameweeks"]))
    manifest = {
        "method": {
            "evaluation_seasons": [SEASON_LABELS[season] for season in EVALUATION_SEASONS],
            "odds_source": "Football-Data.co.uk E0.csv",
            "fixture_source": "vaastav/Fantasy-Premier-League",
            "price_snapshot": "opening average odds only",
            "lookahead_control": "season model trains only on earlier seasons; player form stops at GW-1",
        },
        "coverage": coverage,
        "season_results": rounded_records(comparison),
        "overall": {
            "player_gameweeks": int(comparison["player_gameweeks"].sum()),
            "base_mae": round(weighted_base, 4),
            "odds_mae": round(weighted_odds, 4),
            "mae_improvement_pct": round(100.0 * (weighted_base - weighted_odds) / weighted_base, 4),
            "base_top5_points": round(float(comparison["base_top5_points"].mean()), 4),
            "odds_top5_points": round(float(comparison["odds_top5_points"].mean()), 4),
        },
        "weekly": rounded_records(weekly),
    }
    comparison.to_csv(args.output_dir / "odds_model_summary.csv", index=False)
    weekly.to_csv(args.output_dir / "odds_weekly_summary.csv", index=False)
    player_predictions.to_csv(args.output_dir / "odds_player_predictions.csv", index=False)
    (args.output_dir / "odds_backtest_summary.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["overall"], indent=2))


if __name__ == "__main__":
    main()
