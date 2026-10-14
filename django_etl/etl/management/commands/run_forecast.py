"""Train the points forecast, write next-gameweek forecasts, log and score shadow picks.

    python manage.py run_forecast           # after the daily FPL sync
    python manage.py run_forecast --sync    # read FPL's bootstrap first (deadlines, team news, ep_next)

Runs daily after the FPL sync (see etl.tasks.run_daily_pipeline). See
etl/forecast/service.py for what each step does.
"""
from django.core.management.base import BaseCommand

from etl.forecast.service import run_forecast


class Command(BaseCommand):
    help = "Train the points forecast and update forecasts and shadow captain picks"

    def add_arguments(self, parser):
        parser.add_argument("--sync", action="store_true", help="Refresh deadlines, availability and ep_next from FPL first")

    def handle(self, *args, **options):
        if options["sync"]:
            from etl.services.etl_runner import _sync_athletes
            from etl.services.forecast_sync import sync_forecast_tables
            from etl.services.fpl_client import FPLClient

            with FPLClient() as client:
                bootstrap = client.get_bootstrap_static()
            _sync_athletes(bootstrap.get("elements", []))
            sync_forecast_tables(bootstrap.get("events", []), bootstrap.get("elements", []))
        result = run_forecast(log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(str(result)))
