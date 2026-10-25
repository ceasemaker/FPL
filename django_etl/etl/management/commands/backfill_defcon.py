"""Fill this season's defensive-contribution fields from FPL's live gameweek data.

    python manage.py backfill_defcon            # every finished gameweek so far
"""
from django.core.management.base import BaseCommand
from django.db.models import Max

from etl.models import Athlete, AthleteStat
from etl.services.etl_runner import defcon_fields
from etl.services.fpl_client import FPLClient


class Command(BaseCommand):
    help = "Backfill defensive contributions per player per gameweek from event/{gw}/live/"

    def handle(self, *args, **options):
        latest = AthleteStat.objects.aggregate(gw=Max("game_week"))["gw"] or 0
        known = set(Athlete.objects.values_list("id", flat=True))
        client = FPLClient()
        for gw in range(1, latest + 1):
            payload = client.get_event_live(gw)
            updated = 0
            for element in payload.get("elements", []):
                if element.get("id") not in known:
                    continue
                updated += AthleteStat.objects.filter(athlete_id=element["id"], game_week=gw).update(**defcon_fields(element))
            self.stdout.write(f"GW{gw}: {updated} player rows updated")
