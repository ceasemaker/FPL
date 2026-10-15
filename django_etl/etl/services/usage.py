"""Usage rate: how much of his team's ball a player uses, and what he makes of it.

Adapted from basketball's usage rate (Hollinger), following the football
version popularised by the Sincere FC video series:

* A **possession-ending action** (PEA) is a shot, or losing the ball:
  an incomplete pass or cross, a failed take-on, being tackled or
  dispossessed, or a miscontrol. Opta's "possession lost" counts the losses
  (within ~4% of the sum of its parts), so PEA = possession lost + shots.
* **Usage rate** is the share of his team's PEAs a player accounts for while
  on the pitch, with team totals taken from the club he played for that season:

      usage = 100 * PEA_i * (team minutes / 11) / (minutes_i * team PEA)

  (basketball's USG% with 11 players instead of 5).
* **Creation** is chances created (Opta key passes: passes that lead directly
  to a shot). The videos use FBref's "shot-creating actions", which also count
  take-ons, fouls won and shots leading to shots; that stat isn't available
  here, so charts label the axis "chances created".
* **Possession-adjusted** values rescale per-90 numbers to a team with 50% of
  the ball (Premier League only, where club possession is published).
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache

from django.db.models import Sum

from ..models import GameweekHistory, PlayerSeasonStat, TeamSeasonStat
from .pl_stats_client import COMPETITIONS

CACHE_TTL = 3600
MIN_MINUTES = 90

# Field -> stat names per source (sdp first; classic used where sdp is absent).
SDP = {
    "minutes": "timePlayed",
    "lost": "totalLossesOfPossession",
    "shots": "totalShots",
    "created": "keyPassesAttemptAssists",
    "goals": "goals",
    "assists": "goalAssists",
    "xg": "expectedGoals",
    "xa": "expectedAssists",
    "dribbles_won": "successfulDribbles",
    "dribbles_lost": "unsuccessfulDribbles",
    "tackled": "timesTackled",
    "miscontrols": "overruns",
    "touches": "touches",
    "box_touches": "totalTouchesInOppositionBox",
}
CLASSIC = {
    "minutes": "mins_played",
    "lost": "poss_lost_all",
    "shots": "total_scoring_att",
    "created": "total_att_assist",
    "goals": "goals",
    "assists": "goal_assist",
    "dribbles_won": "won_contest",
    "tackled": "dispossessed",
    "miscontrols": "unsuccessful_touch",
    "touches": "touches",
    "box_touches": "touches_in_opp_box",
}
POSITIONS = {"Goalkeeper": "GKP", "Defender": "DEF", "Midfielder": "MID", "Forward": "FWD"}


def _number(stats: dict, key: str | None) -> float | None:
    if key is None or stats.get(key) in (None, ""):
        return None
    try:
        return float(stats[key])
    except (TypeError, ValueError):
        return None


def _row(stats: dict, names: dict) -> dict:
    row = {field: _number(stats, key) for field, key in names.items()}
    if names is CLASSIC:
        total, contest = _number(stats, "total_contest"), row.get("dribbles_won")
        row["dribbles_lost"] = None if total is None or contest is None else total - contest
        row["xg"] = row["xa"] = None
    return row


def player_usage(season: int, competition: str = "premier-league") -> list[dict]:
    """Per-player usage for one season and competition (players with any minutes)."""
    comp = COMPETITIONS[competition]
    rows = PlayerSeasonStat.objects.filter(competition_id=comp["opta"], season=season)
    # Fallback club for players missing from the season's squad lists (January
    # departures, loans): the club FPL had him at for most of his minutes that
    # season. FPL's club code is the Opta team id.
    fpl_club: dict[str, str] = {}
    team_names: dict[str, str] = {}
    if competition == "premier-league":
        minutes = (
            GameweekHistory.objects.filter(season=season, minutes__gt=0)
            .values("code", "team_code").annotate(m=Sum("minutes")).order_by("code", "-m")
        )
        for row in minutes:
            fpl_club.setdefault(str(row["code"]), str(row["team_code"]))
        team_names = {str(t): n for t, n in TeamSeasonStat.objects.filter(
            competition_id=comp["opta"], season=season).values_list("opta_team_id", "name")}
    by_player: dict[str, dict] = {}
    # Prefer the SDP sheet (it has xG/xA); fall back to classic.
    for record in sorted(rows, key=lambda r: r.source != PlayerSeasonStat.SOURCE_SDP):
        if record.opta_player_id in by_player:
            continue
        names = SDP if record.source == PlayerSeasonStat.SOURCE_SDP else CLASSIC
        stat = _row(record.stats, names)
        if not stat.get("minutes"):
            continue
        team_id = record.season_team_id or fpl_club.get(record.opta_player_id) or None
        by_player[record.opta_player_id] = {
            "id": record.opta_player_id,
            "athleteId": record.athlete_id,
            "name": record.name,
            "position": POSITIONS.get(record.position, record.position),
            "teamId": team_id,
            "team": record.season_team_name or team_names.get(team_id or "", "") or record.current_team_name,
            "teamKnown": bool(team_id),
            **stat,
        }

    players = list(by_player.values())
    for p in players:
        p["pea"] = None if p["lost"] is None or p["shots"] is None else p["lost"] + p["shots"]

    # Team totals over every player of the club that season.
    totals: dict[str, dict[str, float]] = defaultdict(lambda: {"pea": 0.0, "minutes": 0.0})
    for p in players:
        if p["teamId"] and p["pea"] is not None:
            totals[p["teamId"]]["pea"] += p["pea"]
            totals[p["teamId"]]["minutes"] += p["minutes"]

    possession = {}
    if competition == "premier-league":
        for team in TeamSeasonStat.objects.filter(competition_id=comp["opta"], season=season):
            value = _number(team.stats, "possessionPercentage")
            if value:
                possession[str(team.opta_team_id)] = value

    for p in players:
        team = totals.get(p["teamId"]) if p["teamId"] else None
        if team and team["pea"] and p["pea"] is not None and p["minutes"]:
            p["usage"] = round(100 * p["pea"] * (team["minutes"] / 11) / (p["minutes"] * team["pea"]), 2)
        else:
            p["usage"] = None
        p["teamPossession"] = possession.get(p["teamId"]) if p["teamId"] else None
    return players


def build_payload(season: int, competition: str) -> dict:
    key = f"usage:{competition}:{season}:v1"
    cached = cache.get(key)
    if cached:
        return cached
    players = [p for p in player_usage(season, competition) if p["minutes"] >= MIN_MINUTES]
    available = (
        PlayerSeasonStat.objects.values_list("competition_id", "season").distinct().order_by("-season")
    )
    by_id = {v["opta"]: k for k, v in COMPETITIONS.items()}
    payload = {
        "season": season,
        "seasonLabel": f"{season}/{(season + 1) % 100:02d}",
        "competition": competition,
        "available": sorted({(by_id.get(c), s) for c, s in available if by_id.get(c)}, key=lambda x: (x[0], -x[1])),
        "possessionAvailable": any(p["teamPossession"] for p in players),
        "players": players,
    }
    cache.set(key, payload, CACHE_TTL)
    return payload
