"""Year-on-year squad changes: defenders a club lost, and players who "made the leap".

Both ideas come from Sincere FC's videos ("The Iraola Files" and the usage-rate
series), measured here with our own data.

* **Defensive turnover** (FPL data). For each club, the minutes its goalkeepers
  and defenders played last season, and how many of those minutes belonged to
  players who are no longer at the club when the new season starts (sold,
  loaned, released or retired). Membership at the start of a past season is
  the player's club in his first gameweek row up to ``START_WINDOW``; for the
  season in progress it is FPL's current club list, which also holds players
  who have not played yet. Promoted clubs have no Premier League minutes to
  lose, so they are listed separately.
* **Made the leap** (Opta data via the Premier League). For players at the same
  club in consecutive seasons, the change in usage rate, chances created, xG +
  xA and touches in the box (per 90). ``leap_persistence`` checks how much of a
  big rise usually survives into the following season, so a jump can be read
  against how often jumps last.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from django.core.cache import cache
from django.db.models import Max, Sum

from ..models import Athlete, FixtureHistory, GameweekHistory, PlayerSeasonStat, Team, TeamSeasonStat
from .usage import player_usage

CACHE_TTL = 3600
START_WINDOW = 4  # gameweeks: the summer window closes around GW3-4
DEFENSIVE = (1, 2)  # FPL element types: goalkeeper, defender
LEAP_METRICS = ("usage", "created90", "xgi90", "box90")
PERSIST_MIN_MINUTES = 900
PERSIST_TOP_SHARE = 0.2  # "big risers": the top fifth of rises in each season pair


def season_label(season: int) -> str:
    return f"{season}/{(season + 1) % 100:02d}"


def current_season() -> int | None:
    return GameweekHistory.objects.aggregate(s=Max("season"))["s"]


def _team_names() -> dict[int, str]:
    names: dict[int, str] = {}
    for season, team_id, name in TeamSeasonStat.objects.filter(competition_id=8).order_by("season").values_list(
            "season", "opta_team_id", "name"):
        if str(team_id).isdigit():
            names[int(team_id)] = name
    for code, name in Team.objects.exclude(code=None).values_list("code", "name"):
        names[code] = name
    return names


def _start_clubs(season: int) -> dict[int, int]:
    """Player code -> club code at the start of ``season``."""
    if season == current_season():
        return {
            code: team for code, team in Athlete.objects.exclude(team__code=None).values_list("code", "team__code")
            if code is not None
        }
    clubs: dict[int, int] = {}
    rows = (GameweekHistory.objects.filter(season=season, gameweek__lte=START_WINDOW)
            .order_by("code", "gameweek").values_list("code", "team_code"))
    for code, team in rows:
        clubs.setdefault(code, team)
    return clubs


def _clubs(season: int) -> set[int]:
    clubs: set[int] = set()
    for home, away in FixtureHistory.objects.filter(season=season).values_list("team_h_code", "team_a_code"):
        clubs.update((home, away))
    return clubs


def _conceded(season: int) -> dict[int, dict]:
    """Goals conceded and clean sheets per finished match, per club."""
    out: dict[int, dict] = defaultdict(lambda: {"matches": 0, "conceded": 0, "clean_sheets": 0})
    for home, away, hs, as_ in FixtureHistory.objects.filter(season=season, team_h_score__isnull=False).values_list(
            "team_h_code", "team_a_code", "team_h_score", "team_a_score"):
        for team, against in ((home, as_), (away, hs)):
            out[team]["matches"] += 1
            out[team]["conceded"] += against
            out[team]["clean_sheets"] += int(against == 0)
    return out


def _per_match(record: dict | None, key: str) -> float | None:
    if not record or not record["matches"]:
        return None
    return round(record[key] / record["matches"], 3)


def defensive_turnover(season: int) -> list[dict]:
    """One row per club in ``season`` that was also in the league the season before."""
    previous = season - 1
    clubs_now, clubs_before = _clubs(season), _clubs(previous)
    if not clubs_now or not clubs_before:
        return []
    names = _team_names()
    start = _start_clubs(season)

    played = (GameweekHistory.objects.filter(season=previous, position__in=DEFENSIVE, minutes__gt=0)
              .values("code", "team_code").annotate(m=Sum("minutes"), name=Max("web_name"), pos=Max("position")))
    total: dict[int, int] = defaultdict(int)
    leavers: dict[int, list[dict]] = defaultdict(list)
    for row in played:
        club = row["team_code"]
        total[club] += row["m"]
        now = start.get(row["code"])
        if now == club:
            continue
        leavers[club].append({
            "name": row["name"],
            "position": "GKP" if row["pos"] == 1 else "DEF",
            "minutes": row["m"],
            "to": names.get(now, "Another club") if now in clubs_now else "Left the Premier League",
        })

    conceded_before, conceded_now = _conceded(previous), _conceded(season)
    rows = []
    for club in sorted(clubs_now):
        before, now = conceded_before.get(club), conceded_now.get(club)
        base = {
            "code": club,
            "team": names.get(club, str(club)),
            "concededBefore": _per_match(before, "conceded"),
            "concededNow": _per_match(now, "conceded"),
            "cleanSheetsBefore": _per_match(before, "clean_sheets"),
            "cleanSheetsNow": _per_match(now, "clean_sheets"),
            "matchesNow": now["matches"] if now else 0,
        }
        if club not in clubs_before:
            rows.append({**base, "promoted": True, "minutesLost": None, "share": None, "defensiveMinutes": None, "leavers": []})
            continue
        lost = sorted(leavers[club], key=lambda p: -p["minutes"])
        minutes_lost = sum(p["minutes"] for p in lost)
        rows.append({
            **base,
            "promoted": False,
            "defensiveMinutes": total[club],
            "minutesLost": minutes_lost,
            "share": round(minutes_lost / total[club], 3) if total[club] else None,
            "leavers": lost,
        })
    return rows


def _bootstrap_difference(a: list[float], b: list[float], rng, n: int = 4000) -> list[float] | None:
    if len(a) < 3 or len(b) < 3:
        return None
    a_arr, b_arr = np.asarray(a), np.asarray(b)
    draws = [rng.choice(a_arr, len(a_arr)).mean() - rng.choice(b_arr, len(b_arr)).mean() for _ in range(n)]
    return [round(float(np.percentile(draws, 2.5)), 3), round(float(np.percentile(draws, 97.5)), 3)]


def turnover_relationship(seasons: list[int]) -> dict | None:
    """Did clubs that lost the most defensive minutes concede more the next season?

    Uses completed seasons only. Compares the change in goals conceded per
    match (this season minus last) for the quarter of club-seasons that lost
    the largest share of their defensive minutes against everyone else.
    """
    pairs = []
    for season in seasons:
        for row in defensive_turnover(season):
            if row["promoted"] or row["share"] is None or row["concededBefore"] is None or row["concededNow"] is None:
                continue
            pairs.append((row["share"], row["concededNow"] - row["concededBefore"]))
    if len(pairs) < 12:
        return None
    pairs.sort(key=lambda p: -p[0])
    cut = max(3, len(pairs) // 4)
    heavy, rest = pairs[:cut], pairs[cut:]
    change = lambda group: [c for _, c in group]
    rng = np.random.default_rng(7)
    shares, changes = np.array([s for s, _ in pairs]), np.array([c for _, c in pairs])
    return {
        "seasons": [season_label(s) for s in seasons],
        "clubSeasons": len(pairs),
        "heavyCount": len(heavy),
        "heavyMinShare": round(heavy[-1][0], 3),
        "heavyChange": round(float(np.mean(change(heavy))), 3),
        "restChange": round(float(np.mean(change(rest))), 3),
        "difference": round(float(np.mean(change(heavy)) - np.mean(change(rest))), 3),
        "differenceRange": _bootstrap_difference(change(heavy), change(rest), rng),
        "correlation": round(float(np.corrcoef(shares, changes)[0, 1]), 3),
    }


def turnover_payload(season: int) -> dict:
    key = f"squad-turnover:{season}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    current = current_season()
    seasons = sorted(set(GameweekHistory.objects.values_list("season", flat=True).distinct()))
    available = [s for s in seasons if s - 1 in seasons]
    completed = [s for s in available if s != current]
    payload = {
        "season": season,
        "seasonLabel": season_label(season),
        "previousLabel": season_label(season - 1),
        "inProgress": season == current,
        "available": sorted(available, reverse=True),
        "clubs": defensive_turnover(season),
        "relationship": turnover_relationship(completed),
    }
    cache.set(key, payload, CACHE_TTL)
    return payload


def _profile(player: dict) -> dict:
    minutes = player["minutes"] or 0
    per90 = lambda v: None if v is None or not minutes else round(v / minutes * 90, 3)
    xgi = None if player.get("xg") is None or player.get("xa") is None else player["xg"] + player["xa"]
    return {
        "minutes": round(minutes),
        "usage": player["usage"],
        "created90": per90(player["created"]),
        "xgi90": per90(xgi),
        "box90": per90(player.get("box_touches")),
    }


def player_leaps(season: int) -> list[dict]:
    """Players at the same club last season and this, with both seasons' profiles."""
    before = {p["id"]: p for p in player_usage(season - 1) if p["teamKnown"]}
    rows = []
    for p in player_usage(season):
        old = before.get(p["id"])
        if not old or not p["teamKnown"] or old["teamId"] != p["teamId"] or p["position"] == "GKP":
            continue
        rows.append({
            "id": p["id"],
            "athleteId": p["athleteId"],
            "name": p["name"],
            "position": p["position"],
            "team": p["team"],
            "before": _profile(old),
            "now": _profile(p),
        })
    return rows


