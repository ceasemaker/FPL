"""Backtest the fixture model (projected goals and clean-sheet chances) and record whether it may be shown.

    python manage.py backtest_fixture_model
"""
import json

from django.core.management.base import BaseCommand

from etl.services.fixture_model import backtest


class Command(BaseCommand):
    help = "Walk-forward backtest of the fixture model (stored as ModelEvaluation 'fixture_model')"

    def handle(self, *args, **options):
        self.stdout.write("FIXTURE_MODEL " + json.dumps(backtest()))
