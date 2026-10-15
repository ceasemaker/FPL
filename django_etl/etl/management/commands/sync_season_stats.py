"""Load player season stat sheets from the Premier League's stats APIs.

Examples (2026/27):

    python manage.py sync_season_stats --season 2026                      # PL, SDP API (xG, xGOT)
    python manage.py sync_season_stats --season 2026 --source classic     # PL, classic API (~260 stats)
    python manage.py sync_season_stats --season 2026 --source classic --competition champions-league

Re-running is safe: rows are upserted on (source, competition, season, Opta
player id). See PREMIER_LEAGUE_DATA_API.md for what each source covers.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from etl.models import Athlete, PlayerSeasonStat
from etl.services.pl_stats_client import (
    CLASSIC_POSITIONS,
    COMPETITIONS,
    ClassicStatsClient,
    PLStatsClient,
)


class Command(BaseCommand):
    help = "Load player season stats from the Premier League stats APIs"

    def add_arguments(self, parser):
        parser.add_argument("--season", type=int, required=True, help="Start year, e.g. 2026 for 2026/27")
        parser.add_argument("--competition", choices=sorted(COMPETITIONS), default="premier-league")
        parser.add_argument(
            "--source",
            choices=[PlayerSeasonStat.SOURCE_SDP, PlayerSeasonStat.SOURCE_CLASSIC],
            default=PlayerSeasonStat.SOURCE_SDP,
        )
        parser.add_argument("--delay", type=float, default=0.4, help="Seconds between requests")
        parser.add_argument("--limit", type=int, default=None, help="Only the first N players (for testing)")
        parser.add_argument("--workers", type=int, default=1,
                            help="Fetch this many sheets at once (each worker keeps --delay between its own requests)")

    def handle(self, *args, **options):
        season = options["season"]
        competition = COMPETITIONS[options["competition"]]
        source = options["source"]
        label = f"{options['competition']} {season}/{(season + 1) % 100:02d} ({source})"
        self.athletes_by_code = {
            str(code): athlete_id
            for code, athlete_id in Athlete.objects.exclude(code__isnull=True).values_list("code", "id")
        }

        if source == PlayerSeasonStat.SOURCE_SDP:
            rows = self._sdp_rows(competition["opta"], season, options)
        else:
            rows = self._classic_rows(competition["classic"], season, options)

        created = updated = linked = empty = 0
        for index, row in enumerate(rows, start=1):
            if not row["stats"]:
                empty += 1
                continue
            athlete_id = self.athletes_by_code.get(row["opta_player_id"])
            linked += athlete_id is not None
            _, was_created = PlayerSeasonStat.objects.update_or_create(
                source=source,
                competition_id=competition["opta"],
                season=season,
                opta_player_id=row["opta_player_id"],
                defaults={
                    "source_player_id": row["source_player_id"],
                    "athlete_id": athlete_id,
                    "name": row["name"],
                    "position": row["position"],
                    "current_team_name": row["team"],
                    "stats": row["stats"],
                },
            )
            created += was_created
            updated += not was_created
            if index % 100 == 0:
                self.stdout.write(f"  {index} processed")

        self.stdout.write(self.style.SUCCESS(
            f"✓ {label}: {created} created, {updated} updated, {empty} without a stat sheet; "
            f"{linked} linked to current FPL players"
        ))

    def _limited(self, players: list, options) -> list:
        return players[: options["limit"]] if options["limit"] else players

    @staticmethod
    def _fetch_all(items, fetch, workers: int):
        """Run ``fetch`` over ``items``, in parallel when asked; results keep input order.

        Only the HTTP requests run in threads; the caller writes to the
        database from the main thread.
        """
        if workers <= 1:
            for item in items:
                yield item, fetch(item)
            return
        import threading
        from concurrent.futures import ThreadPoolExecutor

        local = threading.local()

        def run(item):
            return fetch(item, local)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            yield from zip(items, pool.map(run, items))

    def _sdp_rows(self, competition: int, season: int, options):
        client = PLStatsClient(delay=options["delay"])
        players = self._limited(list(client.iter_season_players(competition, season)), options)
        self.stdout.write(f"{len(players)} players listed")

        def fetch(meta, local=None):
            worker = client
            if local is not None:
                worker = getattr(local, "client", None) or PLStatsClient(delay=options["delay"])
                local.client = worker
            return worker.get_player_season_stats(competition, season, str(meta["id"]))

        for meta, stats in self._fetch_all(players, fetch, options["workers"]):
            opta_id = str(meta["id"])
            yield {
                "opta_player_id": opta_id,
                "source_player_id": opta_id,
                "name": meta.get("name") or "",
                "position": meta.get("position") or "",
                "team": (meta.get("currentTeam") or {}).get("name") or "",
                "stats": stats,
            }

    def _classic_rows(self, competition: int, season: int, options):
        client = ClassicStatsClient(delay=options["delay"])
        season_id = client.season_id(competition, season)
        if season_id is None:
            raise CommandError(f"Classic API has no {season} season for competition {competition}")
        players = self._limited(list(client.iter_players_with_minutes(competition, season_id)), options)
        self.stdout.write(f"{len(players)} players with minutes (classic season id {season_id})")
        def fetch(owner, local=None):
            worker = client
            if local is not None:
                worker = getattr(local, "client", None) or ClassicStatsClient(delay=options["delay"])
                local.client = worker
            return worker.get_player_season_stats(int(owner["id"]), competition, season_id)

        for owner, stats in self._fetch_all(players, fetch, options["workers"]):
            pulselive_id = int(owner["id"])
            opta = ((owner.get("altIds") or {}).get("opta") or "").lstrip("p")
            yield {
                # A few players lack an Opta id; key them by pulselive id so they
                # still load, just without an FPL link.
                "opta_player_id": opta or f"pl{pulselive_id}",
                "source_player_id": str(pulselive_id),
                "name": (owner.get("name") or {}).get("display") or "",
                "position": CLASSIC_POSITIONS.get((owner.get("info") or {}).get("position"), ""),
                "team": (owner.get("currentTeam") or {}).get("name") or "",
                "stats": stats,
            }
