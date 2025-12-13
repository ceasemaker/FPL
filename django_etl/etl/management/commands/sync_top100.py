"""Management command to sync Top 100 manager data."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from ...services.fpl_client import FPLClient
from ...services.top100_etl import Top100Config, sync_top100_for_gameweek


def get_current_gameweek() -> int | None:
    """Fetch the current gameweek from the FPL API."""
    client = FPLClient()
    data = client.get_bootstrap_static()
    events = data.get("events", [])
    current = next((e for e in events if e.get("is_current")), None)
    return current.get("id") if current else None


class Command(BaseCommand):
    help = "Sync Top 100 (or N) managers data for a specific gameweek"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "gameweek",
            type=int,
            nargs="?",
            default=None,
            help="The gameweek to sync data for (default: current gameweek)",
        )
        parser.add_argument(
            "--manager-count",
            type=int,
            default=100,
            help="Number of top managers to track (default: 100)",
        )
        parser.add_argument(
            "--league-id",
            type=str,
            default="314",
            help="League ID to fetch standings from (default: 314 = Overall)",
        )
        parser.add_argument(
            "--range",
            type=int,
            nargs=2,
            metavar=("START_GW", "END_GW"),
            help="Sync a range of gameweeks (inclusive)",
        )

    def handle(self, *args, **options):
        config = Top100Config(
            league_id=options["league_id"],
            manager_count=options["manager_count"],
        )
        
        if options["range"]:
            start_gw, end_gw = options["range"]
            self.stdout.write(f"Syncing Top {config.manager_count} for GW{start_gw}-{end_gw}")
            
            for gw in range(start_gw, end_gw + 1):
                self.stdout.write(f"Processing GW{gw}...")
                summary = sync_top100_for_gameweek(gw, config)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"GW{gw}: Avg points = {summary.average_points}, "
                        f"Template team size = {len(summary.template_team)}"
                    )
                )
        else:
            gw = options["gameweek"]
            
            # Auto-detect current gameweek if not provided
            if gw is None:
                gw = get_current_gameweek()
                if gw is None:
                    self.stderr.write(
                        self.style.ERROR("Could not determine current gameweek from API")
                    )
                    return
                self.stdout.write(f"Auto-detected current gameweek: {gw}")
            
            self.stdout.write(f"Syncing Top {config.manager_count} for GW{gw}")
            
            summary = sync_top100_for_gameweek(gw, config)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully synced Top {config.manager_count} for GW{gw}\n"
                    f"Average points: {summary.average_points}\n"
                    f"Highest: {summary.highest_points}, Lowest: {summary.lowest_points}\n"
                    f"Template team players: {len(summary.template_team)}\n"
                    f"Chip usage: {summary.chip_usage}"
                )
            )
