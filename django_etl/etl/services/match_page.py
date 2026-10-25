"""Everything the Match page shows, for one Premier League match (Opta match id).

Finished matches carry the timeline (goals from ``MatchGoal``; cards, subs and
VAR from ``MatchEvent``), Opta momentum, lineups with formation slots, team
stats and every player's match sheet with his FPL points. Upcoming matches
carry what is known before kick-off: odds (when collected), form and the last
meetings. See etl/services/match_details.py for where the data comes from.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db.models import Count, Q

from ..models import (
    Fixture, FixtureHistory, FixtureOdds, GameweekHistory, MatchGoal, PlMatch, Team, TeamSeasonStat,
)

CACHE_TTL = 15 * 60
TEAM_STATS = [
    "expectedGoals", "expectedGoalsOnTarget", "possessionPercentage", "totalScoringAtt", "ontargetScoringAtt",
    "attemptsIbox", "attemptsObox", "attBxLeft", "attBxCentre", "attBxRight", "bigChanceCreated", "touchesInOppBox",
    "accuratePass", "totalPass", "wonCorners", "totalTackle", "interception", "saves", "fkFoulLost", "expectedAssists",
    "attGoalLowLeft", "attGoalLowCentre", "attGoalLowRight", "attGoalHighLeft", "attGoalHighCentre", "attGoalHighRight",
    "attSvLowLeft", "attSvLowCentre", "attSvLowRight", "attSvHighLeft", "attSvHighCentre", "attSvHighRight",
]
POSITIONS = {"Goalkeeper": "GK", "Defender": "DEF", "Midfielder": "MID", "Forward": "FWD", "Substitute": "SUB"}


def _teams() -> dict[str, dict]:
    """Opta team id -> name and short code (FPL's code where the club is in FPL)."""
    teams: dict[str, dict] = {}
    for opta_id, name in TeamSeasonStat.objects.filter(competition_id=8).order_by("season").values_list("opta_team_id", "name"):
        teams[str(opta_id)] = {"name": name, "short": name[:3].upper()}
    for code, name, short in Team.objects.exclude(code=None).values_list("code", "name", "short_name"):
        teams.setdefault(str(code), {"name": name, "short": short})
        teams[str(code)]["short"] = short or teams[str(code)]["short"]
    return teams


def _team(teams: dict, team_id: str) -> dict:
    t = teams.get(str(team_id), {"name": str(team_id), "short": str(team_id)[:3]})
    return {"id": str(team_id), "name": t["name"], "short": t["short"]}


def _form(team_id: str, before, teams: dict, n: int = 5) -> list[dict]:
    rows = PlMatch.objects.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id), home_score__isnull=False)
    if before is not None:  # a postponed match may have no kick-off time yet
        rows = rows.filter(kickoff__lt=before)
    rows = rows.order_by("-kickoff")[:n]
    out = []
    for r in rows:
        home = r.home_team_id == team_id
        gf, ga = (r.home_score, r.away_score) if home else (r.away_score, r.home_score)
        opp = r.away_team_id if home else r.home_team_id
        out.append({"matchId": r.match_id, "opp": _team(teams, opp)["short"], "home": home, "gf": gf, "ga": ga,
                    "res": "W" if gf > ga else "D" if gf == ga else "L", "date": r.kickoff.date().isoformat() if r.kickoff else None})
    return out


def _h2h(match: PlMatch, teams: dict, n: int = 6) -> list[dict]:
    pair = Q(home_team_id=match.home_team_id, away_team_id=match.away_team_id) | Q(home_team_id=match.away_team_id, away_team_id=match.home_team_id)
    return [{"matchId": r.match_id, "date": r.kickoff.date().isoformat() if r.kickoff else None,
             "home": _team(teams, r.home_team_id)["short"], "away": _team(teams, r.away_team_id)["short"],
             "hs": r.home_score, "as": r.away_score}
            for r in (PlMatch.objects.filter(pair, home_score__isnull=False).exclude(pk=match.pk)
                      .filter(**({"kickoff__lt": match.kickoff} if match.kickoff else {})).order_by("-kickoff")[:n])]


def _odds(match: PlMatch) -> dict | None:
    fixture = Fixture.objects.filter(team_h__code=int(match.home_team_id), team_a__code=int(match.away_team_id),
                                     kickoff_time__date=match.kickoff.date() if match.kickoff else None).first()
    if fixture is None:
        return None
    odds = FixtureOdds.objects.filter(fixture__fixture=fixture).first()
    if odds is None or odds.home_odds is None:
        return {"fixtureId": fixture.id}
    implied = [1 / float(o) for o in (odds.home_odds, odds.draw_odds, odds.away_odds) if o]
    total = sum(implied) if len(implied) == 3 else None
    return {
        "fixtureId": fixture.id,
        "home": float(odds.home_odds), "draw": float(odds.draw_odds) if odds.draw_odds else None,
        "away": float(odds.away_odds) if odds.away_odds else None,
        # Bookmaker margin removed so the three chances add up to 100%.
        "chances": [round(p / total * 100, 1) for p in implied] if total else None,
        "updated": odds.last_updated.isoformat() if getattr(odds, "last_updated", None) else None,
    }


