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
    Athlete, Fixture, FixtureHistory, FixtureOdds, GameweekHistory, MatchGoal, PlMatch, Team, TeamSeasonStat,
)

from .match_goals import premier_league_clubs

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


def _team(teams: dict, team_id: str, name: str = "", short: str = "") -> dict:
    """A club by Opta id; cup and European opponents fall back to the names stored on the match."""
    t = teams.get(str(team_id)) or {"name": name or str(team_id), "short": short or (name or str(team_id))[:3].upper()}
    return {"id": str(team_id), "name": t["name"], "short": t["short"]}


def _side(teams: dict, match: PlMatch, home: bool) -> dict:
    return _team(teams, match.home_team_id if home else match.away_team_id,
                 match.home_team_name if home else match.away_team_name,
                 match.home_team_short if home else match.away_team_short)


EUROPE = {5, 6, 1125}


def _round(match: PlMatch) -> str:
    """A readable round: the feed's own name ("Semi-Finals"), else "Matchday 3" in
    Europe; the feed's bare "Round" says nothing, so it is dropped."""
    name = (match.round_name or "").strip()
    if name and not name.isdigit() and name.lower() != "round":
        return name
    day = name if name.isdigit() else match.matchweek
    return f"Matchday {day}" if day and match.competition_id in EUROPE else ""


def _form(team_id: str, before, teams: dict, n: int = 5) -> list[dict]:
    rows = PlMatch.objects.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id), home_score__isnull=False)
    if before is not None:  # a postponed match may have no kick-off time yet
        rows = rows.filter(kickoff__lt=before)
    rows = rows.order_by("-kickoff")[:n]
    out = []
    for r in rows:
        home = r.home_team_id == team_id
        gf, ga = (r.home_score, r.away_score) if home else (r.away_score, r.home_score)
        res = "W" if gf > ga else "D" if gf == ga else "L"
        if gf == ga and r.home_penalties is not None and r.away_penalties is not None:
            pf, pa = (r.home_penalties, r.away_penalties) if home else (r.away_penalties, r.home_penalties)
            res = "W" if pf > pa else "L"  # a tie settled on penalties
        out.append({"matchId": r.match_id, "opp": _side(teams, r, not home)["short"], "home": home, "gf": gf, "ga": ga,
                    "res": res, "date": r.kickoff.date().isoformat() if r.kickoff else None,
                    "competition": r.competition_name or "Premier League", "league": r.competition_id == PlMatch.PREMIER_LEAGUE})
    return out


