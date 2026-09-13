"""Season-rollover guards for the FPL ETL.

FPL reassigns the small integer ``id`` values for teams and players between
seasons while ``code`` stays stable, so a naive refresh violates the unique
``code`` constraints and aborts the whole pass. These tests pin the guards that
make the rollover survivable.
"""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.test import TestCase

from ..models import (
    Athlete,
    AthletePrediction,
    AthleteStat,
    ElementSummary,
    EventStatus,
    Fixture,
    PriceSnapshot,
    Team,
    Top100Manager,
    Top100Pick,
    Top100Summary,
)
from ..services.etl_runner import (
    _handle_season_rollover,
    _latest_played_gameweek,
    _prune_unplayed_gameweeks,
    _season_start_year,
    _stored_season_start_year,
    _sync_athletes,
    _sync_teams,
)


def team_payload(team_id: int, code: int, name: str) -> dict:
    return {"id": team_id, "code": code, "name": name, "short_name": name[:3].upper()}


def athlete_payload(athlete_id: int, code: int, web_name: str, team: int = 1) -> dict:
    return {
        "id": athlete_id,
        "code": code,
        "web_name": web_name,
        "first_name": web_name,
        "second_name": web_name,
        "team": team,
        "element_type": 3,
        "now_cost": 50,
    }


class TeamRolloverTests(TestCase):
    def test_team_code_moving_to_a_new_id_does_not_break_the_sync(self) -> None:
        # Last season: Burnley held id 5. This season FPL reassigns it to id 3.
        Team.objects.create(id=5, code=90, name="Burnley")
        Team.objects.create(id=3, code=91, name="Bournemouth")

        _sync_teams([team_payload(3, 90, "Burnley"), team_payload(5, 91, "Bournemouth")])

        self.assertEqual(Team.objects.get(id=3).code, 90)
        self.assertEqual(Team.objects.get(id=3).name, "Burnley")
        self.assertEqual(Team.objects.get(id=5).code, 91)
        self.assertEqual(Team.objects.get(id=5).name, "Bournemouth")

    def test_relegated_team_keeps_its_row_but_is_marked_unavailable(self) -> None:
        Team.objects.create(id=21, code=99, name="Relegated FC")
        Team.objects.create(id=1, code=3, name="Arsenal")

        _sync_teams([team_payload(1, 3, "Arsenal")])

        self.assertTrue(Team.objects.get(id=21).unavailable)
        self.assertFalse(Team.objects.get(id=1).unavailable)

    def test_team_present_in_payload_is_never_left_unavailable(self) -> None:
        # The conflict-clearing step marks rows unavailable; the team's own
        # upsert must clear that again when it is still in the league.
        Team.objects.create(id=5, code=90, name="Burnley", unavailable=True)

        _sync_teams([team_payload(5, 90, "Burnley")])

        self.assertFalse(Team.objects.get(id=5).unavailable)


class AthleteRolloverTests(TestCase):
    def setUp(self) -> None:
        Team.objects.create(id=1, code=3, name="Arsenal")

    def test_athlete_code_moving_to_a_new_id_retires_the_stale_row(self) -> None:
        Athlete.objects.create(id=100, code=5001, web_name="Saka", team_id=1)

        _sync_athletes([athlete_payload(250, 5001, "Saka")])

        moved = Athlete.objects.get(id=250)
        self.assertEqual(moved.code, 5001)
        self.assertEqual(moved.web_name, "Saka")

        stale = Athlete.objects.get(id=100)
        self.assertTrue(stale.removed)
        self.assertTrue(stale.has_temporary_code)
        self.assertLess(stale.code, 0)

    def test_two_players_swapping_ids_both_survive(self) -> None:
        Athlete.objects.create(id=100, code=5001, web_name="Saka", team_id=1)
        Athlete.objects.create(id=101, code=5002, web_name="Rice", team_id=1)

        _sync_athletes(
            [athlete_payload(101, 5001, "Saka"), athlete_payload(100, 5002, "Rice")]
        )

        self.assertEqual(Athlete.objects.get(id=101).web_name, "Saka")
        self.assertEqual(Athlete.objects.get(id=101).code, 5001)
        self.assertEqual(Athlete.objects.get(id=100).web_name, "Rice")
        self.assertEqual(Athlete.objects.get(id=100).code, 5002)

    def test_temporary_code_collision_picks_a_free_negative_code(self) -> None:
        Athlete.objects.create(id=100, code=5001, web_name="Saka", team_id=1)
        Athlete.objects.create(
            id=102, code=-5001, web_name="Older", team_id=1, has_temporary_code=True
        )

        _sync_athletes([athlete_payload(250, 5001, "Saka")])

        self.assertEqual(Athlete.objects.get(id=250).code, 5001)
        self.assertEqual(Athlete.objects.get(id=100).code, -5002)
        self.assertEqual(Athlete.objects.get(id=102).code, -5001)

    def test_departed_athlete_is_marked_removed(self) -> None:
        Athlete.objects.create(id=100, code=5001, web_name="Saka", team_id=1)
        Athlete.objects.create(id=101, code=5002, web_name="Gone", team_id=1)

        _sync_athletes([athlete_payload(100, 5001, "Saka")])

        self.assertTrue(Athlete.objects.get(id=101).removed)
        self.assertFalse(Athlete.objects.get(id=100).removed)

    def test_athlete_without_a_code_is_skipped_rather_than_aborting(self) -> None:
        payload = athlete_payload(300, 5003, "Fine")
        broken = athlete_payload(301, 5004, "Broken")
        broken["code"] = None

        with self.assertLogs("etl.services.etl_runner", level="WARNING"):
            _sync_athletes([payload, broken])

        self.assertTrue(Athlete.objects.filter(id=300).exists())
        self.assertFalse(Athlete.objects.filter(id=301).exists())


