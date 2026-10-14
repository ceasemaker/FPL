"""Walk-forward backtest of the points forecast; stores the verdict.

    python manage.py backtest_forecast                  # weekly retraining, as in production
    python manage.py backtest_forecast --retrain-every 4  # faster, for development

Trains week by week on 2022/23 onwards and tests 2023/24 to 2025/26. The
stored ModelEvaluation decides whether the homepage may show a captain pick
(see etl/forecast/backtest.py for the baselines and the rule).
"""
import json

from django.core.management.base import BaseCommand

from etl.forecast import VERSION
from etl.forecast.backtest import TEST_SEASONS, evaluate
from etl.forecast.data import load_fixtures, load_players
from etl.forecast.service import MODEL_NAME
from etl.models import ModelEvaluation
from etl.services.forecast_sync import elite_squads


class Command(BaseCommand):
    help = "Backtest the points forecast against fixed baselines and store the result"

    def add_arguments(self, parser):
        parser.add_argument("--retrain-every", type=int, default=1)
        parser.add_argument("--dry-run", action="store_true", help="Print the result without storing it")

    def handle(self, *args, **options):
        players = load_players()
        players = players[players["season"] <= max(TEST_SEASONS)]
        summary = evaluate(players, load_fixtures(), elite_squads(), retrain_every=options["retrain_every"], log=self.stdout.write)
        brief = {k: summary[k] for k in ("accuracy", "accepted")}
        brief["captain"] = {k: summary["captain"][k] for k in ("points_per_week", "versus")}
        brief["lineup"] = summary["lineup"]
        self.stdout.write(json.dumps(brief, indent=1))
        if options["dry_run"]:
            return
        ModelEvaluation.objects.create(
            name=MODEL_NAME, version=VERSION, accepted=summary["accepted"]["captain"], summary=summary,
        )
        verdict = "accepted" if summary["accepted"]["captain"] else "not accepted"
        self.stdout.write(self.style.SUCCESS(f"Stored evaluation: captain picks {verdict}"))
