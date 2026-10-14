"""Train the points forecast, write next-gameweek forecasts, log and score shadow picks.

    python manage.py run_forecast

Runs daily after the FPL sync (see etl.tasks.run_daily_pipeline). See
etl/forecast/service.py for what each step does.
"""
from django.core.management.base import BaseCommand

from etl.forecast.service import run_forecast


class Command(BaseCommand):
    help = "Train the points forecast and update forecasts and shadow captain picks"

    def handle(self, *args, **options):
        result = run_forecast(log=self.stdout.write)
        self.stdout.write(self.style.SUCCESS(str(result)))
