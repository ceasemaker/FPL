"""Per-match detail for Premier League matches: team stats, lineups, events,
momentum (SDP API, Opta ids) and every player's match sheet (classic API).

Per finished match:

* ``details``: three SDP requests: ``v3/matches/{id}/stats`` (~194 team
  stats per side, incl. xG and shot-zone counts), ``v3/matches/{id}/lineups``
  (players, captains, formation rows) and the raw Opta feed behind
  ``v1/matches/{id}/momentum`` (formation slots, cards with reasons,
  substitutions, VAR decisions, per-minute momentum).
* ``players``: the classic fixture (one request, which maps its pulselive id
  to the Opta match id and lists each squad with pulselive and Opta ids),
  then one sheet per player who played (~28 requests).

``sync_match_goals`` creates the ``PlMatch`` rows these hang off. A match is
marked synced only once its data is stored, so a failure is retried next run.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections, transaction

from ..models import MatchEvent, MatchLineupPlayer, MatchTeamStat, PlayerMatchStat, PlMatch
from .pl_stats_client import COMPETITIONS, ClassicStatsClient, PLStatsClient

logger = logging.getLogger(__name__)

CARD_KINDS = {"YC": "yellow", "Y2C": "second_yellow", "RC": "red"}
PERIODS = {"FirstHalf": 1, "SecondHalf": 2, "ExtraFirstHalf": 3, "ExtraSecondHalf": 4}


def _card_kind(text: str) -> str:
    """Events-feed card types ("Yellow", "Red", "YellowRed", "SecondYellow")."""
    t = (text or "").lower().replace(" ", "")
    if "second" in t or ("yellow" in t and "red" in t):
        return "second_yellow"
    return "red" if "red" in t else "yellow"


def _events_minute(item: dict) -> int:
    from .match_goals import _minute
    return _minute(item)


def _int(value, default=None):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _opta(alt_ids: dict | None, prefix: str) -> str:
    value = str((alt_ids or {}).get("opta") or "")
    return value[1:] if value.startswith(prefix) else value


# ------------------------------------------------------------------ parsing

def parse_team_stats(stats: list[dict], lineups: dict, match: PlMatch) -> list[dict]:
    formations = {
        side: ((lineups.get(f"{side}_team") or {}).get("formation") or {}).get("formation", "")
        for side in ("home", "away")
    }
    rows = []
    for entry in stats:
        side = str(entry.get("side", "")).lower()
        if side not in ("home", "away"):
            continue
        rows.append({
            "team_id": match.home_team_id if side == "home" else match.away_team_id,
            "is_home": side == "home",
            "formation": formations.get(side, ""),
            "stats": entry.get("stats") or {},
        })
    return rows


def parse_lineups(lineups: dict, feed: dict, match: PlMatch, events: dict | None = None) -> list[dict]:
    """Squads with formation slots and minutes on/off.

    On/off minutes come from the raw Opta feed (Premier League) or, for cup and
    European matches that have no feed, from the events feed.
    """
    live = feed.get("liveData") or {}
    slots = {}
    for team in live.get("lineUp") or []:
        for p in team.get("player") or []:
            slots[str(p.get("opPlayerId"))] = p
    on, off = {}, {}
    for sub in live.get("substitute") or []:
        on[str(sub.get("opPlayerOnId"))] = _int(sub.get("timeMin"))
        off[str(sub.get("opPlayerOffId"))] = _int(sub.get("timeMin"))
    for card in live.get("card") or []:
        if card.get("type") in ("Y2C", "RC"):
            off.setdefault(str(card.get("opPlayerId")), _int(card.get("timeMin")))
    for side in ("homeTeam", "awayTeam"):
        team = (events or {}).get(side) or {}
        for sub in team.get("subs") or []:
            on.setdefault(str(sub.get("playerOnId")), _events_minute(sub))
            off.setdefault(str(sub.get("playerOffId")), _events_minute(sub))
        for card in team.get("cards") or []:
            if _card_kind(card.get("type")) != "yellow":
                off.setdefault(str(card.get("playerId")), _events_minute(card))

    rows = []
    for side, team_id in (("home", match.home_team_id), ("away", match.away_team_id)):
        team = lineups.get(f"{side}_team") or {}
        grid = {}
        for r, line in enumerate((team.get("formation") or {}).get("lineup") or []):
            for c, pid in enumerate(line):
                grid[str(pid)] = (r, c)
        for p in team.get("players") or []:
            pid = str(p.get("id"))
            slot = slots.get(pid, {})
            starter = pid in grid
            rows.append({
                "team_id": team_id,
                "player_id": pid,
                "name": p.get("knownName") or f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(),
                "shirt": str(p.get("shirtNum") or ""),
                "position": slot.get("position") or p.get("position") or "",
                "position_side": slot.get("positionSide") or "",
                "formation_place": _int(slot.get("formationPlace")) or None,
                "formation_row": grid[pid][0] if starter else None,
                "formation_col": grid[pid][1] if starter else None,
                "starter": starter,
                "captain": bool(p.get("isCaptain")),
                "minute_on": on.get(pid),
                "minute_off": off.get(pid),
            })
    return rows


def parse_events(feed: dict) -> list[dict]:
    live = feed.get("liveData") or {}
    rows = []
    for card in live.get("card") or []:
        rows.append({
            "team_id": str(card.get("opContestantId", "")),
            "kind": CARD_KINDS.get(card.get("type"), "yellow"),
            "minute": _int(card.get("timeMin"), 0),
            "period": _int(card.get("periodId"), 0),
            "player_id": str(card.get("opPlayerId") or ""),
            "player_name": card.get("playerName") or "",
            "detail": card.get("cardReason") or "",
            "timestamp": card.get("timestamp") or "",
        })
    for sub in live.get("substitute") or []:
        rows.append({
            "team_id": str(sub.get("opContestantId", "")),
            "kind": "sub",
            "minute": _int(sub.get("timeMin"), 0),
            "period": _int(sub.get("periodId"), 0),
            "player_id": str(sub.get("opPlayerOnId") or ""),
            "player_name": sub.get("playerOnName") or "",
            "other_player_id": str(sub.get("opPlayerOffId") or ""),
            "other_player_name": sub.get("playerOffName") or "",
            "detail": sub.get("subReason") or "",
            "timestamp": sub.get("timestamp") or "",
        })
    for var in live.get("VAR") or []:
        rows.append({
            "team_id": str(var.get("opContestantId", "")),
            "kind": "var",
            "minute": _int(var.get("timeMin"), 0),
            "period": _int(var.get("periodId"), 0),
            "player_id": str(var.get("opPlayerId") or ""),
            "player_name": var.get("playerName") or "",
            "detail": ": ".join(x for x in (var.get("type"), var.get("outcome")) if x),
            "timestamp": var.get("timestamp") or "",
        })
    return sorted(rows, key=lambda r: (r["period"], r["minute"], r["timestamp"]))


def parse_events_feed(events: dict, match: PlMatch, names: dict[str, str]) -> list[dict]:
    """Cards and substitutions from the events feed (cup and European matches).

    This feed has no card reasons and no VAR decisions; those come only with
    the raw Opta feed the Premier League publishes for its own matches.
    """
    rows = []
    for side, team_id in (("homeTeam", match.home_team_id), ("awayTeam", match.away_team_id)):
        team = events.get(side) or {}
        for card in team.get("cards") or []:
            pid = str(card.get("playerId") or "")
            rows.append({"team_id": team_id, "kind": _card_kind(card.get("type")), "minute": _events_minute(card),
                         "period": PERIODS.get(card.get("period"), 0), "player_id": pid, "player_name": names.get(pid, ""),
                         "detail": "", "timestamp": card.get("timestamp") or ""})
        for sub in team.get("subs") or []:
            on, out = str(sub.get("playerOnId") or ""), str(sub.get("playerOffId") or "")
            rows.append({"team_id": team_id, "kind": "sub", "minute": _events_minute(sub), "period": PERIODS.get(sub.get("period"), 0),
                         "player_id": on, "player_name": names.get(on, ""), "other_player_id": out,
                         "other_player_name": names.get(out, ""), "detail": "", "timestamp": sub.get("timestamp") or ""})
    return sorted(rows, key=lambda r: (r["period"], r["minute"], r["timestamp"]))


def parse_momentum(feed: dict) -> list[list]:
    """[[period, minute, home, away], ...] in match order."""
    points = []
    for p in (feed.get("liveData") or {}).get("predictions") or []:
        if p.get("type") != "Momentum":
            continue
        values = {v.get("type"): float(v.get("probability") or 0) for v in p.get("prediction") or []}
        points.append([_int(p.get("periodId"), 0), _int(p.get("timeMin"), 0),
                       round(values.get("Home", 0.0), 5), round(values.get("Away", 0.0), 5)])
    return sorted(points)


def compact_sheet(sheet: dict) -> dict:
    """Drop zeros: most of a match sheet is zero, and a missing stat reads as 0."""
    return {k: v for k, v in sheet.items() if v not in (0, 0.0, None)}


# ------------------------------------------------------------------ syncing

def sync_details(match: PlMatch, client: PLStatsClient) -> bool:
    stats = client.get_match_stats(match.match_id)
    lineups = client.get_match_lineups(match.match_id)
    league = match.competition_id == PlMatch.PREMIER_LEAGUE
    # The raw Opta feed (momentum, card reasons, VAR) exists for league matches only.
    feed = client.get_match_feed(match.match_id) if league else {}
    events = None if league else client.get_match_events(match.match_id)
    if not stats or not lineups or (league and not feed) or (not league and not events):
        logger.warning("Match %s: detail feeds incomplete; retrying next run", match.match_id)
        return False
    lineup_rows = parse_lineups(lineups, feed, match, events)
    names = {r["player_id"]: r["name"] for r in lineup_rows}
    event_rows = parse_events(feed) if league else parse_events_feed(events, match, names)
    with transaction.atomic():
        match.team_stats.all().delete()
        match.lineups.all().delete()
        match.events.all().delete()
        MatchTeamStat.objects.bulk_create([MatchTeamStat(match=match, **r) for r in parse_team_stats(stats, lineups, match)])
        MatchLineupPlayer.objects.bulk_create([MatchLineupPlayer(match=match, **r) for r in lineup_rows])
        MatchEvent.objects.bulk_create([MatchEvent(match=match, **r) for r in event_rows])
        match.momentum = parse_momentum(feed) if league else []
        match.details_synced = True
        match.save(update_fields=["momentum", "details_synced"])
    return True


def sync_players(match: PlMatch, fixture: dict, client: ClassicStatsClient) -> bool:
    """Store the sheets of everyone who played (starters and used substitutes)."""
    played = {
        p.player_id: p
        for p in match.lineups.all()
        if p.starter or p.minute_on is not None
    }
    squad = []
    for team in fixture.get("teamLists") or []:
        for p in (team.get("lineup") or []) + (team.get("substitutes") or []):
            opta = _opta(p.get("altIds"), "p")
            if opta in played and p.get("id"):
                squad.append((opta, int(p["id"])))
    if not squad:
        logger.warning("Match %s: no classic squad matched the lineups", match.match_id)
        return False
    rows = []
    for opta, pulselive in squad:
        sheet = client.get_player_match_stats(pulselive, fixture["id"])
        if not sheet:
            continue
        rows.append(PlayerMatchStat(
            match=match, player_id=opta, source_player_id=pulselive, team_id=played[opta].team_id,
            minutes=_int(sheet.get("mins_played"), 0), started=bool(sheet.get("game_started")),
            stats=compact_sheet(sheet),
        ))
    if len(rows) < len(squad) * 0.8:
        logger.warning("Match %s: only %s of %s player sheets; retrying next run", match.match_id, len(rows), len(squad))
        return False
    with transaction.atomic():
        match.player_stats.all().delete()
        PlayerMatchStat.objects.bulk_create(rows)
        match.players_synced = True
        match.save(update_fields=["players_synced"])
    return True


def _parallel(items, work, workers: int):
    def run(item):
        try:
            return work(item)
        except Exception:
            logger.exception("Match detail sync failed for %s", item)
            return False
        finally:
            close_old_connections()
    if workers <= 1:
        return [run(i) for i in items]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, items))


def sync_season_details(season: int, workers: int = 3, delay: float = 0.4, refresh: bool = False, log=logger.info) -> dict:
    """Details for every stored finished match of the season, in every competition."""
    matches = PlMatch.objects.filter(season=season, home_score__isnull=False)
    if not refresh:
        matches = matches.filter(details_synced=False)
    matches = list(matches)
    clients = {}

    def work(match):
        import threading
        client = clients.setdefault(threading.get_ident(), PLStatsClient(delay=delay))
        return sync_details(match, client)

    done = sum(_parallel(matches, work, workers))
    log(f"{season}/{(season + 1) % 100:02d} details: {done} of {len(matches)} matches stored")
    return {"stored": done, "tried": len(matches)}


def sync_season_players(season: int, workers: int = 3, delay: float = 0.4, refresh: bool = False, log=logger.info) -> dict:
    """Player sheets for every finished league match whose details are stored.

    The classic API's per-player sheets are wired up for the Premier League
    only; cup and European minutes come from the lineups instead.
    """
    pending = PlMatch.objects.filter(season=season, details_synced=True, competition_id=PlMatch.PREMIER_LEAGUE)
    if not refresh:
        pending = pending.filter(players_synced=False)
    by_classic = {m.classic_id: m for m in pending if m.classic_id}
    by_opta = {m.match_id: m for m in pending}
    if not by_opta:
        log(f"{season}/{(season + 1) % 100:02d} players: nothing to do")
        return {"stored": 0, "tried": 0}

    lister = ClassicStatsClient(delay=delay)
    season_id = lister.season_id(COMPETITIONS["premier-league"]["classic"], season)
    if season_id is None:
        log(f"{season}: no classic season id")
        return {"stored": 0, "tried": 0}
    # Fixtures we already know, plus any finished fixture not yet mapped to a match.
    known = {m.classic_id for m in PlMatch.objects.filter(season=season, classic_id__isnull=False, competition_id=PlMatch.PREMIER_LEAGUE)}
    targets = [fid for fid in (int(f["id"]) for f in lister.iter_fixtures(season_id)) if fid in by_classic or fid not in known]
    clients = {}

    def work(fixture_id):
        import threading
        client = clients.setdefault(threading.get_ident(), ClassicStatsClient(delay=delay))
        fixture = client.get_fixture(fixture_id)
        match = by_opta.get(_opta(fixture.get("altIds"), "g"))
        if match is None:
            return False
        if match.classic_id != fixture_id:
            match.classic_id = fixture_id
            match.save(update_fields=["classic_id"])
        return sync_players(match, fixture, client)

    done = sum(_parallel(targets, work, workers))
    log(f"{season}/{(season + 1) % 100:02d} players: {done} of {len(by_opta)} matches stored")
    return {"stored": done, "tried": len(by_opta)}
