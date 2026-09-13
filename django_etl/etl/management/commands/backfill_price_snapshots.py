"""
Management command to backfill PriceSnapshot table from existing RawEndpointSnapshot records.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from etl.models import Athlete, PriceSnapshot, RawEndpointSnapshot


class Command(BaseCommand):
    help = "Backfill PriceSnapshot table from RawEndpointSnapshot records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of snapshots to process"
        )

    def handle(self, *args, **options):
        limit = options.get("limit")

        # Get all bootstrap-static snapshots ordered by time
        snapshots_qs = RawEndpointSnapshot.objects.filter(
            endpoint="bootstrap-static"
        ).order_by("created_at")

        if limit:
            snapshots_qs = snapshots_qs[:limit]

        snapshot_count = snapshots_qs.count()
        self.stdout.write(f"Found {snapshot_count} snapshots to process")

        processed = 0
        for snapshot in snapshots_qs.iterator(chunk_size=50):
            try:
                payload = snapshot.payload
                elements = payload.get("elements", [])

                snapshots_to_create = []
                for element in elements:
                    athlete_id = element.get("id")
                    if not athlete_id:
                        continue

                    # Skip if athlete doesn't exist
                    if not Athlete.objects.filter(id=athlete_id).exists():
                        continue

                    price_snapshot = PriceSnapshot(
                        athlete_id=athlete_id,
                        snapshot_time=snapshot.created_at,
                        cost=element.get("now_cost", 0),
                        transfers_in_total=element.get("transfers_in", 0),
                        transfers_out_total=element.get("transfers_out", 0),
                        transfers_in_event=element.get("transfers_in_event", 0),
                        transfers_out_event=element.get("transfers_out_event", 0),
                        total_points=element.get("total_points", 0),
                        form=str(element.get("form", "0.0")),
                        selected_by_percent=str(element.get("selected_by_percent", "0.0")),
                    )
                    snapshots_to_create.append(price_snapshot)

                # Bulk create with ignore_conflicts
                if snapshots_to_create:
                    PriceSnapshot.objects.bulk_create(
                        snapshots_to_create,
                        ignore_conflicts=True,
                        batch_size=100
                    )

                processed += 1
                if processed % 10 == 0:
                    self.stdout.write(f"Processed {processed}/{snapshot_count} snapshots")

            except Exception as e:
                self.stderr.write(f"Error processing snapshot {snapshot.id}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f"Successfully backfilled PriceSnapshot table")
        )
