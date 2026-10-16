from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase

from ..models import MatchGoal, PlayerSeasonStat, PlMatch
from ..services import clutch
from ..services.holdup import holdup_players
from ..services.match_goals import goals_from_events


def goal(time, period, player, kind="Goal", stamp="", assist=None):
    return {"time": str(time), "period": period, "playerId": player, "goalType": kind,
            "timestamp": stamp, "assistPlayerId": assist}


class GoalOrderTests(TestCase):
    def test_goals_are_ordered_and_stoppage_time_is_folded_in(self):
        events = {
            "homeTeam": {"id": "1", "goals": [goal(47, "FirstHalf", "10", stamp="T2"), goal(94, "SecondHalf", "11", "Penalty", "T4")]},
            "awayTeam": {"id": "2", "goals": [goal(12, "FirstHalf", "20", stamp="T1"), goal(60, "SecondHalf", "99", "Own", "T3")]},
        }
        goals = goals_from_events(events)
        self.assertEqual([(g["player_id"], g["minute"], g["home_after"], g["away_after"]) for g in goals],
                         [("20", 12, 0, 1), ("10", 45, 1, 1), ("99", 60, 1, 2), ("11", 90, 2, 2)])
        self.assertEqual(goals[2]["team_id"], "2", "an own goal counts for the team it helped")


class ClutchTests(TestCase):
    def setUp(self):
        cache.clear()

    def _match(self, n, home, away, goals):
        match = PlMatch.objects.create(season=2024, match_id=str(n), home_team_id="1", away_team_id="2",
                                       home_score=home, away_score=away, goals_synced=True)
        h = a = 0
        for order, (minute, is_home, player) in enumerate(goals, start=1):
            h, a = h + is_home, a + (not is_home)
            MatchGoal.objects.create(match=match, order=order, team_id="1" if is_home else "2", is_home=is_home,
                                     minute=minute, goal_type="Goal", player_id=player, home_after=h, away_after=a)

    def test_late_winner_is_worth_more_than_padding_a_lead(self):
        # Goalless draws, late 1-0 home wins (player 8), and routs whose 85th-minute
        # fourth goal is player 9's.
        for n in range(40):
            self._match(n, 0, 0, [])
        for n in range(40, 80):
            self._match(n, 1, 0, [(85, True, "8")])
        for n in range(80, 120):
            self._match(n, 4, 0, [(10, True, "7"), (20, True, "7"), (30, True, "7"), (85, True, "9")])
        probs = clutch.win_probability_table()["probs"]
        players = {p["id"]: p for p in clutch.clutch_players(2024, probs)}
        self.assertGreater(players["8"]["pointsWon"] / 40, 0.5)
        self.assertAlmostEqual(players["9"]["pointsWon"], 0.0, places=6)
        self.assertEqual(players["8"]["decisive"], 40)
        self.assertEqual(players["8"]["lateDecisive"], 40)
        self.assertEqual(players["9"]["decisive"], 0)
        for p in players.values():
            self.assertGreaterEqual(p["pointsWon"], 0)

    def test_expected_points_rise_with_the_lead(self):
        for n in range(30):
            self._match(n, 1, 0, [(50, True, "1")])
        for n in range(30, 60):
            self._match(n, 0, 0, [])
        probs = clutch.win_probability_table()["probs"]
        self.assertGreater(clutch.expected_points(probs, 60, 1, True), clutch.expected_points(probs, 60, 0, True))


class HoldupTests(TestCase):
    def test_missing_sdp_stats_count_as_zero(self):
        PlayerSeasonStat.objects.create(
            source="sdp", competition_id=8, season=2024, opta_player_id="5", name="Striker", position="Forward",
            season_team_id="9", season_team_name="Club 9",
            stats={"timePlayed": 1800, "successfulLayoffs": 30, "aerialDuelsWon": 50},
        )
        row = holdup_players(2024)[0]
        self.assertEqual((row["layoffs_won"], row["layoffs_lost"], row["fouls_won"]), (30, 0, 0))
        self.assertEqual(row["aerials_won"], 50)
