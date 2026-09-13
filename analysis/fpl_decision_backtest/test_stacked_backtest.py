import unittest

import numpy as np
import pandas as pd

from run_stacked_backtest import add_realized_3gw, bootstrap_gate


def synthetic_predictions(stacked_noise: float, odds_noise: float) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    rows = []
    for gameweek in range(1, 39):
        for player in range(120):
            actual = float(rng.poisson(3.0))
            rows.append({
                "season": 2025, "gameweek": gameweek, "player_id": player,
                "total_points": actual,
                "realized_3gw": actual * 2.71,
                "stacked_xp": actual + rng.normal(0.0, stacked_noise),
                "odds_xp": actual + rng.normal(0.0, odds_noise),
            })
    return pd.DataFrame(rows)


class StackedBacktestTests(unittest.TestCase):
    def test_gate_accepts_clearly_better_model(self):
        gate = bootstrap_gate(synthetic_predictions(stacked_noise=0.5, odds_noise=2.0))
        self.assertTrue(gate["accepted_for_optimizer"])
        self.assertGreater(gate["mae_gain"], 0)

    def test_gate_rejects_clearly_worse_model(self):
        gate = bootstrap_gate(synthetic_predictions(stacked_noise=2.0, odds_noise=0.5))
        self.assertFalse(gate["accepted_for_optimizer"])

    def test_gate_rejects_indistinguishable_model(self):
        # Identical noise: no significant MAE/correlation gain, so no promotion.
        gate = bootstrap_gate(synthetic_predictions(stacked_noise=1.5, odds_noise=1.5))
        self.assertFalse(gate["accepted_for_optimizer"])

    def test_realized_3gw_weights_future_weeks(self):
        frame = pd.DataFrame({
            "season": [2025] * 3, "player_id": [1] * 3,
            "gameweek": [1, 2, 3], "total_points": [2.0, 10.0, 5.0],
        })
        result = add_realized_3gw(frame)
        self.assertAlmostEqual(result["realized_3gw"].iloc[0], 2.0 + 0.9 * 10.0 + 0.81 * 5.0)
        self.assertTrue(np.isnan(result["realized_3gw"].iloc[1]))
        self.assertTrue(np.isnan(result["realized_3gw"].iloc[2]))


if __name__ == "__main__":
    unittest.main()
