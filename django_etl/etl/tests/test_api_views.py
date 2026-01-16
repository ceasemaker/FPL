from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase

from ..models import Athlete, AthletePrediction, AthleteStat, Fixture, Team, RawEndpointSnapshot


class ApiViewTests(TestCase):
    def setUp(self) -> None:
        self.teams = []
        for idx in range(1, 6):
            self.teams.append(
                Team.objects.create(id=idx, code=100 + idx, name=f"Team {idx}", short_name=f"T{idx}")
            )

        # Create athletes covering required positions with max 3 per team
        players = [
            (1, "GK1", 1, self.teams[0]),
            (2, "DEF1", 2, self.teams[0]),
            (3, "MID1", 3, self.teams[0]),
            (4, "GK2", 1, self.teams[1]),
            (5, "DEF2", 2, self.teams[1]),
            (6, "MID2", 3, self.teams[1]),
            (7, "DEF3", 2, self.teams[2]),
            (8, "MID3", 3, self.teams[2]),
            (9, "FWD1", 4, self.teams[2]),
            (10, "DEF4", 2, self.teams[3]),
            (11, "MID4", 3, self.teams[3]),
            (12, "FWD2", 4, self.teams[3]),
            (13, "DEF5", 2, self.teams[4]),
            (14, "MID5", 3, self.teams[4]),
            (15, "FWD3", 4, self.teams[4]),
        ]

        self.athletes = []
        for player_id, name, position, team in players:
            athlete = Athlete.objects.create(
                id=player_id,
                code=1000 + player_id,
                first_name=name,
                second_name="Test",
                web_name=name,
                now_cost=60,
                element_type=position,
                team=team,
                team_code=team.code,
                form=Decimal("5.0"),
                total_points=50,
            )
            self.athletes.append(athlete)

        # Set current gameweek to 1
        AthleteStat.objects.create(athlete=self.athletes[0], game_week=1, minutes=90)

        # Predictions for GW2
        for athlete in self.athletes:
            AthletePrediction.objects.create(
                athlete=athlete,
                game_week=2,
                predicted_points=Decimal("5.5"),
            )

        RawEndpointSnapshot.objects.create(
            endpoint="bootstrap-static",
            payload={
                "elements": [
                    {
                        "id": athlete.id,
                        "transfers_in_event": athlete.id * 2,
                        "transfers_out_event": athlete.id,
                        "selected_by_percent": str(athlete.id / 100),
                    }
                    for athlete in self.athletes
                ]
            },
        )
        RawEndpointSnapshot.objects.create(
            endpoint="bootstrap-static",
            payload={
                "elements": [
                    {
                        "id": athlete.id,
                        "transfers_in_event": athlete.id * 3,
                        "transfers_out_event": athlete.id * 2,
                        "selected_by_percent": str(athlete.id / 90),
                    }
                    for athlete in self.athletes
                ]
            },
        )

        Fixture.objects.create(
            id=1,
            event=2,
            team_h=self.teams[0],
            team_a=self.teams[1],
            team_h_difficulty=2,
            team_a_difficulty=3,
        )

    def test_optimize_team_returns_unique_squad(self) -> None:
        response = self.client.get("/api/optimize-team/?budget=1000&horizon=1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        player_ids = [player["id"] for player in payload["players"]]
        self.assertEqual(len(player_ids), 15)
        self.assertEqual(len(set(player_ids)), 15)
        self.assertEqual(payload["mode"], "open_pool")

    def test_fixtures_ticker_response_shape(self) -> None:
        response = self.client.get("/api/fixtures/ticker/?horizon=3")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["start_gameweek"], 2)
        self.assertEqual(payload["end_gameweek"], 4)
        self.assertEqual(payload["horizon"], 3)
        self.assertEqual(len(payload["teams"]), 5)

    def test_price_change_predictor(self) -> None:
        athlete_rise = self.athletes[0]
        athlete_fall = self.athletes[1]
        athlete_rise.transfers_in_event = 100
        athlete_rise.transfers_out_event = 10
        athlete_rise.save(update_fields=["transfers_in_event", "transfers_out_event"])
        athlete_fall.transfers_in_event = 5
        athlete_fall.transfers_out_event = 50
        athlete_fall.save(update_fields=["transfers_in_event", "transfers_out_event"])

        response = self.client.get("/api/price-predictor/?limit=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["risers"])
        self.assertTrue(payload["fallers"])
        self.assertIn("transfer_delta", payload["risers"][0])

    def test_price_predictor_history(self) -> None:
        response = self.client.get("/api/price-predictor/history/?top=3&limit=2")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["snapshot_count"], 2)
        self.assertTrue(payload["series"])

    def test_price_predictor_history_ownership(self) -> None:
        response = self.client.get("/api/price-predictor/history/?top=3&limit=2&metric=ownership")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["snapshot_count"], 2)
        self.assertTrue(payload["series"])

    @patch("etl.api_views.requests.get")
    def test_image_proxy_allows_whitelisted_hosts(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"image"
        mock_response.headers = {"Content-Type": "image/png"}
        mock_get.return_value = mock_response

        response = self.client.get(
            "/api/image-proxy/",
            {"url": "https://resources.premierleague.com/test.png"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_image_proxy_blocks_unknown_hosts(self) -> None:
        response = self.client.get(
            "/api/image-proxy/",
            {"url": "https://example.com/test.png"},
        )
        self.assertEqual(response.status_code, 400)
