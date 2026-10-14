"""Load club season stat sheets from the Premier League SDP stats API.

    python manage.py sync_team_season_stats --season 2026

Re-running is safe: rows are upserted on (competition, season, Opta team id).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from etl.models import Team, TeamSeasonStat
from etl.services.pl_stats_client import PREMIER_LEAGUE, PLStatsClient


class Command(BaseCommand):
    help = "Load club season stats (xG, xGOT conceded, shots conceded, ...) from the PL stats API"

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True, help="Start year, e.g. 2026 for 2026/27")
        parser.add_argument("--delay", type=float, default=0.4, help="Seconds between requests")

    def handle(self, *args, **options):
        season = options["season"]
        client = PLStatsClient(delay=options["delay"])
        teams_by_code = {str(code): team_id for code, team_id in Team.objects.values_list("code", "id")}

        teams = client.get_season_teams(PREMIER_LEAGUE, season)
        created = updated = linked = 0
        for team in teams:
            opta_id = str(team["id"])
            stats = client.get_team_season_stats(PREMIER_LEAGUE, season, opta_id)
            team_id = teams_by_code.get(opta_id)
            linked += team_id is not None
            _, was_created = TeamSeasonStat.objects.update_or_create(
                competition_id=PREMIER_LEAGUE,
                season=season,
                opta_team_id=opta_id,
                defaults={"team_id": team_id, "name": team.get("name") or "", "stats": stats},
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(teams)} clubs for {season}/{(season + 1) % 100:02d}: "
            f"{created} created, {updated} updated, {linked} linked to FPL teams"
        ))
