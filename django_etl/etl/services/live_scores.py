"""Games in progress, read live from the Premier League feed.

Scores, goals and lineups are stored by the nightly sync, so a game that has
kicked off since has nothing stored yet. The Matches calendar and the Match
page ask the feed instead: one request per game for the score and minute, three
more for the Match page's scorers and team stats, each cached for a minute (an
hour once the game is over). The feed being slow or down leaves a game as it was: every
call has a hard deadline, since a timeout per connection attempt can still
add up to a minute when the host's addresses don't answer.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.core.cache import cache

from .match_goals import goals_from_events

logger = logging.getLogger(__name__)

LIVE_TTL = 60
LIVE_WINDOW = timedelta(hours=18)  # covers a 12:30 kick-off until the 3:30am sync stores the score
NOT_STARTED = {"", "PreMatch", "Postponed", "Abandoned", "Cancelled", "Suspended"}
DEADLINE = 6  # seconds for one feed request, however many addresses it tries
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="live-feed")


def _fetch(method: str, match_id: str):
    """One feed request that gives up after ``DEADLINE`` seconds (raising TimeoutError)."""
    from .pl_stats_client import PLStatsClient

    client = PLStatsClient(timeout=5, delay=0, retries=1)
    return _pool.submit(getattr(client, method), match_id).result(timeout=DEADLINE)


def live_state(match_id: str) -> dict | None:
    """The feed's period, clock and score for one match, cached for a minute (a finished one for an hour)."""
    key = f"match-live:{match_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    try:
        row = _fetch("get_match", match_id)
    except Exception as exc:  # the feed being down must not take the page with it
        logger.warning("Live score for match %s unavailable: %s", match_id, exc)
        row = {}
    home, away = row.get("homeTeam") or {}, row.get("awayTeam") or {}
    period = row.get("period") or ""
    state = {}
    if period not in NOT_STARTED and home.get("score") is not None and away.get("score") is not None:
        state = {"period": period, "clock": str(row.get("clock") or ""), "score": [home["score"], away["score"]]}
    cache.set(key, state, LIVE_TTL * 60 if period == "FullTime" else LIVE_TTL)
    return state or None


def live_detail(match_id: str, finished: bool = False) -> dict:
    """Goals so far (scorers named from the live lineups) and each side's team stats and formation.

    ``{"goals": [...], "teams": {"home": {"formation", "stats"}, "away": {...}}}``. Three requests,
    each on its own: a missing one leaves its part empty rather than losing the rest.
    """
    key = f"match-live-detail:{match_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    def get(method: str):
        try:
            return _fetch(method, match_id)
        except Exception as exc:
            logger.warning("Live %s for match %s unavailable: %s", method, match_id, exc)
            return None

    events, lineups, stats = get("get_match_events"), get("get_match_lineups") or {}, get("get_match_stats") or []
    names = {}
    for side in ("home_team", "away_team"):
        for p in (lineups.get(side) or {}).get("players") or []:
            names[str(p.get("id"))] = p.get("knownName") or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
    goals = [{"minute": g["minute"], "period": 1 if g["period"] == "FirstHalf" else 2, "team": g["team_id"],
              "scorer": (names.get(g["player_id"]) or "Unknown") + (" (own goal)" if g["goal_type"] == "Own" else ""),
              "assist": names.get(g["assist_player_id"]) if g["assist_player_id"] else None, "type": g["goal_type"],
              "home": g["home_after"], "away": g["away_after"]} for g in goals_from_events(events or {})]
    teams = {}
    for entry in stats:
        side = str(entry.get("side", "")).lower()
        if side in ("home", "away"):
            formation = ((lineups.get(f"{side}_team") or {}).get("formation") or {}).get("formation", "")
            teams[side] = {"formation": formation, "stats": entry.get("stats") or {}}
    detail = {"goals": goals, "teams": teams}
    # A failed events request must not be cached as "no goals" for long.
    cache.set(key, detail, LIVE_TTL * 60 if finished and events is not None else LIVE_TTL)
    return detail


def live_fpl_points(gameweek: int, home_code: str, away_code: str) -> list[dict]:
    """FPL points so far for one league match, from FPL's live gameweek scores.

    Stands in until the nightly sync stores the gameweek. Bonus points only
    appear once FPL confirms them. The gameweek's scores are cached for a minute,
    reduced to points per fixture so the whole response is never kept.
    """
    from ..models import Athlete, Fixture

    fixture_id = Fixture.objects.filter(event=gameweek, team_h__code=int(home_code), team_a__code=int(away_code)) \
        .values_list("id", flat=True).first()
    if fixture_id is None:
        return []
    key = f"fpl-live:{gameweek}"
    by_fixture = cache.get(key)
    if by_fixture is None:
        from .fpl_client import FPLClient

        try:
            data = _pool.submit(FPLClient(timeout=5).get_event_live, gameweek).result(timeout=DEADLINE)
        except Exception as exc:  # FPL being down must not take the page with it
            logger.warning("FPL live points for gameweek %s unavailable: %s", gameweek, exc)
            data = {}
        by_fixture = {}
        for element in data.get("elements") or []:
            for part in element.get("explain") or []:
                stats = part.get("stats") or []
                minutes = next((s["value"] for s in stats if s.get("identifier") == "minutes"), 0)
                if minutes:
                    by_fixture.setdefault(part["fixture"], {})[element["id"]] = sum(s.get("points", 0) for s in stats)
        cache.set(key, by_fixture, LIVE_TTL if data else 15)
    points = by_fixture.get(fixture_id) or {}
    return [{"id": str(code), "fplId": pid, "name": name, "team": str(team), "fpl": points[pid]}
            for pid, code, name, team in Athlete.objects.filter(id__in=points).values_list("id", "code", "web_name", "team_code")]
