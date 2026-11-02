"""Two full FPL squads for the homepage pitch: the Top 100 managers' team and the team of the season.

Both follow FPL's squad shape (2 goalkeepers, 5 defenders, 5 midfielders,
3 forwards) and a legal starting formation (1 goalkeeper, at least 3
defenders, 2 midfielders and 1 forward), but not the budget or the
three-per-club limit: the point is who the players are, whatever they cost.

- Top 100: the most-owned players in each position among the top 100
  managers' latest squads. The XI is whoever they start most, the captain
  whoever they captain most. A manager on Free Hit is counted with their
  squad from the gameweek before, since the Free Hit squad isn't their team.
  Only the latest sync's managers count: a gameweek synced more than once
  keeps the rows of managers who have since dropped out of the top 100.
- Season: the most FPL points so far in each position; the XI is the
  highest-scoring legal formation.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Max

from ..models import Athlete, Top100Manager, Top100Pick

CACHE_KEY = "home-squads"
CACHE_TTL = 30 * 60
MANAGERS = 100
SYNC_WINDOW = timedelta(hours=2)  # one sync of 100 managers takes minutes; older rows are from earlier syncs
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
SQUAD = {1: 2, 2: 5, 3: 5, 4: 3}
MIN_XI = {2: 3, 3: 2, 4: 1}  # plus one goalkeeper; ten outfield players


def pick_xi(squad: list[dict], score) -> tuple[list[int], list[int]]:
    """The 11 with the highest ``score`` in a legal formation, and the bench in FPL order (goalkeeper first)."""
    by_pos = {t: sorted((p for p in squad if p["type"] == t), key=score, reverse=True) for t in SQUAD}
    xi = [by_pos[1][0]] + [p for t, n in MIN_XI.items() for p in by_pos[t][:n]]
    rest = sorted((p for t in MIN_XI for p in by_pos[t][MIN_XI[t]:]), key=score, reverse=True)
    xi += rest[:10 - sum(MIN_XI.values())]
    bench = by_pos[1][1:] + rest[10 - sum(MIN_XI.values()):]
    return [p["id"] for p in xi], [p["id"] for p in bench]


def _player(a: Athlete, **extra) -> dict:
    return {"id": a.id, "name": a.web_name, "team": str(a.team_code or (a.team.code if a.team else "")), "teamShort": a.team.short_name if a.team else "",
            "position": POSITIONS[a.element_type], "type": a.element_type, "points": a.total_points, **extra}


def _ordered(players: list[dict]) -> list[dict]:
    return sorted(players, key=lambda p: p["type"])


def season_squad() -> dict | None:
    picked = []
    for t, n in SQUAD.items():
        picked += [_player(a) for a in Athlete.objects.select_related("team").filter(element_type=t).order_by("-total_points", "-form", "id")[:n]]
    if len(picked) < sum(SQUAD.values()):
        return None
    xi, bench = pick_xi(picked, lambda p: p["points"])
    best = max((p for p in picked if p["id"] in xi), key=lambda p: p["points"])
    second = max((p for p in picked if p["id"] in xi and p["id"] != best["id"]), key=lambda p: p["points"])
    return {"players": _ordered(picked), "xi": xi, "bench": bench, "captain": best["id"], "vice": second["id"],
            "points": sum(p["points"] for p in picked if p["id"] in xi)}


def top100_squad() -> dict | None:
    gw = Top100Manager.objects.order_by("-game_week").values_list("game_week", flat=True).first()
    if gw is None:
        return None
    rows = Top100Manager.objects.filter(game_week=gw)
    synced = rows.aggregate(last=Max("updated_at"))["last"]
    managers = list(rows.filter(updated_at__gte=synced - SYNC_WINDOW).order_by("rank").values("id", "entry_id", "active_chip")[:MANAGERS])
    on_free_hit = [m["entry_id"] for m in managers if (m["active_chip"] or "").lower() == "freehit"]
    previous = list(Top100Manager.objects.filter(game_week=gw - 1, entry_id__in=on_free_hit).values_list("id", flat=True))
    sources = [m["id"] for m in managers if m["entry_id"] not in on_free_hit] + previous

    owned, started, captained = Counter(), Counter(), Counter()
    for athlete, position, captain in Top100Pick.objects.filter(manager_id__in=sources).values_list("athlete_id", "position", "is_captain"):
        owned[athlete] += 1
        started[athlete] += position <= 11
        captained[athlete] += captain
    athletes = {a.id: a for a in Athlete.objects.select_related("team").filter(id__in=owned, element_type__in=SQUAD)}
    count = len(sources)

    picked = []
    for t, n in SQUAD.items():
        ids = sorted((i for i, a in athletes.items() if a.element_type == t), key=lambda i: (owned[i], started[i], athletes[i].total_points), reverse=True)
        picked += [_player(athletes[i], owned=round(owned[i] / count * 100), started=round(started[i] / count * 100), captained=captained[i])
                   for i in ids[:n]]
    if len(picked) < sum(SQUAD.values()):
        return None
    xi, bench = pick_xi(picked, lambda p: (p["started"], p["owned"]))
    in_xi = sorted((p for p in picked if p["id"] in xi), key=lambda p: p["captained"], reverse=True)
    return {"players": _ordered(picked), "xi": xi, "bench": bench, "captain": in_xi[0]["id"], "vice": in_xi[1]["id"],
            "gameweek": gw, "managers": count, "freeHit": len(previous)}


def build_payload() -> dict:
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached
    payload = {"top100": top100_squad(), "season": season_squad()}
    cache.set(CACHE_KEY, payload, CACHE_TTL)
    return payload
