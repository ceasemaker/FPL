"""Team news for planning: injuries and bans, set-piece takers, the next deadline.

- Injuries and bans come from FPL's own flags and news text.
- Set-piece takers come from what happened on the pitch this season (Opta
  season stats): who took the penalties, corners and free kicks for each club.
  FPL's own set-piece notes are empty this season, so these are counts, not
  official orders.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.cache import cache
from django.db.models import Max
from django.utils import timezone

from ..models import Athlete, GameweekSummary, PlayerSeasonStat, PlMatch, Team

STATUS = {"d": "Doubtful", "i": "Injured", "s": "Suspended", "u": "Unavailable", "n": "Not in squad"}
POSITIONS = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
SET_PIECES = {
    "penalties": (["penaltiesTaken"], ["att_pen_goal", "att_pen_target", "att_pen_post", "att_pen_miss"]),
    "corners": (["cornersTakenInclShortCorners", "corner_taken"], []),
    "freeKicks": (["freekickTotal"], ["att_freekick_total", "freekick_cross"]),
}


def _count(stats: dict, single: list[str], summed: list[str]) -> int:
    for k in single:
        if stats.get(k) is not None:
            return int(float(stats[k]))
    return int(sum(float(stats.get(k) or 0) for k in summed))


def build_payload() -> dict:
    key = "team-news:v1"
    cached = cache.get(key)
    if cached:
        return cached
    now = timezone.now()
    season = GameweekSummary.objects.aggregate(s=Max("season"))["s"]
    nxt = GameweekSummary.objects.filter(season=season, deadline_time__gt=now).order_by("gameweek").first()
    teams = {t.id: t for t in Team.objects.exclude(code=None)}

    flagged = defaultdict(list)
    # Injured, doubtful and suspended only: "unavailable" mostly means left or loaned out.
    for a in Athlete.objects.filter(removed=False, status__in=("d", "i", "s")).select_related("team").order_by("-news_added"):
        if not a.team_id or a.team_id not in teams:
            continue
        flagged[a.team_id].append({
            "id": a.id, "name": a.web_name, "position": POSITIONS.get(a.element_type, ""), "status": a.status,
            "label": STATUS.get(a.status, "Flagged"), "chance": a.chance_of_playing_next_round, "news": a.news or "",
            "since": a.news_added.isoformat() if a.news_added else None, "ownership": float(a.selected_by_percent or 0),
        })

    stat_season = PlMatch.objects.filter(competition_id=PlMatch.PREMIER_LEAGUE).aggregate(s=Max("season"))["s"]
    by_player: dict[int, dict] = {}
    for athlete_id, stats in PlayerSeasonStat.objects.filter(season=stat_season, competition_id=PlMatch.PREMIER_LEAGUE, athlete__isnull=False).values_list("athlete_id", "stats"):
        counts = {name: _count(stats, single, summed) for name, (single, summed) in SET_PIECES.items()}
        prev = by_player.get(athlete_id)
        by_player[athlete_id] = {k: max(v, (prev or {}).get(k, 0)) for k, v in counts.items()}  # SDP and classic rows
    athletes = {a.id: a for a in Athlete.objects.filter(id__in=by_player).select_related("team")}
    takers = defaultdict(lambda: {k: [] for k in SET_PIECES})
    for a_id, counts in by_player.items():
        a = athletes.get(a_id)
        if not a or not a.team_id:
            continue
        for kind, n in counts.items():
            if n:
                takers[a.team_id][kind].append({"id": a_id, "name": a.web_name, "count": n})
    clubs = []
    for t in sorted(teams.values(), key=lambda t: t.name):
        sp = {k: sorted(v, key=lambda r: -r["count"])[:3] for k, v in takers[t.id].items()}
        clubs.append({"id": str(t.code), "name": t.name, "short": t.short_name, "flagged": flagged.get(t.id, []), "setPieces": sp})

    payload = {
        "deadline": {"gameweek": nxt.gameweek, "time": nxt.deadline_time.isoformat()} if nxt else None,
        "season": stat_season, "clubs": clubs,
        "flaggedCount": sum(len(v) for v in flagged.values()),
    }
    cache.set(key, payload, 10 * 60)
    return payload
