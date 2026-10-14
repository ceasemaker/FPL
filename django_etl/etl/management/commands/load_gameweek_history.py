"""Load past seasons' gameweek history into Postgres for the points forecast.

    python manage.py load_gameweek_history

Reads the committed files in etl/data/ (built by etl/ml/build_history_file.py)
and replaces those seasons' rows. Safe to re-run. The current season is kept
in step by the daily ETL instead.
"""
from django.core.management.base import BaseCommand

from etl.services.forecast_sync import current_season, load_history_files, sync_current_season


class Command(BaseCommand):
    help = "Load past seasons' gameweek history (and mirror the current season)"

    def handle(self, *args, **options):
        result = load_history_files()
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {result['player_gameweeks']:,} player-gameweeks and {result['fixtures']:,} fixtures "
            f"from {result['seasons']} past seasons"
        ))
        season = current_season()
        if season:
            rows = sync_current_season(season)
            self.stdout.write(self.style.SUCCESS(f"Mirrored {rows:,} player-gameweeks for {season}/{(season + 1) % 100:02d}"))
