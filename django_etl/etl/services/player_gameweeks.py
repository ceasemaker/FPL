"""Per-gameweek FPL stat log and same-position percentiles for one player.

Everything here is official FPL data as synced into ``AthleteStat`` (event-live)
and ``ElementSummary.history`` (opponent / venue labels). Percentiles are
computed against players of the same position with at least ``MIN_MINUTES``
season minutes, and the cohort is reported so the number can be read honestly.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Max, Sum

from ..models import Athlete, AthleteStat, ElementSummary, Team

POSITION_LABELS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
MIN_MINUTES = 90
CACHE_TTL = 600

GAMEWEEK_FIELDS = (
    "minutes", "total_points", "goals_scored", "assists", "clean_sheets",
    "goals_conceded", "own_goals", "penalties_saved", "penalties_missed",
    "yellow_cards", "red_cards", "saves", "bonus", "bps", "influence",
    "creativity", "threat", "ict_index", "starts", "expected_goals",
    "expected_assists", "expected_goal_involvements", "expected_goals_conceded",
    "in_dreamteam", "selected", "transfers_in", "transfers_out", "value",
)

# (key, label, higher_is_better, per_90_capable)
PERCENTILE_STATS = (
    ("total_points", "Points", True),
    ("minutes", "Minutes", True),
    ("goals_scored", "Goals", True),
    ("assists", "Assists", True),
    ("expected_goals", "xG", True),
    ("expected_assists", "xA", True),
    ("expected_goal_involvements", "xGI", True),
    ("expected_goals_conceded", "xGC", False),
    ("clean_sheets", "Clean sheets", True),
    ("saves", "Saves", True),
    ("bonus", "Bonus", True),
    ("bps", "BPS", True),
    ("influence", "Influence", True),
    ("creativity", "Creativity", True),
    ("threat", "Threat", True),
    ("ict_index", "ICT", True),
)
PER_90_STATS = ("expected_goals", "expected_assists", "expected_goal_involvements", "expected_goals_conceded")


def _num(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _percentile(sorted_values: list[float], value: float, higher_is_better: bool) -> int:
    """Percentile rank with ties split; 100 = best in cohort."""
    n = len(sorted_values)
    if n == 0:
        return 0
    below = bisect_left(sorted_values, value)
    ties = bisect_right(sorted_values, value) - below
    rank = (below + ties / 2) / n
    if not higher_is_better:
        rank = 1 - rank
    return int(round(rank * 100))


def _season_totals(position: int, through_gw: int) -> dict[int, dict]:
    """Season sums per athlete for the cohort, keyed by athlete id."""
    rows = (
        AthleteStat.objects.filter(
            athlete__element_type=position,
            athlete__removed=False,
            game_week__lte=through_gw,
        )
        .values("athlete_id")
        .annotate(**{key: Sum(key) for key, _, _ in PERCENTILE_STATS})
    )
    return {row["athlete_id"]: row for row in rows}


def _cohort_percentiles(athlete: Athlete, through_gw: int) -> dict:
    cache_key = f"player_gameweeks:cohort:{athlete.element_type}:{through_gw}"
    totals = cache.get(cache_key)
    if totals is None:
        totals = _season_totals(athlete.element_type, through_gw)
        cache.set(cache_key, totals, CACHE_TTL)

    player_totals = totals.get(athlete.id)
    cohort = {aid: t for aid, t in totals.items() if (t["minutes"] or 0) >= MIN_MINUTES}

    def per90(t, key):
        mins = t["minutes"] or 0
        return float(t[key] or 0) * 90 / mins if mins else 0.0

    stats = []
    if player_totals is not None and cohort:
        for key, label, higher in PERCENTILE_STATS:
            values = sorted(float(t[key] or 0) for t in cohort.values())
            stats.append({
                "key": key,
                "label": label,
                "value": _num(player_totals[key]) or 0,
                "percentile": _percentile(values, float(player_totals[key] or 0), higher),
                "higher_is_better": higher,
            })
        for key in PER_90_STATS:
            label = dict((k, l) for k, l, _ in PERCENTILE_STATS)[key] + " / 90"
            higher = key != "expected_goals_conceded"
            values = sorted(per90(t, key) for t in cohort.values())
            stats.append({
                "key": f"{key}_per_90",
                "label": label,
                "value": round(per90(player_totals, key), 2),
                "percentile": _percentile(values, per90(player_totals, key), higher),
                "higher_is_better": higher,
            })

    return {
        "position": POSITION_LABELS.get(athlete.element_type, "UNK"),
        "cohort_size": len(cohort),
        "cohort_min_minutes": MIN_MINUTES,
        "player_in_cohort": bool(player_totals) and (player_totals["minutes"] or 0) >= MIN_MINUTES,
        "stats": stats,
    }


def _opponent_labels(athlete: Athlete) -> dict[int, list[dict]]:
    summary = ElementSummary.objects.filter(athlete=athlete).only("history").first()
    if not summary:
        return {}
    team_short = dict(Team.objects.values_list("id", "short_name"))
    labels: dict[int, list[dict]] = {}
    for row in summary.history or []:
        round_no = row.get("round")
        if not round_no:
            continue
        labels.setdefault(int(round_no), []).append({
            "opponent": team_short.get(row.get("opponent_team")) or "—",
            "was_home": bool(row.get("was_home")),
            "team_h_score": row.get("team_h_score"),
            "team_a_score": row.get("team_a_score"),
        })
    return labels


def build_player_gameweeks(athlete: Athlete) -> dict:
    through_gw = AthleteStat.objects.aggregate(max_gw=Max("game_week"))["max_gw"] or 0
    opponents = _opponent_labels(athlete)

    gameweeks = []
    for stat in AthleteStat.objects.filter(athlete=athlete).order_by("game_week"):
        row = {"game_week": stat.game_week, "fixtures": opponents.get(stat.game_week, [])}
        for field in GAMEWEEK_FIELDS:
            row[field] = _num(getattr(stat, field))
        gameweeks.append(row)

    return {
        "player_id": athlete.id,
        "web_name": athlete.web_name,
        "data_through_gameweek": through_gw,
        "source": "FPL official (event-live + element-summary)",
        "gameweeks": gameweeks,
        "percentiles": _cohort_percentiles(athlete, through_gw),
    }