def _h2h(match: PlMatch, teams: dict, n: int = 6) -> list[dict]:
    pair = Q(home_team_id=match.home_team_id, away_team_id=match.away_team_id) | Q(home_team_id=match.away_team_id, away_team_id=match.home_team_id)
    return [{"matchId": r.match_id, "date": r.kickoff.date().isoformat() if r.kickoff else None,
             "home": _side(teams, r, True)["short"], "away": _side(teams, r, False)["short"],
             "hs": r.home_score, "as": r.away_score, "competition": r.competition_name or "Premier League"}
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


def went_to_extra_time(result_type: str, competition_id: int) -> bool:
    """The League Cup (before the final) and the Community Shield go straight to penalties."""
    if result_type == "AfterExtraTime":
        return True
    return result_type == "PenaltyShootout" and competition_id not in (2, 38)


def _players_from_lineups(match: PlMatch, lineups: list[dict], goals: list[dict]) -> list[dict]:
    """Minutes, goals and assists for matches without Opta player sheets (cups, Europe).

    Minutes come from who started and when players came on or off; 90 is used
    for the full match, so extra time is not counted.
    """
    full = 120 if any(g["minute"] > 90 for g in goals) or went_to_extra_time(match.result_type, match.competition_id) else 90
    rows = []
    for p in lineups:
        on = 0 if p["starter"] else p["minute_on"]
        if on is None:
            continue
        off = p["minute_off"] if p["minute_off"] is not None else full
        name = p["name"]
        rows.append({
            "id": p["player_id"], "fplId": p.get("fplId"), "name": name, "team": p["team_id"], "position": POSITIONS.get(p["position"], ""),
            "minutes": max(0, off - on), "started": p["starter"], "fpl": None,
            "goals": sum(1 for g in goals if g["scorer"] == name), "assists": sum(1 for g in goals if g["assist"] == name),
            **{k: None for k in ("shots", "boxShots", "bigChances", "chances", "boxTouches", "passes", "accuratePasses", "defence", "saves")},
        })
    return rows


def build_payload(match_id: str) -> dict | None:
    key = f"match-page:{match_id}:v4"
    cached = cache.get(key)
    if cached:
        return cached
    match = PlMatch.objects.filter(match_id=str(match_id)).first()
    if match is None:
        return None
    teams = _teams()
    clubs = premier_league_clubs(match.season)
    finished = match.home_score is not None
    league = match.competition_id == PlMatch.PREMIER_LEAGUE
    # FPL gameweeks and points belong to league matches only.
    gameweek = ((FixtureHistory.objects.filter(season=match.season, team_h_code=int(match.home_team_id),
                                               team_a_code=int(match.away_team_id)).values_list("gameweek", flat=True).first()
                 or match.matchweek) if league else None)
    lineups = list(match.lineups.values(
        "team_id", "player_id", "name", "shirt", "position", "position_side", "formation_place",
        "formation_row", "formation_col", "starter", "captain", "minute_on", "minute_off"))
    names = {p["player_id"]: p["name"] for p in lineups}
    # FPL ids (Athlete.code is the Opta id) so names link to Player pages.
    fpl_ids = {str(c): i for c, i in Athlete.objects.filter(code__in=[int(x) for x in names if x.isdigit()]).values_list("code", "id")}
    for p in lineups:
        p["fplId"] = fpl_ids.get(p["player_id"])
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
            "id": ps.player_id, "fplId": fpl_ids.get(ps.player_id), "name": names.get(ps.player_id, ps.player_id), "team": ps.team_id,
            "position": POSITIONS.get(positions.get(ps.player_id, ""), ""), "minutes": ps.minutes, "started": ps.started,
            "fpl": fpl.get(ps.player_id), "goals": s.get("goals", 0), "assists": s.get("goal_assist", 0),
            "shots": s.get("total_scoring_att", 0), "boxShots": s.get("attempts_ibox", 0),
            "bigChances": s.get("big_chance_missed", 0) + s.get("big_chance_scored", 0),
            "chances": s.get("total_att_assist", 0), "boxTouches": s.get("touches_in_opp_box", 0),
            "passes": s.get("total_pass", 0), "accuratePasses": s.get("accurate_pass", 0),
            "defence": s.get("total_tackle", 0) + s.get("interception", 0), "saves": s.get("saves", 0),
        })

    if not players and not league and finished:
        players = _players_from_lineups(match, lineups, goals)

    payload = {
        "matchId": match.match_id,
        "season": match.season,
        "gameweek": gameweek,
        "kickoff": match.kickoff.isoformat() if match.kickoff else None,
        "status": "finished" if finished else "upcoming",
        "competition": match.competition_name or "Premier League",
        "competitionId": match.competition_id,
        "round": _round(match) if not league else "",
        "penalties": [match.home_penalties, match.away_penalties] if match.home_penalties is not None else None,
        "home": _side(teams, match, True),
        "away": _side(teams, match, False),
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
        # Only Premier League clubs' games are all stored; a cup opponent's form
        # would be its games against PL clubs alone, so it is left out (None).
        "form": {side: _form(team_id, match.kickoff, teams) if league or team_id in clubs else None
                 for side, team_id in (("home", match.home_team_id), ("away", match.away_team_id))},
        "h2h": _h2h(match, teams),
        "odds": None if finished or not league else _odds(match),
    }
    cache.set(key, payload, CACHE_TTL if not finished else CACHE_TTL * 8)
    return payload


def match_for_fixture(fixture_id: int) -> str | None:
    """Opta match id for an FPL fixture (current season), to link from FPL screens."""
    fixture = Fixture.objects.select_related("team_h", "team_a").filter(id=fixture_id).first()
    if fixture is None or not fixture.team_h or not fixture.team_a:
        return None
    match = (PlMatch.objects.filter(competition_id=PlMatch.PREMIER_LEAGUE, home_team_id=str(fixture.team_h.code),
                                    away_team_id=str(fixture.team_a.code)).order_by("-season").first())
    return match.match_id if match else None
