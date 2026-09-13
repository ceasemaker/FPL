"""Exercise cached input construction through the serving model, without a DB."""
import importlib.util
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from etl.services.player_analysis import build_player_analysis

_spec = importlib.util.spec_from_file_location(
    "build_workbench_inputs",
    Path(__file__).resolve().parents[3] / "analysis/fpl_decision_backtest/build_workbench_inputs.py",
)
_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder)


class WorkbenchInputTests(SimpleTestCase):
    def test_double_blank_unknown_kickoff_and_actual_completed_matches(self):
        teams = [{"id": i, "name": f"Team {i}", "short_name": f"T{i}"} for i in (1, 2, 3)]
        def fixture(identifier, event, home, away, finished=False, kickoff=None):
            return {"id": identifier, "event": event, "team_h": home, "team_a": away,
                    "finished": finished, "kickoff_time": kickoff,
                    "team_h_difficulty": 2, "team_a_difficulty": 4}
        fixtures = [
            fixture(1, 1, 1, 2, True),
            fixture(2, 2, 1, 3, False),  # Postponed: not a played match.
            fixture(30, 3, 1, 2, kickoff="2026-09-05T12:00:00Z"),
            fixture(31, 3, 3, 1),  # Second match, kickoff still unknown.
            fixture(40, 4, 2, 3),  # Team 1 blank.
            fixture(50, 5, 1, 3),
        ]
        bootstrap = {"teams": teams, "elements": [
            {"id": 10, "team": 1, "element_type": 4, "web_name": "Test", "status": "a", "starts": 1, "minutes": 90, "expected_goals": 0.4, "now_cost": 80},
        ]}
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            for name, data in {
                "fpl-bootstrap-2026-09-04.json": bootstrap,
                "fpl-fixtures-2026-09-04.json": fixtures,
                "premier-league-gw3-gw4-odds-2026-09-04.json": {"fixtures": []},
                "champions-league-schedule-odds-2026-09-04.json": {"fixtures": []},
            }.items():
                (data_dir / name).write_text(json.dumps(data))
            snapshot = _builder.build_inputs("2026-09-04", 3, 3, data_dir)
        self.assertEqual(snapshot["schema_version"], 2)
        self.assertEqual([row["fixture_id"] for row in snapshot["rows"]], [30, 31, None, 50])
        self.assertEqual(len({row["row_key"] for row in snapshot["rows"]}), 4)
        self.assertTrue(all(row["team_matches"] == 1 for row in snapshot["rows"]))
        result = build_player_analysis([10], 3, 3, snapshot)
        player = result["players"][0]
        self.assertEqual([week["fixture_count"] for week in player["fixtures"]], [2, 0, 1])
        self.assertEqual(player["fixtures"][1]["expected_points"], 0)
        self.assertAlmostEqual(player["weighted_horizon_xp"], player["focus"]["expected_points"] + 0.81 * player["fixtures"][2]["expected_points"], places=3)
