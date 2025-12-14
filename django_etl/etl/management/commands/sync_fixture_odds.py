"""
Django management command to sync betting odds for upcoming fixtures.

Usage:
    python manage.py sync_fixture_odds
    python manage.py sync_fixture_odds --days=14
    python manage.py sync_fixture_odds --event-id=12345
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import sys
from pathlib import Path

# Add sofa_sport scripts to path
scripts_path = Path(__file__).resolve().parent.parent.parent.parent / "sofa_sport" / "scripts"
sys.path.insert(0, str(scripts_path))

from fetch_fixture_odds import sync_upcoming_fixtures_odds, sync_single_fixture_odds


class Command(BaseCommand):
    help = "Fetch and store betting odds for upcoming fixtures from SofaSport API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days ahead to fetch odds for (default: 7)"
        )
        parser.add_argument(
            "--event-id",
            type=int,
            help="Fetch odds for a specific event ID only"
        )

    def handle(self, *args, **options):
        days = options["days"]
        event_id = options.get("event_id")

        self.stdout.write(self.style.SUCCESS("🎲 Starting fixture odds sync..."))
        
        if event_id:
            # Sync single fixture
            self.stdout.write(f"Fetching odds for event ID: {event_id}")
            success = sync_single_fixture_odds(event_id)
            
            if success:
                self.stdout.write(self.style.SUCCESS("✅ Odds fetched successfully"))
            else:
                self.stdout.write(self.style.ERROR("❌ Failed to fetch odds"))
                sys.exit(1)
        else:
            # Sync all upcoming fixtures
            self.stdout.write(f"Fetching odds for fixtures in next {days} days...")
            result = sync_upcoming_fixtures_odds(days_ahead=days)
            
            # Print summary
            self.stdout.write(self.style.SUCCESS(f"\n✅ Success: {result['success']}"))
            if result['failed'] > 0:
                self.stdout.write(self.style.WARNING(f"❌ Failed: {result['failed']}"))
            if result['skipped'] > 0:
                self.stdout.write(self.style.WARNING(f"⏭️  Skipped: {result['skipped']}"))
            
            self.stdout.write(self.style.SUCCESS("\n✨ Odds sync complete!"))
