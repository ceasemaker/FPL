from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase

from ..models import Athlete, FixtureHistory, GameweekHistory, PlayerSeasonStat, Team
from ..services.squad_changes import defensive_turnover, leap_persistence, player_leaps


def week(season, gameweek, code, team, position, minutes, name=None):
    return GameweekHistory.objects.create(
        season=season, gameweek=gameweek, code=code, element=code, web_name=name or f"P{code}",
        team_code=team, position=position, minutes=minutes,
    )


def fixture(season, fixture_id, home, away, home_score=None, away_score=None):
    return FixtureHistory.objects.create(
        season=season, fixture_id=fixture_id, gameweek=1, team_h_code=home, team_a_code=away,
        team_h_score=home_score, team_a_score=away_score,
    )


class DefensiveTurnoverTests(TestCase):
    def setUp(self):
        cache.clear()
        Team.objects.create(id=1, code=10, name="Ten", short_name="TEN")
        Team.objects.create(id=2, code=20, name="Twenty", short_name="TWE")
        Team.objects.create(id=3, code=30, name="Thirty", short_name="THI")
        fixture(2023, 1, 10, 20, 2, 1)
        fixture(2023, 2, 20, 10, 0, 0)
        fixture(2024, 1, 10, 30, 1, 3)
        fixture(2024, 2, 20, 10)  # not played yet
        # Last season at club 10: a defender who moves to club 20, a keeper who
        # stays, a defender who leaves the league, and a midfielder (ignored).
        week(2023, 1, 1, 10, 2, 900, "Mover")
        week(2023, 1, 2, 10, 1, 1800, "Keeper")
        week(2023, 1, 3, 10, 2, 450, "Gone")
        week(2023, 1, 4, 10, 3, 900, "Mid")
        week(2024, 1, 1, 20, 2, 90, "Mover")
        week(2024, 1, 2, 10, 1, 90)
        week(2024, 1, 4, 10, 3, 90)
        week(2025, 1, 2, 10, 1, 90)  # makes 2024 a completed season

    def test_counts_last_seasons_defensive_minutes_that_left(self):
        rows = {r["code"]: r for r in defensive_turnover(2024)}
        ten = rows[10]
        self.assertEqual(ten["defensiveMinutes"], 3150)
        self.assertEqual(ten["minutesLost"], 1350)
        self.assertAlmostEqual(ten["share"], 0.429, places=3)
        self.assertEqual([(p["name"], p["minutes"], p["to"]) for p in ten["leavers"]],
                         [("Mover", 900, "Twenty"), ("Gone", 450, "Left the Premier League")])
        # Conceded per finished match: 1 and 0 last season; 3 this season.
        self.assertEqual(ten["concededBefore"], 0.5)
        self.assertEqual(ten["concededNow"], 3.0)
        self.assertEqual(ten["matchesNow"], 1)

    def test_promoted_club_has_nothing_to_lose(self):
        rows = {r["code"]: r for r in defensive_turnover(2024)}
        self.assertTrue(rows[30]["promoted"])
        self.assertIsNone(rows[30]["minutesLost"])

    def test_current_season_uses_fpl_squads_not_appearances(self):
        # In the season in progress a player still on the books counts as
        # staying even if he has no gameweek rows yet.
        fixture(2025, 1, 10, 20)
        fixture(2024, 3, 10, 20, 0, 0)
        week(2024, 2, 5, 10, 2, 900, "Injured")
        Athlete.objects.create(id=5, code=5, first_name="I", second_name="Njured", web_name="Injured",
                               now_cost=45, element_type=2, team_id=1, team_code=10)
        Athlete.objects.create(id=2, code=2, first_name="K", second_name="Eeper", web_name="Keeper",
                               now_cost=45, element_type=1, team_id=1, team_code=10)
        rows = {r["code"]: r for r in defensive_turnover(2025)}
        self.assertEqual(rows[10]["leavers"], [])
        self.assertEqual(rows[20]["leavers"], [{"name": "Mover", "position": "DEF", "minutes": 90, "to": "Left the Premier League"}])


def sheet(season, opta_id, team_id, minutes, lost, shots, created, xg=0.0, xa=0.0, position="Midfielder"):
    return PlayerSeasonStat.objects.create(
        source="sdp", competition_id=8, season=season, opta_player_id=str(opta_id), name=f"P{opta_id}",
        position=position, season_team_id=str(team_id), season_team_name=f"Club {team_id}",
        stats={"timePlayed": minutes, "totalLossesOfPossession": lost, "totalShots": shots,
               "keyPassesAttemptAssists": created, "expectedGoals": xg, "expectedAssists": xa},
    )


class LeapTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_only_players_at_the_same_club_both_seasons(self):
        sheet(2023, 1, 9, 1800, 100, 20, 20, xg=2, xa=2)
        sheet(2024, 1, 9, 1800, 140, 40, 40, xg=4, xa=4)
        sheet(2023, 2, 9, 1800, 100, 20, 20)
        sheet(2024, 2, 8, 1800, 100, 20, 20)  # moved club
        rows = {r["id"]: r for r in player_leaps(2024)}
        self.assertEqual(set(rows), {"1"})
        self.assertAlmostEqual(rows["1"]["before"]["xgi90"], 0.2)
        self.assertAlmostEqual(rows["1"]["now"]["xgi90"], 0.4)
        self.assertAlmostEqual(rows["1"]["now"]["created90"], 2.0)

    def test_persistence_measures_how_much_of_a_rise_survives(self):
        # Created per 90: 1.0 -> 2.0 -> 1.5, so half the rise is kept.
        sheet(2022, 1, 9, 1800, 100, 20, 20)
        sheet(2023, 1, 9, 1800, 100, 20, 40)
        sheet(2024, 1, 9, 1800, 100, 20, 30)
        out = leap_persistence([2022, 2023, 2024])
        self.assertEqual(out["seasons"], ["2023/24"])
        self.assertEqual(out["metrics"]["created90"], {"risers": 1, "medianKept": 0.5, "stillAbove": 1.0})
