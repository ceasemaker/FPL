"""Record which club each player played for in a season.

    python manage.py sync_season_teams --season 2024
    python manage.py sync_season_teams --season 2025 --competition champions-league

Season sheets (sync_season_stats) only carry a player's *current* club, which
is wrong for anyone who has moved since. This reads each club's squad for that
season (one request per club) and fills ``season_team_id``/``season_team_name``
on the season's rows. Premier League rows use the SDP squads (Opta ids);
other competitions use the classic API's squads (pulselive ids). A player in
two squads (a mid-season move) keeps the club whose squad lists him with the
later join date.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from etl.models import PlayerSeasonStat
from etl.services.pl_stats_client import COMPETITIONS, ClassicStatsClient, PLStatsClient


class Command(BaseCommand):
    help = "Fill each season row's club from that season's squads"

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True)
        parser.add_argument("--competition", choices=sorted(COMPETITIONS), default="premier-league")
        parser.add_argument("--delay", type=float, default=0.4)

    def handle(self, *args, **options):
        season = options["season"]
        competition = COMPETITIONS[options["competition"]]
        if options["competition"] == "premier-league":
            by_player = self._sdp(competition["opta"], season, options["delay"])
            rows = PlayerSeasonStat.objects.filter(competition_id=competition["opta"], season=season)
            key = lambda row: row.opta_player_id
        else:
            by_player = self._classic(competition["classic"], season, options["delay"])
            rows = PlayerSeasonStat.objects.filter(
                competition_id=competition["opta"], season=season, source=PlayerSeasonStat.SOURCE_CLASSIC
            )
            key = lambda row: row.source_player_id
        matched = 0
        for row in rows:
            team = by_player.get(str(key(row)))
            if not team:
                continue
            row.season_team_id, row.season_team_name = team[1], team[2]
            row.save(update_fields=["season_team_id", "season_team_name"])
            matched += 1
        self.stdout.write(self.style.SUCCESS(
            f"✓ {options['competition']} {season}/{(season + 1) % 100:02d}: club found for {matched} of {rows.count()} rows"
        ))

    @staticmethod
    def _keep_latest(by_player: dict, player_id: str, joined: str, team_id: str, team_name: str) -> None:
        current = by_player.get(player_id)
        if current is None or joined > current[0]:
            by_player[player_id] = (joined, team_id, team_name)

    def _sdp(self, competition: int, season: int, delay: float) -> dict:
        client = PLStatsClient(delay=delay)
        teams = client.get_season_teams(competition, season)
        if not teams:
            raise CommandError(f"No clubs listed for {season}")
        by_player: dict = {}
        for team in teams:
            for player in client.get_season_squad(competition, season, team["id"]):
                joined = ((player.get("dates") or {}).get("joinedClub")) or ""
                self._keep_latest(by_player, str(player["id"]), joined, str(team["id"]), team.get("name", ""))
        return by_player

    def _classic(self, competition: int, season: int, delay: float) -> dict:
        client = ClassicStatsClient(delay=delay)
        season_id = client.season_id(competition, season)
        if season_id is None:
            raise CommandError(f"Classic API has no {season} season for competition {competition}")
        by_player: dict = {}
        for team in client.get_season_teams(season_id):
            for player in client.get_season_squad(int(team["id"]), season_id):
                # ``id`` matches the stats leaderboards' ids; ``playerId`` is a different (person) id.
                player_id = str(int(player.get("id") or 0))
                self._keep_latest(by_player, player_id, "", str(int(team["id"])), team.get("name", ""))
        return by_player