class SeasonDetectionTests(TestCase):
    def test_season_start_year_uses_the_earliest_deadline(self) -> None:
        events = [
            {"id": 2, "deadline_time": "2026-08-22T17:30:00Z"},
            {"id": 1, "deadline_time": "2026-08-15T17:30:00Z"},
            {"id": 25, "deadline_time": "2027-02-14T11:30:00Z"},
        ]
        self.assertEqual(_season_start_year(events), 2026)

    def test_season_start_year_is_none_without_usable_deadlines(self) -> None:
        self.assertIsNone(_season_start_year([]))
        self.assertIsNone(_season_start_year([{"id": 1, "deadline_time": None}]))

    def test_stored_season_start_year_reads_the_earliest_fixture(self) -> None:
        self.assertIsNone(_stored_season_start_year())
        Team.objects.create(id=1, code=3, name="Arsenal")
        Team.objects.create(id=2, code=7, name="Villa")
        Fixture.objects.create(
            id=1,
            event=1,
            team_h_id=1,
            team_a_id=2,
            kickoff_time=datetime(2025, 8, 16, 14, 0, tzinfo=dt_timezone.utc),
        )
        Fixture.objects.create(
            id=2,
            event=2,
            team_h_id=2,
            team_a_id=1,
            kickoff_time=datetime(2026, 1, 3, 14, 0, tzinfo=dt_timezone.utc),
        )
        self.assertEqual(_stored_season_start_year(), 2025)


class SeasonPurgeTests(TestCase):
    def setUp(self) -> None:
        Team.objects.create(id=1, code=3, name="Arsenal")
        Team.objects.create(id=2, code=7, name="Villa")
        self.athlete = Athlete.objects.create(id=100, code=5001, web_name="Saka", team_id=1)
        Fixture.objects.create(
            id=1,
            event=1,
            team_h_id=1,
            team_a_id=2,
            kickoff_time=datetime(2025, 8, 16, 14, 0, tzinfo=dt_timezone.utc),
        )
        AthleteStat.objects.create(athlete=self.athlete, game_week=21, total_points=9)
        ElementSummary.objects.create(athlete=self.athlete, fixtures=[], history=[])
        EventStatus.objects.create(event=21, status="r")
        PriceSnapshot.objects.create(
            athlete=self.athlete,
            snapshot_time=datetime(2026, 1, 16, 2, 0, tzinfo=dt_timezone.utc),
            cost=100,
            transfers_in_total=0,
            transfers_out_total=0,
        )
        AthletePrediction.objects.create(
            athlete=self.athlete, game_week=21, predicted_points=Decimal("5.00")
        )
        manager = Top100Manager.objects.create(
            entry_id=1,
            game_week=15,
            player_name="Someone",
            entry_name="Some Team",
            rank=1,
        )
        Top100Pick.objects.create(
            manager=manager, athlete=self.athlete, game_week=15, position=1
        )
        Top100Summary.objects.create(game_week=15)

    def test_new_season_purges_gameweek_scoped_rows(self) -> None:
        purged = _handle_season_rollover([{"id": 1, "deadline_time": "2026-08-15T17:30:00Z"}])

        self.assertTrue(purged)
        self.assertEqual(AthleteStat.objects.count(), 0)
        self.assertEqual(ElementSummary.objects.count(), 0)
        self.assertEqual(EventStatus.objects.count(), 0)
        self.assertEqual(PriceSnapshot.objects.count(), 0)
        self.assertEqual(AthletePrediction.objects.count(), 0)
        self.assertEqual(Top100Pick.objects.count(), 0)
        self.assertEqual(Top100Summary.objects.count(), 0)
        self.assertEqual(Top100Manager.objects.count(), 0)

        # Bootstrap-derived rows are rewritten by the sync functions, not purged,
        # so foreign keys stay valid through the rollover.
        self.assertEqual(Team.objects.count(), 2)
        self.assertEqual(Athlete.objects.count(), 1)
        self.assertEqual(Fixture.objects.count(), 1)

    def test_same_season_refresh_keeps_everything(self) -> None:
        purged = _handle_season_rollover([{"id": 1, "deadline_time": "2025-08-15T17:30:00Z"}])

        self.assertFalse(purged)
        self.assertEqual(AthleteStat.objects.count(), 1)
        self.assertEqual(Top100Summary.objects.count(), 1)

    def test_empty_database_is_not_treated_as_a_rollover(self) -> None:
        Fixture.objects.all().delete()

        purged = _handle_season_rollover([{"id": 1, "deadline_time": "2026-08-15T17:30:00Z"}])

        self.assertFalse(purged)
        self.assertEqual(AthleteStat.objects.count(), 1)


