import math
from unittest.mock import patch

from django.test import SimpleTestCase

from etl.services.player_analysis import (
    build_player_analysis,
    calculate_fixture_snapshot,
    calculate_snapshot,
    render_player_report_html,
    render_player_report_tex,
)


def _snapshot():
    rows = []
    for gameweek, market in ((3, True), (4, False)):
        for player_id, name, position, xg, xa, ownership, price in (
            (1, "Forward", "FWD", 1.2, 0.2, 0.70, 12.0),
            (2, "Creator", "MID", 0.4, 0.8, 0.20, 8.0),
        ):
            rows.append({
                "row_key": f"{player_id}|{gameweek}",
                "player_label": f"{name} - TST ({player_id})",
                "player_id": player_id,
                "player": name,
                "position": position,
                "team": "TST",
                "gameweek": gameweek,
                "opponent": "OPP",
                "venue": "H",
                "fdr": 2,
                "opponent_fdr": 4,
                "price_m": price,
                "ownership": ownership,
                "status": "a",
                "availability": 1.0,
                "season_minutes": 180,
                "starts": 2,
                "team_matches": 2,
                "total_points": 10,
                "form": 5.0,
                "points_per_game": 5.0,
                "expected_goals": xg,
                "expected_assists": xa,
                "bonus": 2,
                "saves": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "defensive_contribution": 8,
                "penalties_order": None,
                "set_piece_order": None,
                "team_lambda_market": 2.5 if market else None,
                "opponent_lambda_market": 0.8 if market else None,
                "market_basis": "1X2 Poisson fit" if market else "FDR proxy",
                "days_previous_europe": None,
                "days_next_europe": None,
                "news": "",
                "source_url": "https://example.test",
            })
    return {
        "snapshot_date": "2026-09-04",
        "generated_at": "2026-09-04T12:00:00+00:00",
        "players": [
            {"player_label": "Forward - TST (1)", "player_id": 1},
            {"player_label": "Creator - TST (2)", "player_id": 2},
        ],
        "rows": rows,
    }


