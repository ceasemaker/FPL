"""Rate My Team: a squad's projected points against the top 100 managers' squads.

Over the next gameweeks the forecast covers (up to three), each squad's best
legal XI and captain is projected with the AeroFPL points forecast; the rating
is where the manager's squad ranks among the top 100's. Strengths and
weaknesses compare each position's projected points with the top 100's
average, and the weakest links are the starters projected lowest.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Max

from ..models import Athlete, Top100Pick
from .planner import _gameweeks, manager_squad, projections

POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
MAX_WEEKS = 3


def best_xi(ids: list[int], pos: dict[int, str], pts: dict[int, float]) -> tuple[float, list[int], int | None]:
    """Best legal XI (1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD) by projected points, plus its captain."""
    ranked = sorted(ids, key=lambda i: -pts.get(i, 0.0))
    take = lambda p, n: [i for i in ranked if pos.get(i) == p][:n]
    xi = take("GKP", 1) + take("DEF", 3) + take("MID", 2) + take("FWD", 1)
    limits = {"DEF": 5, "MID": 5, "FWD": 3}
    for i in ranked:
        if len(xi) >= 11:
            break
        p = pos.get(i)
        if p == "GKP" or i in xi or p not in limits:
            continue
        if sum(1 for x in xi if pos.get(x) == p) < limits[p]:
            xi.append(i)
    captain = max(xi, key=lambda i: pts.get(i, 0.0)) if xi else None
    total = sum(pts.get(i, 0.0) for i in xi) + (pts.get(captain, 0.0) if captain else 0.0)
    return total, xi, captain


def build_payload(manager_id: int, client=None) -> dict:
    squad = manager_squad(manager_id, client)
    next_gw, _ = _gameweeks()
    proj = projections(next_gw)
    weeks = [g for g in range(next_gw, next_gw + MAX_WEEKS) if any(str(g) in v for v in proj["points"].values())]
    if not weeks:
        return {"available": False, "reason": "No projections for the coming gameweeks yet."}

    def week_pts(gw: int) -> dict[int, float]:
        return {int(a): v[str(gw)] for a, v in proj["points"].items() if str(gw) in v}

    per_week = {gw: week_pts(gw) for gw in weeks}
    mine = [p["id"] for p in squad["squad"]]

    latest = Top100Pick.objects.aggregate(gw=Max("game_week"))["gw"]
    rivals: dict[int, list[int]] = defaultdict(list)
    for manager, athlete in Top100Pick.objects.filter(game_week=latest).values_list("manager_id", "athlete_id"):
        rivals[manager].append(athlete)
    rivals = {m: ids for m, ids in rivals.items() if len(ids) == 15}

    every = set(mine) | {i for ids in rivals.values() for i in ids}
    athletes = {a.id: a for a in Athlete.objects.filter(id__in=every).select_related("team")}
    pos = {i: POSITIONS.get(a.element_type, "") for i, a in athletes.items()}

    def score(ids: list[int]) -> tuple[float, dict[str, float], dict[int, float]]:
        total, by_pos, by_player = 0.0, defaultdict(float), defaultdict(float)
        for gw in weeks:
            pts = per_week[gw]
            t, xi, cap = best_xi(ids, pos, pts)
            total += t
            for i in xi:
                by_pos[pos.get(i, "")] += pts.get(i, 0.0)
                by_player[i] += pts.get(i, 0.0)
        return total, dict(by_pos), dict(by_player)

    my_total, my_pos, my_players = score(mine)
    rival_scores = [score(ids) for ids in rivals.values()]
    totals = sorted(s[0] for s in rival_scores)
    beaten = sum(1 for t in totals if t < my_total)
    avg_pos = {p: round(sum(s[1].get(p, 0.0) for s in rival_scores) / len(rival_scores), 1) for p in ("GKP", "DEF", "MID", "FWD")} if rival_scores else {}

    def player(i: int) -> dict:
        a = athletes.get(i)
        return {"id": i, "name": a.web_name if a else str(i), "team": a.team.short_name if a and a.team else "", "position": pos.get(i, ""),
                "price": a.now_cost if a else None, "projected": round(my_players.get(i, 0.0), 1), "status": a.status if a else "a"}

    starters = sorted((i for i in mine if i in my_players), key=lambda i: my_players[i])
    return {
        "available": True,
        "manager": {"id": manager_id, "name": squad["name"], "teamName": squad["teamName"]},
        "weeks": weeks,
        "projected": round(my_total, 1),
        "top100": {"count": len(totals), "gameweek": latest, "median": round(totals[len(totals) // 2], 1) if totals else None,
                   "best": round(totals[-1], 1) if totals else None, "beaten": beaten,
                   "percentile": round(beaten / len(totals) * 100) if totals else None},
        "positions": [{"position": p, "you": round(my_pos.get(p, 0.0), 1), "top100": avg_pos.get(p)} for p in ("GKP", "DEF", "MID", "FWD")],
        "weakest": [player(i) for i in starters[:3]],
        "bench": [player(i) for i in mine if i not in my_players],
        "flagged": [player(i) for i in mine if athletes.get(i) and athletes[i].status != "a"],
        "record": proj.get("record"),
    }
