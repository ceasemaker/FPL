"""Load the history tables into DataFrames."""
from __future__ import annotations

import pandas as pd
from django.db import connection

from ..models import FixtureHistory, GameweekHistory

PLAYER_COLUMNS = [
    "season", "gameweek", "code", "element", "web_name", "team_code", "position", "start_price",
    "minutes", "starts", "saves",
    "bonus", "bps", "expected_goals", "expected_assists", "expected_goals_conceded", "total_points",
]
FIXTURE_COLUMNS = ["season", "gameweek", "team_h_code", "team_a_code", "team_h_score", "team_a_score", "kickoff_time"]


def _read_table(queryset, columns: list[str], chunk: int = 20_000) -> pd.DataFrame:
    """Read rows in chunks straight into typed columns.

    Building a DataFrame from ``values_list`` holds every row as a Python
    tuple first: ~240 MB of objects for a 26 MB table, which doesn't fit next to
    the web service on a 512 MB instance. Reading a chunk at a time keeps that
    to a few MB.
    """
    sql, params = queryset.values_list(*columns).query.sql_with_params()
    parts = []
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        while True:
            rows = cursor.fetchmany(chunk)
            if not rows:
                break
            parts.append(pd.DataFrame.from_records(rows, columns=columns))
            del rows
    if not parts:
        return pd.DataFrame(columns=columns)
    return pd.concat(parts, ignore_index=True)


def load_players() -> pd.DataFrame:
    frame = _read_table(GameweekHistory.objects.all(), PLAYER_COLUMNS)
    frame["start_price"] = pd.to_numeric(frame["start_price"], errors="coerce").astype(float)
    for column in ("expected_goals", "expected_assists", "expected_goals_conceded"):
        frame[column] = frame[column].astype(float)
    # Smaller types for the identifiers and counts (exact, so features don't
    # change); names repeat ~38 times per player, so store them once.
    for column in ("season", "gameweek", "code", "element", "team_code", "position"):
        frame[column] = frame[column].astype("int32")
    frame["web_name"] = frame["web_name"].astype("category")
    return frame


def load_fixtures() -> pd.DataFrame:
    frame = pd.DataFrame.from_records(
        FixtureHistory.objects.exclude(gameweek=None).values_list(*FIXTURE_COLUMNS), columns=FIXTURE_COLUMNS
    )
    return frame


def load_usage() -> pd.DataFrame:
    """Season usage profiles from the Premier League's Opta sheets, one row per player-season.

    Columns: season, code, usage, pea90, created90, create_per_pea, box90,
    team_possession. Used as *previous-season* features, so they are known
    before any gameweek of the season being forecast.
    """
    from ..models import PlayerSeasonStat
    from ..services.usage import player_usage

    seasons = sorted(set(PlayerSeasonStat.objects.filter(competition_id=8).values_list("season", flat=True)))
    rows = []
    for season in seasons:
        for p in player_usage(season, "premier-league"):
            if not p["minutes"] or p["pea"] is None or not str(p["id"]).isdigit():
                continue
            per90 = lambda v: None if v is None else v / p["minutes"] * 90
            rows.append({
                "season": season,
                "code": int(p["id"]),
                "usage": p["usage"],
                "pea90": per90(p["pea"]),
                "created90": per90(p["created"]),
                "create_per_pea": (p["created"] / p["pea"]) if p["created"] is not None and p["pea"] else None,
                "box90": per90(p.get("box_touches")),
                "team_possession": p["teamPossession"],
                "usage_minutes": p["minutes"],
            })
    return pd.DataFrame(rows, columns=["season", "code", "usage", "pea90", "created90", "create_per_pea",
                                       "box90", "team_possession", "usage_minutes"])


# Opta per-match stats summed per FPL gameweek (etl/services/match_details.py).
# Penalties taken: every ``att_pen_*`` outcome (scored, saved, missed, post).
OPTA_STATS = {
    "op_shots": ("total_scoring_att",),
    "op_box_shots": ("attempts_ibox",),
    "op_big_chances": ("big_chance_missed", "big_chance_scored"),
    "op_box_touches": ("touches_in_opp_box",),
    "op_chances": ("total_att_assist",),
    "op_big_created": ("big_chance_created",),
    "op_corners": ("corner_taken",),
}
OPTA_COLUMNS = [*OPTA_STATS, "op_pens"]


def load_opta_gameweeks() -> pd.DataFrame:
    """One row per (season, FPL gameweek, player code) with summed Opta match stats.

    Matches are placed in FPL gameweeks through FPL's own fixture list (FPL
    team codes are Opta team ids), so postponed and rescheduled matches land in
    the gameweek FPL scored them in.
    """
    from ..models import FixtureHistory, PlayerMatchStat

    gameweek = {
        (season, str(home), str(away)): gw
        for season, home, away, gw in FixtureHistory.objects.exclude(gameweek=None)
        .values_list("season", "team_h_code", "team_a_code", "gameweek")
    }
    rows = []
    for season, home, away, code, stats in PlayerMatchStat.objects.filter(match__competition_id=8).values_list(
            "match__season", "match__home_team_id", "match__away_team_id", "player_id", "stats").iterator(chunk_size=5000):
        gw = gameweek.get((season, home, away))
        if gw is None or not str(code).isdigit():
            continue
        row = {"season": season, "gameweek": gw, "code": int(code)}
        for column, keys in OPTA_STATS.items():
            row[column] = sum(float(stats.get(k, 0)) for k in keys)
        row["op_pens"] = sum(float(v) for k, v in stats.items() if k.startswith("att_pen_"))
        rows.append(row)
    frame = pd.DataFrame(rows, columns=["season", "gameweek", "code", *OPTA_COLUMNS])
    if frame.empty:
        return frame
    frame = frame.groupby(["season", "gameweek", "code"], as_index=False).sum()
    for column in ("season", "gameweek", "code"):
        frame[column] = frame[column].astype("int32")
    return frame
