"""Backfill as-of-deadline ownership/transfer/price context onto AthleteStat.

Source is the stored element-summary ``history`` on ``ElementSummary``. Each
history row is a deadline snapshot for its round, so this is safe to re-run.
Only existing AthleteStat rows are touched, and only history rows whose
(fixture, round) matches a current-season Fixture are trusted.
"""
from django.core.management.base import BaseCommand

from etl.models import ElementSummary
from etl.services.etl_runner import (
    current_season_fixture_keys,
    gameweek_context_from_history,
    sync_gameweek_context,
)


class Command(BaseCommand):
    help = "Update AthleteStat.selected/transfers_in/transfers_out/value from element-summary history (existing rows only)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report counts only")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        valid_fixtures = current_season_fixture_keys()
        summaries = (
            ElementSummary.objects.filter(athlete__removed=False)
            .select_related("athlete")
            .iterator()
        )
        athletes = 0
        rows = 0
        for summary in summaries:
            athletes += 1
            if dry_run:
                rows += len(gameweek_context_from_history(summary.history, valid_fixtures))
                continue
            rows += sync_gameweek_context(summary.athlete, summary.history, valid_fixtures)

        verb = "Would write" if dry_run else "Wrote"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} gameweek context for {rows} rows across {athletes} athletes")
        )
