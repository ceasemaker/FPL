"""Transfer planner: a manager's squad as the starting point, plus what planning needs.

- The squad from FPL (picks for the latest gameweek; the week before when a Free
  Hit was played), with each player's purchase and selling price. Purchase
  prices come from the manager's transfer history; players kept since the start
  use their season start price. FPL keeps half of any rise when you sell.
- Bank, free transfers and chips left. Free transfers are worked out from the
  manager's history (FPL doesn't publish the number), so the page lets the
  manager correct them.
- Every club's next six gameweeks: league fixtures with FPL's difficulty, and
  cup and European games played in the run-up to each gameweek.
- The player list for picking replacements.

Price-change flags come from the existing tracker (/api/price-changes/).
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max, Q
from django.utils import timezone

import secrets
from datetime import timedelta

from ..models import (
    Athlete, Fixture, ForecastPrediction, GameweekSummary, MatchLineupPlayer, ModelEvaluation, PlannerSync, PlMatch, Team,
)
from .fpl_client import FPLClient
from .match_goals import COMPETITIONS

HORIZON = 6
MAX_FREE_TRANSFERS = 5
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
CHIPS = {"wildcard": "Wildcard", "freehit": "Free Hit", "bboost": "Bench Boost", "3xc": "Triple Captain"}
SHORT_COMPS = {2: "EFL", 1: "FAC", 5: "UCL", 6: "UEL", 1125: "UECL", 38: "CS", 174: "USC"}


class ManagerNotFound(Exception):
    pass


def selling_price(purchase: int, now: int) -> int:
    """FPL selling price in tenths of £m: you keep half of any rise, rounded down."""
    if now <= purchase:
        return now
    return purchase + (now - purchase) // 2


def free_transfers(history: list[dict], chips: list[dict], next_gw: int) -> int:
    """Free transfers for ``next_gw``, replayed from the season's history.

    One a week from gameweek 2, up to five banked. Transfers beyond the free
    ones are hits and leave zero. A Wildcard or Free Hit week keeps what was
    banked. An estimate: FPL doesn't publish it, and one-off top-ups aren't known.
    """
    made = {h["event"]: h.get("event_transfers", 0) for h in history}
    chip_weeks = {c["event"] for c in chips if c.get("name") in ("wildcard", "freehit")}
    ft = 1  # going into gameweek 2
    for gw in range(2, next_gw):
        if gw in chip_weeks:
            ft = min(MAX_FREE_TRANSFERS, ft + 1)
        else:
            ft = min(MAX_FREE_TRANSFERS, max(0, ft - made.get(gw, 0)) + 1)
    return ft if next_gw > 1 else 0


def chips_left(chips: list[dict], next_gw: int) -> list[dict]:
    """Each chip once per half of the season (gameweeks 1–19 and 20–38)."""
    half = (1, 19) if next_gw <= 19 else (20, 38)
    used = {c["name"] for c in chips if half[0] <= c.get("event", 0) <= half[1]}
    return [{"key": k, "name": v, "available": k not in used} for k, v in CHIPS.items()]


def _gameweeks():
    season = GameweekSummary.objects.aggregate(s=Max("season"))["s"]
    rows = list(GameweekSummary.objects.filter(season=season).order_by("gameweek").values("gameweek", "deadline_time"))
    now = timezone.now()
    upcoming = [r for r in rows if r["deadline_time"] and r["deadline_time"] > now]
    next_gw = upcoming[0]["gameweek"] if upcoming else (rows[-1]["gameweek"] + 1 if rows else 1)
    return next_gw, {r["gameweek"]: r["deadline_time"] for r in rows}


def team_fixtures(next_gw: int, deadlines: dict) -> dict[str, dict[int, dict]]:
    """Club code -> gameweek -> {fixtures: [...], before: [cup/European games before it]}."""
    last = next_gw + HORIZON - 1
    teams = {t.id: t for t in Team.objects.exclude(code=None)}
    out: dict[str, dict[int, dict]] = defaultdict(lambda: defaultdict(lambda: {"fixtures": [], "before": []}))
    for f in Fixture.objects.filter(event__gte=next_gw, event__lte=last).order_by("kickoff_time"):
        h, a = teams.get(f.team_h_id), teams.get(f.team_a_id)
        if not h or not a:
            continue
        out[str(h.code)][f.event]["fixtures"].append({"opp": a.short_name, "oppCode": str(a.code), "home": True, "difficulty": f.team_h_difficulty})
        out[str(a.code)][f.event]["fixtures"].append({"opp": h.short_name, "oppCode": str(h.code), "home": False, "difficulty": f.team_a_difficulty})
    # Cup and European games, filed under the next gameweek they come before.
    start, end = deadlines.get(next_gw - 1), deadlines.get(last)
    if start and end:
        codes = {str(t.code) for t in teams.values()}
        for m in PlMatch.objects.filter(Q(home_team_id__in=codes) | Q(away_team_id__in=codes), kickoff__gt=start, kickoff__lte=end).exclude(competition_id=PlMatch.PREMIER_LEAGUE):
            gw = next((g for g in range(next_gw, last + 1) if deadlines.get(g) and m.kickoff <= deadlines[g]), None)
            if gw is None:
                continue
            for club, home in ((m.home_team_id, True), (m.away_team_id, False)):
                if club in codes:
                    out[club][gw]["before"].append({"competition": SHORT_COMPS.get(m.competition_id, COMPETITIONS.get(m.competition_id, "")),
                                                     "kickoff": m.kickoff.isoformat(), "home": home,
                                                     "opp": (m.away_team_short if home else m.home_team_short) or ""})
    return {club: {gw: dict(v) for gw, v in weeks.items()} for club, weeks in out.items()}


def player_list() -> list[dict]:
    key = "planner:players:v1"
    cached = cache.get(key)
    if cached:
        return cached
    rows = []
    for a in Athlete.objects.filter(removed=False).select_related("team"):
        if not a.team:
            continue
        rows.append({
            "id": a.id, "code": a.code, "name": a.web_name, "fullName": f"{a.first_name} {a.second_name}".strip(),
            "team": str(a.team.code), "teamShort": a.team.short_name, "position": POSITIONS.get(a.element_type, ""),
            "price": a.now_cost, "points": a.total_points, "form": float(a.form or 0), "ppg": float(a.points_per_game or 0),
            "ownership": float(a.selected_by_percent or 0), "minutes": a.minutes, "status": a.status or "a",
            "news": a.news or "", "chance": a.chance_of_playing_next_round,
            "epNext": float(a.ep_next) if a.ep_next is not None else None,
        })
    cache.set(key, rows, 10 * 60)
    return rows


def manager_squad(manager_id: int, client: FPLClient | None = None) -> dict:
    key = f"planner:manager:{manager_id}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    client = client or FPLClient()
    next_gw, _ = _gameweeks()
    current = max(1, next_gw - 1)
    try:
        info = client.get_manager_info(manager_id)
        picks = client.get_manager_picks(manager_id, current)
    except Exception as exc:  # 404 for an unknown manager, network errors
        raise ManagerNotFound(str(exc)) from exc
    if picks.get("active_chip") == "freehit" and current > 1:
        # The Free Hit squad reverts: plan from the squad before it.
        picks = {**client.get_manager_picks(manager_id, current - 1), "entry_history": picks.get("entry_history", {})}
    history = client.get_manager_history(manager_id)
    transfers = client.get_manager_transfers(manager_id)

    bought = {}
    for t in sorted(transfers, key=lambda t: t.get("time") or ""):
        bought[t["element_in"]] = t["element_in_cost"]
    athletes = {a.id: a for a in Athlete.objects.filter(id__in=[p["element"] for p in picks.get("picks", [])]).select_related("team")}
    squad = []
    for p in picks.get("picks", []):
        a = athletes.get(p["element"])
        if not a:
            continue
        purchase = bought.get(a.id, a.now_cost - (a.cost_change_start or 0))
        squad.append({"id": a.id, "slot": p.get("position"), "purchase": purchase, "selling": selling_price(purchase, a.now_cost),
                      "captain": bool(p.get("is_captain")), "vice": bool(p.get("is_vice_captain"))})

    chips = history.get("chips", [])
    entry_history = picks.get("entry_history", {})
    payload = {
        "managerId": manager_id,
        "name": f"{info.get('player_first_name', '')} {info.get('player_last_name', '')}".strip(),
        "teamName": info.get("name", ""),
        "overallRank": info.get("summary_overall_rank"),
        "points": info.get("summary_overall_points"),
        "currentGameweek": current,
        "nextGameweek": next_gw,
        "bank": entry_history.get("bank", 0),
        "teamValue": entry_history.get("value"),
        "freeTransfers": free_transfers(history.get("current", []), chips, next_gw),
        "chips": chips_left(chips, next_gw),
        "squad": squad,
    }
    cache.set(key, payload, 5 * 60)
    return payload


def projections(next_gw: int) -> dict:
    """Forecast points per player and gameweek, with the forecast's published record.

    The AeroFPL points forecast (etl.forecast) where it has the player; FPL's own
    expected points for the next gameweek otherwise, labelled as such.
    """
    key = f"planner:projections:{next_gw}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    last = next_gw + HORIZON - 1
    season = ForecastPrediction.objects.order_by("-season").values_list("season", flat=True).first()
    points: dict[str, dict[str, float]] = defaultdict(dict)
    if season is not None:
        for el, gw, pts in ForecastPrediction.objects.filter(season=season, gameweek__gte=next_gw, gameweek__lte=last).values_list("element", "gameweek", "predicted_points"):
            points[str(el)][str(gw)] = round(float(pts), 2)
    fpl_only = []
    for a_id, ep in Athlete.objects.filter(removed=False, ep_next__isnull=False).values_list("id", "ep_next"):
        if str(a_id) not in points:
            points[str(a_id)][str(next_gw)] = round(float(ep), 2)
            fpl_only.append(a_id)
    record = None
    ev = ModelEvaluation.objects.filter(name="points_forecast").order_by("-created_at").first()
    if ev and ev.summary.get("accuracy"):
        acc = ev.summary["accuracy"]
        record = {"version": ev.version, "playerWeeks": acc.get("player_weeks"), "modelError": acc.get("model_mae"),
                  "formError": acc.get("form_mae"), "seasons": ev.summary.get("test_seasons", [])}
    payload = {"points": dict(points), "fplOnly": fpl_only, "record": record, "covers": [next_gw, last]}
    cache.set(key, payload, 30 * 60)
    return payload


def rotation(next_gw: int, deadlines: dict) -> dict:
    """Per player: starts and minutes in his club's last five games (every
    competition), and how many games his club plays in the next 14 days."""
    key = f"planner:rotation:{next_gw}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    codes = {str(c) for c in Team.objects.exclude(code=None).values_list("code", flat=True)}
    now = timezone.now()
    last5: dict[str, list[int]] = {}
    for club in codes:
        last5[club] = list(PlMatch.objects.filter(Q(home_team_id=club) | Q(away_team_id=club), home_score__isnull=False, details_synced=True)
                           .order_by("-kickoff").values_list("id", flat=True)[:5])
    match_ids = {m for ids in last5.values() for m in ids}
    full = {m: 120 if rt not in ("", "NormalResult") and c not in (2, 38) else 90
            for m, rt, c in PlMatch.objects.filter(id__in=match_ids).values_list("id", "result_type", "competition_id")}
    by_player: dict[str, dict] = defaultdict(lambda: {"starts": 0, "minutes": 0, "games": 0})
    for row in MatchLineupPlayer.objects.filter(match_id__in=match_ids).values("match_id", "team_id", "player_id", "starter", "minute_on", "minute_off"):
        if row["match_id"] not in last5.get(row["team_id"], []):
            continue
        r = by_player[row["player_id"]]
        on = 0 if row["starter"] else row["minute_on"]
        r["starts"] += int(row["starter"])
        if on is not None:
            r["minutes"] += max(0, (row["minute_off"] if row["minute_off"] is not None else full.get(row["match_id"], 90)) - on)
    upcoming = {club: PlMatch.objects.filter(Q(home_team_id=club) | Q(away_team_id=club), kickoff__gte=now, kickoff__lt=now + timedelta(days=14)).count()
                for club in codes}
    out = {}
    for a_id, code, team_code in Athlete.objects.filter(removed=False).values_list("id", "code", "team__code"):
        club = str(team_code) if team_code else ""
        r = by_player.get(str(code))
        out[str(a_id)] = {"starts": r["starts"] if r else 0, "minutes": r["minutes"] if r else 0,
                          "clubGames": len(last5.get(club, [])), "next14": upcoming.get(club, 0)}
    cache.set(key, out, 30 * 60)
    return out


def build_payload(manager_id: int, client: FPLClient | None = None) -> dict:
    squad = manager_squad(manager_id, client)
    next_gw, deadlines = _gameweeks()
    return {
        **squad,
        "gameweeks": [{"gameweek": g, "deadline": deadlines[g].isoformat() if deadlines.get(g) else None}
                      for g in range(next_gw, next_gw + HORIZON)],
        "fixtures": team_fixtures(next_gw, deadlines),
        "players": player_list(),
        "projections": projections(next_gw),
        "rotation": rotation(next_gw, deadlines),
    }


# ------------------------------------------------------------------ mini-leagues

def manager_leagues(manager_id: int, client: FPLClient | None = None) -> list[dict]:
    """The manager's invitational classic leagues (not the big public ones)."""
    client = client or FPLClient()
    try:
        info = client.get_manager_info(manager_id)
    except Exception as exc:
        raise ManagerNotFound(str(exc)) from exc
    # Closest races first: the leagues where the manager ranks highest.
    rows = [{"id": l["id"], "name": l["name"], "rank": l.get("entry_rank")}
            for l in info.get("leagues", {}).get("classic", []) if l.get("league_type") == "x"]
    return sorted(rows, key=lambda r: r["rank"] or 10**9)


