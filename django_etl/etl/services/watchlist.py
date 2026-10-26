"""Watchlist: what a manager needs on the players they're tracking, in one request.

Price and FPL's own price-move signal come from the existing tracker on the
page; this adds status, form, projected points (the AeroFPL forecast where it
has the player, FPL's expected points otherwise), the next five gameweeks of
fixtures with clean-sheet chance and projected goals (fixture model, when
published) and recent starts.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Q

from ..models import Athlete, Fixture
from .fixture_model import projections as fixture_projections
from .planner import _gameweeks, projections, rotation

POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
MAX_PLAYERS = 60
WEEKS = 5


def build_payload(ids: list[int]) -> dict:
    ids = ids[:MAX_PLAYERS]
    next_gw, deadlines = _gameweeks()
    gws = list(range(next_gw, next_gw + WEEKS))
    athletes = {a.id: a for a in Athlete.objects.filter(id__in=ids).select_related("team")}
    proj = projections(next_gw)
    rot = rotation(next_gw, deadlines)
    model = (fixture_projections() or {}).get("fixtures", {})

    clubs = {a.team_id for a in athletes.values() if a.team_id}
    fixtures = defaultdict(lambda: defaultdict(list))
    for f in Fixture.objects.filter(event__in=gws).filter(Q(team_h_id__in=clubs) | Q(team_a_id__in=clubs)).select_related("team_h", "team_a"):
        cell = model.get(str(f.id))
        for team, opp, home in ((f.team_h, f.team_a, True), (f.team_a, f.team_h, False)):
            if team and team.id in clubs and opp:
                fixtures[team.id][f.event].append({
                    "opp": opp.short_name, "home": home, "difficulty": f.team_h_difficulty if home else f.team_a_difficulty,
                    "cleanSheet": cell[("homeCleanSheet" if home else "awayCleanSheet")] if cell else None,
                    "goals": cell[("homeGoals" if home else "awayGoals")] if cell else None,
                })
    players = []
    for i in ids:
        a = athletes.get(i)
        if not a:
            continue
        pts = proj["points"].get(str(i), {})
        players.append({
            "id": a.id, "name": a.web_name, "team": str(a.team.code) if a.team else "", "teamShort": a.team.short_name if a.team else "",
            "position": POSITIONS.get(a.element_type, ""), "price": a.now_cost, "form": float(a.form or 0), "points": a.total_points,
            "ownership": float(a.selected_by_percent or 0), "status": a.status or "a", "news": a.news or "", "chance": a.chance_of_playing_next_round,
            "projected": {str(g): pts.get(str(g)) for g in gws},
            "fixtures": {str(g): fixtures[a.team_id].get(g, []) for g in gws} if a.team_id else {},
            "rotation": rot.get(str(i)),
        })
    return {"gameweeks": gws, "players": players, "fixtureModel": bool(model)}