class UnplayedGameweekPruneTests(TestCase):
    """A gameweek that has not kicked off cannot hold real statistics.

    This guard is what repairs a database that rolled over before the season
    check existed, so it has to be idempotent and safe mid-season.
    """

    def setUp(self) -> None:
        Team.objects.create(id=1, code=3, name="Arsenal")
        self.athlete = Athlete.objects.create(id=100, code=5001, web_name="Saka", team_id=1)
        for game_week in (1, 2, 3, 7, 21):
            AthleteStat.objects.create(
                athlete=self.athlete, game_week=game_week, total_points=game_week
            )

    @staticmethod
    def events(finished_through: int, current: int | None = None) -> list[dict]:
        payload = []
        for event_id in range(1, 39):
            payload.append(
                {
                    "id": event_id,
                    "deadline_time": f"2026-08-{min(28, 14 + event_id):02d}T17:30:00Z",
                    "finished": event_id <= finished_through,
                    "is_current": event_id == current,
                }
            )
        return payload

    def test_stats_above_the_latest_played_gameweek_are_removed(self) -> None:
        with self.assertLogs("etl.services.etl_runner", level="WARNING"):
            removed = _prune_unplayed_gameweeks(self.events(finished_through=3, current=3))

        self.assertEqual(removed, 2)
        self.assertEqual(
            sorted(AthleteStat.objects.values_list("game_week", flat=True)), [1, 2, 3]
        )

    def test_prune_is_idempotent(self) -> None:
        events = self.events(finished_through=3, current=3)
        _prune_unplayed_gameweeks(events)

        self.assertEqual(_prune_unplayed_gameweeks(events), 0)
        self.assertEqual(AthleteStat.objects.count(), 3)

    def test_in_progress_gameweek_keeps_its_live_stats(self) -> None:
        AthleteStat.objects.create(athlete=self.athlete, game_week=4, total_points=2)

        _prune_unplayed_gameweeks(self.events(finished_through=3, current=4))

        self.assertIn(4, AthleteStat.objects.values_list("game_week", flat=True))

    def test_stale_top100_snapshots_are_removed(self) -> None:
        manager = Top100Manager.objects.create(
            entry_id=1,
            game_week=15,
            player_name="Someone",
            entry_name="Some Team",
            rank=1,
        )
        Top100Pick.objects.create(
            manager=manager, athlete=self.athlete, game_week=15, position=1
        )
        Top100Summary.objects.create(game_week=15)

        _prune_unplayed_gameweeks(self.events(finished_through=3, current=3))

        self.assertEqual(Top100Summary.objects.count(), 0)
        self.assertEqual(Top100Pick.objects.count(), 0)
        self.assertEqual(Top100Manager.objects.count(), 0)

    def test_preseason_clears_every_gameweek_row(self) -> None:
        _prune_unplayed_gameweeks(self.events(finished_through=0))

        self.assertEqual(AthleteStat.objects.count(), 0)

    def test_latest_played_gameweek(self) -> None:
        self.assertEqual(_latest_played_gameweek(self.events(finished_through=3, current=3)), 3)
        self.assertEqual(_latest_played_gameweek(self.events(finished_through=3, current=4)), 4)
        self.assertEqual(_latest_played_gameweek(self.events(finished_through=0)), 0)
        self.assertIsNone(_latest_played_gameweek([]))
