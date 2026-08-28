import unittest

from run_odds_backtest import no_vig_probabilities, normalize_team


class OddsBacktestTests(unittest.TestCase):
    def test_no_vig_probabilities_sum_to_one(self):
        probabilities = no_vig_probabilities(2.0, 3.5, 4.0)
        self.assertAlmostEqual(sum(probabilities), 1.0)
        self.assertGreater(probabilities[0], probabilities[2])

    def test_team_aliases_match_sources(self):
        self.assertEqual(normalize_team("Tottenham"), normalize_team("Spurs"))
        self.assertEqual(normalize_team("Sheffield Utd"), normalize_team("Sheff Utd"))
        self.assertEqual(normalize_team("Man United"), normalize_team("Man Utd"))


if __name__ == "__main__":
    unittest.main()
