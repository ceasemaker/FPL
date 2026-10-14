from __future__ import annotations

from decimal import Decimal

from django.core.cache import cache
from unittest.mock import patch

from django.test import TestCase

from ..models import Athlete, AthleteStat, PlayerSeasonStat, Team, TeamSeasonStat
from ..services.stats_explorer import CATALOGUE, LENSES, TEAM_CATALOGUE


class StatsExplorerCatalogueTests(TestCase):
    def test_keys_are_unique_and_lenses_reference_real_stats(self) -> None:
        keys = [stat["key"] for stat in CATALOGUE]
        self.assertEqual(len(keys), len(set(keys)))
        for lens in LENSES.values():
            for column in lens["columns"] + lens.get("keeperColumns", []):
                self.assertIn(column, keys)

    def test_every_stat_declares_how_it_is_computed(self) -> None:
        required = {"count": ["raw"], "rate": ["num", "den"], "diff": ["plus", "minus"], "fpl": ["raw"]}
        for stat in CATALOGUE:
            for field in required[stat["kind"]]:
                self.assertTrue(stat.get(field), f"{stat['key']} lacks {field}")
            self.assertTrue(stat["help"], stat["key"])


class StatsExplorerEndpointTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.city = Team.objects.create(id=11, code=43, name="Man City", short_name="MCI")
        self.villa = Team.objects.create(id=2, code=7, name="Aston Villa", short_name="AVL")
        self.haaland = Athlete.objects.create(
            id=411, code=223094, web_name="Haaland", first_name="Erling", second_name="Haaland",
            element_type=4, team=self.city, team_code=43, now_cost=150, total_points=60,
            selected_by_percent=Decimal("75.0"), minutes=540, status="a",
        )
        self.watkins = Athlete.objects.create(
            id=500, code=178301, web_name="Watkins", first_name="Ollie", second_name="Watkins",
            element_type=4, team=self.villa, team_code=7, now_cost=90, total_points=30,
            minutes=450, status="a",
        )
        for athlete in (self.haaland, self.watkins):
            AthleteStat.objects.create(athlete=athlete, game_week=1, minutes=90)
        PlayerSeasonStat.objects.create(
            source="classic", competition_id=8, season=2026, opta_player_id="223094", athlete=self.haaland,
            name="Erling Haaland", stats={"mins_played": 540.0, "goals": 6.0, "total_scoring_att": 20.0, "red_card": 0},
        )
        PlayerSeasonStat.objects.create(
            source="sdp", competition_id=8, season=2026, opta_player_id="223094", athlete=self.haaland,
            name="Erling Haaland", stats={"expectedGoals": 4.82, "timePlayed": 540.0},
        )
        PlayerSeasonStat.objects.create(
            source="classic", competition_id=5, season=2026, opta_player_id="223094", athlete=self.haaland,
            name="Erling Haaland", stats={"mins_played": 180.0, "goals": 2.0},
        )
        PlayerSeasonStat.objects.create(
            source="classic", competition_id=8, season=2026, opta_player_id="178301", athlete=self.watkins,
            name="Ollie Watkins", stats={"mins_played": 450.0, "goals": 3.0},
        )
        TeamSeasonStat.objects.create(
            competition_id=8, season=2026, opta_team_id="43", team=self.city, name="Manchester City",
            stats={"gamesPlayed": 6, "expectedGoals": 11.78, "unlisted": 1},
        )

    @patch("etl.services.stats_explorer.UCL_CLUB_MIN_PLAYERS", 1)
    def test_payload_splits_competitions_and_flags_ucl_clubs(self) -> None:
        response = self.client.get("/api/stats-explorer/?season=2026")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        players = {p["name"]: p for p in payload["players"]}
        haaland = players["Haaland"]
        self.assertEqual(haaland["pl"]["goals"], 6.0)
        self.assertEqual(haaland["pl"]["expectedGoals"], 4.82)
        self.assertEqual(haaland["ucl"]["goals"], 2.0)
        self.assertNotIn("red_card", haaland["pl"])  # only catalogue keys are shipped
        self.assertEqual(haaland["fpl"]["fpl_price"], 15.0)
        self.assertIsNone(players["Watkins"]["ucl"])
        self.assertEqual(payload["uclTeamIds"], [self.city.id])
        team = payload["teams"][0]
        self.assertTrue(team["inUcl"])
        self.assertEqual(set(team["stats"]), {item["key"] for item in TEAM_CATALOGUE})

    def test_one_player_with_ucl_minutes_does_not_make_a_ucl_club(self) -> None:
        payload = self.client.get("/api/stats-explorer/?season=2026").json()

        self.assertEqual(payload["uclTeamIds"], [])
        self.assertIsNotNone(next(p for p in payload["players"] if p["name"] == "Haaland")["ucl"])

    def test_bad_season_is_rejected(self) -> None:
        self.assertEqual(self.client.get("/api/stats-explorer/?season=abc").status_code, 400)
