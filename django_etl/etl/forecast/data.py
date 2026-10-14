"""Load the history tables into DataFrames."""
from __future__ import annotations

import pandas as pd

from ..models import FixtureHistory, GameweekHistory

PLAYER_COLUMNS = [
    "season", "gameweek", "code", "element", "web_name", "team_code", "position", "start_price",
    "minutes", "starts", "goals_scored", "assists", "clean_sheets", "goals_conceded", "saves",
    "bonus", "bps", "expected_goals", "expected_assists", "expected_goals_conceded", "total_points",
]
FIXTURE_COLUMNS = ["season", "gameweek", "team_h_code", "team_a_code", "team_h_score", "team_a_score", "kickoff_time"]


def load_players() -> pd.DataFrame:
    frame = pd.DataFrame.from_records(GameweekHistory.objects.values_list(*PLAYER_COLUMNS), columns=PLAYER_COLUMNS)
    frame["start_price"] = pd.to_numeric(frame["start_price"], errors="coerce").astype(float)
    return frame


def load_fixtures() -> pd.DataFrame:
    frame = pd.DataFrame.from_records(
        FixtureHistory.objects.exclude(gameweek=None).values_list(*FIXTURE_COLUMNS), columns=FIXTURE_COLUMNS
    )
    return frame
