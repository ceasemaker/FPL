import unittest

import numpy as np

from run_structural_backtest import (
    _apply_platt,
    _fit_platt,
    expected_floor_poisson,
    infer_goal_lambdas,
    poisson_match_probabilities,
    total_goals_lambda,
)


class StructuralBacktestTests(unittest.TestCase):
    def test_total_lambda_reproduces_over_probability(self):
        goal_lambda = total_goals_lambda(0.57)
        probability = 1.0 - np.exp(-goal_lambda) * (
            1.0 + goal_lambda + goal_lambda**2 / 2.0
        )
        self.assertAlmostEqual(probability, 0.57, places=8)

    def test_goal_lambdas_fit_market_and_total(self):
        home, draw, away, over = 0.55, 0.25, 0.20, 0.58
        home_lambda, away_lambda = infer_goal_lambdas(home, draw, away, over)
        fitted = poisson_match_probabilities(home_lambda, away_lambda)
        self.assertGreater(home_lambda, away_lambda)
        self.assertAlmostEqual(home_lambda + away_lambda, total_goals_lambda(over), places=8)
        self.assertLess(np.mean(np.abs(np.asarray(fitted) - [home, draw, away])), 0.035)

    def test_no_goal_expectation_has_no_concession_deduction(self):
        result = expected_floor_poisson(np.array([0.0]), 2)
        self.assertAlmostEqual(float(result[0]), 0.0, places=12)

    def test_concession_deduction_increases_with_goal_rate(self):
        result = expected_floor_poisson(np.array([0.5, 1.5, 3.0]), 2)
        self.assertTrue(np.all(np.diff(result) > 0))


    def test_platt_identity_when_already_calibrated(self):
        rng = np.random.default_rng(7)
        probabilities = rng.uniform(0.05, 0.95, size=5000)
        outcomes = (rng.random(5000) < probabilities).astype(float)
        intercept, slope = _fit_platt(probabilities, outcomes)
        calibrated = _apply_platt(probabilities, intercept, slope)
        self.assertLess(float(np.mean(np.abs(calibrated - probabilities))), 0.05)

    def test_platt_corrects_systematic_overconfidence(self):
        rng = np.random.default_rng(11)
        true_probabilities = rng.uniform(0.02, 0.30, size=8000)
        overstated = np.clip(true_probabilities * 2.0, 0.0, 0.99)
        outcomes = (rng.random(8000) < true_probabilities).astype(float)
        intercept, slope = _fit_platt(overstated, outcomes)
        calibrated = _apply_platt(overstated, intercept, slope)
        self.assertAlmostEqual(float(calibrated.mean()), float(outcomes.mean()), delta=0.02)
        raw_brier = float(np.mean((overstated - outcomes) ** 2))
        calibrated_brier = float(np.mean((calibrated - outcomes) ** 2))
        self.assertLess(calibrated_brier, raw_brier)


if __name__ == "__main__":
    unittest.main()
