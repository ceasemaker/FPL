"""Chart Lab data: base stats the browser combines into user-written formulas.

The lab ships raw season totals (and per-gameweek rows on request) for a fixed
set of official FPL stats. Formulas such as ``per90(xg) / xa`` are evaluated
client-side, so the server never parses user input.

The one non-official stat is ``xcs`` (expected clean sheets), estimated from
expected goals conceded; see ``expected_clean_sheet_chance``.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from django.core.cache import cache
from django.db.models import Max

from ..models import Athlete, AthleteStat, Fixture

CACHE_TTL = 600
MAX_SERIES_PLAYERS = 6
POSITION_LABELS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

# Formula variable -> (AthleteStat field, label). Order is the display order.
SUMMED_METRICS: dict[str, tuple[str, str]] = {
    "pts": ("total_points", "Total points"),
    "mins": ("minutes", "Minutes"),
    "starts": ("starts", "Starts"),
    "g": ("goals_scored", "Goals"),
    "a": ("assists", "Assists"),
    "xg": ("expected_goals", "Expected goals (xG)"),
    "xa": ("expected_assists", "Expected assists (xA)"),
    "xgi": ("expected_goal_involvements", "Expected goal involvements (xGI)"),
    "cs": ("clean_sheets", "Clean sheets"),
    "gc": ("goals_conceded", "Goals conceded"),
    "xgc": ("expected_goals_conceded", "Expected goals conceded (xGC)"),
    "saves": ("saves", "Saves"),
    "bonus": ("bonus", "Bonus points"),
    "bps": ("bps", "Bonus points system (BPS)"),
    "inf": ("influence", "Influence"),
    "cre": ("creativity", "Creativity"),
    "thr": ("threat", "Threat"),
    "ict": ("ict_index", "ICT index"),
    "yc": ("yellow_cards", "Yellow cards"),
    "rc": ("red_cards", "Red cards"),
}

EXTRA_METRICS: dict[str, str] = {
    "xcs": "Expected clean sheets (xCS, estimated)",
    "price": "Price (£m)",
    "own": "Ownership (%)",
}


def metric_catalog() -> list[dict]:
    catalog = [{"key": key, "label": label} for key, (_, label) in SUMMED_METRICS.items()]
    catalog += [{"key": key, "label": label} for key, label in EXTRA_METRICS.items()]
    return catalog


def _fixtures_per_team_gameweek() -> dict[tuple[int, int], int]:
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for team_h_id, team_a_id, event in Fixture.objects.filter(event__isnull=False).values_list(
        "team_h_id", "team_a_id", "event"
    ):
        counts[(team_h_id, event)] += 1
        counts[(team_a_id, event)] += 1
    return counts


def expected_clean_sheet_chance(minutes: int, xgc: float, matches: int) -> float:
    """Expected clean sheets earned in one gameweek row.

    FPL publishes no xCS. With goals conceded ~ Poisson(xGC), the chance of a
    clean sheet in a match is exp(-xGC). FPL only awards clean-sheet points
    for 60+ minutes. A gameweek row merges a double gameweek, so xGC and
    minutes are split evenly across the team's fixtures that week.
    """
    matches = matches or 1
    if (minutes or 0) / matches < 60:
        return 0.0
    return matches * math.exp(-float(xgc or 0) / matches)


def expected_clean_sheets(athlete_ids: Iterable[int]) -> dict[int, float]:
    """Season xCS per player (see ``expected_clean_sheet_chance``)."""
    fixtures = _fixtures_per_team_gameweek()
    totals: dict[int, float] = defaultdict(float)
    rows = AthleteStat.objects.filter(athlete_id__in=list(athlete_ids)).values_list(
        "athlete_id", "athlete__team_id", "game_week", "minutes", "expected_goals_conceded"
    )
    for athlete_id, team_id, game_week, minutes, xgc in rows:
        totals[athlete_id] += expected_clean_sheet_chance(
            minutes, xgc, fixtures.get((team_id, game_week), 1)
        )
    return totals


def _number(value) -> float:
    return round(float(value or 0), 3)


def _latest_gameweek() -> int:
    return AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 0


def build_player_totals() -> dict:
    """Season totals of every chartable stat for every listed player."""
    latest = _latest_gameweek()
    cache_key = f"chart_lab:totals:gw{latest}:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached

    athletes = list(
        Athlete.objects.filter(removed=False)
        .select_related("team")
        .only(
            "id", "web_name", "first_name", "second_name", "element_type",
            "now_cost", "selected_by_percent", "team__short_name",
        )
    )
    totals: dict[int, dict[str, float]] = {
        a.id: {key: 0.0 for key in SUMMED_METRICS} for a in athletes
    }
    fields = [field for field, _ in SUMMED_METRICS.values()]
    for row in AthleteStat.objects.filter(athlete_id__in=totals).values("athlete_id", *fields):
        bucket = totals[row["athlete_id"]]
        for key, (field, _) in SUMMED_METRICS.items():
            bucket[key] += float(row[field] or 0)
    xcs = expected_clean_sheets(totals)

    players = []
    for athlete in athletes:
        values = {key: _number(value) for key, value in totals[athlete.id].items()}
        values["xcs"] = _number(xcs.get(athlete.id, 0.0))
        values["price"] = _number((athlete.now_cost or 0) / 10)
        values["own"] = _number(athlete.selected_by_percent)
        players.append({
            "id": athlete.id,
            "name": athlete.web_name,
            "full_name": f"{athlete.first_name} {athlete.second_name}".strip(),
            "team": athlete.team.short_name if athlete.team else None,
            "position": POSITION_LABELS.get(athlete.element_type, "—"),
            "values": values,
        })

    payload = {"latest_gameweek": latest, "metrics": metric_catalog(), "players": players}
    cache.set(cache_key, payload, CACHE_TTL)
    return payload


def build_player_series(athlete_ids: list[int]) -> dict:
    """Per-gameweek stats for up to ``MAX_SERIES_PLAYERS`` players."""
    athlete_ids = athlete_ids[:MAX_SERIES_PLAYERS]
    athletes = {
        a.id: a
        for a in Athlete.objects.filter(id__in=athlete_ids).select_related("team")
    }
    fixtures = _fixtures_per_team_gameweek()
    fields = [field for field, _ in SUMMED_METRICS.values()]
    rows_by_player: dict[int, list[dict]] = defaultdict(list)
    for row in (
        AthleteStat.objects.filter(athlete_id__in=athletes)
        .order_by("game_week")
        .values("athlete_id", "game_week", "value", *fields)
    ):
        athlete = athletes[row["athlete_id"]]
        values = {key: _number(row[field]) for key, (field, _) in SUMMED_METRICS.items()}
        values["xcs"] = _number(expected_clean_sheet_chance(
            row["minutes"],
            row["expected_goals_conceded"],
            fixtures.get((athlete.team_id, row["game_week"]), 1),
        ))
        values["price"] = _number((row["value"] or athlete.now_cost or 0) / 10)
        # Weekly ownership is a manager count with no denominator; leave it out
        # rather than mix units with the season-level percentage.
        values["own"] = None
        rows_by_player[row["athlete_id"]].append({"gameweek": row["game_week"], "values": values})

    return {
        "series": [
            {
                "id": athlete_id,
                "name": athletes[athlete_id].web_name,
                "team": athletes[athlete_id].team.short_name if athletes[athlete_id].team else None,
                "points": rows_by_player.get(athlete_id, []),
            }
            for athlete_id in athlete_ids
            if athlete_id in athletes
        ]
    }
