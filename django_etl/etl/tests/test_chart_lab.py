from __future__ import annotations

import math
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase

from ..models import Athlete, AthleteStat, Fixture, Team
from ..services.chart_lab import expected_clean_sheet_chance


class ChartLabTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.home = Team.objects.create(id=1, code=101, name="Home", short_name="HOM")
        self.away = Team.objects.create(id=2, code=102, name="Away", short_name="AWY")
        self.defender = Athlete.objects.create(
            id=10, code=1010, first_name="Dan", second_name="Def", web_name="Def",
            now_cost=55, element_type=2, team=self.home, team_code=101,
            selected_by_percent=Decimal("12.5"),
        )
        self.striker = Athlete.objects.create(
            id=11, code=1011, first_name="Sam", second_name="Striker", web_name="Striker",
            now_cost=90, element_type=4, team=self.away, team_code=102,
        )
        Fixture.objects.create(id=1, event=1, team_h=self.home, team_a=self.away)
        Fixture.objects.create(id=2, event=2, team_h=self.away, team_a=self.home)
        AthleteStat.objects.create(
            athlete=self.defender, game_week=1, minutes=90, total_points=6,
            clean_sheets=1, expected_goals_conceded=Decimal("0.5"),
            expected_assists=Decimal("0.2"), value=55,
        )
        AthleteStat.objects.create(
            athlete=self.defender, game_week=2, minutes=90, total_points=2,
            expected_goals_conceded=Decimal("1.5"), expected_assists=Decimal("0.1"), value=56,
        )
        AthleteStat.objects.create(
            athlete=self.striker, game_week=1, minutes=80, total_points=9, goals_scored=1,
            expected_goals=Decimal("0.9"), expected_assists=Decimal("0.3"), value=90,
        )

    def test_players_endpoint_returns_season_totals_and_catalog(self) -> None:
        response = self.client.get("/api/chart-lab/players/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["latest_gameweek"], 2)
        keys = {metric["key"] for metric in payload["metrics"]}
        self.assertTrue({"xg", "xa", "xcs", "mins", "price", "own"} <= keys)

        defender = next(p for p in payload["players"] if p["id"] == self.defender.id)
        self.assertEqual(defender["position"], "DEF")
        self.assertEqual(defender["values"]["pts"], 8)
        self.assertEqual(defender["values"]["mins"], 180)
        self.assertAlmostEqual(defender["values"]["xa"], 0.3)
        self.assertAlmostEqual(defender["values"]["xcs"], round(math.exp(-0.5) + math.exp(-1.5), 3))
        self.assertEqual(defender["values"]["price"], 5.5)
        self.assertEqual(defender["values"]["own"], 12.5)

    def test_series_endpoint_returns_gameweek_rows(self) -> None:
        response = self.client.get(f"/api/chart-lab/series/?ids={self.defender.id},{self.striker.id}")

        self.assertEqual(response.status_code, 200)
        series = {s["id"]: s for s in response.json()["series"]}
        defender_points = series[self.defender.id]["points"]
        self.assertEqual([p["gameweek"] for p in defender_points], [1, 2])
        self.assertEqual(defender_points[1]["values"]["price"], 5.6)
        self.assertIsNone(defender_points[0]["values"]["own"])
        self.assertAlmostEqual(series[self.striker.id]["points"][0]["values"]["xg"], 0.9)

    def test_series_endpoint_rejects_bad_ids(self) -> None:
        self.assertEqual(self.client.get("/api/chart-lab/series/").status_code, 400)
        self.assertEqual(self.client.get("/api/chart-lab/series/?ids=abc").status_code, 400)

    def test_expected_clean_sheet_chance(self) -> None:
        self.assertAlmostEqual(expected_clean_sheet_chance(90, 1.0, 1), math.exp(-1.0))
        # Double gameweek: 2 matches, xGC split evenly.
        self.assertAlmostEqual(expected_clean_sheet_chance(180, 2.0, 2), 2 * math.exp(-1.0))
        self.assertEqual(expected_clean_sheet_chance(45, 0.1, 1), 0.0)
