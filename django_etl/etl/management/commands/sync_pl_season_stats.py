"""Load season stat sheets from the Premier League stats API.

Example (last season, 2025/26):

    python manage.py sync_pl_season_stats --season 2025

Re-running is safe: rows are upserted on (competition, season, Opta player id).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from etl.models import Athlete, PlayerSeasonStat
from etl.services.pl_stats_client import PREMIER_LEAGUE, PLStatsClient


class Command(BaseCommand):
    help = "Load player season stats (incl. xG and xGOT) from the Premier League stats API"

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True, help="Start year, e.g. 2025 for 2025/26")
        parser.add_argument("--competition", type=int, default=PREMIER_LEAGUE, help="Opta competition id (8 = Premier League)")
        parser.add_argument("--delay", type=float, default=0.4, help="Seconds between requests")
        parser.add_argument("--limit", type=int, default=None, help="Only the first N players (for testing)")

    def handle(self, *args, **options):
        season = options["season"]
        competition = options["competition"]
        client = PLStatsClient(delay=options["delay"])
        athletes_by_code = {
            str(code): athlete_id
            for code, athlete_id in Athlete.objects.exclude(code__isnull=True).values_list("code", "id")
        }

        players = list(client.iter_season_players(competition, season))
        if options["limit"]:
            players = players[: options["limit"]]
        self.stdout.write(f"{len(players)} players with minutes in {season}/{(season + 1) % 100:02d}")

        created = updated = linked = empty = 0
        for index, meta in enumerate(players, start=1):
            opta_id = str(meta["id"])
            stats = client.get_player_season_stats(competition, season, opta_id)
            if not stats:
                empty += 1
                continue
            athlete_id = athletes_by_code.get(opta_id)
            linked += athlete_id is not None
            _, was_created = PlayerSeasonStat.objects.update_or_create(
                competition_id=competition,
                season=season,
                opta_player_id=opta_id,
                defaults={
                    "athlete_id": athlete_id,
                    "name": meta.get("name") or "",
                    "position": meta.get("position") or "",
                    "current_team_name": (meta.get("currentTeam") or {}).get("name") or "",
                    "stats": stats,
                },
            )
            created += was_created
            updated += not was_created
            if index % 100 == 0:
                self.stdout.write(f"  {index}/{len(players)}")

        self.stdout.write(self.style.SUCCESS(
            f"✓ {created} created, {updated} updated, {empty} without a stat sheet; "
            f"{linked} linked to current FPL players"
        ))
