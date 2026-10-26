"""Who takes each club's set pieces: penalties, corners and free kicks.

Counted from what happened on the pitch this season (Opta season stats, league
matches). FPL's own set-piece notes are empty this season, so these are counts,
not official orders. Shown on each Team page and as tags in the Players list.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max

from ..models import Athlete, PlayerSeasonStat, PlMatch

SET_PIECES = {
    "penalties": (["penaltiesTaken"], ["att_pen_goal", "att_pen_target", "att_pen_post", "att_pen_miss"]),
    "corners": (["cornersTakenInclShortCorners", "corner_taken"], []),
    "freeKicks": (["freekickTotal"], ["att_freekick_total", "freekick_cross"]),
}


def _count(stats: dict, single: list[str], summed: list[str]) -> int:
    for k in single:
        if stats.get(k) is not None:
            return int(float(stats[k]))
    return int(sum(float(stats.get(k) or 0) for k in summed))


def takers() -> dict[int, dict[str, list[dict]]]:
    """FPL team id -> {kind: up to three takers, most first}."""
    key = "set-pieces:v1"
    cached = cache.get(key)
    if cached is not None:
        return cached
    season = PlMatch.objects.filter(competition_id=PlMatch.PREMIER_LEAGUE).aggregate(s=Max("season"))["s"]
    by_player: dict[int, dict] = {}
    # Only the set-piece keys from the database, not each player's whole stat sheet.
    keys = sorted({k for single, summed in SET_PIECES.values() for k in single + summed})
    lookups = {f"stats__{k}": k for k in keys}
    for row in PlayerSeasonStat.objects.filter(season=season, competition_id=PlMatch.PREMIER_LEAGUE, athlete__isnull=False).values("athlete_id", *lookups):
        stats = {k: row[f"stats__{k}"] for k in keys if row[f"stats__{k}"] is not None}
        counts = {name: _count(stats, single, summed) for name, (single, summed) in SET_PIECES.items()}
        prev = by_player.get(row["athlete_id"]) or {}
        by_player[row["athlete_id"]] = {k: max(v, prev.get(k, 0)) for k, v in counts.items()}  # SDP and classic rows
    names = dict(Athlete.objects.filter(id__in=by_player, removed=False).values_list("id", "web_name"))
    teams = dict(Athlete.objects.filter(id__in=by_player, removed=False).values_list("id", "team_id"))
    out: dict[int, dict[str, list[dict]]] = defaultdict(lambda: {k: [] for k in SET_PIECES})
    for a_id, counts in by_player.items():
        if not teams.get(a_id):
            continue
        for kind, n in counts.items():
            if n:
                out[teams[a_id]][kind].append({"id": a_id, "name": names[a_id], "count": n})
    result = {t: {k: sorted(v, key=lambda r: -r["count"])[:3] for k, v in kinds.items()} for t, kinds in out.items()}
    cache.set(key, result, 60 * 60)
    return result


def roles() -> dict[int, list[str]]:
    """Player id -> the set pieces he takes most for his club."""
    out: dict[int, list[str]] = defaultdict(list)
    for kinds in takers().values():
        for kind, rows in kinds.items():
            if rows:
                out[rows[0]["id"]].append(kind)
    return dict(out)
