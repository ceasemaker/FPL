"""Everything the Player page shows for one FPL player (by FPL element id).

- Who he is in FPL: price, ownership, status, points.
- Every match he played this season in every competition: minutes from the
  lineups, goals and assists, and for league games his FPL points and xG.
- How he compares: per-90 numbers against players in his FPL position with
  450+ league minutes, as percentiles.
- What's next for his club in every competition.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max, Q

from ..models import AthleteStat, Athlete, Fixture, SofasportHeatmap, GameweekHistory, MatchGoal, MatchLineupPlayer, PlayerSeasonStat, PlMatch
from .match_page import _round, _teams, went_to_extra_time
from .sample_size import SMALL_SAMPLE, qualifying_minutes

CACHE_TTL = 15 * 60
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
POSITION_NAMES = {1: "goalkeepers", 2: "defenders", 3: "midfielders", 4: "forwards"}

# Season-stat keys differ between the two Premier League feeds; take the first present.
SEASON_KEYS = {
    "minutes": ["mins_played", "timePlayed"],
    "shots": ["total_scoring_att", "totalScoringAtt", "totalShots"],
    "boxShots": ["attempts_ibox", "attemptsIbox", "shotsInsideBox"],
    "chances": ["total_att_assist", "keyPassesAttemptAssists", "totalAttAssist"],
    "boxTouches": ["touches_in_opp_box", "touchesInOppBox"],
    "carries": ["progressive_carries", "progressiveCarries"],
    "tackles": ["total_tackle", "totalTackles", "totalTackle"],
    "interceptions": ["interception", "interceptions"],
    "recoveries": ["ball_recovery", "recoveries"],
    "saves": ["saves", "savesMade"],
}
# What each position is judged on, in plain words (key, label, decimals).
COMPARE = {
    1: [("saves", "Saves", 1), ("points", "FPL points", 1), ("xgc", "Expected goals conceded", 2)],
    2: [("xgi", "Expected goal involvements (xG + xA)", 2), ("defence", "Tackles + interceptions", 1), ("recoveries", "Ball recoveries", 1),
        ("boxTouches", "Touches in the opposition box", 1), ("points", "FPL points", 1)],
    3: [("xg", "Expected goals (xG)", 2), ("xa", "Expected assists (xA)", 2), ("shots", "Shots", 1), ("chances", "Chances created", 1),
        ("boxTouches", "Touches in the opposition box", 1), ("points", "FPL points", 1)],
    4: [("xg", "Expected goals (xG)", 2), ("xa", "Expected assists (xA)", 2), ("shots", "Shots", 1), ("boxShots", "Shots inside the box", 1),
        ("boxTouches", "Touches in the opposition box", 1), ("points", "FPL points", 1)],
}
LOWER_IS_BETTER = {"xgc"}


def _first(stats: dict, keys: list[str]) -> float:
    for k in keys:
        if k in stats and stats[k] is not None:
            try:
                return float(stats[k])
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _min_minutes() -> int:
    return qualifying_minutes(AthleteStat.objects.aggregate(gw=Max("game_week"))["gw"] or 0)


def _per90_pool(season: int, min_minutes: int) -> dict[int, dict[int, dict]]:
    """position -> player code -> per-90 numbers, for players with enough league minutes."""
    key = f"player-pool:{season}:{min_minutes}:v2"
    cached = cache.get(key)
    if cached:
        return cached
    fpl: dict[int, dict] = defaultdict(lambda: defaultdict(float))
    for code, pos, mins, xg, xa, xgc, pts in GameweekHistory.objects.filter(season=season).values_list(
            "code", "position", "minutes", "expected_goals", "expected_assists", "expected_goals_conceded", "total_points"):
        row = fpl[code]
        row["position"] = pos
        row["minutes"] += mins or 0
        row["xg"] += float(xg or 0); row["xa"] += float(xa or 0); row["xgc"] += float(xgc or 0); row["points"] += pts or 0
    opta = {}
    for pid, stats in PlayerSeasonStat.objects.filter(season=season, competition_id=PlMatch.PREMIER_LEAGUE).values_list("opta_player_id", "stats"):
        opta[str(pid)] = {k: _first(stats, keys) for k, keys in SEASON_KEYS.items()}
    pool: dict[int, dict[int, dict]] = defaultdict(dict)
    for code, row in fpl.items():
        mins = row["minutes"]
        if mins < min_minutes:
            continue
        o = opta.get(str(code), {})
        per = lambda v: v / mins * 90
        values = {"minutes": mins, "xg": per(row["xg"]), "xa": per(row["xa"]), "xgi": per(row["xg"] + row["xa"]), "xgc": per(row["xgc"]),
                  "points": per(row["points"])}
        if o.get("minutes"):
            om = o["minutes"]
            for k in ("shots", "boxShots", "chances", "boxTouches", "carries", "recoveries", "saves"):
                values[k] = o[k] / om * 90
            values["defence"] = (o["tackles"] + o["interceptions"]) / om * 90
        pool[int(row["position"])][code] = values
    pool = {p: dict(v) for p, v in pool.items()}
    cache.set(key, pool, 60 * 60)
    return pool


def _compare(code: int, position: int, season: int) -> dict:
    min_minutes = _min_minutes()
    pool = _per90_pool(season, min_minutes).get(position, {})
    me = pool.get(code)
    rows = []
    for key, label, dp in COMPARE.get(position, []):
        values = [v[key] for v in pool.values() if key in v]
        if not me or key not in me or len(values) < 10:
            continue
        mine = me[key]
        below = sum(1 for v in values if (v > mine if key in LOWER_IS_BETTER else v < mine))
        rows.append({"key": key, "label": label, "value": round(mine, dp), "pct": round(below / (len(values) - 1) * 100) if len(values) > 1 else None,
                     "decimals": dp})
    return {"rows": rows, "poolSize": len(pool), "positionName": POSITION_NAMES.get(position, "players"), "minMinutes": min_minutes,
            "qualified": me is not None, "smallSample": bool(me and me["minutes"] < SMALL_SAMPLE), "smallSampleMinutes": SMALL_SAMPLE}


def build_payload(player_id: int) -> dict | None:
    key = f"player-page:{player_id}:v2"
    cached = cache.get(key)
    if cached:
        return cached
    a = Athlete.objects.select_related("team").filter(id=player_id).first()
    if a is None:
        return None
    season = PlMatch.objects.aggregate(s=Max("season"))["s"]
    code = str(a.code)
    club = str(a.team.code) if a.team and a.team.code else ""
    teams = _teams()

    # Every match he was in the squad for, in every competition.
    lineups = {l["match_id"]: l for l in MatchLineupPlayer.objects.filter(player_id=code, match__season=season).values(
        "match_id", "team_id", "starter", "minute_on", "minute_off", "captain")}
    matches = {m.id: m for m in PlMatch.objects.filter(id__in=lineups)}
    goals = defaultdict(lambda: [0, 0])
    for g in MatchGoal.objects.filter(match_id__in=lineups).filter(Q(player_id=code) | Q(assist_player_id=code)).exclude(goal_type="Own"):
        goals[g.match_id][0] += int(g.player_id == code)
        goals[g.match_id][1] += int(g.assist_player_id == code)
    gw = {}
    for h in GameweekHistory.objects.filter(season=season, code=a.code).values("gameweek", "minutes", "total_points", "bonus",
                                                                            "expected_goals", "expected_assists", "goals_scored", "assists"):
        gw[h["gameweek"]] = h
    fixture_gw = {}
    if club:
        for f in Fixture.objects.select_related("team_h", "team_a").filter(Q(team_h__code=int(club)) | Q(team_a__code=int(club))):
            if f.team_h and f.team_a:
                fixture_gw[(str(f.team_h.code), str(f.team_a.code))] = f.event

    log = []
    for mid, l in lineups.items():
        m = matches[mid]
        on = 0 if l["starter"] else l["minute_on"]
        played = on is not None
        full = 120 if went_to_extra_time(m.result_type, m.competition_id) else 90
        mins = max(0, (l["minute_off"] if l["minute_off"] is not None else full) - on) if played else 0
        home = m.home_team_id == l["team_id"]
        opp_id = m.away_team_id if home else m.home_team_id
        opp = teams.get(opp_id) or {"name": (m.away_team_name if home else m.home_team_name) or opp_id,
                                    "short": (m.away_team_short if home else m.home_team_short) or opp_id[:3]}
        finished = m.home_score is not None
        gf, ga = ((m.home_score, m.away_score) if home else (m.away_score, m.home_score)) if finished else (None, None)
        res = None if not finished else ("W" if gf > ga else "L" if gf < ga else "D")
        if res == "D" and m.home_penalties is not None:
            res = "W" if (m.home_penalties > m.away_penalties) == home else "L"
        league = m.competition_id == PlMatch.PREMIER_LEAGUE
        g = gw.get(fixture_gw.get((m.home_team_id, m.away_team_id))) if league else None
        log.append({
            "matchId": m.match_id, "kickoff": m.kickoff.isoformat() if m.kickoff else None,
            "competitionId": m.competition_id, "competition": m.competition_name or "Premier League",
            "round": "" if league else _round(m), "home": home, "opp": {"id": opp_id, "name": opp["name"], "short": opp["short"]},
            "res": res, "gf": gf, "ga": ga, "started": l["starter"], "minutes": mins, "unused": not played,
            "goals": goals[mid][0], "assists": goals[mid][1], "captain": l["captain"],
            "gameweek": fixture_gw.get((m.home_team_id, m.away_team_id)) if league else None,
            "fpl": g["total_points"] if g else None, "bonus": g["bonus"] if g else None,
            "xg": float(g["expected_goals"]) if g and g["expected_goals"] is not None else None,
            "xa": float(g["expected_assists"]) if g and g["expected_assists"] is not None else None,
        })
    log.sort(key=lambda r: r["kickoff"] or "")

    by_comp: dict[int, dict] = {}
    for r in log:
        c = by_comp.setdefault(r["competitionId"], {"competitionId": r["competitionId"], "competition": r["competition"],
                                                     "apps": 0, "starts": 0, "minutes": 0, "goals": 0, "assists": 0})
        if r["unused"]:
            continue
        c["apps"] += 1; c["starts"] += int(r["started"]); c["minutes"] += r["minutes"]; c["goals"] += r["goals"]; c["assists"] += r["assists"]

    upcoming = []
    if club:
        for m in PlMatch.objects.filter(Q(home_team_id=club) | Q(away_team_id=club), home_score__isnull=True, kickoff__isnull=False).order_by("kickoff")[:6]:
            home = m.home_team_id == club
            opp_id = m.away_team_id if home else m.home_team_id
            opp = teams.get(opp_id) or {"name": (m.away_team_name if home else m.home_team_name) or opp_id,
                                        "short": (m.away_team_short if home else m.home_team_short) or opp_id[:3]}
            upcoming.append({"matchId": m.match_id, "kickoff": m.kickoff.isoformat(), "competitionId": m.competition_id,
                             "competition": m.competition_name or "Premier League", "home": home,
                             "opp": {"id": opp_id, "name": opp["name"], "short": opp["short"]},
                             "gameweek": fixture_gw.get((m.home_team_id, m.away_team_id)) if m.competition_id == PlMatch.PREMIER_LEAGUE else None})
    difficulty = {}
    if club:
        for f in Fixture.objects.select_related("team_h", "team_a").filter(finished=False).filter(Q(team_h__code=int(club)) | Q(team_a__code=int(club))):
            home = f.team_h and str(f.team_h.code) == club
            d = f.team_h_difficulty if home else f.team_a_difficulty
            if d is not None and f.team_h and f.team_a:
                difficulty[f"{f.team_h.code}-{f.team_a.code}"] = d
    for u in upcoming:
        key = f"{club}-{u['opp']['id']}" if u["home"] else f"{u['opp']['id']}-{club}"
        u["difficulty"] = difficulty.get(key) if u["competitionId"] == PlMatch.PREMIER_LEAGUE else None

    position = a.element_type
    payload = {
        "id": a.id, "code": a.code, "name": f"{a.first_name} {a.second_name}".strip(), "short": a.web_name,
        "position": POSITIONS.get(position, ""), "positionId": position,
        "team": {"id": club, "name": a.team.name if a.team else "", "short": a.team.short_name if a.team else ""},
        "price": a.now_cost / 10 if a.now_cost else None, "ownership": float(a.selected_by_percent or 0),
        "status": a.status, "news": a.news or "", "chance": a.chance_of_playing_next_round,
        "fpl": {"points": a.total_points, "form": float(a.form or 0), "ppg": float(a.points_per_game or 0),
                "epNext": float(a.ep_next) if a.ep_next is not None else None, "minutes": a.minutes,
                "transfersInEvent": a.transfers_in_event, "transfersOutEvent": a.transfers_out_event},
        "season": season,
        "byCompetition": sorted(by_comp.values(), key=lambda c: (c["competitionId"] != PlMatch.PREMIER_LEAGUE, -c["minutes"])),
        "log": log,
        "upcoming": upcoming,
        "compare": _compare(a.code, position, season),
        # SofaScore heatmaps collected in earlier seasons' runs (collection is paused).
        "heatmaps": [{"gameweek": gw} for gw in SofasportHeatmap.objects.filter(athlete=a, fixture__fixture__event__isnull=False)
                     .values_list("fixture__fixture__event", flat=True).order_by("-fixture__fixture__event").distinct()[:38]],
    }
    cache.set(key, payload, CACHE_TTL)
    return payload
