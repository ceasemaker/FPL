from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from ..services.fixture_market import (
    adjustment_for_context,
    calibrate_points,
    calibrate_probability,
    context_from_odds,
    poisson_total_goals_from_over_25,
    remove_vig,
)


class FixtureMarketTests(SimpleTestCase):
    def test_remove_vig_probabilities_sum_to_one(self) -> None:
        probabilities = remove_vig(Decimal("1.80"), Decimal("3.60"), Decimal("4.50"))

        self.assertIsNotNone(probabilities)
        self.assertAlmostEqual(sum(probabilities or ()), 1.0, places=10)
        self.assertGreater((probabilities or (0,))[0], 0.5)

    def test_poisson_inversion_recreates_over_probability(self) -> None:
        target = 0.55
        mean = poisson_total_goals_from_over_25(target)
        calculated = 1 - __import__("math").exp(-mean) * (1 + mean + mean * mean / 2)

        self.assertAlmostEqual(calculated, target, places=6)

    def test_position_specific_adjustments_are_bounded(self) -> None:
        odds = SimpleNamespace(
            home_odds=Decimal("1.55"),
            draw_odds=Decimal("4.30"),
            away_odds=Decimal("6.00"),
            over_odds=Decimal("1.75"),
            under_odds=Decimal("2.10"),
            btts_yes_odds=Decimal("1.95"),
            btts_no_odds=Decimal("1.85"),
        )
        context = context_from_odds(odds, is_home=True, fpl_difficulty=3)

        self.assertIsNotNone(context)
        defender = adjustment_for_context(2, context)
        forward = adjustment_for_context(4, context)
        self.assertGreaterEqual(defender.multiplier, 0.82)
        self.assertLessEqual(defender.multiplier, 1.18)
        self.assertGreaterEqual(forward.multiplier, 0.82)
        self.assertLessEqual(forward.multiplier, 1.18)
        self.assertNotEqual(defender.market_ease, forward.market_ease)

    def test_no_adjustment_leaves_points_unchanged(self) -> None:
        self.assertEqual(calibrate_points(6.25, None), 6.25)

    def test_probability_blend_uses_bounded_market_weight(self) -> None:
        self.assertAlmostEqual(calibrate_probability(0.40, 0.60), 0.47)
        self.assertEqual(calibrate_probability(None, 1.2), 1.0)
