"""Everything the Team page shows for one club and season (club = Opta team id).

Every match in every competition with the team stats for both sides, so the
page can total any subset (league only, home only, the last ten) without
another request; the league table built from stored results; league
per-game averages to compare against; and the squad with appearances, goals
and assists in all competitions plus FPL points and price.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max, Q

from ..models import Athlete, MatchGoal, MatchLineupPlayer, MatchTeamStat, PlMatch, Team
from . import set_pieces
from .match_page import _round, _teams, went_to_extra_time

CACHE_TTL = 15 * 60
STATS = [
    "expectedGoals", "totalScoringAtt", "ontargetScoringAtt", "attemptsIbox", "attemptsObox",
    "attBxLeft", "attBxCentre", "attBxRight", "bigChanceCreated", "touchesInOppBox", "possessionPercentage",
    "accuratePass", "totalPass", "wonCorners", "totalTackle", "interception", "saves", "goals",
    "attGoalLowLeft", "attGoalLowCentre", "attGoalLowRight", "attGoalHighLeft", "attGoalHighCentre", "attGoalHighRight",
    "attSvLowLeft", "attSvLowCentre", "attSvLowRight", "attSvHighLeft", "attSvHighCentre", "attSvHighRight",
]
OPTIONAL = {"expectedGoals", "possessionPercentage"}
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def _num(value):
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _stats(stats: dict) -> dict:
    # Opta leaves out zero counts, so a missing key is a zero; but xG is only
    # published for league matches and possession is never zero, so for those
    # a missing key means "not available".
    return {k: (_num(stats.get(k)) if k in OPTIONAL else (_num(stats.get(k)) or 0)) for k in STATS}


def league_table(season: int) -> list[dict]:
    rows: dict[str, dict] = defaultdict(lambda: {"p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
    for m in PlMatch.objects.filter(season=season, competition_id=PlMatch.PREMIER_LEAGUE, home_score__isnull=False):
        for team, gf, ga in ((m.home_team_id, m.home_score, m.away_score), (m.away_team_id, m.away_score, m.home_score)):
            r = rows[team]
            r["p"] += 1; r["gf"] += gf; r["ga"] += ga
            if gf > ga: r["w"] += 1; r["pts"] += 3
            elif gf == ga: r["d"] += 1; r["pts"] += 1
            else: r["l"] += 1
    if not rows:  # before the first match: everyone level
        for m in PlMatch.objects.filter(season=season, competition_id=PlMatch.PREMIER_LEAGUE).values_list("home_team_id", flat=True).distinct():
            rows[m]
    table = sorted(rows.items(), key=lambda kv: (-kv[1]["pts"], -(kv[1]["gf"] - kv[1]["ga"]), -kv[1]["gf"]))
    return [{"team": t, "pos": i + 1, **r, "gd": r["gf"] - r["ga"]} for i, (t, r) in enumerate(table)]


def _league_averages(season: int) -> dict:
    """Per-team, per-game averages over the season's league matches."""
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    # Only the keys the page uses, not each match's whole stat sheet.
    rows = MatchTeamStat.objects.filter(match__season=season, match__competition_id=PlMatch.PREMIER_LEAGUE).values(*[f"stats__{k}" for k in STATS])
    for row in rows:
        stats = {k: row[f"stats__{k}"] for k in STATS if row[f"stats__{k}"] is not None}
        for k, v in _stats(stats).items():
            if v is not None:
                totals[k] += v
                counts[k] += 1
    return {k: round(totals[k] / counts[k], 2) for k in totals if counts[k]}


def _squad(team_code: str, season: int, match_ids: list[int]) -> list[dict]:
    apps: dict[str, dict] = defaultdict(lambda: {"apps": 0, "starts": 0, "minutes": 0, "goals": 0, "assists": 0, "name": ""})
    full = {m: 120 if went_to_extra_time(rt, c) else 90
            for m, rt, c in PlMatch.objects.filter(id__in=match_ids).values_list("id", "result_type", "competition_id")}
    for p in MatchLineupPlayer.objects.filter(match_id__in=match_ids, team_id=team_code).values(
            "match_id", "player_id", "name", "starter", "minute_on", "minute_off"):
        on = 0 if p["starter"] else p["minute_on"]
        if on is None:
            continue
        a = apps[p["player_id"]]
        a["name"] = p["name"]
        a["apps"] += 1
        a["starts"] += int(p["starter"])
        a["minutes"] += max(0, (p["minute_off"] if p["minute_off"] is not None else full.get(p["match_id"], 90)) - on)
    for g in MatchGoal.objects.filter(match_id__in=match_ids, team_id=team_code).exclude(goal_type="Own"):
        apps[g.player_id]["goals"] += 1
        if g.assist_player_id:
            apps[g.assist_player_id]["assists"] += 1

    current = season == PlMatch.objects.aggregate(s=Max("season"))["s"]
    fpl = {}
    if current:
        for a in Athlete.objects.filter(team__code=int(team_code)).exclude(removed=True):
            fpl[str(a.code)] = a
    rows = []
    for pid in set(apps) | set(fpl):
        a, f = apps.get(pid), fpl.get(pid)
        if a is None and f is None:
            continue
        a = a or {"apps": 0, "starts": 0, "minutes": 0, "goals": 0, "assists": 0, "name": ""}
        rows.append({
            "optaId": pid, "fplId": f.id if f else None, "name": (f"{f.first_name} {f.second_name}".strip() if f else a["name"]) or pid,
            "short": f.web_name if f else a["name"].split(" ")[-1], "position": POSITIONS.get(f.element_type, "") if f else "",
            "apps": a["apps"], "starts": a["starts"], "minutes": a["minutes"], "goals": a["goals"], "assists": a["assists"],
            "fplPoints": f.total_points if f else None, "price": f.now_cost / 10 if f and f.now_cost else None,
            "status": f.status if f else None, "news": f.news if f else "",
            "chance": f.chance_of_playing_next_round if f else None,
        })
    return sorted(rows, key=lambda r: (-r["minutes"], r["name"]))


