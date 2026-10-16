"""Store Premier League matches and their goals, in order, from the SDP API.

One request per page of a season's matches, then one per finished match not
yet stored (a full season is ~385 requests; a weekly refresh ~10). A match's
goals are only kept when they add up to its final score, so a half-published
match is retried on the next run instead of being stored wrong.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db import transaction

from ..models import MatchGoal, PlMatch
from .pl_stats_client import PREMIER_LEAGUE, PLStatsClient

logger = logging.getLogger(__name__)
LONDON = ZoneInfo("Europe/London")


def _kickoff(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=LONDON)
    except ValueError:
        return None


def _minute(goal: dict) -> int:
    """Match minute with stoppage time folded in (45+3 -> 45, 90+4 -> 90)."""
    try:
        minute = int(str(goal.get("time", "0")).split("+")[0])
    except ValueError:
        minute = 0
    if goal.get("period") == "FirstHalf":
        return max(1, min(minute, 45))
    if goal.get("period") == "SecondHalf":
        return max(46, min(minute, 90))
    return max(1, min(minute, 90))


def goals_from_events(events: dict) -> list[dict]:
    """Goals in the order they were scored, with the score after each."""
    goals = []
    for side in ("homeTeam", "awayTeam"):
        team = events.get(side) or {}
        for goal in team.get("goals") or []:
            goals.append({**goal, "_home": side == "homeTeam", "_team": str(team.get("id", ""))})
    # Timestamps order goals exactly; the minute is the fallback.
    goals.sort(key=lambda g: (g.get("timestamp") or "", _minute(g)))
    home = away = 0
    out = []
    for order, goal in enumerate(goals, start=1):
        if goal["_home"]:
            home += 1
        else:
            away += 1
        out.append({
            "order": order,
            "team_id": goal["_team"],
            "is_home": goal["_home"],
            "minute": _minute(goal),
            "period": goal.get("period") or "",
            "goal_type": goal.get("goalType") or "Goal",
            "player_id": str(goal.get("playerId") or ""),
            "assist_player_id": str(goal.get("assistPlayerId") or ""),
            "home_after": home,
            "away_after": away,
        })
    return out


def sync_season(season: int, client: PLStatsClient | None = None, refresh: bool = False, log=logger.info) -> dict:
    client = client or PLStatsClient()
    stored = skipped = 0
    for row in client.iter_season_matches(PREMIER_LEAGUE, season):
        home, away = row.get("homeTeam") or {}, row.get("awayTeam") or {}
        finished = row.get("period") == "FullTime"
        match, _ = PlMatch.objects.update_or_create(
            match_id=str(row["matchId"]),
            defaults={
                "season": season,
                "matchweek": row.get("matchWeek"),
                "kickoff": _kickoff(row.get("kickoff")),
                "home_team_id": str(home.get("id", "")),
                "away_team_id": str(away.get("id", "")),
                "home_score": home.get("score") if finished else None,
                "away_score": away.get("score") if finished else None,
            },
        )
        if not finished or (match.goals_synced and not refresh):
            continue
        goals = goals_from_events(client.get_match_events(match.match_id))
        home_count = sum(1 for g in goals if g["is_home"])
        if home_count != match.home_score or len(goals) - home_count != match.away_score:
            logger.warning("Match %s: goals %s-%s don't match the score %s-%s; retrying next run",
                           match.match_id, home_count, len(goals) - home_count, match.home_score, match.away_score)
            skipped += 1
            continue
        with transaction.atomic():
            match.goals.all().delete()
            MatchGoal.objects.bulk_create([MatchGoal(match=match, **g) for g in goals])
            match.goals_synced = True
            match.save(update_fields=["goals_synced"])
        stored += 1
    total = PlMatch.objects.filter(season=season, goals_synced=True).count()
    log(f"{season}/{(season + 1) % 100:02d}: stored {stored} matches ({skipped} skipped); {total} complete")
    return {"stored": stored, "skipped": skipped, "complete": total}