def build_payload(match_id: str) -> dict | None:
    key = f"match-page:{match_id}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    match = PlMatch.objects.filter(match_id=str(match_id)).first()
    if match is None:
        return None
    teams = _teams()
    finished = match.home_score is not None
    gameweek = (FixtureHistory.objects.filter(season=match.season, team_h_code=int(match.home_team_id),
                                              team_a_code=int(match.away_team_id)).values_list("gameweek", flat=True).first()
                or match.matchweek)
    lineups = list(match.lineups.values(
        "team_id", "player_id", "name", "shirt", "position", "position_side", "formation_place",
        "formation_row", "formation_col", "starter", "captain", "minute_on", "minute_off"))
    names = {p["player_id"]: p["name"] for p in lineups}
    goals = [{"minute": g.minute, "period": 1 if g.period == "FirstHalf" else 2, "team": g.team_id,
              "scorer": names.get(g.player_id, g.player_id) if g.goal_type != "Own" else f"{names.get(g.player_id, 'Own goal')} (own goal)",
              "assist": names.get(g.assist_player_id) if g.assist_player_id else None, "type": g.goal_type,
              "home": g.home_after, "away": g.away_after}
             for g in MatchGoal.objects.filter(match=match).order_by("order")]
    events = list(match.events.values("minute", "period", "team_id", "kind", "player_name", "other_player_name", "detail"))
    team_stats = {t.team_id: {"formation": t.formation, **{k: t.stats.get(k) for k in TEAM_STATS}} for t in match.team_stats.all()}

    # FPL points for the gameweek; flag teams that played twice that week.
    fpl = {}
    double = set()
    if gameweek:
        fpl = {str(c): p for c, p in GameweekHistory.objects.filter(season=match.season, gameweek=gameweek)
               .values_list("code", "total_points")}
        for code in (match.home_team_id, match.away_team_id):
            n = FixtureHistory.objects.filter(Q(team_h_code=int(code)) | Q(team_a_code=int(code)),
                                              season=match.season, gameweek=gameweek).count()
            if n > 1:
                double.add(code)
    positions = {p["player_id"]: p["position"] for p in lineups}
    players = []
    for ps in match.player_stats.all():
        s = ps.stats
        players.append({
            "id": ps.player_id, "name": names.get(ps.player_id, ps.player_id), "team": ps.team_id,
            "position": POSITIONS.get(positions.get(ps.player_id, ""), ""), "minutes": ps.minutes, "started": ps.started,
            "fpl": fpl.get(ps.player_id), "goals": s.get("goals", 0), "assists": s.get("goal_assist", 0),
            "shots": s.get("total_scoring_att", 0), "boxShots": s.get("attempts_ibox", 0),
            "bigChances": s.get("big_chance_missed", 0) + s.get("big_chance_scored", 0),
            "chances": s.get("total_att_assist", 0), "boxTouches": s.get("touches_in_opp_box", 0),
            "passes": s.get("total_pass", 0), "accuratePasses": s.get("accurate_pass", 0),
            "defence": s.get("total_tackle", 0) + s.get("interception", 0), "saves": s.get("saves", 0),
        })

    payload = {
        "matchId": match.match_id,
        "season": match.season,
        "gameweek": gameweek,
        "kickoff": match.kickoff.isoformat() if match.kickoff else None,
        "status": "finished" if finished else "upcoming",
        "home": _team(teams, match.home_team_id),
        "away": _team(teams, match.away_team_id),
        "score": [match.home_score, match.away_score] if finished else None,
        "goals": goals,
        "events": events,
        "momentum": match.momentum,
        "lineups": lineups,
        "teamStats": team_stats,
        "players": players,
        "fplDouble": sorted(double),
        "detailsAvailable": match.details_synced,
        "playersAvailable": match.players_synced,
        "form": {"home": _form(match.home_team_id, match.kickoff, teams), "away": _form(match.away_team_id, match.kickoff, teams)},
        "h2h": _h2h(match, teams),
        "odds": None if finished else _odds(match),
    }
    cache.set(key, payload, CACHE_TTL if not finished else CACHE_TTL * 8)
    return payload


def match_for_fixture(fixture_id: int) -> str | None:
    """Opta match id for an FPL fixture (current season), to link from FPL screens."""
    fixture = Fixture.objects.select_related("team_h", "team_a").filter(id=fixture_id).first()
    if fixture is None or not fixture.team_h or not fixture.team_a:
        return None
    match = PlMatch.objects.filter(home_team_id=str(fixture.team_h.code), away_team_id=str(fixture.team_a.code)).order_by("-season").first()
    return match.match_id if match else None
