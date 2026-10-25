"""DEFCON: how reliably each player earns FPL's defensive-contribution points.

FPL (2025/26 on) gives 2 points for reaching a threshold of defensive
actions in a match: 10 clearances, blocks, interceptions and tackles for a
defender; 12 including recoveries for a midfielder or forward. What repeats
is how often a player clears the bar, so the page ranks the hit rate (matches
with the points over matches played), with recent form and per-90 volume.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max

from ..models import Athlete, AthleteStat

THRESHOLD = {"DEF": 10, "MID": 12, "FWD": 12}
POSITIONS = {2: "DEF", 3: "MID", 4: "FWD"}
RECENT = 5


def build_payload() -> dict:
    latest = AthleteStat.objects.aggregate(gw=Max("game_week"))["gw"] or 0
    key = f"defcon:gw{latest}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    athletes = {a.id: a for a in Athlete.objects.filter(removed=False, element_type__in=POSITIONS).select_related("team")}
    rows: dict[int, dict] = defaultdict(lambda: {"matches": 0, "hits": 0, "dc": 0, "minutes": 0, "points": 0, "recent": []})
    for s in AthleteStat.objects.filter(athlete_id__in=athletes).order_by("game_week").values(
            "athlete_id", "game_week", "matches_played", "dc_hits", "defensive_contribution", "minutes", "dc_points"):
        r = rows[s["athlete_id"]]
        r["matches"] += s["matches_played"]
        r["hits"] += s["dc_hits"]
        r["dc"] += s["defensive_contribution"]
        r["minutes"] += s["minutes"]
        r["points"] += s["dc_points"]
        if s["matches_played"]:
            r["recent"].append({"gw": s["game_week"], "hits": s["dc_hits"], "matches": s["matches_played"], "dc": s["defensive_contribution"]})
    players = []
    for a_id, r in rows.items():
        a = athletes[a_id]
        if not r["matches"]:
            continue
        pos = POSITIONS[a.element_type]
        recent = r["recent"][-RECENT:]
        players.append({
            "id": a_id, "name": a.web_name, "team": str(a.team.code) if a.team else "", "teamShort": a.team.short_name if a.team else "",
            "position": pos, "threshold": THRESHOLD[pos], "price": a.now_cost, "ownership": float(a.selected_by_percent or 0),
            "matches": r["matches"], "hits": r["hits"], "hitRate": round(r["hits"] / r["matches"], 3),
            "perMatch": round(r["dc"] / r["matches"], 1), "per90": round(r["dc"] / r["minutes"] * 90, 1) if r["minutes"] else None,
            "minutes": r["minutes"], "points": r["points"],
            "recent": recent, "recentHits": sum(x["hits"] for x in recent), "recentMatches": sum(x["matches"] for x in recent),
        })
    players.sort(key=lambda p: (-p["hitRate"], -p["perMatch"]))
    payload = {"gameweek": latest, "thresholds": THRESHOLD, "recentGameweeks": RECENT, "players": players,
               "available": any(p["hits"] or p["perMatch"] for p in players)}
    cache.set(key, payload, 30 * 60)
    return payload
