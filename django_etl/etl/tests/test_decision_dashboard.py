from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from etl.services.decision_dashboard import _accepted_forecast_summary, _player_rows, _research_summary


class DecisionDashboardServiceTests(SimpleTestCase):
    def test_player_rows_calculate_value_and_exposure(self):
        rows = _player_rows({
            "horizon": 3,
            "squad": [{
                "id": 1,
                "name": "Example",
                "position": "MID",
                "current_price": 10.0,
                "ownership": 0.7,
                "predictions": {"2": 5.0, "3": 4.0, "4": 3.0},
            }],
        })
        self.assertEqual(rows[0]["role"], "shield")
        self.assertEqual(rows[0]["next_xp"], 5.0)
        self.assertEqual(rows[0]["horizon_xp"], 11.03)
        self.assertEqual(rows[0]["xp_per_m"], 1.1)


class AcceptedForecastSummaryTests(SimpleTestCase):
    def test_none_when_no_stacked_summary(self):
        self.assertIsNone(_accepted_forecast_summary(None))

    def test_summary_extracts_gate_evidence(self):
        summary = _accepted_forecast_summary({
            "authority_gate": {
                "accepted_for_mean_forecast": True,
                "accepted_for_optimizer": False,
                "accepted_for_transfer_horizon": False,
                "mae_gain": 0.036,
                "mae_gain_ci95": [0.026, 0.046],
                "correlation_gain_ci95": [0.009, 0.05],
                "top5_points_diff_ci95": [-0.63, 0.17],
                "horizon_correlation_gain_ci95": [0.002, 0.038],
            },
        })
        self.assertTrue(summary["accepted_for_mean_forecast"])
        self.assertFalse(summary["accepted_for_optimizer"])
        self.assertFalse(summary["accepted_for_transfer_horizon"])
        self.assertEqual(summary["evidence"]["mae_gain_vs_odds_ridge"], 0.036)
        self.assertIn("optimizer remains unchanged", summary["caveat"])

    def test_research_summary_keeps_optimizer_as_prototype(self):
        summary = _research_summary({"authority_gate": {
            "mae_gain": 0.036,
            "top5_points_weekly_diff": -0.22,
        }}, [])
        optimizer = next(layer for layer in summary["layers"] if layer["name"] == "Transfer optimizer")
        self.assertEqual(optimizer["status"], "prototype")
        self.assertEqual(summary["evidence"]["top5_difference"], -0.22)


class DecisionDashboardViewTests(SimpleTestCase):
    def test_manager_id_must_be_numeric(self):
        response = self.client.get("/api/decision-dashboard/?manager_id=nope")
        self.assertEqual(response.status_code, 400)

    @patch("etl.api_views.build_decision_dashboard")
    def test_dashboard_returns_service_payload(self, build_payload):
        build_payload.return_value = {"manager": {"name": "Didier Drogon"}}
        response = self.client.get("/api/decision-dashboard/?manager_id=576154&risk_profile=chase")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["manager"]["name"], "Didier Drogon")
        build_payload.assert_called_once_with(576154, "chase")

    def test_research_report_is_served_inline(self):
        with TemporaryDirectory() as directory:
            base_dir = Path(directory) / "django_etl"
            report = base_dir.parent / "output" / "pdf" / "FPL_RESEARCH_REPORT.pdf"
            report.parent.mkdir(parents=True)
            report.write_bytes(b"%PDF-test")
            with override_settings(BASE_DIR=base_dir):
                response = self.client.get("/api/decision-dashboard/research-report/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "application/pdf")
                self.assertEqual(b"".join(response.streaming_content), b"%PDF-test")
