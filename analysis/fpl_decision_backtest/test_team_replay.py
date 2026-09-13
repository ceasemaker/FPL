import unittest

import pandas as pd

from run_team_replay import (
    best_lineup,
    frozen_horizon_lookups,
    normalized_human_points,
    realized_normal_points,
    squad_is_legal,
)


class TeamReplayTests(unittest.TestCase):
    def setUp(self):
        positions = (["Goalkeeper"] * 2 + ["Defender"] * 5 + ["Midfielder"] * 5 + ["Forward"] * 3)
        self.lookup = {
            index: {
                "player_id": index,
                "position": position,
                "team": f"Club{index // 2}",
                "predicted_points": float(index),
                "total_points": 1.0,
                "actual_minutes": 90,
            }
            for index, position in enumerate(positions, 1)
        }

    def test_valid_fpl_squad(self):
        self.assertTrue(squad_is_legal(range(1, 16), self.lookup))

    def test_lineup_has_eleven_and_captain_is_doubled(self):
        lineup, captain, score = best_lineup(range(1, 16), self.lookup)
        self.assertEqual(len(lineup), 11)
        self.assertIn(captain, lineup)
        self.assertEqual(score, sum(self.lookup[player]["predicted_points"] for player in lineup) + self.lookup[captain]["predicted_points"])

    def test_human_score_uses_normal_captain_even_on_bench_boost(self):
        rows = []
        for position, player in enumerate(range(1, 16), 1):
            rows.append({
                "element": player,
                "position_selected": position,
                "is_captain": player == 10,
                "is_vice_captain": player == 11,
                "multiplier": 1,
                "active_chip": "Bench Boost",
            })
        self.assertEqual(normalized_human_points(pd.DataFrame(rows), self.lookup), 12.0)

    def test_frozen_horizon_projects_blank_as_zero(self):
        lookups = frozen_horizon_lookups(
            self.lookup,
            {(f"club{index // 2}", 10): 1.0 for index in range(1, 16)},
            10,
        )
        self.assertEqual(lookups[1][1]["predicted_points"], 0.0)

    def test_outfield_autosub_preserves_a_legal_formation(self):
        starters = [1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15]
        self.lookup[3]["actual_minutes"] = 0
        self.lookup[3]["total_points"] = 0.0
        self.lookup[6]["total_points"] = 5.0
        points = realized_normal_points(
            range(1, 16), starters, captain=15, vice_captain=14,
            bench_order=[2, 6, 7, 12], lookup=self.lookup,
        )
        self.assertEqual(points, 16.0)


if __name__ == "__main__":
    unittest.main()
