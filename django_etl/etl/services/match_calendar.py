"""Every match the Premier League clubs play, in every competition, for the Matches calendar.

One window of days: the league, the domestic cups and Europe side by side, so
congested runs (a Thursday in Europe before a Sunday kick-off) show at a glance.
League matches carry their FPL gameweek and, when collected, the match odds.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from ..models import Fixture, FixtureOdds, PlMatch, Team
from .match_page import _round

CACHE_TTL = 10 * 60
MAX_DAYS = 120


def _clubs() -> list[dict]:
    return [{"id": str(code), "name": name, "short": short or name[:3].upper()}
            for code, name, short in Team.objects.exclude(code=None).order_by("name").values_list("code", "name", "short_name")]


def _side(match: PlMatch, home: bool, clubs: dict[str, dict]) -> dict:
    team_id = match.home_team_id if home else match.away_team_id
    club = clubs.get(team_id)
    if club:
        return club
    name = match.home_team_name if home else match.away_team_name
    short = match.home_team_short if home else match.away_team_short
    return {"id": team_id, "name": name or team_id, "short": short or (name or team_id)[:3].upper()}


def _fpl_fixtures(matches: list[PlMatch]) -> dict[tuple[str, str], dict]:
    """FPL fixture id, gameweek and match-odds chances for league matches, by (home, away)."""
    pairs = {(m.home_team_id, m.away_team_id) for m in matches if m.competition_id == PlMatch.PREMIER_LEAGUE}
    if not pairs:
        return {}
    out = {}
    fixtures = Fixture.objects.select_related("team_h", "team_a").filter(team_h__isnull=False, team_a__isnull=False)
    odds = {o.fixture.fixture_id: o for o in FixtureOdds.objects.select_related("fixture").filter(home_odds__isnull=False)}
    for f in fixtures:
        key = (str(f.team_h.code), str(f.team_a.code))
        if key not in pairs:
            continue
        row = {"fixtureId": f.id, "gameweek": f.event, "chances": None}
        o = odds.get(f.id)
        if o and o.draw_odds and o.away_odds:
            implied = [1 / float(x) for x in (o.home_odds, o.draw_odds, o.away_odds)]
            row["chances"] = [round(p / sum(implied) * 100) for p in implied]
        out[key] = row
    return out


def build_calendar(start: date, days: int) -> dict:
    days = max(1, min(days, MAX_DAYS))
    key = f"match-calendar:{start.isoformat()}:{days}"
    cached = cache.get(key)
    if cached:
        return cached
    tz = timezone.get_current_timezone()
    begin = timezone.make_aware(datetime.combine(start, time.min), tz)
    end = begin + timedelta(days=days)
    club_list = _clubs()
    clubs = {c["id"]: c for c in club_list}
    ids = list(clubs)
    involved = Q(home_team_id__in=ids) | Q(away_team_id__in=ids)
    matches = list(PlMatch.objects.filter(involved, kickoff__gte=begin, kickoff__lt=end).order_by("kickoff"))
    fpl = _fpl_fixtures(matches)

    rows = []
    for m in matches:
        finished = m.home_score is not None
        league = m.competition_id == PlMatch.PREMIER_LEAGUE
        extra = fpl.get((m.home_team_id, m.away_team_id), {}) if league else {}
        rows.append({
            "matchId": m.match_id,
            "kickoff": m.kickoff.isoformat(),
            "competitionId": m.competition_id,
            "competition": m.competition_name or "Premier League",
            "round": "" if league else _round(m),
            "home": _side(m, True, clubs),
            "away": _side(m, False, clubs),
            "status": "finished" if finished else "upcoming",
            "score": [m.home_score, m.away_score] if finished else None,
            "penalties": [m.home_penalties, m.away_penalties] if m.home_penalties is not None else None,
            "gameweek": extra.get("gameweek") or (m.matchweek if league else None),
            "fixtureId": extra.get("fixtureId"),
            "chances": None if finished else extra.get("chances"),
        })

    # Each club's previous match before the window, so the first game in view
    # still shows how much rest came before it.
    previous = {}
    for club in ids:
        last = (PlMatch.objects.filter(Q(home_team_id=club) | Q(away_team_id=club), kickoff__lt=begin)
                .order_by("-kickoff").values_list("kickoff", flat=True).first())
        if last:
            previous[club] = last.isoformat()

    payload = {"start": start.isoformat(), "days": days, "today": timezone.localdate().isoformat(),
               "clubs": club_list, "matches": rows, "previous": previous}
    cache.set(key, payload, CACHE_TTL)
    return payload
