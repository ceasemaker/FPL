"""Games in progress, read live from the Premier League feed.

Scores, goals and lineups are stored by the nightly sync, so a game that has
kicked off since has nothing stored yet. The Matches calendar and the Match
page ask the feed instead: one request per game for the score and minute, two
more for the Match page's scorers, each cached for a minute (an hour once the
game is over). The feed being slow or down leaves a game as it was: every
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


def live_goals(match_id: str, finished: bool = False) -> list[dict]:
    """Goals so far, in the Match page's shape, with scorers named from the live lineups."""
    key = f"match-live-goals:{match_id}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        goals = goals_from_events(_fetch("get_match_events", match_id))
        lineups = _fetch("get_match_lineups", match_id) if goals else {}
    except Exception as exc:
        logger.warning("Live goals for match %s unavailable: %s", match_id, exc)
        cache.set(key, [], LIVE_TTL)
        return []
    names = {}
    for side in ("home_team", "away_team"):
        for p in (lineups.get(side) or {}).get("players") or []:
            names[str(p.get("id"))] = p.get("knownName") or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
    out = [{"minute": g["minute"], "period": 1 if g["period"] == "FirstHalf" else 2, "team": g["team_id"],
            "scorer": (names.get(g["player_id"]) or "Unknown") + (" (own goal)" if g["goal_type"] == "Own" else ""),
            "assist": names.get(g["assist_player_id"]) if g["assist_player_id"] else None, "type": g["goal_type"],
            "home": g["home_after"], "away": g["away_after"]} for g in goals]
    cache.set(key, out, LIVE_TTL * 60 if finished else LIVE_TTL)
    return out
