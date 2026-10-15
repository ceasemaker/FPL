from __future__ import annotations

import pandas as pd
from django.test import TestCase

from ..forecast.features import _usage_context
from ..models import PlayerSeasonStat, TeamSeasonStat
from ..services.usage import player_usage


def sheet(opta_id, team_id, minutes, lost, shots, created, goals=0, assists=0):
    return PlayerSeasonStat.objects.create(
        source="sdp", competition_id=8, season=2024, opta_player_id=str(opta_id), name=f"P{opta_id}",
        position="Midfielder", season_team_id=str(team_id), season_team_name=f"Club {team_id}",
        current_team_name="Elsewhere",
        stats={"timePlayed": minutes, "totalLossesOfPossession": lost, "totalShots": shots,
               "keyPassesAttemptAssists": created, "goals": goals, "goalAssists": assists},
    )


class UsageRateTests(TestCase):
    def test_usage_is_share_of_team_actions_while_on_the_pitch(self):
        # Two players at one club, each 990 minutes (11 full matches of team time
        # in total = 1,980 player-minutes / 11 = 180 team minutes).
        sheet(1, 9, 990, 90, 30, 20)   # 120 actions
        sheet(2, 9, 990, 30, 10, 5)    # 40 actions
        TeamSeasonStat.objects.create(competition_id=8, season=2024, opta_team_id="9", name="Club 9",
                                      stats={"possessionPercentage": 40})
        rows = {p["id"]: p for p in player_usage(2024)}
        # usage = 100 * 120 * (1980 / 11) / (990 * 160) = 13.64
        self.assertAlmostEqual(rows["1"]["usage"], 13.64, places=2)
        self.assertAlmostEqual(rows["2"]["usage"], 4.55, places=2)
        self.assertEqual(rows["1"]["pea"], 120)
        self.assertEqual(rows["1"]["team"], "Club 9", "the season's club, not today's")
        self.assertEqual(rows["1"]["teamPossession"], 40)

    def test_unknown_season_club_gives_no_usage(self):
        sheet(3, "", 900, 50, 10, 5)
        self.assertIsNone(player_usage(2024)[0]["usage"])


class UsageFeatureTests(TestCase):
    def test_context_uses_last_season_and_flags_a_move(self):
        targets = pd.DataFrame([
            {"season": 2025, "gameweek": 1, "code": 1, "team_code": 50},
            {"season": 2025, "gameweek": 1, "code": 2, "team_code": 50},
            {"season": 2025, "gameweek": 1, "code": 3, "team_code": 60},
        ])
        players = pd.DataFrame([
            {"season": 2024, "gameweek": 38, "code": 1, "team_code": 70, "minutes": 90},
            {"season": 2024, "gameweek": 38, "code": 2, "team_code": 50, "minutes": 90},
            {"season": 2024, "gameweek": 38, "code": 3, "team_code": 60, "minutes": 90},
        ])
        usage = pd.DataFrame([
            {"season": 2024, "code": 1, "usage": 25.0, "pea90": 20, "created90": 2, "create_per_pea": 0.1,
             "box90": 5, "team_possession": 45, "usage_minutes": 3000},
            {"season": 2024, "code": 2, "usage": 18.0, "pea90": 15, "created90": 1, "create_per_pea": 0.07,
             "box90": 2, "team_possession": 55, "usage_minutes": 3000},
        ])
        out = _usage_context(targets, players, usage).set_index("code")
        self.assertEqual(out.loc[1, "prev_usage"], 25.0)
        self.assertEqual(out.loc[1, "moved_club"], 1.0)
        self.assertEqual(out.loc[2, "moved_club"], 0.0)
        # Player 1 arrives at a club whose top returning user is player 2 (18%).
        self.assertEqual(out.loc[1, "team_top_usage"], 18.0)
        # Player 2's top teammate is the newcomer (25%).
        self.assertEqual(out.loc[2, "team_top_usage"], 25.0)
        self.assertTrue(pd.isna(out.loc[3, "prev_usage"]))
