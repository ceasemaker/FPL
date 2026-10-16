"""Hold-up play: the striker who holds the ball up and lays it off.

From Sincere FC's "Why 'Hold-Up Play' Needs To Become a Statistic in
Football". The video's "wall pass" is Opta's **lay-off**: a pass, usually one
touch, played back to a team-mate by a player receiving the ball with his back
to goal. Next to it, aerial duels won (winning the long ball) and fouls won
(being impossible to knock off it) complete the picture.

Opta's SDP sheets leave a stat out when it is zero, so a missing hold-up stat
on a sheet with minutes counts as zero here.
"""
from __future__ import annotations

import numpy as np
from django.core.cache import cache
from django.db.models import Sum

from ..models import GameweekHistory, PlayerSeasonStat
from .pl_stats_client import COMPETITIONS
from .usage import player_usage

CACHE_TTL = 3600
MIN_MINUTES = 90
LINK_MIN_MINUTES = 900
FIELDS = ("layoffs_won", "layoffs_lost", "aerials_won", "aerials_lost", "fouls_won")


def _season_label(season: int) -> str:
    return f"{season}/{(season + 1) % 100:02d}"


def holdup_players(season: int, competition: str = "premier-league") -> list[dict]:
    rows = []
    for p in player_usage(season, competition):
        if p["position"] == "GKP" or not p["minutes"]:
            continue
        row = {
            "id": p["id"],
            "athleteId": p["athleteId"],
            "name": p["name"],
            "position": p["position"],
            "team": p["team"],
            "minutes": round(p["minutes"]),
            "goals": p["goals"] or 0,
            "assists": p["assists"] or 0,
            **{field: p.get(field) or 0 for field in FIELDS},
        }
        rows.append(row)
    return rows


def points_link(seasons: list[int]) -> dict | None:
    """Do forwards who lay the ball off more score more FPL points per 90?

    Pools Premier League forwards with ``LINK_MIN_MINUTES`` in a season, over
    the seasons that have both Opta sheets and FPL history, and correlates
    successful lay-offs per 90 with FPL points per 90 (and with assists per 90).
    """
    pairs = []
    for season in seasons:
        fpl = {
            str(code): (points, minutes)
            for code, points, minutes in GameweekHistory.objects.filter(season=season).values("code")
            .annotate(p=Sum("total_points"), m=Sum("minutes")).values_list("code", "p", "m")
        }
        for row in holdup_players(season):
            if row["position"] != "FWD" or row["minutes"] < LINK_MIN_MINUTES or row["id"] not in fpl:
                continue
            points, minutes = fpl[row["id"]]
            if not minutes:
                continue
            pairs.append((row["layoffs_won"] / row["minutes"] * 90, points / minutes * 90, row["assists"] / row["minutes"] * 90))
    if len(pairs) < 20:
        return None
    layoffs, points, assists = (np.array(column) for column in zip(*pairs))
    return {
        "seasons": [_season_label(s) for s in seasons],
        "players": len(pairs),
        "minMinutes": LINK_MIN_MINUTES,
        "withPoints": round(float(np.corrcoef(layoffs, points)[0, 1]), 3),
        "withAssists": round(float(np.corrcoef(layoffs, assists)[0, 1]), 3),
    }


def build_payload(season: int, competition: str) -> dict:
    key = f"holdup:{competition}:{season}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    available = PlayerSeasonStat.objects.values_list("competition_id", "season").distinct()
    by_id = {v["opta"]: k for k, v in COMPETITIONS.items()}
    pl_seasons = sorted({s for c, s in available if c == COMPETITIONS["premier-league"]["opta"]})
    fpl_seasons = set(GameweekHistory.objects.values_list("season", flat=True).distinct())
    current = max(fpl_seasons) if fpl_seasons else None
    link_key = f"holdup-link:{','.join(map(str, pl_seasons))}:v1"
    link = cache.get(link_key)
    if link is None:
        link = points_link([s for s in pl_seasons if s in fpl_seasons and s != current]) or {}
        cache.set(link_key, link, CACHE_TTL * 24)
    payload = {
        "season": season,
        "seasonLabel": _season_label(season),
        "competition": competition,
        "available": sorted({(by_id.get(c), s) for c, s in available if by_id.get(c)}, key=lambda x: (x[0], -x[1])),
        "players": [p for p in holdup_players(season, competition) if p["minutes"] >= MIN_MINUTES],
        "pointsLink": link or None,
    }
    cache.set(key, payload, CACHE_TTL)
    return payload