def leap_persistence(seasons: list[int]) -> dict | None:
    """How much of a big one-season rise is still there the season after?

    For each run of three completed seasons (A, B, C) and players at the same
    club in A and B with ``PERSIST_MIN_MINUTES`` in all three, take the top
    fifth of rises from A to B, then measure the C value against A and B:
    kept = (C - A) / (B - A). Reported per metric as the median kept share and
    the share of risers still above their A level in C.
    """
    usable = [s for s in seasons if s - 1 in seasons and s + 1 in seasons]
    if not usable:
        return None
    profiles = {s: {p["id"]: p for p in player_usage(s)} for s in sorted({x + d for x in usable for d in (-1, 0, 1)})}
    out = {}
    for metric in LEAP_METRICS:
        kept, above, risers = [], [], 0
        for b in usable:
            trio = []
            for pid, pb in profiles[b].items():
                pa, pc = profiles[b - 1].get(pid), profiles[b + 1].get(pid)
                if not pa or not pc or not pa["teamKnown"] or pa["teamId"] != pb["teamId"] or pb["position"] == "GKP":
                    continue
                if min(pa["minutes"] or 0, pb["minutes"] or 0, pc["minutes"] or 0) < PERSIST_MIN_MINUTES:
                    continue
                va, vb, vc = (_profile(x)[metric] for x in (pa, pb, pc))
                if None in (va, vb, vc) or vb <= va:
                    continue
                trio.append((vb - va, va, vb, vc))
            if not trio:
                continue
            trio.sort(key=lambda t: -t[0])
            top = trio[:max(1, round(len(trio) * PERSIST_TOP_SHARE))]
            for rise, va, vb, vc in top:
                kept.append((vc - va) / rise)
                above.append(vc > va)
            risers += len(top)
        if risers:
            out[metric] = {
                "risers": risers,
                "medianKept": round(float(np.median(kept)), 3),
                "stillAbove": round(float(np.mean(above)), 3),
            }
    return {"seasons": [season_label(s) for s in usable], "minMinutes": PERSIST_MIN_MINUTES, "metrics": out} if out else None


def leap_payload(season: int) -> dict:
    key = f"squad-leap:{season}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    current = current_season()
    seasons = sorted(set(PlayerSeasonStat.objects.filter(competition_id=8).values_list("season", flat=True)))
    persistence_key = f"squad-leap-persistence:{','.join(map(str, seasons))}:v1"
    persistence = cache.get(persistence_key)
    if persistence is None:
        persistence = leap_persistence([s for s in seasons if s != current]) or {}
        cache.set(persistence_key, persistence, CACHE_TTL * 24)
    payload = {
        "season": season,
        "seasonLabel": season_label(season),
        "previousLabel": season_label(season - 1),
        "inProgress": season == current,
        "available": sorted([s for s in seasons if s - 1 in seasons], reverse=True),
        "players": player_leaps(season),
        "persistence": persistence or None,
    }
    cache.set(key, payload, CACHE_TTL)
    return payload
