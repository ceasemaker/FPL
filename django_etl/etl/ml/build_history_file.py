"""Build the compact gameweek history file the points model trains on.

The raw weekly exports (``fpl_data/{season}/player_data``, ~90 MB) are not in
git. This script reduces them to one row per player per gameweek with only the
columns the model uses, plus the season's fixtures, and writes
``etl/data/gameweek_history.csv.gz`` and ``etl/data/fixture_history.csv.gz``.
``python manage.py load_gameweek_history`` then loads both into Postgres.

It also writes ``etl/data/elite_squads.csv.gz``: the weekly 15-man squads,
captains and benches of the managers who finished the season in the top 100
(2023/24 onwards). The backtest uses them as the hardest captain baseline and
as real squads to test lineup choices on. They are survivorship-biased: these
managers were picked *because* their choices worked out.

Run from the repo root:

    python django_etl/etl/ml/build_history_file.py \\
        --data-root ~/Desktop/personal/FPL/fpl_data \\
        --fixtures-dir analysis/fpl_decision_backtest/data/historical_market

Sources: the weekly FPL API exports collected by this project, and the FPL
fixtures/teams files for past seasons (the live API only serves the current
season). Player and team ids are per season, so rows carry the stable FPL
``code`` (the Opta id) for both.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

SEASONS = (2022, 2023, 2024, 2025)
POSITIONS = {"Goalkeeper": 1, "Defender": 2, "Midfielder": 3, "Forward": 4}
NUMERIC = [
    "minutes", "starts", "goals_scored", "assists", "clean_sheets", "goals_conceded",
    "own_goals", "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves",
    "bonus", "bps", "expected_goals", "expected_assists", "expected_goals_conceded",
    "defensive_contribution", "total_points",
]
OUT = Path(__file__).resolve().parent.parent / "data"


def slug(season: int) -> str:
    return f"{season}-{(season + 1) % 100:02d}"


def week(path: Path) -> int:
    return int(re.search(r"week-(\d+)", path.name).group(1))


def season_frames(data_root: Path, fixtures_dir: Path, season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    teams = pd.read_csv(fixtures_dir / f"{slug(season)}-teams.csv")
    team_code = teams.set_index("name")["code"]
    team_code_by_id = teams.set_index("id")["code"]

    files = sorted((data_root / str(season) / "player_data").glob("public-epl-stats-players-week-*.csv"), key=week)
    if len(files) != 38:
        raise SystemExit(f"{season}: expected 38 weekly files, found {len(files)}")
    weekly = []
    for path in files:
        frame = pd.read_csv(path, low_memory=False)
        frame["gameweek"] = week(path)
        weekly.append(frame)
    players = pd.concat(weekly, ignore_index=True)
    # 2024/25's Assistant Manager chip listed managers as a fifth position.
    players = players[players["position"] != "Manager"]

    overall = pd.read_csv(data_root / str(season) / "overall_player_data" / "overall_payer_data.csv", low_memory=False)
    overall["start_price"] = (overall["now_cost"] - overall["cost_change_start"].fillna(0)) / 10.0
    players = players.merge(overall[["id", "code", "start_price"]], on="id", how="left", validate="many_to_one")
    if players["code"].isna().any():
        raise SystemExit(f"{season}: {players['code'].isna().sum()} rows without a player code")

    for column in NUMERIC:
        if column not in players:  # defensive_contribution starts in 2025/26
            players[column] = 0
        players[column] = pd.to_numeric(players[column], errors="coerce").fillna(0)
    players["season"] = season
    players["element"] = players["id"]
    players["team_code"] = players["team"].map(team_code)
    players["position"] = players["position"].map(POSITIONS)
    if players[["team_code", "position"]].isna().any().any():
        raise SystemExit(f"{season}: unmapped team or position")

    fixtures = pd.read_csv(fixtures_dir / f"{slug(season)}-fixtures.csv")
    fixtures = fixtures[fixtures["event"].notna()].copy()
    fixtures = pd.DataFrame({
        "season": season,
        "fixture_id": fixtures["id"],
        "gameweek": fixtures["event"].astype(int),
        "kickoff_time": fixtures["kickoff_time"],
        "team_h_code": fixtures["team_h"].map(team_code_by_id),
        "team_a_code": fixtures["team_a"].map(team_code_by_id),
        "team_h_score": fixtures["team_h_score"],
        "team_a_score": fixtures["team_a_score"],
    })
    columns = ["season", "gameweek", "element", "code", "web_name", "team_code", "position", "start_price", *NUMERIC]
    return players[columns], fixtures


def elite_squads(data_root: Path, season: int) -> pd.DataFrame:
    """Top-100 finishers' squads, one block of rows per manager (stable order across weeks)."""
    files = sorted((data_root / str(season) / "top_100_teams").glob("public-epl-stats-top100-teams-gw-*.csv"))
    if not files:
        return pd.DataFrame()
    overall = pd.read_csv(data_root / str(season) / "overall_player_data" / "overall_payer_data.csv", low_memory=False)
    code = overall.set_index("id")["code"]
    frames = []
    for path in files:
        frame = pd.read_csv(path, low_memory=False)
        if frame.empty:
            continue
        # Each manager's block starts again at slot 1. Splitting on that copes
        # with Assistant Manager weeks, where a block has a 16th (manager) row.
        manager = frame["position_selected"].eq(1).cumsum() - 1
        keep = frame["position_name"] != "Manager"
        frame, manager = frame[keep], manager[keep]
        frames.append(pd.DataFrame({
            "season": season,
            "gameweek": pd.to_numeric(frame["event"]).astype(int),
            "manager": manager,
            "code": frame["element"].map(code),
            "position": frame["position_name"].map(POSITIONS),
            "slot": frame["position_selected"],
            "multiplier": frame["multiplier"],
            "is_captain": frame["is_captain"].astype(str).eq("True").astype(int),
            "is_vice_captain": frame["is_vice_captain"].astype(str).eq("True").astype(int),
            "chip": frame["active_chip"].fillna("No Chip"),
        }))
    squads = pd.concat(frames, ignore_index=True)
    if squads["code"].isna().any():
        raise SystemExit(f"{season}: squad players without a code")
    squads["code"] = squads["code"].astype(int)
    return squads


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--fixtures-dir", type=Path, required=True)
    args = parser.parse_args()

    players, fixtures = zip(*(season_frames(args.data_root.expanduser(), args.fixtures_dir, s) for s in SEASONS))
    players = pd.concat(players, ignore_index=True)
    fixtures = pd.concat(fixtures, ignore_index=True)
    # Every registered player is kept, including those who never played all
    # season: whether a player will play is not known at earlier deadlines, so
    # dropping them would select the population with hindsight.
    for column in ("expected_goals", "expected_assists", "expected_goals_conceded"):
        players[column] = players[column].round(2)

    OUT.mkdir(exist_ok=True)
    players.to_csv(OUT / "gameweek_history.csv.gz", index=False, compression="gzip")
    fixtures.to_csv(OUT / "fixture_history.csv.gz", index=False, compression="gzip")
    squads = pd.concat([elite_squads(args.data_root.expanduser(), s) for s in SEASONS], ignore_index=True)
    squads.to_csv(OUT / "elite_squads.csv.gz", index=False, compression="gzip")
    print(f"{squads.groupby(['season', 'gameweek', 'manager']).ngroups:,} elite squad-weeks")
    print(f"{len(players):,} player-gameweeks, {len(fixtures):,} fixtures → {OUT}")
    print(players.groupby("season").agg(rows=("code", "size"), players=("code", "nunique"), points=("total_points", "sum")))


if __name__ == "__main__":
    main()
