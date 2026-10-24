"""Captain backtest for the points forecast (v2 vs v3 with Opta match features).

    python manage.py evaluate_captain

Walk-forward over 2023/24-2025/26 with weekly retraining (~45 minutes and
~450 MB, so run it as a Render one-off job). Stores the result as a
ModelEvaluation named "captain": the homepage captain card shows its record,
and run_forecast switches to v3 when the backtest chose it. See
etl/forecast/captain_eval.py for the comparators and the pass rule.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from etl.forecast.captain_eval import run
from etl.forecast.service import CAPTAIN_EVALUATION
from etl.models import ModelEvaluation


class Command(BaseCommand):
    help = "Backtest the forecast's captain picks against simple rules and store the verdict"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print the result without storing it")

    def handle(self, *args, **options):
        result = run(log=self.stdout.write)
        if not options["dry_run"]:
            ModelEvaluation.objects.create(name=CAPTAIN_EVALUATION, version=result["chosen"],
                                           accepted=result["passed"], summary=result)
        self.stdout.write("RESULT_JSON " + json.dumps(result, default=str))
