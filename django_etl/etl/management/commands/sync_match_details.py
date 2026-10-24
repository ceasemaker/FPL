"""Store per-match team stats, lineups, events, momentum and player sheets.

    python manage.py sync_match_details                      # current season, details then players
    python manage.py sync_match_details --seasons 2024 2025 --workers 3
    python manage.py sync_match_details --only details       # skip the (slow) player sheets

Needs the season's matches first (sync_match_goals). Finished matches already
stored are skipped unless --refresh. A full season of player sheets is
~11,000 requests (about an hour with 3 workers); run backfills as Render jobs.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Max

from etl.models import GameweekHistory
from etl.services.match_details import sync_season_details, sync_season_players


class Command(BaseCommand):
    help = "Store per-match team stats, lineups, events, momentum and player sheets"

    def add_arguments(self, parser):
        parser.add_argument("--seasons", type=int, nargs="*")
        parser.add_argument("--only", choices=["details", "players"])
        parser.add_argument("--workers", type=int, default=3)
        parser.add_argument("--delay", type=float, default=0.4)
        parser.add_argument("--refresh", action="store_true")

    def handle(self, *args, **options):
        seasons = options["seasons"] or [GameweekHistory.objects.aggregate(s=Max("season"))["s"]]
        kwargs = {"workers": options["workers"], "delay": options["delay"], "refresh": options["refresh"], "log": self.stdout.write}
        for season in seasons:
            if options["only"] != "players":
                sync_season_details(season, **kwargs)
            if options["only"] != "details":
                sync_season_players(season, **kwargs)
