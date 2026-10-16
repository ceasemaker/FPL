"""Store Premier League matches and their goals (for the clutch-goals chart).

    python manage.py sync_match_goals --seasons 2021 2022 2023 2024 2025 2026
    python manage.py sync_match_goals            # the current season only

Already-stored matches are skipped unless --refresh is given.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Max

from etl.models import GameweekHistory
from etl.services.match_goals import sync_season
from etl.services.pl_stats_client import PLStatsClient


class Command(BaseCommand):
    help = "Store Premier League matches and their goals in order"

    def add_arguments(self, parser):
        parser.add_argument("--seasons", type=int, nargs="*")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--delay", type=float, default=0.4)

    def handle(self, *args, **options):
        seasons = options["seasons"] or [GameweekHistory.objects.aggregate(s=Max("season"))["s"]]
        client = PLStatsClient(delay=options["delay"])
        for season in seasons:
            sync_season(season, client, refresh=options["refresh"], log=self.stdout.write)
