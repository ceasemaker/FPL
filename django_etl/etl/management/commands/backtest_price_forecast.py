"""Backtest the seven-day price-rise forecast and record whether it may be shown.

    python manage.py backtest_price_forecast
"""
import json

from django.core.management.base import BaseCommand

from etl.services.price_forecast import backtest


class Command(BaseCommand):
    help = "Backtest the seven-day price-rise forecast (stored as ModelEvaluation 'price_forecast')"

    def handle(self, *args, **options):
        self.stdout.write("PRICE_FORECAST " + json.dumps(backtest()))
