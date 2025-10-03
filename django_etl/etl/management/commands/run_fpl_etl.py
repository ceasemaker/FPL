"""Management command that executes the full FPL ETL pipeline."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from ...services.etl_runner import PipelineConfig, run_pipeline


class Command(BaseCommand):
    help = "Run the Fantasy Premier League ETL pipeline"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Continuously poll the FPL API, sleeping between iterations.",
        )
        parser.add_argument(
            "--sleep",
            type=int,
            default=300,
            help="Seconds to sleep between iterations when looping (default: 300).",
        )
        parser.add_argument(
            "--no-snapshots",
            action="store_true",
            help="Disable storage of raw API payload snapshots.",
        )
        parser.add_argument(
            "--player-limit",
            type=int,
            default=None,
            help="Limit number of players processed (useful for quick tests).",
        )

    def handle(self, *args, **options):  # type: ignore[override]
        config = PipelineConfig(
            loop=options["loop"],
            sleep_seconds=options["sleep"],
            snapshot_payloads=not options["no_snapshots"],
            player_limit=options["player_limit"],
        )
        run_pipeline(config)
