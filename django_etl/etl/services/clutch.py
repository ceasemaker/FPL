"""Clutch goals: how many league points a player's goals were worth.

From Sincere FC's "Football's Most Clutch Players – By the Numbers". A goal's
worth depends on when it goes in and what the score was: a 90th-minute winner
from 1-1 is worth far more than a fourth goal at 3-0.

* **Win probability.** From every stored Premier League match, the share of
  matches that ended in a home win, draw or away win given the minute (5-minute
  buckets) and the goal difference at that moment (capped at ±3). Thin cells
  borrow from neighbouring buckets until they hold ``MIN_CELL`` samples.
* **Expected points** for a team at a moment = 3 × P(win) + P(draw).
* **Points won by a goal** = the scoring team's expected points just after the
  goal minus just before it, at the same minute. Own goals change the score
  but aren't credited to anyone; assists are credited with the goal's value
  separately.

Goals are counted for the club the player scored them for.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from django.core.cache import cache

from ..models import Athlete, MatchGoal, PlayerSeasonStat, PlMatch, TeamSeasonStat
from .usage import POSITIONS

CACHE_TTL = 3600
BUCKET = 5
MAX_DIFF = 3
MIN_CELL = 300  # minute-samples (≈ 60 matches' worth of five-minute spells)
DECISIVE_LATE_MINUTE = 75


def _season_label(season: int) -> str:
    return f"{season}/{(season + 1) % 100:02d}"


def _bucket(minute: int) -> int:
    return min(minute, 90) // BUCKET


def _clip(diff: int) -> int:
    return max(-MAX_DIFF, min(MAX_DIFF, diff))


def _match_goals() -> dict[int, list[tuple]]:
    goals: dict[int, list[tuple]] = defaultdict(list)
    for row in MatchGoal.objects.filter(match__goals_synced=True).order_by("match_id", "order").values_list(
            "match_id", "minute", "is_home"):
        goals[row[0]].append((row[1], row[2]))
    return goals


def win_probability_table() -> dict:
    """P(home win, draw, away win) by minute bucket and home goal difference."""
    key = f"clutch-winprob:{PlMatch.objects.filter(goals_synced=True).count()}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    counts = np.zeros((90 // BUCKET + 1, 2 * MAX_DIFF + 1, 3))
    goals = _match_goals()
    matches = 0
    for match_id, home, away in PlMatch.objects.filter(goals_synced=True).values_list("id", "home_score", "away_score"):
        result = 0 if home > away else 1 if home == away else 2
        events = goals.get(match_id, [])
        diff, index = 0, 0
        for minute in range(0, 91):
            # The state as each minute starts: goals scored before it.
            while index < len(events) and events[index][0] < minute:
                diff += 1 if events[index][1] else -1
                index += 1
            counts[_bucket(minute), _clip(diff) + MAX_DIFF, result] += 1
        matches += 1

    probs = np.zeros_like(counts)
    buckets = counts.shape[0]
    for b in range(buckets):
        for d in range(counts.shape[1]):
            cell = counts[b, d].copy()
            width = 0
            while cell.sum() < MIN_CELL and width < buckets:
                width += 1
                cell = counts[max(0, b - width):b + width + 1, d].sum(axis=0)
            total = cell.sum()
            probs[b, d] = cell / total if total else [1 / 3] * 3
    table = {"probs": probs.tolist(), "matches": matches}
    cache.set(key, table, CACHE_TTL * 24)
    return table


def expected_points(probs, minute: int, home_diff: int, home: bool) -> float:
    p = probs[_bucket(minute)][_clip(home_diff) + MAX_DIFF]
    return 3 * p[0] + p[1] if home else 3 * p[2] + p[1]


def goal_values(season: int, probs) -> list[dict]:
    """Every goal of the season with the points it was worth to the scoring team."""
    out = []
    goals = MatchGoal.objects.filter(match__season=season, match__goals_synced=True).order_by("match_id", "order")
    for g in goals.values("match_id", "team_id", "is_home", "minute", "goal_type", "player_id",
                          "assist_player_id", "home_after", "away_after"):
        after = g["home_after"] - g["away_after"]
        before = after - (1 if g["is_home"] else -1)
        value = expected_points(probs, g["minute"], after, g["is_home"]) - expected_points(probs, g["minute"], before, g["is_home"])
        # A goal can't hurt the team that scores it; a small negative is table noise.
        value = max(0.0, value)
        team_before = before if g["is_home"] else -before
        out.append({**g, "value": value, "levelled_or_led": team_before in (-1, 0)})
    return out


def _names(season: int) -> dict[str, dict]:
    names: dict[str, dict] = {}
    for opta_id, name, position, athlete in (
            PlayerSeasonStat.objects.filter(competition_id=8).order_by("season")
            .values_list("opta_player_id", "name", "position", "athlete_id")):
        names[opta_id] = {"name": name, "position": POSITIONS.get(position, position), "athleteId": athlete}
    for opta_id, name, position, athlete in (
            PlayerSeasonStat.objects.filter(competition_id=8, season=season)
            .values_list("opta_player_id", "name", "position", "athlete_id")):
        names[opta_id] = {"name": name, "position": POSITIONS.get(position, position), "athleteId": athlete}
    for code, web_name, element_type, athlete_id in Athlete.objects.values_list("code", "web_name", "element_type", "id"):
        names.setdefault(str(code), {"name": web_name, "position": {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}.get(element_type, ""), "athleteId": athlete_id})
    return names


def clutch_players(season: int, probs) -> list[dict]:
    teams = {}
    for team_id, name in TeamSeasonStat.objects.filter(competition_id=8).order_by("season").values_list("opta_team_id", "name"):
        teams[str(team_id)] = name
    for team_id, name in TeamSeasonStat.objects.filter(competition_id=8, season=season).values_list("opta_team_id", "name"):
        teams[str(team_id)] = name
    names = _names(season)
    players: dict[tuple, dict] = {}

    def entry(player_id: str, team_id: str) -> dict:
        key = (player_id, team_id)
        if key not in players:
            info = names.get(player_id, {})
            players[key] = {
                "id": player_id, "athleteId": info.get("athleteId"), "name": info.get("name", player_id),
                "position": info.get("position", ""), "team": teams.get(team_id, team_id),
                "goals": 0, "penalties": 0, "pointsWon": 0.0, "pointsWonNoPens": 0.0, "decisive": 0, "lateDecisive": 0,
                "assists": 0, "assistPointsWon": 0.0, "bestGoal": None,
            }
        return players[key]

    for g in goal_values(season, probs):
        if g["goal_type"] == "Own":
            continue
        if g["player_id"]:
            p = entry(g["player_id"], g["team_id"])
            p["goals"] += 1
            p["pointsWon"] += g["value"]
            if g["goal_type"] == "Penalty":
                p["penalties"] += 1
            else:
                p["pointsWonNoPens"] += g["value"]
            if g["levelled_or_led"]:
                p["decisive"] += 1
                if g["minute"] >= DECISIVE_LATE_MINUTE:
                    p["lateDecisive"] += 1
            if p["bestGoal"] is None or g["value"] > p["bestGoal"]["value"]:
                p["bestGoal"] = {"value": round(g["value"], 2), "minute": g["minute"],
                                 "score": f'{g["home_after"]}-{g["away_after"]}'}
        if g["assist_player_id"]:
            a = entry(g["assist_player_id"], g["team_id"])
            a["assists"] += 1
            a["assistPointsWon"] += g["value"]
    rows = list(players.values())
    for p in rows:
        for field in ("pointsWon", "pointsWonNoPens", "assistPointsWon"):
            p[field] = round(p[field], 3)
    return rows


def clutch_persistence(seasons: list[int], probs, min_goals: int = 5) -> dict | None:
    """Is "clutch" a repeatable skill? Year-to-year correlations for the same player.

    For players with ``min_goals`` non-penalty goals in consecutive completed
    seasons: the correlation of points won per goal (the clutch part) next to
    the correlation of goals scored (the plain scoring part).
    """
    by_season = {}
    for season in seasons:
        rows: dict[str, list[float]] = defaultdict(lambda: [0, 0.0])
        for p in clutch_players(season, probs):
            open_play = p["goals"] - p["penalties"]
            rows[p["id"]][0] += open_play
            rows[p["id"]][1] += p["pointsWonNoPens"]
        by_season[season] = rows
    per_goal, goals = [], []
    for season in seasons:
        nxt = by_season.get(season + 1)
        if nxt is None:
            continue
        for pid, (g1, v1) in by_season[season].items():
            if pid in nxt and g1 >= min_goals and nxt[pid][0] >= min_goals:
                g2, v2 = nxt[pid]
                per_goal.append((v1 / g1, v2 / g2))
                goals.append((g1, g2))
    if len(per_goal) < 15:
        return None
    corr = lambda pairs: round(float(np.corrcoef(*zip(*pairs))[0, 1]), 3)
    return {
        "seasons": [_season_label(s) for s in seasons],
        "pairs": len(per_goal),
        "minGoals": min_goals,
        "perGoal": corr(per_goal),
        "goals": corr(goals),
    }


def build_payload(season: int) -> dict:
    synced = PlMatch.objects.filter(goals_synced=True)
    key = f"clutch:{season}:{synced.count()}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    table = win_probability_table()
    seasons = sorted(set(synced.values_list("season", flat=True)))
    current = max(seasons) if seasons else None
    completed = [s for s in seasons if s != current]
    persistence_key = f"clutch-persistence:{','.join(map(str, completed))}:{table['matches']}:v1"
    persistence = cache.get(persistence_key)
    if persistence is None:
        persistence = clutch_persistence(completed, table["probs"]) or {}
        cache.set(persistence_key, persistence, CACHE_TTL * 24)
    late = expected_points(table["probs"], 88, 1, True) - expected_points(table["probs"], 88, 0, True)
    padding = expected_points(table["probs"], 70, 3, True) - expected_points(table["probs"], 70, 2, True)
    payload = {
        "season": season,
        "seasonLabel": _season_label(season),
        "inProgress": season == current,
        "available": sorted(seasons, reverse=True),
        "matches": table["matches"],
        "matchesThisSeason": synced.filter(season=season).count(),
        "examples": {"lateWinner": round(late, 2), "fourthGoal": round(padding, 2)},
        "players": clutch_players(season, table["probs"]) if season in seasons else [],
        "persistence": persistence or None,
    }
    cache.set(key, payload, CACHE_TTL)
    return payload
