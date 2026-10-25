"""Store Premier League matches and their goals, in order, from the SDP API.

One request per page of a season's matches, then one per finished match not
yet stored (a full season is ~385 requests; a weekly refresh ~10). A match's
goals are only kept when they add up to its final score. The events endpoint
still lists goals VAR later cancelled (about one match in thirty in 2024/25),
so when it doesn't add up the raw Opta feed, which leaves them out, is used
instead; a match that still doesn't add up is retried on the next run.
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
    if goal.get("period") in ("ExtraFirstHalf", "ExtraSecondHalf", "ExtraTime"):
        return max(91, min(minute, 120))
    return max(1, min(minute, 120))


def goals_from_events(events: dict) -> list[dict]:
    """Goals in the order they were scored, with the score after each."""
    goals = []
    for side in ("homeTeam", "awayTeam"):
        team = events.get(side) or {}
        for goal in team.get("goals") or []:
            if "shoot" in str(goal.get("period", "")).lower() or "penalt" in str(goal.get("period", "")).lower():
                continue  # shoot-out kicks are not goals in the score
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


OPTA_TYPES = {"G": "Goal", "PG": "Penalty", "OG": "Own"}


def goals_from_feed(feed: dict, home_team_id: str, away_team_id: str) -> list[dict]:
    """Goals from the raw Opta feed; the side is read from the score change."""
    raw = sorted((feed.get("liveData") or {}).get("goal") or [], key=lambda g: (g.get("timestamp") or "", g.get("timeMin") or 0))
    out, home, away = [], 0, 0
    for order, goal in enumerate(raw, start=1):
        is_home = int(goal.get("homeScore", home)) > home
        home, away = int(goal.get("homeScore", home)), int(goal.get("awayScore", away))
        period = {1: "FirstHalf", 2: "SecondHalf"}.get(goal.get("periodId"), "")
        out.append({
            "order": order,
            "team_id": home_team_id if is_home else away_team_id,
            "is_home": is_home,
            "minute": _minute({"time": goal.get("timeMin", 0), "period": period}),
            "period": period,
            "goal_type": OPTA_TYPES.get(goal.get("type"), "Goal"),
            "player_id": str(goal.get("opScorerId") or ""),
            "assist_player_id": str(goal.get("opAssistPlayerId") or ""),
            "home_after": home,
            "away_after": away,
        })
    return out


def _adds_up(goals: list[dict], match: PlMatch) -> bool:
    home = sum(1 for g in goals if g["is_home"])
    return home == match.home_score and len(goals) - home == match.away_score


# Opta competition ids for everything a Premier League club can play.
COMPETITIONS = {
    8: "Premier League", 2: "League Cup", 1: "FA Cup", 5: "Champions League", 6: "Europa League",
    1125: "Conference League", 38: "Community Shield", 174: "UEFA Super Cup",
}
CUP_COMPETITIONS = [c for c in COMPETITIONS if c != PREMIER_LEAGUE]


def premier_league_clubs(season: int) -> set[str]:
    """Opta ids of the season's Premier League clubs (to keep only their cup ties)."""
    clubs = set(PlMatch.objects.filter(season=season, competition_id=PREMIER_LEAGUE)
                .values_list("home_team_id", flat=True))
    return {c for c in clubs if c}


def _penalties(row: dict, side: str):
    """Shoot-out score ("homePenaltyScore") for ties settled on penalties."""
    value = row.get(f"{side}PenaltyScore")
    return int(value) if isinstance(value, (int, float)) else None


def sync_season(season: int, client: PLStatsClient | None = None, refresh: bool = False, log=logger.info,
                competition: int = PREMIER_LEAGUE) -> dict:
    """Store a competition's matches and goals for one season.

    For cups and European competitions only matches involving a Premier League
    club are kept (sync the league first, so its clubs are known).
    """
    client = client or PLStatsClient()
    stored = skipped = kept = 0
    clubs = premier_league_clubs(season) if competition != PREMIER_LEAGUE else None
    if clubs is not None and not clubs:
        log(f"{season}: no Premier League clubs stored yet; sync the league first")
        return {"stored": 0, "skipped": 0, "complete": 0}
    for row in client.iter_season_matches(competition, season):
        home, away = row.get("homeTeam") or {}, row.get("awayTeam") or {}
        home_id, away_id = str(home.get("id", "")), str(away.get("id", ""))
        if clubs is not None and home_id not in clubs and away_id not in clubs:
            continue
        kept += 1
        finished = row.get("period") == "FullTime"
        match, _ = PlMatch.objects.update_or_create(
            match_id=str(row["matchId"]),
            defaults={
                "season": season,
                "competition_id": competition,
                "competition_name": row.get("competition") or COMPETITIONS.get(competition, ""),
                "round_name": str(row.get("round") or row.get("matchWeek") or ""),
                "matchweek": row.get("matchWeek"),
                "kickoff": _kickoff(row.get("kickoff")),
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_team_name": home.get("name") or "",
                "away_team_name": away.get("name") or "",
                "home_team_short": home.get("abbr") or "",
                "away_team_short": away.get("abbr") or "",
                "result_type": row.get("resultType") or "",
                "home_score": home.get("score") if finished else None,
                "away_score": away.get("score") if finished else None,
                "home_penalties": _penalties(row, "home") if finished else None,
                "away_penalties": _penalties(row, "away") if finished else None,
            },
        )
        if not finished or (match.goals_synced and not refresh):
            continue
        goals = goals_from_events(client.get_match_events(match.match_id))
        if not _adds_up(goals, match) and competition == PREMIER_LEAGUE:
            goals = goals_from_feed(client.get_match_feed(match.match_id), match.home_team_id, match.away_team_id)
        if not _adds_up(goals, match):
            logger.warning("Match %s: goals don't match the score %s-%s; retrying next run",
                           match.match_id, match.home_score, match.away_score)
            skipped += 1
            continue
        with transaction.atomic():
            match.goals.all().delete()
            MatchGoal.objects.bulk_create([MatchGoal(match=match, **g) for g in goals])
            match.goals_synced = True
            match.save(update_fields=["goals_synced"])
        stored += 1
    total = PlMatch.objects.filter(season=season, competition_id=competition, goals_synced=True).count()
    name = COMPETITIONS.get(competition, competition)
    log(f"{season}/{(season + 1) % 100:02d} {name}: stored {stored} matches ({skipped} skipped); {total} complete"
        + (f"; {kept} involve Premier League clubs" if clubs is not None else ""))
    return {"stored": stored, "skipped": skipped, "complete": total}
