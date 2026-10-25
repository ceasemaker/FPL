"""Store Premier League matches and their goals (for the clutch-goals chart).

    python manage.py sync_match_goals --seasons 2021 2022 2023 2024 2025 2026
    python manage.py sync_match_goals            # the current season, every competition
    python manage.py sync_match_goals --competitions 8   # Premier League only

Already-stored matches are skipped unless --refresh is given.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Max

from etl.models import GameweekHistory
from etl.services.match_goals import CUP_COMPETITIONS, PREMIER_LEAGUE, sync_season
from etl.services.pl_stats_client import PLStatsClient


class Command(BaseCommand):
    help = "Store Premier League matches and their goals in order"

    def add_arguments(self, parser):
        parser.add_argument("--seasons", type=int, nargs="*")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--competitions", type=int, nargs="*",
                            help="Opta competition ids (default: the Premier League, then every cup and European competition)")
        parser.add_argument("--delay", type=float, default=0.4)

    def handle(self, *args, **options):
        seasons = options["seasons"] or [GameweekHistory.objects.aggregate(s=Max("season"))["s"]]
        client = PLStatsClient(delay=options["delay"])
        competitions = options["competitions"] or [PREMIER_LEAGUE, *CUP_COMPETITIONS]
        for season in seasons:
            # The league first: cup ties are kept only for its clubs.
            for competition in sorted(competitions, key=lambda c: c != PREMIER_LEAGUE):
                sync_season(season, client, refresh=options["refresh"], log=self.stdout.write, competition=competition)