MAX_RIVALS = 20


def league_view(league_id: int, manager_id: int, client: FPLClient | None = None) -> dict:
    """Top of a mini-league with each manager's current squad and captain, and
    how the manager's squad differs from theirs."""
    key = f"planner:league:{league_id}:v1"
    cached = cache.get(key)
    client = client or FPLClient()
    if not cached:
        next_gw, _ = _gameweeks()
        current = max(1, next_gw - 1)
        standings = client.get_league_standings(str(league_id))
        entries = standings.get("standings", {}).get("results", [])[:MAX_RIVALS]
        rows = []
        for e in entries:
            try:
                picks = client.get_manager_picks(e["entry"], current)
            except Exception:
                picks = {"picks": []}
            rows.append({"entry": e["entry"], "manager": e.get("player_name", ""), "team": e.get("entry_name", ""),
                         "rank": e.get("rank"), "total": e.get("total"), "gw": e.get("event_total"),
                         "picks": [p["element"] for p in picks.get("picks", [])],
                         "captain": next((p["element"] for p in picks.get("picks", []) if p.get("is_captain")), None)})
        cached = {"league": {"id": league_id, "name": standings.get("league", {}).get("name", "")}, "gameweek": current, "managers": rows}
        cache.set(key, cached, 10 * 60)
    mine = next((m for m in cached["managers"] if m["entry"] == manager_id), None)
    if mine is None:
        mine_picks = [p["id"] for p in manager_squad(manager_id, client)["squad"]]
    else:
        mine_picks = mine["picks"]
    rivals = [m for m in cached["managers"] if m["entry"] != manager_id]
    owned = defaultdict(int)
    captains = defaultdict(int)
    for m in rivals:
        for p in m["picks"]:
            owned[p] += 1
        if m["captain"]:
            captains[m["captain"]] += 1
    n = len(rivals) or 1
    names = {a.id: (a.web_name, a.team.short_name if a.team else "") for a in Athlete.objects.filter(id__in=set(owned) | set(mine_picks) | set(captains)).select_related("team")}
    row = lambda pid, extra: {"id": pid, "name": names.get(pid, ("?", ""))[0], "team": names.get(pid, ("", ""))[1], **extra}
    return {
        **cached,
        "rivals": len(rivals),
        "theyHave": sorted([row(p, {"owners": c, "share": round(c / n * 100)}) for p, c in owned.items() if p not in mine_picks],
                           key=lambda r: -r["owners"])[:12],
        "onlyYou": sorted([row(p, {"owners": owned.get(p, 0), "share": round(owned.get(p, 0) / n * 100)}) for p in mine_picks if owned.get(p, 0) / n < 0.25],
                          key=lambda r: r["owners"]),
        "captains": sorted([row(p, {"owners": c, "share": round(c / n * 100)}) for p, c in captains.items()], key=lambda r: -r["owners"])[:6],
    }


# ------------------------------------------------------------------ sync

SYNC_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alikes (0/o, 1/l/i)
MAX_SYNC_BYTES = 64 * 1024


def new_sync_code() -> str:
    while True:
        code = "".join(secrets.choice(SYNC_ALPHABET) for _ in range(10))
        if not PlannerSync.objects.filter(code=code).exists():
            return code
