from decimal import Decimal

from django.test import TestCase

from etl.models import Athlete, AthleteStat, ElementSummary, Team
from etl.services.player_gameweeks import _percentile


class PlayerGameweeksTests(TestCase):
    def setUp(self):
        self.team = Team.objects.create(id=1, code=1, name="A", short_name="AAA")
        self.opp = Team.objects.create(id=2, code=2, name="B", short_name="BBB")
        self.players = []
        for i, pts in enumerate(((2, 5), (4, 1), (8, 9)), start=1):
            a = Athlete.objects.create(
                id=i, code=100 + i, first_name="F", second_name="S", web_name=f"P{i}",
                element_type=3, team=self.team,
            )
            self.players.append(a)
            for gw, p in zip((1, 2), pts):
                AthleteStat.objects.create(
                    athlete=a, game_week=gw, total_points=p, minutes=90,
                    expected_goals=Decimal("0.5"), selected=1000 * i, value=50 + i,
                )
        # A low-minutes player must be excluded from the cohort but still get a log.
        self.sub = Athlete.objects.create(
            id=9, code=109, first_name="F", second_name="S", web_name="Sub", element_type=3, team=self.team
        )
        AthleteStat.objects.create(athlete=self.sub, game_week=1, total_points=1, minutes=10)
        ElementSummary.objects.create(
            athlete=self.players[2],
            history=[
                {"round": 1, "opponent_team": 2, "was_home": True, "team_h_score": 2, "team_a_score": 0},
                {"round": 2, "opponent_team": 2, "was_home": False, "team_h_score": 1, "team_a_score": 1},
            ],
        )

    def test_game_log_and_opponents(self):
        res = self.client.get("/api/players/3/gameweeks/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["data_through_gameweek"], 2)
        self.assertEqual([g["game_week"] for g in body["gameweeks"]], [1, 2])
        gw1 = body["gameweeks"][0]
        self.assertEqual(gw1["total_points"], 8)
        self.assertEqual(gw1["expected_goals"], 0.5)
        self.assertEqual(gw1["selected"], 3000)
        self.assertEqual(gw1["fixtures"], [{"opponent": "BBB", "was_home": True, "team_h_score": 2, "team_a_score": 0}])

    def test_percentiles_use_same_position_cohort_with_minutes_floor(self):
        body = self.client.get("/api/players/3/gameweeks/").json()["percentiles"]
        self.assertEqual(body["position"], "MID")
        self.assertEqual(body["cohort_size"], 3)  # Sub excluded (10 minutes)
        self.assertTrue(body["player_in_cohort"])
        pts = next(s for s in body["stats"] if s["key"] == "total_points")
        self.assertEqual(pts["value"], 17)
        self.assertEqual(pts["percentile"], 83)  # best of 3, ties split
        low = self.client.get("/api/players/2/gameweeks/").json()["percentiles"]  # 5 pts, lowest
        self.assertEqual(next(s for s in low["stats"] if s["key"] == "total_points")["percentile"], 17)
        self.assertIn("expected_goals_per_90", {s["key"] for s in body["stats"]})

    def test_low_minutes_player_flagged_out_of_cohort(self):
        body = self.client.get("/api/players/9/gameweeks/").json()
        self.assertFalse(body["percentiles"]["player_in_cohort"])
        self.assertEqual(len(body["gameweeks"]), 1)

    def test_unknown_player_404(self):
        self.assertEqual(self.client.get("/api/players/999/gameweeks/").status_code, 404)

    def test_percentile_direction(self):
        vals = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(_percentile(vals, 4.0, True), 88)
        self.assertEqual(_percentile(vals, 4.0, False), 12)
        self.assertEqual(_percentile([], 1.0, True), 0)
