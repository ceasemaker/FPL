from __future__ import annotations

from django.test import TestCase

from ..models import PlMatch
from ..services.match_details import compact_sheet, parse_events, parse_lineups, parse_momentum, parse_team_stats

LINEUPS = {
    "home_team": {"teamId": "14", "formation": {"formation": "4-3-3", "lineup": [["1"], ["2", "3"]], "subs": ["9"]},
                  "players": [{"id": "1", "firstName": "Ali", "lastName": "Keeper", "shirtNum": "1", "isCaptain": False, "position": "Goalkeeper"},
                              {"id": "2", "firstName": "Bo", "lastName": "Back", "shirtNum": "4", "isCaptain": True, "position": "Defender"},
                              {"id": "3", "firstName": "Cy", "lastName": "Red", "shirtNum": "5", "position": "Defender"},
                              {"id": "9", "firstName": "Di", "lastName": "Sub", "knownName": "Dimi", "shirtNum": "20", "position": "Forward"}]},
    "away_team": {"teamId": "43", "formation": {"formation": "4-4-2", "lineup": [["50"]], "subs": []},
                  "players": [{"id": "50", "firstName": "Ed", "lastName": "Away", "shirtNum": "1", "position": "Goalkeeper"}]},
}
FEED = {"liveData": {
    "lineUp": [{"player": [{"opPlayerId": "2", "position": "Defender", "positionSide": "Left", "formationPlace": "3"}]}],
    "substitute": [{"opContestantId": "14", "periodId": 2, "timeMin": 70, "opPlayerOnId": "9", "playerOnName": "Dimi",
                    "opPlayerOffId": "2", "playerOffName": "B. Back", "subReason": "Tactical", "timestamp": "T3"}],
    "card": [{"opContestantId": "14", "periodId": 2, "timeMin": 62, "type": "Y2C", "opPlayerId": "3", "playerName": "C. Red",
              "cardReason": "Foul", "timestamp": "T2"},
             {"opContestantId": "43", "periodId": 1, "timeMin": 8, "type": "YC", "opPlayerId": "50", "playerName": "E. Away",
              "cardReason": "Dissent", "timestamp": "T1"}],
    "VAR": [{"opContestantId": "43", "periodId": 2, "timeMin": 80, "type": "Goal awarded", "outcome": "No goal",
             "opPlayerId": "50", "playerName": "E. Away", "timestamp": "T4"}],
    "predictions": [{"type": "Momentum", "periodId": 2, "timeMin": 46, "prediction": [{"type": "Home", "probability": "0.02"}, {"type": "Away", "probability": "0.01"}]},
                    {"type": "Momentum", "periodId": 1, "timeMin": 1, "prediction": [{"type": "Home", "probability": "0.001"}, {"type": "Away", "probability": "0.002"}]}],
}}


class MatchDetailParsingTests(TestCase):
    def setUp(self):
        self.match = PlMatch(season=2026, match_id="1", home_team_id="14", away_team_id="43")

    def test_lineups_place_starters_and_track_minutes_on_and_off(self):
        rows = {r["player_id"]: r for r in parse_lineups(LINEUPS, FEED, self.match)}
        self.assertEqual((rows["1"]["formation_row"], rows["2"]["formation_row"], rows["3"]["formation_col"]), (0, 1, 1))
        self.assertTrue(rows["2"]["captain"])
        self.assertEqual((rows["2"]["position_side"], rows["2"]["formation_place"], rows["2"]["minute_off"]), ("Left", 3, 70))
        self.assertEqual(rows["3"]["minute_off"], 62, "sent off counts as coming off")
        self.assertFalse(rows["9"]["starter"])
        self.assertEqual((rows["9"]["name"], rows["9"]["minute_on"]), ("Dimi", 70))
        self.assertEqual(rows["50"]["team_id"], "43")

    def test_events_in_match_order_with_reasons(self):
        events = parse_events(FEED)
        self.assertEqual([(e["minute"], e["kind"], e["detail"]) for e in events],
                         [(8, "yellow", "Dissent"), (62, "second_yellow", "Foul"), (70, "sub", "Tactical"), (80, "var", "Goal awarded: No goal")])
        self.assertEqual(events[2]["other_player_id"], "2")

    def test_momentum_sorted_by_period_and_minute(self):
        self.assertEqual(parse_momentum(FEED), [[1, 1, 0.001, 0.002], [2, 46, 0.02, 0.01]])

    def test_team_stats_by_side_with_formation(self):
        rows = parse_team_stats([{"side": "Away", "stats": {"expectedGoals": 1.2}}, {"side": "Home", "stats": {"expectedGoals": 0.4}}],
                                LINEUPS, self.match)
        self.assertEqual([(r["team_id"], r["is_home"], r["formation"], r["stats"]["expectedGoals"]) for r in rows],
                         [("43", False, "4-4-2", 1.2), ("14", True, "4-3-3", 0.4)])

    def test_sheets_drop_zeros(self):
        self.assertEqual(compact_sheet({"touches": 31.0, "winning_goal": 0.0, "goals": 0}), {"touches": 31.0})