def build_payload(team_code: str, season: int | None = None) -> dict | None:
    team_code = str(team_code)
    seasons = sorted(set(PlMatch.objects.filter(Q(home_team_id=team_code) | Q(away_team_id=team_code),
                                                competition_id=PlMatch.PREMIER_LEAGUE).values_list("season", flat=True)), reverse=True)
    if not seasons:
        return None
    season = season if season in seasons else seasons[0]
    key = f"team-page:{team_code}:{season}:v3"
    cached = cache.get(key)
    if cached:
        return cached

    teams = _teams()
    matches = list(PlMatch.objects.filter(Q(home_team_id=team_code) | Q(away_team_id=team_code), season=season).order_by("kickoff"))
    stats = defaultdict(dict)
    formations = {}
    for s in MatchTeamStat.objects.filter(match__in=matches):
        stats[s.match_id][s.team_id] = _stats(s.stats)
        if s.team_id == team_code:
            formations[s.match_id] = s.formation

    rows = []
    for m in matches:
        home = m.home_team_id == team_code
        opp_id = m.away_team_id if home else m.home_team_id
        opp = teams.get(opp_id) or {"name": (m.away_team_name if home else m.home_team_name) or opp_id,
                                    "short": (m.away_team_short if home else m.home_team_short) or opp_id[:3]}
        finished = m.home_score is not None
        gf, ga = ((m.home_score, m.away_score) if home else (m.away_score, m.home_score)) if finished else (None, None)
        res = None
        if finished:
            res = "W" if gf > ga else "L" if gf < ga else "D"
            if res == "D" and m.home_penalties is not None:
                pf, pa = (m.home_penalties, m.away_penalties) if home else (m.away_penalties, m.home_penalties)
                res = "W" if pf > pa else "L"
        pair = stats.get(m.id, {})
        rows.append({
            "matchId": m.match_id, "kickoff": m.kickoff.isoformat() if m.kickoff else None,
            "competitionId": m.competition_id, "competition": m.competition_name or "Premier League",
            "round": "" if m.competition_id == PlMatch.PREMIER_LEAGUE else _round(m),
            "home": home, "opp": {"id": opp_id, "name": opp["name"], "short": opp["short"]},
            "status": "finished" if finished else "upcoming", "gf": gf, "ga": ga, "res": res,
            "penalties": ([m.home_penalties, m.away_penalties] if home else [m.away_penalties, m.home_penalties]) if m.home_penalties is not None else None,
            "formation": formations.get(m.id, ""),
            "for": pair.get(team_code), "against": pair.get(opp_id),
        })

    table = league_table(season)
    me = next((r for r in table if r["team"] == team_code), None)
    info = teams.get(team_code) or {"name": team_code, "short": team_code[:3]}
    payload = {
        "team": {"id": team_code, "name": info["name"], "short": info["short"]},
        "season": season, "seasons": seasons,
        "table": [{**r, "name": (teams.get(r["team"]) or {}).get("name", r["team"]), "short": (teams.get(r["team"]) or {}).get("short", "")} for r in table],
        "position": me["pos"] if me else None,
        "matches": rows,
        "leagueAverages": _league_averages(season),
        "squad": _squad(team_code, season, [m.id for m in matches if m.home_score is not None]),
        "setPieces": _set_pieces(team_code) if season == seasons[0] else None,
    }
    cache.set(key, payload, CACHE_TTL)
    return payload


def _set_pieces(team_code: str) -> dict | None:
    """This season's set-piece takers, for a club in FPL (none for promoted-away or cup-only sides)."""
    team_id = Team.objects.filter(code=team_code).values_list("id", flat=True).first()
    return set_pieces.takers().get(team_id) if team_id else None


def club_list() -> list[dict]:
    teams = _teams()
    return [{"id": str(code), "name": name, "short": short or teams.get(str(code), {}).get("short", "")}
            for code, name, short in Team.objects.exclude(code=None).order_by("name").values_list("code", "name", "short_name")]
