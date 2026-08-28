from __future__ import annotations

import unittest

from live_team_analysis import Player, infer_selling_price, lineup_for_week


def player(player_id: int, position: int, mean: float, ownership: float = 0.1) -> Player:
    return Player(
        player_id=player_id,
        name=f"P{player_id}",
        team=(player_id % 8) + 1,
        position=position,
        price=50,
        ownership=ownership,
        status="a",
        chance=1.0,
        predictions={2: mean},
        variances={2: 9.0},
    )


class LiveTeamAnalysisTests(unittest.TestCase):
    def test_selling_price_uses_half_profit_rounded_down(self) -> None:
        self.assertEqual(infer_selling_price(50, 53), 51)
        self.assertEqual(infer_selling_price(50, 49), 49)

    def test_balanced_lineup_is_legal_and_captains_highest_mean(self) -> None:
        positions = [1, 1] + [2] * 5 + [3] * 5 + [4] * 3
        players = {
            index: player(index, position, mean=float(index))
            for index, position in enumerate(positions, start=1)
        }
        result = lineup_for_week(list(players), players, 2, "balanced")
        self.assertEqual(len(result["starters"]), 11)
        self.assertEqual(result["captain"], max(result["starters"], key=lambda pid: players[pid].predictions[2]))
        starting_positions = [players[player_id].position for player_id in result["starters"]]
        self.assertEqual(starting_positions.count(1), 1)
        self.assertGreaterEqual(starting_positions.count(2), 3)
        self.assertGreaterEqual(starting_positions.count(3), 2)
        self.assertGreaterEqual(starting_positions.count(4), 1)

    def test_protect_mode_prefers_high_ownership_on_equal_mean(self) -> None:
        positions = [1, 1] + [2] * 5 + [3] * 5 + [4] * 3
        players = {
            index: player(index, position, mean=4.0, ownership=0.1)
            for index, position in enumerate(positions, start=1)
        }
        high_ownership_midfielder = 8
        players[high_ownership_midfielder] = player(
            high_ownership_midfielder,
            3,
            mean=4.0,
            ownership=1.5,
        )
        result = lineup_for_week(list(players), players, 2, "protect")
        self.assertEqual(result["captain"], high_ownership_midfielder)


if __name__ == "__main__":
    unittest.main()