class PlayerAnalysisServiceTests(SimpleTestCase):
    def test_double_gameweek_scores_each_match_before_aggregating(self):
        snapshot = _snapshot()
        first_match = [{**row, "fixture_id": 31} for row in snapshot["rows"] if row["gameweek"] == 3]
        second_match = [{**row, "fixture_id": 32, "opponent": "SECOND", "venue": "A", "team_lambda_market": None, "opponent_lambda_market": None} for row in first_match]
        snapshot["rows"] = first_match + second_match + [row for row in snapshot["rows"] if row["gameweek"] == 4]
        separate = calculate_fixture_snapshot({"rows": first_match}) + calculate_fixture_snapshot({"rows": second_match})
        result = build_player_analysis([1, 2], 3, 2, snapshot)
        for player in result["players"]:
            expected = sum(row["expected_points"] for row in separate if row["player_id"] == player["id"])
            self.assertAlmostEqual(player["focus"]["expected_points"], expected, places=4)
            self.assertEqual(player["focus"]["fixture_count"], 2)
            self.assertEqual(player["focus"]["data_basis"], "mixed")
            self.assertEqual(len(player["fixtures"]), 2)
            self.assertAlmostEqual(player["weighted_horizon_xp"], expected + 0.9 * player["fixtures"][1]["expected_points"], places=3)
            self.assertAlmostEqual(player["captain_total_xp"], 2 * expected, places=3)
        self.assertEqual(len({row["id"] for row in result["top_players"]}), len(result["top_players"]))
        self.assertIn("SECOND", render_player_report_html(result))
        self.assertIn("SECOND", render_player_report_tex(result))

    def test_weekly_return_distribution_includes_one_return_in_each_match(self):
        fixture = self._single_player()
        with patch("etl.services.player_analysis.calculate_fixture_snapshot", return_value=[
            {**fixture, "fixture_id": 1, "attacking_blank_probability": 0.5, "return_probability": 0.5, "multiple_return_probability": 0.1},
            {**fixture, "fixture_id": 2, "attacking_blank_probability": 0.4, "return_probability": 0.6, "multiple_return_probability": 0.2},
        ]):
            week = calculate_snapshot({})[0]
        self.assertEqual(week["attacking_blank_probability"], 0.2)
        self.assertEqual(week["return_probability"], 0.8)
        # P(0)=.5*.4; P(1)=.4*.4 + .5*.4; P(2+)=.44
        self.assertEqual(week["multiple_return_probability"], 0.44)

    def test_duplicate_fixture_rows_are_rejected(self):
        row = _snapshot()["rows"][0]
        with self.assertRaisesRegex(ValueError, "Duplicate player fixture"):
            calculate_snapshot({"rows": [row, row]})

    def _single_player(self, **changes):
        row = {**_snapshot()["rows"][0], "starts": 2, "team_matches": 2, **changes}
        return calculate_snapshot({"rows": [row]}, {"start_prior_strength": 0.0})[0]

    def test_goalkeeper_saves_and_conceded_use_completed_groups(self):
        row = self._single_player(position="GKP", saves=12, expected_goals=0.1, opponent_lambda_market=2.0)
        # Independently enumerate the discrete score for every plausible count.
        expected_saves = sum((n // 3) * math.exp(-6) * 6 ** n / math.factorial(n) for n in range(70))
        expected_conceded = sum((n // 2) * math.exp(-2) * 2 ** n / math.factorial(n) for n in range(70))
        self.assertAlmostEqual(row["components"]["saves"], expected_saves, places=4)
        self.assertAlmostEqual(row["components"]["goals_conceded"], -expected_conceded, places=4)
        self.assertAlmostEqual(row["components"]["goals"], 10 * row["goal_lambda"])

    def test_defensive_contribution_is_threshold_reward(self):
        for position, threshold in (("DEF", 10), ("MID", 12), ("FWD", 12)):
            with self.subTest(position=position):
                row = self._single_player(position=position, defensive_contribution=16)
                rate = row["dc90_shrunk"]
                expected = 2 * sum(math.exp(-rate) * rate ** n / math.factorial(n) for n in range(threshold, 70))
                self.assertAlmostEqual(row["components"]["defensive_contribution"], expected, places=4)

    def test_unavailable_player_scores_zero(self):
        row = self._single_player(position="GKP", availability=0, saves=12)
        self.assertEqual(row["expected_points"], 0)
        self.assertEqual(row["return_probability"], 0)
        self.assertEqual(row["attacking_blank_probability"], 1)

    def test_blank_gameweek_has_no_appearance_or_clean_sheet_points(self):
        row = self._single_player(position="DEF", opponent="Blank", team_lambda_market=None, opponent_lambda_market=None, fdr=0, opponent_fdr=0)
        self.assertEqual(row["expected_minutes"], 0)
        self.assertEqual(row["expected_points"], 0)
        self.assertTrue(all(value == 0 for value in row["components"].values()))

    def test_partial_availability_scales_nonlinear_rewards(self):
        full = self._single_player(position="GKP", saves=12)
        partial = self._single_player(position="GKP", saves=12, availability=0.25)
        self.assertAlmostEqual(partial["components"]["saves"], full["components"]["saves"] * 0.25, places=3)
        self.assertLessEqual(partial["multiple_return_probability"], partial["return_probability"])
        self.assertLessEqual(partial["return_probability"], 0.25)

    def test_inconsistent_start_counts_cannot_create_negative_sub_probability(self):
        row = self._single_player(starts=4, team_matches=2)
        self.assertEqual(row["p_start"], 1)
        self.assertEqual(row["p_sub"], 0)

    def test_components_are_auditable_and_probabilities_are_coherent(self):
        rows = calculate_snapshot(_snapshot())
        player = next(row for row in rows if row["player_id"] == 1 and row["gameweek"] == 3)
        self.assertAlmostEqual(player["return_probability"] + player["attacking_blank_probability"], 1.0, places=3)
        self.assertAlmostEqual(player["expected_points"], sum(player["components"].values()), places=3)
        self.assertAlmostEqual(player["differential_upside"] + player["omission_risk"], player["expected_points"], places=3)
        self.assertEqual(player["data_basis"], "market")

    def test_builds_comparison_and_weighted_horizon(self):
        result = build_player_analysis([1, 2], gameweek=3, horizon=2, snapshot=_snapshot())
        self.assertEqual(result["meta"]["gameweeks"], [3, 4])
        self.assertEqual(len(result["players"]), 2)
        first = result["players"][0]
        expected = first["fixtures"][0]["expected_points"] + 0.9 * first["fixtures"][1]["expected_points"]
        self.assertAlmostEqual(first["weighted_horizon_xp"], expected, places=3)

    def test_dynamic_reports_include_selected_players(self):
        result = build_player_analysis([1, 2], gameweek=3, horizon=2, snapshot=_snapshot())
        self.assertIn("Player Analysis: Forward vs Creator", render_player_report_tex(result))
        self.assertIn("Dynamic player analysis", render_player_report_html(result))
        self.assertIn("Forward", render_player_report_html(result))


class PlayerAnalysisViewTests(SimpleTestCase):
    @patch("etl.api_views.build_player_analysis")
    def test_analysis_endpoint_validates_and_returns_payload(self, build):
        build.return_value = {"meta": {"focus_gameweek": 3}, "players": []}
        response = self.client.get("/api/decision-dashboard/player-analysis/?player_ids=1,2&gameweek=3&horizon=2")
        self.assertEqual(response.status_code, 200)
        build.assert_called_once_with([1, 2], gameweek=3, horizon=2)

    def test_analysis_endpoint_rejects_more_than_two_players(self):
        response = self.client.get("/api/decision-dashboard/player-analysis/?player_ids=1,2,3")
        self.assertEqual(response.status_code, 400)

    @patch("etl.api_views.render_player_report_tex", return_value="\\documentclass{article}")
    @patch("etl.api_views.build_player_analysis", return_value={"players": [], "meta": {}})
    def test_tex_report_download(self, _build, _render):
        response = self.client.get("/api/decision-dashboard/player-report/?player_ids=1&format=tex")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/x-tex; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])
