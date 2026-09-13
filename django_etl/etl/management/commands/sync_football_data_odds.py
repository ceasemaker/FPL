from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from etl.services.football_data import sync_current_season


class Command(BaseCommand):
    help = "Download the once-daily Football-Data Premier League historical odds CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Deliberately bypass today's completed/attempted guard",
        )

    def handle(self, *args, **options):
        result = sync_current_season(force=options["force"])
        self.stdout.write(json.dumps(result, sort_keys=True))
