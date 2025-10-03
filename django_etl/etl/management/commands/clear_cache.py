"""Management command to clear Redis cache after ETL updates."""
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clear Redis cache to force fresh data after ETL run"

    def handle(self, *args, **options):
        """Clear all cached data."""
        self.stdout.write("Clearing Redis cache...")
        
        # Clear all cache keys with our prefix
        cache.clear()
        
        self.stdout.write(self.style.SUCCESS("✓ Cache cleared successfully"))
        self.stdout.write("Next API requests will rebuild cache with fresh data")
