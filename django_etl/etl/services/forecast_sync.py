"""Keep the forecasting tables current from the live FPL data.

Called at the end of every ETL pass. Three jobs:

* copy this season's per-gameweek rows (`AthleteStat`, `Fixture`) into the
  season-keyed history tables, so the model sees every season through one
  table and the rows survive the season-rollover purge;
* record the bootstrap `events` facts (deadline, FPL's most-captained player);
* before each deadline, record FPL's expected points and ownership for the
  next gameweek (`DeadlineSnapshot`), which `Athlete` would otherwise overwrite.
"""
from __future__ import annotations

import gzip
import logging
from datetime import datetime
from pathlib import Path
from typing import Sequence

import pandas as pd
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import (
    Athlete,
    AthleteStat,
    DeadlineSnapshot,
    Fixture,
    FixtureHistory,
    GameweekHistory,
    GameweekSummary,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_FIELDS = [
    "minutes", "starts", "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals",
    "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus", "bps",
    "expected_goals", "expected_assists", "expected_goals_conceded", "total_points",
]


def season_of(events_payload: Sequence[dict]) -> int | None:
    deadlines = [parse_datetime(e["deadline_time"]) for e in events_payload if e.get("deadline_time")]
    deadlines = [d for d in deadlines if d is not None]
    return min(deadlines).year if deadlines else None


def current_season() -> int | None:
    """Season start year of the fixtures we hold (FPL seasons start in August)."""
    earliest = Fixture.objects.exclude(kickoff_time=None).order_by("kickoff_time").values_list("kickoff_time", flat=True).first()
    return earliest.year if earliest else None


# ------------------------------------------------------------ history files

def load_history_files(data_dir: Path = DATA_DIR) -> dict[str, int]:
    """Upsert the committed past-season files into the history tables."""
    players = pd.read_csv(data_dir / "gameweek_history.csv.gz")
    fixtures = pd.read_csv(data_dir / "fixture_history.csv.gz")
    seasons = sorted(players["season"].unique().tolist())
    with transaction.atomic():
        GameweekHistory.objects.filter(season__in=seasons).delete()
        GameweekHistory.objects.bulk_create(
            [
                GameweekHistory(
                    season=r.season, gameweek=r.gameweek, code=r.code, element=r.element,
                    web_name=r.web_name, team_code=r.team_code, position=r.position,
                    start_price=None if pd.isna(r.start_price) else round(float(r.start_price), 1),
                    **{f: getattr(r, f) for f in HISTORY_FIELDS},
                )
                for r in players.itertuples(index=False)
            ],
            batch_size=5000,
        )
        FixtureHistory.objects.filter(season__in=seasons).delete()
        FixtureHistory.objects.bulk_create(
            [
                FixtureHistory(
                    season=r.season, fixture_id=r.fixture_id, gameweek=r.gameweek,
                    kickoff_time=parse_datetime(r.kickoff_time) if isinstance(r.kickoff_time, str) else None,
                    team_h_code=r.team_h_code, team_a_code=r.team_a_code,
                    team_h_score=None if pd.isna(r.team_h_score) else int(r.team_h_score),
                    team_a_score=None if pd.isna(r.team_a_score) else int(r.team_a_score),
                )
                for r in fixtures.itertuples(index=False)
            ],
            batch_size=2000,
        )
    return {"seasons": len(seasons), "player_gameweeks": len(players), "fixtures": len(fixtures)}


def elite_squads(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    with gzip.open(data_dir / "elite_squads.csv.gz") as handle:
        return pd.read_csv(handle)


# ------------------------------------------------------- live season sync

def sync_current_season(season: int) -> int:
    """Mirror this season's AthleteStat and Fixture rows into the history tables."""
    athletes = {
        a["id"]: a
        for a in Athlete.objects.values("id", "code", "web_name", "team__code", "element_type", "now_cost", "cost_change_start")
    }
    rows = []
    for stat in AthleteStat.objects.values("athlete_id", "game_week", *HISTORY_FIELDS):
        athlete = athletes.get(stat["athlete_id"])
        if not athlete or athlete["team__code"] is None or athlete["element_type"] not in (1, 2, 3, 4):
            continue
        rows.append(GameweekHistory(
            season=season,
            gameweek=stat["game_week"],
            code=athlete["code"],
            element=stat["athlete_id"],
            web_name=athlete["web_name"],
            # The player's club today: AthleteStat doesn't keep the club per
            # week, so a mid-season move re-labels his earlier weeks.
            team_code=athlete["team__code"],
            position=athlete["element_type"],
            start_price=round((athlete["now_cost"] - (athlete["cost_change_start"] or 0)) / 10, 1),
            **{f: float(stat[f]) if f.startswith("expected") else stat[f] for f in HISTORY_FIELDS},
        ))
    fixtures = [
        FixtureHistory(
            season=season, fixture_id=f["id"], gameweek=f["event"], kickoff_time=f["kickoff_time"],
            team_h_code=f["team_h__code"], team_a_code=f["team_a__code"],
            team_h_score=f["team_h_score"], team_a_score=f["team_a_score"],
        )
        for f in Fixture.objects.values(
            "id", "event", "kickoff_time", "team_h__code", "team_a__code", "team_h_score", "team_a_score"
        )
        if f["team_h__code"] is not None and f["team_a__code"] is not None
    ]
    with transaction.atomic():
        GameweekHistory.objects.filter(season=season).delete()
        GameweekHistory.objects.bulk_create(rows, batch_size=5000)
        FixtureHistory.objects.filter(season=season).delete()
        FixtureHistory.objects.bulk_create(fixtures, batch_size=2000)
    return len(rows)


def sync_gameweek_summaries(season: int, events_payload: Sequence[dict]) -> None:
    for event in events_payload:
        if not event.get("id"):
            continue
        GameweekSummary.objects.update_or_create(
            season=season,
            gameweek=event["id"],
            defaults={
                "deadline_time": parse_datetime(event["deadline_time"]) if event.get("deadline_time") else None,
                "finished": bool(event.get("finished")),
                "most_captained": event.get("most_captained"),
                "most_selected": event.get("most_selected"),
                "average_entry_score": event.get("average_entry_score") or None,
                "highest_score": event.get("highest_score"),
            },
        )


def next_deadline(events_payload: Sequence[dict], now: datetime | None = None) -> tuple[int, datetime] | None:
    now = now or timezone.now()
    upcoming = []
    for event in events_payload:
        deadline = parse_datetime(event.get("deadline_time") or "")
        if event.get("id") and deadline and deadline > now:
            upcoming.append((deadline, event["id"]))
    if not upcoming:
        return None
    deadline, gameweek = min(upcoming)
    return gameweek, deadline


def snapshot_before_deadline(season: int, events_payload: Sequence[dict], elements_payload: Sequence[dict]) -> int:
    """Record FPL's expected points for the next gameweek; the latest run before the deadline wins."""
    upcoming = next_deadline(events_payload)
    if upcoming is None:
        return 0
    gameweek, _ = upcoming
    now = timezone.now()

    def number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    with transaction.atomic():
        for element in elements_payload:
            if not element.get("id") or element.get("code") is None:
                continue
            DeadlineSnapshot.objects.update_or_create(
                season=season,
                gameweek=gameweek,
                element=element["id"],
                defaults={
                    "code": element["code"],
                    "ep_next": number(element.get("ep_next")),
                    "selected_by_percent": number(element.get("selected_by_percent")),
                    "chance_of_playing": element.get("chance_of_playing_next_round"),
                    "status": element.get("status") or "",
                    "now_cost": element.get("now_cost"),
                    "captured_at": now,
                },
            )
    return len(elements_payload)


def sync_forecast_tables(events_payload: Sequence[dict], elements_payload: Sequence[dict]) -> None:
    season = season_of(events_payload)
    if season is None:
        return
    sync_gameweek_summaries(season, events_payload)
    snapshot_before_deadline(season, events_payload, elements_payload)
    rows = sync_current_season(season)
    logger.info("Forecast tables synced for %s: %s player-gameweeks", season, rows)
